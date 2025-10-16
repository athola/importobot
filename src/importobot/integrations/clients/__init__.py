"""HTTP clients for ingesting test suites from platform APIs."""

from __future__ import annotations

import base64
import logging
import time
from collections.abc import Callable, Iterator
from enum import Enum
from typing import Any, ClassVar, Protocol
from urllib.parse import parse_qs, urlparse

import requests

from importobot.medallion.interfaces.enums import SupportedFormat

logger = logging.getLogger(__name__)


ProgressCallback = Callable[..., None]


class APISource(Protocol):
    """Protocol for platform-specific API clients."""

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Yield paginated payloads while reporting progress."""


class BaseAPIClient:
    """Shared functionality for API clients."""

    _max_retries = 3

    def __init__(
        self,
        *,
        api_url: str,
        tokens: list[str],
        user: str | None,
        project_name: str | None,
        project_id: int | None,
        max_concurrency: int | None,
    ) -> None:
        """Initialize BaseAPIClient with API connection parameters."""
        self.api_url = api_url
        self.tokens = tokens
        self.user = user
        self.project_name = project_name
        self.project_id = project_id
        self.max_concurrency = max_concurrency
        self._session = requests.Session()
        headers = getattr(self._session, "headers", None)
        if headers and hasattr(headers, "update"):
            headers.clear()
            headers.update(
                {
                    "User-Agent": "curl/7.68.0",
                    "Accept": "application/json",
                }
            )

    def _auth_headers(self) -> dict[str, str]:
        """Return default authorization headers."""
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens[0]}"
        return headers

    def _compute_retry_delay(self, response: requests.Response, attempt: int) -> float:
        """Determine retry delay using Retry-After header or exponential backoff."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                value = float(retry_after)
                if value >= 0:
                    return value
            except ValueError:
                logger.debug("Invalid Retry-After header %s", retry_after)
        return float(min(2**attempt, 30))

    def _sleep(self, seconds: float) -> None:
        """Sleep helper to aid testing."""
        time.sleep(seconds)

    def _project_value(self) -> str | int | None:
        """Return preferred project identifier."""
        if self.project_name:
            return self.project_name
        if self.project_id is not None:
            return str(self.project_id)
        return None

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Perform HTTP request with basic retry semantics."""
        headers = headers or {}
        attempt = 0
        while attempt <= self._max_retries:
            response = self._dispatch_request(
                method, url, params=params, headers=headers, json=json
            )
            if response.status_code == 429 and attempt < self._max_retries:
                delay = self._compute_retry_delay(response, attempt)
                logger.info(
                    "Rate limited by %s (attempt %s/%s); retrying in %.2fs",
                    url,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                self._sleep(delay)
                attempt += 1
                continue

            response.raise_for_status()
            return response

        raise RuntimeError(f"Exceeded retry budget for {url}")

    def _dispatch_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None,
        headers: dict[str, str],
        json: dict[str, Any] | None,
    ) -> requests.Response:
        """Dispatch HTTP request to the underlying session."""
        if method.upper() == "GET":
            return self._session.get(url, params=params or {}, headers=headers)
        if method.upper() == "POST":
            try:
                return self._session.post(url, json=json or {}, headers=headers)
            except TypeError:
                return self._session.post(url, json=json or {})
        raise ValueError(f"Unsupported HTTP method '{method}'")


class JiraXrayClient(BaseAPIClient):
    """Client for Jira/Xray issue search."""

    __test__ = False
    _page_size = 200

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Fetch all issues from Jira/Xray API with pagination."""
        start_at = 0
        total: int | None = None
        while True:
            params: dict[str, Any] = {
                "startAt": start_at,
                "maxResults": self._page_size,
            }
            project_ref = self._project_value()
            if project_ref is not None:
                params["jql"] = f"project={project_ref}"

            response = self._request(
                "GET", self.api_url, params=params, headers=self._auth_headers()
            )
            payload = response.json()
            issues = payload.get("issues", [])
            total = payload.get("total", total)
            progress_cb(
                items=len(issues),
                total=total,
                page=(start_at // self._page_size) + 1,
            )
            yield payload

            start_at = payload.get("startAt", start_at) + len(issues)
            if total is not None and start_at >= total:
                break
            if not issues:
                break


class ZephyrClient(BaseAPIClient):
    """
    Flexible Zephyr client that adapts to different server configurations.

    Supports multiple API patterns, authentication methods, and pagination strategies.
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
            "disable_ssl_verify": True,
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
        super().__init__(**kwargs)
        self._discovered_pattern: dict[str, Any] | None = None
        self._working_auth_strategy: dict[str, Any] | None = None
        self._effective_page_size: int = self.DEFAULT_PAGE_SIZES[0]
        parsed = urlparse(self.api_url)
        if parsed.netloc:
            self._base_root = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self._base_root = self.api_url

    def _build_pattern_url(self, path: str) -> str:
        """Construct a usable URL for a pattern path regardless of provided base."""
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
        """Determine whether the API pattern accepts a separate projectKey param."""
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
        """Build a test request for discovery and page-size detection."""
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
        """Remove None-valued entries to avoid sending ambiguous parameters."""
        return {key: value for key, value in params.items() if value is not None}

    @staticmethod
    def _extract_results(payload: Any) -> list[dict[str, Any]]:
        """Normalise payloads into a list of result dictionaries.

        Supports various Zephyr endpoint response structures:
        - Standard: {"results": [...]}
        - Alternative: {"data": [...]}
        - Direct list: [...]
        - Nested: {"testCases": [...]} or {"cases": [...]}
        - Wrapped: {"value": {"results": [...]}}
        - Legacy: {"items": [...]}
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
        """Get total from a dictionary."""
        for key in ["total", "totalCount", "count", "size", "length"]:
            total = payload.get(key)
            if isinstance(total, int):
                return total
        return None

    @staticmethod
    def _get_total_from_nested_dict(
        payload: dict[str, Any], parent_keys: list[str]
    ) -> int | None:
        """Get total from a nested dictionary."""
        for parent_key in parent_keys:
            nested_dict = payload.get(parent_key)
            if isinstance(nested_dict, dict):
                total = ZephyrClient._get_total_from_dict(nested_dict)
                if total is not None:
                    return total
        return None

    @staticmethod
    def _extract_total(payload: Any, default_value: int | None = None) -> int | None:
        """Retrieve total count from payload where available."""
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
        """
        Fetch test cases using discovered API pattern and authentication.

        Automatically adapts to server capabilities and configuration.
        """
        if not self._discover_working_configuration():
            raise RuntimeError("Unable to establish working connection to Zephyr API")

        # Use the discovered pattern to fetch data
        requires_keys_stage = (
            self._discovered_pattern and self._discovered_pattern["requires_keys_stage"]
        )
        if requires_keys_stage:
            yield from self._fetch_with_keys_stage(progress_cb)
        else:
            yield from self._fetch_direct_search(progress_cb)

    def _discover_working_configuration(self) -> bool:
        """
        Discover working API pattern and authentication strategy by trying.

        Different combinations until one succeeds.
        """
        if self._discovered_pattern and self._working_auth_strategy:
            return True

        project_ref = self._project_value()

        # Try each API pattern
        for pattern in self.API_PATTERNS:
            if pattern.get("requires_keys_stage") and not project_ref:
                logger.debug(
                    "Skipping API pattern %s because no project reference was supplied",
                    pattern["name"],
                )
                continue

            logger.debug("Trying API pattern: %s", pattern["name"])

            # Try each authentication strategy
            for auth_strategy in self.AUTH_STRATEGIES:
                logger.debug("Trying auth strategy: %s", auth_strategy["type"])

                fields = "key" if pattern["supports_field_selection"] else None

                if self._test_api_connection(
                    pattern,
                    auth_strategy,
                    project_ref,
                    fields=fields,
                ):
                    self._discovered_pattern = pattern
                    self._working_auth_strategy = auth_strategy
                    self._detect_optimal_page_size(pattern, auth_strategy, project_ref)

                    logger.info(
                        "Discovered working configuration: API pattern=%s, Auth=%s, "
                        "Page size=%d",
                        pattern["name"],
                        str(auth_strategy["type"]),
                        self._effective_page_size,
                    )
                    return True

        logger.error("Failed to discover working Zephyr API configuration")
        return False

    def _test_api_connection(
        self,
        pattern: dict[str, Any],
        auth_strategy: dict[str, Any],
        project_ref: str | int | None,
        *,
        fields: str | None,
    ) -> bool:
        """Test if a specific API pattern + auth strategy combination works."""
        try:
            headers = self._build_auth_headers(auth_strategy)
            test_url, params = self._build_probe_request(
                pattern,
                project_ref,
                page_size=1,
                fields=fields,
            )
            params = self._clean_params(params)

            # Check if SSL verification should be disabled for this pattern
            verify = not pattern.get("disable_ssl_verify", False)

            response = self._session.get(
                test_url, params=params, headers=headers, timeout=10, verify=verify
            )

            request_url = response.request.url
            request_headers = response.request.headers
            logger.debug(
                "Probe: status=%s url=%s hdr=%s resp_hdr=%s verify=%s",
                response.status_code,
                request_url,
                request_headers,
                response.headers,
                verify,
            )

            if response.status_code == 200:
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
        """Detect optimal page size by trying different values."""
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

                # Check if SSL verification should be disabled for this pattern
                verify = not pattern.get("disable_ssl_verify", False)

                response = self._session.get(
                    test_url, params=params, headers=headers, timeout=10, verify=verify
                )

                if response.status_code == 200:
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
        """Build authentication headers based on strategy."""
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
        """Fetch using two-stage pattern: get keys first, then details."""
        if not self._discovered_pattern:
            return

        # Stage 1: Get all test case keys
        all_keys = self._fetch_all_keys(progress_cb)
        if not all_keys:
            logger.warning("No test case keys found")
            return

        # Stage 2: Fetch details in batches
        total_keys = len(all_keys)
        processed_keys = 0

        for batch_start in range(0, total_keys, self._effective_page_size):
            batch_start_size = batch_start + self._effective_page_size
            batch_keys = all_keys[batch_start:batch_start_size]
            batch_details = self._fetch_details_for_keys(batch_keys, progress_cb)

            if batch_details:
                processed_keys += len(batch_details)
                progress_cb(
                    items=len(batch_details),
                    total=total_keys,
                    page=(batch_start // self._effective_page_size) + 1,
                )
                yield {"results": batch_details, "total": total_keys}

    def _fetch_direct_search(
        self, progress_cb: ProgressCallback
    ) -> Iterator[dict[str, Any]]:
        """Fetch directly using search endpoint with pagination."""
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
                # Check if SSL verification should be disabled for this pattern
                verify = not self._discovered_pattern.get("disable_ssl_verify", False)

                response = self._session.get(
                    search_url,
                    params=self._clean_params(params),
                    headers=headers,
                    verify=verify,
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

    def _fetch_all_keys(self, progress_cb: ProgressCallback) -> list[str]:
        """Fetch all test case keys using the two-stage approach."""
        if not self._discovered_pattern:
            return []

        all_keys = []
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
                # Check if SSL verification should be disabled for this pattern
                verify = not self._discovered_pattern.get("disable_ssl_verify", False)

                response = self._session.get(
                    keys_url,
                    params=self._clean_params(params),
                    headers=headers,
                    verify=verify,
                )
                response.raise_for_status()
                payload = response.json()

                results = self._extract_results(payload)
                if not results:
                    break

                batch_keys = [result["key"] for result in results if "key" in result]
                if not batch_keys:
                    break
                all_keys.extend(batch_keys)

                progress_cb(
                    items=len(batch_keys),
                    total=None,
                    page=offset // self._effective_page_size + 1,
                )

                offset += len(batch_keys)

                # Check if we have more items
                if len(results) < self._effective_page_size:
                    break

            except Exception as e:
                logger.error("Failed to fetch keys batch: %s", e)
                break

        return all_keys

    def _fetch_details_for_keys(
        self, keys: list[str], _progress_cb: ProgressCallback
    ) -> list[dict[str, Any]]:
        """Fetch detailed information for a specific batch of keys."""
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
            # Check if SSL verification should be disabled for this pattern
            verify = not self._discovered_pattern.get("disable_ssl_verify", False)

            response = self._session.get(
                details_url,
                params=self._clean_params(params),
                headers=headers,
                verify=verify,
            )
            response.raise_for_status()
            payload = response.json()
            return self._extract_results(payload) or []

        except Exception as e:
            logger.error("Failed to fetch details for keys batch: %s", e)
            return []


class TestRailClient(BaseAPIClient):
    """Client for TestRail API pagination."""

    __test__ = False

    def __init__(self, **kwargs: Any) -> None:
        """Initialize TestRailClient with API connection parameters."""
        super().__init__(**kwargs)
        if self.user and self.tokens:
            self._session.auth = (self.user, self.tokens[0])

    def _auth_headers(self) -> dict[str, str]:
        """Override to rely on requests' built-in Basic auth handling."""
        return {}

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Fetch all test runs from TestRail API with pagination."""
        offset = 0
        page = 1
        while True:
            params = {"offset": offset}
            response = self._request(
                "GET", self.api_url, params=params, headers=self._auth_headers()
            )
            payload = response.json()

            runs = payload.get("runs") or payload.get("cases") or []
            progress_cb(items=len(runs), total=None, page=page)
            yield payload

            next_link = payload.get("_links", {}).get("next")
            if not next_link:
                break

            parsed = urlparse(next_link)
            query = parse_qs(parsed.query)
            if "offset" in query:
                try:
                    offset = int(query["offset"][0])
                except (ValueError, TypeError, IndexError):
                    offset += len(runs)
            else:
                offset += len(runs)
            page += 1


class TestLinkClient(BaseAPIClient):
    """Client for TestLink XML-RPC JSON bridge endpoint."""

    __test__ = False

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Fetch all test suites from TestLink API with pagination."""
        next_cursor: str | None = None
        page = 1
        while True:
            payload = {
                "devKey": self.tokens[0] if self.tokens else "",
                "command": "fetchTestSuite",
                "project": self._project_value(),
            }
            if next_cursor:
                payload["next"] = next_cursor

            response = self._request(
                "POST",
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            body = response.json()
            data = body.get("data", [])
            progress_cb(items=len(data), total=body.get("total"), page=page)
            yield body

            next_cursor = body.get("next")
            if not next_cursor:
                break
            page += 1


def get_api_client(
    fetch_format: SupportedFormat,
    *,
    api_url: str,
    tokens: list[str],
    user: str | None,
    project_name: str | None,
    project_id: int | None,
    max_concurrency: int | None,
) -> APISource:
    """Create platform-specific API clients."""
    mapping = {
        SupportedFormat.JIRA_XRAY: JiraXrayClient,
        SupportedFormat.ZEPHYR: ZephyrClient,
        SupportedFormat.TESTRAIL: TestRailClient,
        SupportedFormat.TESTLINK: TestLinkClient,
    }
    if fetch_format not in mapping:
        raise ValueError(f"Unsupported fetch format {fetch_format}")
    client_cls = mapping[fetch_format]
    client: APISource = client_cls(
        api_url=api_url,
        tokens=tokens,
        user=user,
        project_name=project_name,
        project_id=project_id,
        max_concurrency=max_concurrency,
    )
    return client


__all__ = [
    "APISource",
    "BaseAPIClient",
    "JiraXrayClient",
    "TestLinkClient",
    "TestRailClient",
    "ZephyrClient",
    "get_api_client",
]
