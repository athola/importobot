"""Zephyr API client for retrieving test cases with adaptive API discovery."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from enum import Enum
from http import HTTPStatus
from typing import Any, ClassVar
from urllib.parse import urlparse

from importobot.integrations.clients.base import (
    BaseAPIClient,
    ProgressCallback,
    _KeyBatch,
)
from importobot.utils.logging import get_logger

logger = get_logger()


class ZephyrClient(BaseAPIClient):
    """
    Manage interactions with the Zephyr API to retrieve test cases.

    This client will automatically discover and adapt to different Zephyr API patterns,
    authentication methods, and pagination strategies.
    """

    __test__ = False

    # Configurable page sizes with auto-detection defaults
    DEFAULT_PAGE_SIZES: ClassVar[list[int]] = [100, 200, 250, 500]

    # Multiple API endpoint patterns to try
    API_PATTERNS: ClassVar[list[dict[str, Any]]] = [
        # Two-stage approach: keys from /rest/tests/1.0, details from /rest/atm/1.0
        {
            "name": "working_two_stage",
            "keys_search": "/rest/tests/1.0/testcase/search",
            "details_search": "/rest/atm/1.0/testcase/search",
            "requires_keys_stage": True,
            "supports_field_selection": True,
        },
        # Direct search approach - single endpoint for full test case data
        {
            "name": "direct_search",
            "testcase_search": "/rest/atm/1.0/testcase/search",
            "requires_keys_stage": False,
            "supports_field_selection": True,
        },
        {
            "name": "direct_search_rest_tests",
            "testcase_search": "/rest/tests/1.0/testcase/search",
            "requires_keys_stage": False,
            "supports_field_selection": True,
        },
        # Two-stage approach - keys first, then detailed test case information
        {
            "name": "two_stage_fetch",
            "keys_search": "/rest/tests/1.0/testcase/search",
            "details_search": "/rest/atm/1.0/testcase/search",
            "requires_keys_stage": True,
            "supports_field_selection": True,
        },
        {
            "name": "two_stage_rest_tests",
            "keys_search": "/rest/tests/1.0/testcase/search",
            "details_search": "/rest/tests/1.0/testcase/search",
            "requires_keys_stage": True,
            "supports_field_selection": True,
        },
        # Alternative Zephyr patterns
        {
            "name": "alternative",
            "testcase_search": "/rest/zephyr/latest/testcase",
            "requires_keys_stage": False,
            "supports_field_selection": False,
        },
    ]

    class AuthType(Enum):
        """Supported Zephyr authentication strategies."""

        BEARER = "bearer"
        API_KEY = "api_key"
        BASIC = "basic"
        DUAL_TOKEN = "dual_token"

    # Multiple authentication strategies
    AUTH_STRATEGIES: ClassVar[list[dict[str, Any]]] = [
        {"type": AuthType.BEARER, "header": "Authorization", "format": "Bearer {}"},
        {"type": AuthType.API_KEY, "header": "X-Atlassian-Token", "format": "no-check"},
        {"type": AuthType.BASIC, "use_session_auth": True},
        {"type": AuthType.DUAL_TOKEN, "headers": ["Authorization", "X-Authorization"]},
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize ZephyrClient with API connection parameters."""
        verify_ssl = kwargs.pop("verify_ssl", True)
        super().__init__(verify_ssl=verify_ssl, **kwargs)
        self._discovered_pattern: dict[str, Any] | None = None
        self._working_auth_strategy: dict[str, Any] | None = None
        self._effective_page_size: int = self.DEFAULT_PAGE_SIZES[0]
        parsed = urlparse(self.api_url)
        if parsed.netloc:
            self._base_root = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self._base_root = self.api_url

    def _build_pattern_url(self, path: str) -> str:
        """Build a URL for a given pattern path, ignoring the client's base URL."""
        if path.startswith("http://") or path.startswith("https://"):
            return path

        base = self.api_url.rstrip("/")
        if not base:
            return f"{self._base_root}{path}"

        if path.startswith("/"):
            return f"{self._base_root}{path}"

        return f"{base}/{path}"

    @staticmethod
    def _pattern_uses_project_param(pattern: dict[str, Any]) -> bool:
        """Determine if API pattern accepts separate `projectKey` parameter."""
        path = pattern.get("testcase_search") or pattern.get("keys_search") or ""
        return "rest/atm" in path

    def _build_probe_request(
        self,
        pattern: dict[str, Any],
        project_ref: str | int | None,
        *,
        page_size: int = 1,
        fields: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Construct a test request for API discovery and page-size detection."""
        if pattern["requires_keys_stage"]:
            if project_ref is None:
                return self._build_pattern_url(pattern["keys_search"]), {
                    "maxResults": page_size,
                    "fields": "key",
                }

            params: dict[str, Any] = {
                "query": f'testCase.projectKey IN ("{project_ref}")',
                "maxResults": page_size,
                "fields": "key",
            }
            return self._build_pattern_url(pattern["keys_search"]), params

        params = {
            "maxResults": page_size,
            "fields": fields,
        }
        if project_ref is not None:
            params["query"] = f'testCase.projectKey IN ("{project_ref}")'
            if self._pattern_uses_project_param(pattern):
                params.setdefault("projectKey", project_ref)

        return self._build_pattern_url(pattern["testcase_search"]), params

    @staticmethod
    def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
        """Remove `None` values from parameters to prevent sending ambiguous values."""
        return {key: value for key, value in params.items() if value is not None}

    @staticmethod
    def _extract_results(payload: Any) -> list[dict[str, Any]]:
        """Normalize payloads into a list of result dictionaries.

        Supports various Zephyr endpoint response structures, including:
        - Standard: `{"results": [...]}`
        - Alternative: `{"data": [...]}`
        - Direct list: `[...]`
        - Nested: `{"testCases": [...]}` or `{"cases": [...]}`
        - Wrapped: `{"value": {"results": [...]}}`
        - Legacy: `{"items": [...]}`
        """
        if isinstance(payload, list):
            return payload

        if not isinstance(payload, dict):
            return []

        # Try common result containers
        for key in ["results", "data", "testCases", "cases", "items", "values"]:
            results = payload.get(key)
            if isinstance(results, list):
                return results

        # Try nested structures (e.g., {"value": {"results": [...]}})
        for key in ["value", "response", "content"]:
            nested = payload.get(key)
            if isinstance(nested, dict):
                for nested_key in ["results", "data", "testCases", "cases", "items"]:
                    nested_results = nested.get(nested_key)
                    if isinstance(nested_results, list):
                        return nested_results

        # Try single item wrapped in dict
        if any(key in payload for key in ["key", "id", "name", "testScript"]):
            return [payload]

        return []

    @staticmethod
    def _get_total_from_dict(payload: dict[str, Any]) -> int | None:
        """Extract the total count from a dictionary."""
        for key in ["total", "totalCount", "count", "size", "length"]:
            total = payload.get(key)
            if isinstance(total, int):
                return total
        return None

    @staticmethod
    def _get_total_from_nested_dict(
        payload: dict[str, Any], parent_keys: list[str]
    ) -> int | None:
        """Extract the total count from a nested dictionary."""
        for parent_key in parent_keys:
            nested_dict = payload.get(parent_key)
            if isinstance(nested_dict, dict):
                total = ZephyrClient._get_total_from_dict(nested_dict)
                if total is not None:
                    return total
        return None

    @staticmethod
    def _extract_total(payload: Any, default_value: int | None = None) -> int | None:
        """Retrieve the total count from the payload if available."""
        if not isinstance(payload, dict):
            return default_value

        total = ZephyrClient._get_total_from_dict(payload)
        if total is not None:
            return total

        total = ZephyrClient._get_total_from_nested_dict(
            payload, ["pagination", "paging", "meta", "info"]
        )
        if total is not None:
            return total

        total = ZephyrClient._get_total_from_nested_dict(
            payload, ["value", "response", "content"]
        )
        if total is not None:
            return total

        return default_value

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Retrieve test cases using auto-discovered API pattern and authentication."""
        if not self._discover_working_configuration():
            raise RuntimeError("Unable to establish working connection to Zephyr API")

        # Use the discovered pattern to fetch data
        requires_keys_stage = (
            self._discovered_pattern and self._discovered_pattern["requires_keys_stage"]
        )
        if requires_keys_stage:
            yield from self._fetch_with_keys_stage(progress_cb)
            return

        yield from self._fetch_direct_search(progress_cb)

    def _discover_working_configuration(self) -> bool:
        """Discover working API pattern and authentication strategy.

        Try different combinations iteratively until a successful one is found.
        """
        if self._discovered_pattern and self._working_auth_strategy:
            return True

        project_ref = self._project_value()

        for pattern in self._candidate_patterns(project_ref):
            discovery = self._try_pattern(pattern, project_ref)
            if discovery is not None:
                auth_strategy = discovery
                self._discovered_pattern = pattern
                self._working_auth_strategy = auth_strategy
                self._detect_optimal_page_size(pattern, auth_strategy, project_ref)

                logger.info(
                    (
                        "Discovered working configuration: API pattern=%s, Auth=%s, "
                        "Page size=%d"
                    ),
                    pattern["name"],
                    str(auth_strategy["type"]),
                    self._effective_page_size,
                )
                return True

        logger.error("Failed to discover working Zephyr API configuration")
        return False

    def _candidate_patterns(
        self, project_ref: str | int | None
    ) -> Iterator[dict[str, Any]]:
        """Yield candidate API patterns for discovery.

        Logs debug messages for patterns being attempted or skipped.
        """
        for pattern in self.API_PATTERNS:
            if pattern.get("requires_keys_stage") and not project_ref:
                logger.debug(
                    "Skipping API pattern %s because no project reference was supplied",
                    pattern["name"],
                )
                continue
            logger.debug("Trying API pattern: %s", pattern["name"])
            yield pattern

    def _try_pattern(
        self, pattern: dict[str, Any], project_ref: str | int | None
    ) -> dict[str, Any] | None:
        """Attempt to find a working authentication strategy for a given API pattern.

        Logs debug messages for authentication strategies being attempted.
        """
        fields = "key" if pattern["supports_field_selection"] else None

        for auth_strategy in self.AUTH_STRATEGIES:
            logger.debug("Trying auth strategy: %s", auth_strategy["type"])
            if self._test_api_connection(
                pattern,
                auth_strategy,
                project_ref,
                fields=fields,
            ):
                return auth_strategy
        return None

    def _test_api_connection(
        self,
        pattern: dict[str, Any],
        auth_strategy: dict[str, Any],
        project_ref: str | int | None,
        *,
        fields: str | None,
    ) -> bool:
        """Test if an API pattern and auth strategy combination is functional."""
        try:
            headers = self._build_auth_headers(auth_strategy)
            test_url, params = self._build_probe_request(
                pattern,
                project_ref,
                page_size=1,
                fields=fields,
            )
            params = self._clean_params(params)

            response = self._session.get(
                test_url,
                params=params,
                headers=headers,
                timeout=10,
                verify=self._verify_ssl,
            )

            request_url = response.request.url
            request_headers = response.request.headers
            logger.debug(
                "Probe: status=%s url=%s hdr=%s resp_hdr=%s verify=%s",
                response.status_code,
                request_url,
                request_headers,
                response.headers,
                self._verify_ssl,
            )

            if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                logger.warning(
                    (
                        "Authentication failed with status %s for pattern=%s using "
                        "auth=%s (url=%s)"
                    ),
                    response.status_code,
                    pattern["name"],
                    auth_strategy["type"].value,
                    request_url,
                )
                return False

            if response.status_code == HTTPStatus.OK:
                try:
                    data = response.json()
                except ValueError:
                    return False
                results = self._extract_results(data)
                # Check if we got a meaningful response
                if pattern["requires_keys_stage"] and results:
                    return True
                if not pattern["requires_keys_stage"] and results:
                    return True
                if (
                    not pattern["requires_keys_stage"]
                    and isinstance(data, dict)
                    and data
                ):
                    return True

        except Exception as e:
            logger.debug(
                "API pattern %s with auth %s failed: %s",
                pattern["name"],
                auth_strategy["type"].value,
                e,
            )

        return False

    def _detect_optimal_page_size(
        self,
        pattern: dict[str, Any],
        auth_strategy: dict[str, Any],
        project_ref: str | int | None,
    ) -> None:
        """Detect the optimal page size by iteratively testing different values."""
        for page_size in self.DEFAULT_PAGE_SIZES:
            try:
                headers = self._build_auth_headers(auth_strategy)

                test_url, params = self._build_probe_request(
                    pattern,
                    project_ref,
                    page_size=page_size,
                    fields="key" if pattern["supports_field_selection"] else None,
                )
                params = self._clean_params(params)

                response = self._session.get(
                    test_url,
                    params=params,
                    headers=headers,
                    timeout=10,
                    verify=self._verify_ssl,
                )

                if response.status_code == HTTPStatus.OK:
                    try:
                        response.json()
                    except ValueError:
                        continue
                    # Success! Use this page size
                    self._effective_page_size = page_size
                    logger.debug("Detected optimal page size: %d", page_size)
                    return

            except Exception as e:
                logger.debug("Page size %d failed: %s", page_size, e)
                continue

        # Default to smallest page size if probing fails
        self._effective_page_size = self.DEFAULT_PAGE_SIZES[0]
        logger.warning("Using default page size: %d", self._effective_page_size)

    def _build_auth_headers(
        self, auth_strategy: dict[str, Any] | None
    ) -> dict[str, str]:
        """Construct authentication headers based on the specified strategy."""
        self._session.auth = None
        headers: dict[str, str] = {}

        if not auth_strategy:
            return headers

        strategy_type = auth_strategy["type"]

        if strategy_type == self.AuthType.BEARER:
            if self.tokens:
                headers[auth_strategy["header"]] = auth_strategy["format"].format(
                    self.tokens[0]
                )

        elif strategy_type == self.AuthType.API_KEY:
            headers[auth_strategy["header"]] = auth_strategy["format"]

        elif strategy_type == self.AuthType.BASIC:
            if self.user and self.tokens:
                self._session.auth = (self.user, self.tokens[0])
                credentials = f"{self.user}:{self.tokens[0]}".encode()
                headers["Authorization"] = "Basic " + base64.b64encode(
                    credentials
                ).decode("ascii")

        elif strategy_type == self.AuthType.DUAL_TOKEN:
            if len(self.tokens) >= 1:
                headers["Authorization"] = f"Bearer {self.tokens[0]}"
            if len(self.tokens) >= 2:
                headers["X-Authorization"] = self.tokens[1]

        headers["Accept"] = "application/json"
        return headers

    def _fetch_with_keys_stage(
        self, progress_cb: ProgressCallback
    ) -> Iterator[dict[str, Any]]:
        """Retrieve data using two-stage pattern: first keys, then their details."""
        if not self._discovered_pattern:
            return

        total_keys: int | None = None
        processed_keys = 0
        saw_key_batch = False

        for key_batch in self._fetch_all_keys(progress_cb):
            if not key_batch.keys:
                continue
            saw_key_batch = True

            if key_batch.total is not None:
                total_keys = key_batch.total

            batch_details = self._fetch_details_for_keys(key_batch.keys, progress_cb)

            if batch_details:
                processed_keys += len(batch_details)
                progress_cb(
                    items=len(batch_details),
                    total=total_keys,
                    page=key_batch.page,
                )
                yield {
                    "results": batch_details,
                    "total": total_keys if total_keys is not None else processed_keys,
                }
        if not saw_key_batch:
            logger.warning("No test case keys found")
        elif processed_keys == 0:
            logger.warning("No test case details fetched for discovered keys")

    def _fetch_direct_search(
        self, progress_cb: ProgressCallback
    ) -> Iterator[dict[str, Any]]:
        """Retrieve data directly using the search endpoint with pagination."""
        if not self._discovered_pattern:
            return

        offset = 0
        page = 1

        while True:
            params: dict[str, Any] = {
                "maxResults": self._effective_page_size,
                "startAt": offset,
            }

            if (
                self._discovered_pattern
                and self._discovered_pattern["supports_field_selection"]
            ):
                params["fields"] = "key,name,status,testScript,customFields"

            project_ref = self._project_value()
            if project_ref:
                params["query"] = f'testCase.projectKey IN ("{project_ref}")'
                if self._pattern_uses_project_param(self._discovered_pattern):
                    params.setdefault("projectKey", str(project_ref))

            headers = self._build_auth_headers(self._working_auth_strategy)
            search_url = self._build_pattern_url(
                self._discovered_pattern["testcase_search"]
            )

            try:
                response = self._session.get(
                    search_url,
                    params=self._clean_params(params),
                    headers=headers,
                    verify=self._verify_ssl,
                )
                response.raise_for_status()
                payload = response.json()

                results = self._extract_results(payload)
                if not results:
                    break

                total = self._extract_total(payload, None)
                progress_cb(items=len(results), total=total, page=page)
                yield payload

                offset += len(results)
                page += 1

                # Stop if we've got all items
                if total is not None and offset >= total:
                    break

            except Exception as e:
                logger.error("Failed to fetch page %d: %s", page, e)
                break

    def _fetch_all_keys(self, progress_cb: ProgressCallback) -> Iterator[_KeyBatch]:
        """Yield key batches for two-stage approach without buffering all keys."""
        if not self._discovered_pattern:
            return

        offset = 0

        while True:
            params = {
                "query": f'testCase.projectKey IN ("{self._project_value()}")',
                "maxResults": self._effective_page_size,
                "fields": "key",
                "startAt": offset,
            }

            headers = self._build_auth_headers(self._working_auth_strategy)
            keys_url = self._build_pattern_url(self._discovered_pattern["keys_search"])

            try:
                response = self._session.get(
                    keys_url,
                    params=self._clean_params(params),
                    headers=headers,
                    verify=self._verify_ssl,
                )
                response.raise_for_status()
                payload = response.json()

                results = self._extract_results(payload)
                if not results:
                    return

                batch_keys = [result["key"] for result in results if "key" in result]
                if not batch_keys:
                    return

                total = self._extract_total(payload, None)
                page = offset // self._effective_page_size + 1

                progress_cb(items=len(batch_keys), total=total, page=page)
                yield _KeyBatch(batch_keys, total, page)

                offset += len(batch_keys)

                # Check if we have more items
                if len(results) < self._effective_page_size:
                    return

            except Exception as e:
                logger.error("Failed to fetch keys batch: %s", e)
                return

    def _fetch_details_for_keys(
        self, keys: list[str], _progress_cb: ProgressCallback
    ) -> list[dict[str, Any]]:
        """Retrieve detailed information for a specific batch of keys."""
        if not self._discovered_pattern or not keys:
            return []

        # Format keys for query: "KEY1", "KEY2", "KEY3"
        formatted_keys = ", ".join(f'"{key}"' for key in keys)

        params = {
            "query": f"key IN ({formatted_keys})",
            "maxResults": len(keys),  # Request exactly the number of keys we have
            "fields": "key,name,status,testScript,customFields",
        }

        headers = self._build_auth_headers(self._working_auth_strategy)
        details_url = self._build_pattern_url(
            self._discovered_pattern["details_search"]
        )

        try:
            response = self._session.get(
                details_url,
                params=self._clean_params(params),
                headers=headers,
                verify=self._verify_ssl,
            )
            response.raise_for_status()
            payload = response.json()
            return self._extract_results(payload) or []

        except Exception as e:
            logger.error("Failed to fetch details for keys batch: %s", e)
            return []


__all__ = ["ZephyrClient"]
