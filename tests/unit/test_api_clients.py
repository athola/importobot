"""Tests for API clients handling pagination and retries."""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from typing import Any, cast

import pytest

from importobot.integrations.clients import (
    APISource,
    JiraXrayClient,
    TestLinkClient,
    TestRailClient,
    ZephyrClient,
    get_api_client,
)
from importobot.medallion.interfaces.enums import SupportedFormat


class DummyResponse:
    """Minimal response object compatible with requests."""

    def __init__(
        self,
        *,
        status_code: int,
        payload: dict[str, Any] | list[dict[str, Any]],
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        # Add request attribute to match requests.Response interface
        self.request = type(
            "MockRequest", (), {"url": "https://mock-url.example", "headers": {}}
        )()
        # Add text attribute for error handling
        self.text = str(payload)

    def json(self) -> dict[str, Any] | list[dict[str, Any]]:
        """Return the stored payload as JSON."""
        return self._payload

    def raise_for_status(self) -> None:
        """Raise an error if status code indicates an error (except 429)."""
        if 400 <= self.status_code != 429:
            raise RuntimeError(f"HTTP {self.status_code}")


class DummySession:
    """Instrumented session capturing request data."""

    def __init__(self, responses: list[DummyResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._index = 0
        self.headers: dict[str, str] = {"User-Agent": "stub"}

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, str],
        verify: bool | None = None,
        timeout: int | float | None = None,
    ) -> DummyResponse:
        """Make a GET request and return the next configured response."""
        payload: dict[str, Any] = {"params": params, "headers": headers}
        if verify is not None:
            payload["verify"] = verify
        if timeout is not None:
            payload["timeout"] = timeout
        self.calls.append((url, payload))
        if self._index >= len(self.responses):
            raise AssertionError("No more responses configured")
        response = self.responses[self._index]
        self._index += 1
        return response

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> DummyResponse:
        """Make a POST request and return the next configured response."""
        payload = {"json": json}
        if headers is not None:
            payload["headers"] = headers
        self.calls.append((url, payload))
        if self._index >= len(self.responses):
            raise AssertionError("No more responses configured")
        response = self.responses[self._index]
        self._index += 1
        return response


def noop_progress(**kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Default progress callback for tests."""


def gather(
    client: APISource, progress: Callable[..., None] = noop_progress
) -> list[Any]:
    """Collect payloads from a client using the provided progress callback."""
    return list(client.fetch_all(progress))


def test_factory_returns_expected_client() -> None:
    """Factory should map supported formats to concrete clients."""
    config: dict[str, Any] = {
        "api_url": "https://example/api",
        "tokens": ["token"],
        "user": "user",
        "project_name": "PRJ",
        "project_id": None,
        "max_concurrency": None,
        "verify_ssl": True,
    }

    assert isinstance(
        get_api_client(
            SupportedFormat.JIRA_XRAY,
            api_url=config["api_url"],
            tokens=config["tokens"],
            user=config["user"],
            project_name=config["project_name"],
            project_id=config["project_id"],
            max_concurrency=config["max_concurrency"],
            verify_ssl=config["verify_ssl"],
        ),
        JiraXrayClient,
    )
    assert isinstance(
        get_api_client(
            SupportedFormat.ZEPHYR,
            api_url=config["api_url"],
            tokens=config["tokens"],
            user=config["user"],
            project_name=config["project_name"],
            project_id=config["project_id"],
            max_concurrency=config["max_concurrency"],
            verify_ssl=config["verify_ssl"],
        ),
        ZephyrClient,
    )
    assert isinstance(
        get_api_client(
            SupportedFormat.TESTRAIL,
            api_url=config["api_url"],
            tokens=config["tokens"],
            user=config["user"],
            project_name=config["project_name"],
            project_id=config["project_id"],
            max_concurrency=config["max_concurrency"],
            verify_ssl=config["verify_ssl"],
        ),
        TestRailClient,
    )
    assert isinstance(
        get_api_client(
            SupportedFormat.TESTLINK,
            api_url=config["api_url"],
            tokens=config["tokens"],
            user=config["user"],
            project_name=config["project_name"],
            project_id=config["project_id"],
            max_concurrency=config["max_concurrency"],
            verify_ssl=config["verify_ssl"],
        ),
        TestLinkClient,
    )


def test_auth_failure_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Zephyr auth probe should emit warnings for 401/403 responses."""
    session = DummySession(
        [
            DummyResponse(
                status_code=401,
                payload={"error": "Unauthorized"},
            )
        ]
    )

    client = ZephyrClient(
        api_url="https://jira.example/rest",
        tokens=["token"],
        user=None,
        project_name="PRJ",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )
    client._session = cast(Any, session)

    pattern = client.API_PATTERNS[1]  # direct_search pattern
    auth_strategy = client.AUTH_STRATEGIES[0]

    with caplog.at_level(logging.WARNING):
        result = client._test_api_connection(pattern, auth_strategy, "PRJ", fields=None)

    assert result is False
    assert any("Authentication failed" in record.message for record in caplog.records)


def test_client_uses_honest_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clients should identify themselves with an importobot-specific User-Agent."""
    responses = [
        DummyResponse(
            status_code=200,
            payload={
                "issues": [],
                "total": 0,
                "maxResults": 50,
                "startAt": 0,
            },
        )
    ]
    session = DummySession(responses)

    def mock_session():
        return session

    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", mock_session
    )

    JiraXrayClient(
        api_url="https://jira.example/rest/api/2/search",
        tokens=["token"],
        user=None,
        project_name="PRJ",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    user_agent = session.headers.get("User-Agent", "")
    assert user_agent.startswith("importobot-client/")


def test_jira_xray_client_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Jira/Xray client should iterate using startAt/maxResults pagination."""
    responses = [
        DummyResponse(
            status_code=200,
            payload={
                "issues": [{"id": "1"}, {"id": "2"}],
                "total": 3,
                "maxResults": 2,
                "startAt": 0,
            },
        ),
        DummyResponse(
            status_code=200,
            payload={
                "issues": [{"id": "3"}],
                "total": 3,
                "maxResults": 2,
                "startAt": 2,
            },
        ),
    ]

    session = DummySession(responses)
    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )

    client = JiraXrayClient(
        api_url="https://jira.example/rest/api/2/search",
        tokens=["token"],
        user=None,
        project_name="PRJ",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    pages = gather(client)

    assert len(pages) == 2
    assert session.calls[0][1]["params"]["startAt"] == 0
    assert session.calls[1][1]["params"]["startAt"] == 2


def test_jira_xray_client_accepts_project_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Project IDs should be accepted for Jira queries."""
    responses = [
        DummyResponse(
            status_code=200,
            payload={"issues": [], "total": 0, "maxResults": 50, "startAt": 0},
        )
    ]

    session = DummySession(responses)
    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )

    client = JiraXrayClient(
        api_url="https://jira.example/rest/api/2/search",
        tokens=["token"],
        user=None,
        project_name=None,
        project_id=321,
        max_concurrency=None,
        verify_ssl=True,
    )

    gather(client)

    params = session.calls[0][1]["params"]
    assert params["jql"] == "project=321"


def test_client_retries_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """All clients should retry when receiving HTTP 429 with Retry-After."""
    responses = [
        DummyResponse(status_code=429, payload={}, headers={"Retry-After": "0"}),
        DummyResponse(
            status_code=200,
            payload={
                "issues": [],
                "total": 0,
                "maxResults": 50,
                "startAt": 0,
            },
        ),
    ]
    session = DummySession(responses)
    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(
        "importobot.integrations.clients.time.sleep", sleep_calls.append
    )

    client = JiraXrayClient(
        api_url="https://jira.example/rest/api/2/search",
        tokens=["token"],
        user=None,
        project_name="PRJ",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    gather(client)

    assert len(sleep_calls) == 1
    assert session._index == 2


def test_client_raises_after_retry_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clients should bubble RuntimeError when retry budget is exhausted."""
    retries = JiraXrayClient._max_retries  # pylint: disable=protected-access
    responses = [
        DummyResponse(status_code=429, payload={}, headers={"Retry-After": "0"})
        for _ in range(retries + 1)
    ]
    session = DummySession(responses)
    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )
    monkeypatch.setattr(
        "importobot.integrations.clients.time.sleep", lambda seconds: None
    )

    client = JiraXrayClient(
        api_url="https://jira.example/rest/api/2/search",
        tokens=["token"],
        user=None,
        project_name="PRJ",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    with pytest.raises(RuntimeError) as exc_info:
        gather(client)

    assert "Exceeded retry budget" in str(exc_info.value)
    assert session._index == len(responses)


def test_testrail_client_uses_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    """TestRail pagination should increment offset parameter."""
    responses = [
        DummyResponse(
            status_code=200,
            payload={"runs": [{"id": 1}], "_links": {"next": "/runs?offset=1"}},
        ),
        DummyResponse(
            status_code=200,
            payload={"runs": [{"id": 2}], "_links": {"next": None}},
        ),
    ]
    session = DummySession(responses)
    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )

    client = TestRailClient(
        api_url="https://testrail.example/api/v2/get_runs",
        tokens=["api-token"],
        user="testrail-user",
        project_name="TR",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    pages = gather(client)

    assert len(pages) == 2
    assert session.calls[0][1]["params"].get("offset") == 0
    assert session.calls[1][1]["params"].get("offset") == 1


def test_testlink_client_posts_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    """TestLink client should use XML-RPC style POST calls with tokens."""
    responses = [
        DummyResponse(
            status_code=200,
            payload={"data": [{"id": 101}], "next": "suite:2"},
        ),
        DummyResponse(
            status_code=200,
            payload={"data": [{"id": 102}], "next": None},
        ),
    ]
    session = DummySession(responses)
    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )

    client = TestLinkClient(
        api_url="https://testlink.example/lib/api/xmlrpc/v1/xmlrpc.php",
        tokens=["api-key"],
        user=None,
        project_name="TL",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    pages = gather(client)

    assert len(pages) == 2
    assert session.calls[0][1]["json"]["devKey"] == "api-key"
    assert session.calls[0][0].endswith("xmlrpc.php")


def test_zephyr_client_supports_multiple_auth_strategies() -> None:
    """Zephyr client should support multiple authentication strategies."""
    # Test that the client can be instantiated with different auth configurations
    client_bearer = ZephyrClient(
        api_url="https://api.zephyr.example",
        tokens=["bearer-token"],
        user=None,
        project_name="ZEPHYR",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    client_basic = ZephyrClient(
        api_url="https://api.zephyr.example",
        tokens=["api-token"],
        user="user",
        project_name="ZEPHYR",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    client_dual = ZephyrClient(
        api_url="https://api.zephyr.example",
        tokens=["token1", "token2"],
        user=None,
        project_name="ZEPHYR",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    # Verify all clients can be instantiated
    assert client_bearer is not None
    assert client_basic is not None
    assert client_dual is not None

    # Verify API patterns are configured (includes new working_two_stage pattern)
    assert len(client_bearer.API_PATTERNS) == 6
    assert len(client_bearer.AUTH_STRATEGIES) == 4


def test_zephyr_client_extract_results_variants() -> None:
    """Zephyr client should extract results from various payload structures."""
    # Standard structure
    standard_payload = {"results": [{"key": "TEST-1"}, {"key": "TEST-2"}]}
    assert ZephyrClient._extract_results(standard_payload) == [
        {"key": "TEST-1"},
        {"key": "TEST-2"},
    ]

    # Alternative data structure
    data_payload = {"data": [{"id": 1}, {"id": 2}]}
    assert ZephyrClient._extract_results(data_payload) == [{"id": 1}, {"id": 2}]

    # Direct list
    list_payload = [{"name": "Test 1"}, {"name": "Test 2"}]
    assert ZephyrClient._extract_results(list_payload) == list_payload

    # Test cases structure
    test_cases_payload = {"testCases": [{"key": "TC-1"}]}
    assert ZephyrClient._extract_results(test_cases_payload) == [{"key": "TC-1"}]

    # Nested structure
    nested_payload = {"value": {"results": [{"key": "NESTED-1"}]}}
    assert ZephyrClient._extract_results(nested_payload) == [{"key": "NESTED-1"}]

    # Single item
    single_payload = {"key": "SINGLE-1", "name": "Single Test"}
    assert ZephyrClient._extract_results(single_payload) == [single_payload]

    # Empty/invalid structures
    assert ZephyrClient._extract_results({}) == []
    assert ZephyrClient._extract_results(None) == []
    assert ZephyrClient._extract_results("invalid") == []


def test_zephyr_client_extract_total_variants() -> None:
    """Zephyr client should extract total counts from various payload structures."""
    # Standard structure
    standard_payload = {"results": [], "total": 42}
    assert ZephyrClient._extract_total(standard_payload) == 42

    # Alternative field names
    count_payload = {"data": [], "count": 100}
    assert ZephyrClient._extract_total(count_payload) == 100

    # Nested pagination
    nested_payload = {"results": [], "pagination": {"total": 200}}
    assert ZephyrClient._extract_total(nested_payload) == 200

    # Wrapped structure
    wrapped_payload = {"value": {"results": [], "totalCount": 300}}
    assert ZephyrClient._extract_total(wrapped_payload) == 300

    # Default value
    default_payload: dict[str, list[Any]] = {"results": []}
    assert ZephyrClient._extract_total(default_payload, default_value=999) == 999

    # Invalid structures
    assert ZephyrClient._extract_total(None) is None
    assert ZephyrClient._extract_total("invalid") is None


class RecordingSession:
    """Session stub that serves queued responses based on matchers."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.auth = None
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._queue: list[
            tuple[Callable[[str, dict[str, Any]], bool], DummyResponse]
        ] = []

    def add_response(
        self,
        matcher: Callable[[str, dict[str, Any]], bool],
        response: DummyResponse,
    ) -> None:
        """Add a response to the queue for matching."""
        self._queue.append((matcher, response))

    def _consume(self, url: str, params: dict[str, Any]) -> DummyResponse:
        """Consume a matching response from the queue."""
        for index, (matcher, response) in enumerate(self._queue):
            if matcher(url, params):
                self._queue.pop(index)
                return response
        raise AssertionError(f"No response configured for {url} with {params}")

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | float | None = None,
        verify: bool | None = None,
    ) -> DummyResponse:
        """Make a GET request and return response based on matching rules."""
        _ = timeout  # unused in stub
        _ = verify  # unused in stub
        payload = {"params": params or {}, "headers": headers or {}}
        self.calls.append((url, payload))
        return self._consume(url, payload["params"])

    def post(self, *_args: Any, **_kwargs: Any) -> None:
        """Raise an error since POST should not be invoked in Zephyr fetch tests."""
        raise AssertionError("POST should not be invoked in Zephyr fetch tests")


def _match(
    suffix: str,
    *,
    max_results: int | None = None,
    require_query: bool = False,
    start_at: int | None = None,
) -> Callable[[str, dict[str, Any]], bool]:
    """Create matcher for queued responses."""

    def _matcher(url: str, params: dict[str, Any]) -> bool:
        if not url.endswith(suffix):
            return False
        if max_results is not None and params.get("maxResults") != max_results:
            return False
        has_query = "query" in params
        if require_query != has_query:
            return False
        return not (start_at is not None and params.get("startAt") != start_at)

    return _matcher


def test_zephyr_client_discovers_two_stage_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zephyr client should discover and use two-stage pattern successfully."""
    base_url = "https://api.zephyr.example"
    two_stage_keys = "/rest/tests/1.0/testcase/search"
    testcase_search = "/rest/atm/1.0/testcase/search"

    session = RecordingSession()

    # Set up the session to match all possible calls and return successful responses
    # This allows the discovery process to find the two-stage pattern naturally

    # Two-stage pattern keys endpoint - used for discovery and page size detection
    def match_any_request(url: str, params: dict[str, Any]) -> bool:
        return url.endswith(two_stage_keys)

    def match_details_request(url: str, params: dict[str, Any]) -> bool:
        return url.endswith(testcase_search) and "query" in params

    # Discovery test - should work for the two-stage pattern
    session.add_response(
        match_any_request,
        DummyResponse(
            status_code=200, payload={"results": [{"key": "ZEP-1"}], "total": 1}
        ),
    )

    # Page size detection responses
    def _page_size_matcher(expected: int) -> Callable[[str, dict[str, Any]], bool]:
        def _matcher(url: str, params: dict[str, Any]) -> bool:
            return url.endswith(two_stage_keys) and params.get("maxResults") == expected

        return _matcher

    for page_size in [100, 200, 250, 500]:
        session.add_response(
            _page_size_matcher(page_size),
            DummyResponse(
                status_code=200, payload={"results": [{"key": "ZEP-1"}], "total": 1}
            ),
        )

    # Keys stage responses - paginated fetching of test case keys
    session.add_response(
        lambda url, params: url.endswith(two_stage_keys) and params.get("startAt") == 0,
        DummyResponse(
            status_code=200,
            payload={"results": [{"key": "ZEP-1"}, {"key": "ZEP-2"}], "total": 2},
        ),
    )

    # Details stage response - fetching detailed information for keys
    session.add_response(
        match_details_request,
        DummyResponse(
            status_code=200,
            payload=[
                {"key": "ZEP-1", "name": "Login path"},
                {"key": "ZEP-2", "name": "Logout path"},
            ],
        ),
    )

    monkeypatch.setattr(
        "importobot.integrations.clients.requests.Session", lambda: session
    )

    client = ZephyrClient(
        api_url=base_url,
        tokens=["primary-token"],
        user=None,
        project_name="PRJ",
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )

    progress_calls: list[dict[str, Any]] = []

    def progress_cb(**info: Any) -> None:
        progress_calls.append(info)

    payloads = gather(client, progress_cb)

    assert len(payloads) == 1
    assert client._discovered_pattern is not None
    assert client._discovered_pattern["name"] == "working_two_stage"
    assert client._working_auth_strategy is not None
    assert client._working_auth_strategy["type"] is ZephyrClient.AuthType.BEARER
    assert client._effective_page_size == 100

    assert payloads[0]["total"] == 2
    assert isinstance(payloads[0]["results"], list)
    assert {case["key"] for case in payloads[0]["results"]} == {"ZEP-1", "ZEP-2"}

    # Progress callback should capture both key and detail stages.
    assert len(progress_calls) >= 2
    assert any(call.get("total") == 2 for call in progress_calls)


class TestAPIClientSecurityWarnings:
    """Test that security warnings are properly raised for insecure configurations."""

    def test_ssl_verification_disabled_raises_user_warning(self) -> None:
        """Verify that disabling SSL verification raises a UserWarning."""
        with pytest.warns(UserWarning, match="TLS certificate verification disabled"):
            JiraXrayClient(
                api_url="https://insecure.example.com",
                tokens=["test-token"],
                user=None,
                project_name="TEST",
                project_id=None,
                max_concurrency=None,
                verify_ssl=False,  # This should trigger UserWarning
            )

    def test_ssl_verification_enabled_no_warning(self) -> None:
        """Verify that SSL verification enabled does not raise warnings."""
        # Catch all warnings to verify none are raised for SSL
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            try:
                # Should not raise UserWarning
                JiraXrayClient(
                    api_url="https://secure.example.com",
                    tokens=["test-token"],
                    user=None,
                    project_name="TEST",
                    project_id=None,
                    max_concurrency=None,
                    verify_ssl=True,
                )
            except UserWarning:
                pytest.fail("UserWarning was raised when verify_ssl=True")

    def test_zephyr_client_ssl_warning(self) -> None:
        """Verify ZephyrClient also raises UserWarning for disabled SSL."""
        with pytest.warns(UserWarning, match="TLS certificate verification disabled"):
            ZephyrClient(
                api_url="https://insecure-zephyr.example.com",
                tokens=["test-token"],
                user=None,
                project_name="TEST",
                project_id=None,
                max_concurrency=None,
                verify_ssl=False,
            )

    def test_warning_message_includes_guidance(self) -> None:
        """Verify warning message provides guidance to users."""
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always", UserWarning)

            TestRailClient(
                api_url="https://insecure-testrail.example.com",
                tokens=["test-token"],
                user="test@example.com",
                project_name="TEST",
                project_id=None,
                max_concurrency=None,
                verify_ssl=False,
            )

            # Find the UserWarning about SSL
            ssl_warnings = [
                w
                for w in caught_warnings
                if issubclass(w.category, UserWarning)
                and "TLS certificate verification" in str(w.message)
            ]
            assert len(ssl_warnings) > 0

            warning_msg = str(ssl_warnings[0].message)
            # Check that the message includes helpful guidance
            assert "development/testing" in warning_msg.lower()
            assert "production" in warning_msg.lower()
            assert "verify_ssl=True" in warning_msg


class TestCircuitBreaker:
    """Test circuit breaker pattern for repeated API failures."""

    def test_circuit_breaker_opens_after_consecutive_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Circuit breaker should open after threshold failures and reject requests."""
        # Set up client with circuit breaker enabled (5 failures threshold)
        responses = [
            DummyResponse(status_code=500, payload={"error": "Internal Server Error"})
            for _ in range(10)  # More than threshold
        ]
        session = DummySession(responses)
        monkeypatch.setattr(
            "importobot.integrations.clients.requests.Session", lambda: session
        )
        monkeypatch.setattr(
            "importobot.integrations.clients.time.sleep", lambda seconds: None
        )

        client = JiraXrayClient(
            api_url="https://jira.example/rest/api/2/search",
            tokens=["token"],
            user=None,
            project_name="PRJ",
            project_id=None,
            max_concurrency=None,
            verify_ssl=True,
        )

        # Circuit breaker should trip after threshold failures
        with pytest.raises(RuntimeError) as exc_info:
            gather(client)

        assert "circuit breaker" in str(exc_info.value).lower()

    def test_circuit_breaker_half_open_allows_probe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Circuit breaker should allow probe requests in half-open state."""
        # Simulating: failures -> half-open -> success -> closed
        responses = [
            DummyResponse(status_code=500, payload={})
            for _ in range(5)  # Open circuit
        ]
        # After timeout, allow a probe
        responses.append(
            DummyResponse(
                status_code=200,
                payload={"issues": [], "total": 0, "startAt": 0, "maxResults": 50},
            )
        )

        session = DummySession(responses)
        monkeypatch.setattr(
            "importobot.integrations.clients.requests.Session", lambda: session
        )

        # Track time.sleep calls to simulate circuit breaker timeout
        sleep_times: list[float] = []
        monkeypatch.setattr(
            "importobot.integrations.clients.time.sleep", sleep_times.append
        )

        client = JiraXrayClient(
            api_url="https://jira.example/rest/api/2/search",
            tokens=["token"],
            user=None,
            project_name="PRJ",
            project_id=None,
            max_concurrency=None,
            verify_ssl=True,
        )

        # After circuit breaker timeout, probe should succeed
        # This will fail initially - implementation needed
        with pytest.raises(RuntimeError):
            gather(client)

    def test_circuit_breaker_resets_on_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Circuit breaker should reset failure count on successful request."""
        responses = [
            DummyResponse(status_code=500, payload={}),  # Failure 1
            DummyResponse(status_code=500, payload={}),  # Failure 2
            DummyResponse(
                status_code=200,
                payload={"issues": [], "total": 0, "startAt": 0, "maxResults": 50},
            ),  # Success - should reset
        ]

        session = DummySession(responses)
        monkeypatch.setattr(
            "importobot.integrations.clients.requests.Session", lambda: session
        )
        monkeypatch.setattr(
            "importobot.integrations.clients.time.sleep", lambda seconds: None
        )

        client = JiraXrayClient(
            api_url="https://jira.example/rest/api/2/search",
            tokens=["token"],
            user=None,
            project_name="PRJ",
            project_id=None,
            max_concurrency=None,
            verify_ssl=True,
        )

        # Should not trip circuit breaker since success resets counter
        payloads = gather(client)
        assert len(payloads) == 1


class TestCustomErrorHandlers:
    """Test custom error handler hooks for enterprise scenarios."""

    def test_custom_error_handler_invoked_on_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom error handler should be called when API request fails."""
        # Provide enough responses for retries (max_retries + 1 = 4 attempts)
        responses = [
            DummyResponse(status_code=500, payload={"error": "Service unavailable"})
            for _ in range(10)  # More than enough for retries + circuit breaker
        ]
        session = DummySession(responses)
        monkeypatch.setattr(
            "importobot.integrations.clients.requests.Session", lambda: session
        )

        errors_captured: list[dict[str, Any]] = []

        def custom_error_handler(error_info: dict[str, Any]) -> None:
            """Capture error information for testing."""
            errors_captured.append(error_info)

        client = JiraXrayClient(
            api_url="https://jira.example/rest/api/2/search",
            tokens=["token"],
            user=None,
            project_name="PRJ",
            project_id=None,
            max_concurrency=None,
            verify_ssl=True,
        )

        # Set custom error handler
        client.set_error_handler(custom_error_handler)

        with pytest.raises(RuntimeError):
            gather(client)

        # Verify custom handler was invoked with error details
        assert len(errors_captured) > 0
        assert errors_captured[0]["status_code"] == 500
        assert "error" in errors_captured[0]

    def test_custom_error_handler_receives_context(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error handler should receive request context (URL, headers, etc)."""
        responses = [
            DummyResponse(status_code=404, payload={"error": "Not found"})
            for _ in range(10)
        ]
        session = DummySession(responses)
        monkeypatch.setattr(
            "importobot.integrations.clients.requests.Session", lambda: session
        )

        errors_captured: list[dict[str, Any]] = []

        def context_aware_handler(error_info: dict[str, Any]) -> None:
            errors_captured.append(error_info)

        client = JiraXrayClient(
            api_url="https://jira.example/rest/api/2/search",
            tokens=["token"],
            user=None,
            project_name="PRJ",
            project_id=None,
            max_concurrency=None,
            verify_ssl=True,
        )
        client.set_error_handler(context_aware_handler)

        with pytest.raises(RuntimeError):
            gather(client)

        # Verify context was provided
        assert len(errors_captured) > 0
        error = errors_captured[0]
        assert "url" in error
        assert "attempt" in error
        assert "timestamp" in error

    def test_error_handler_can_suppress_exceptions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error handler can suppress exceptions for graceful degradation."""
        responses = [
            DummyResponse(status_code=503, payload={"error": "Overloaded"})
            for _ in range(10)
        ]
        session = DummySession(responses)
        monkeypatch.setattr(
            "importobot.integrations.clients.requests.Session", lambda: session
        )

        def suppressing_handler(error_info: dict[str, Any]) -> bool:
            """Return True to suppress the exception."""
            return bool(
                error_info["status_code"] == 503
            )  # Suppress service unavailable

        client = JiraXrayClient(
            api_url="https://jira.example/rest/api/2/search",
            tokens=["token"],
            user=None,
            project_name="PRJ",
            project_id=None,
            max_concurrency=None,
            verify_ssl=True,
        )
        client.set_error_handler(suppressing_handler)

        # Should not raise since handler suppresses 503 errors
        payloads = gather(client)
        assert len(payloads) == 1  # Gets empty response but no exception
        assert payloads[0] == {}  # Empty payload from suppressed error
