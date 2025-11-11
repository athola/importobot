"""Performance-oriented tests for API retrieval caching behaviour."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from importobot.integrations.clients import ZephyrClient


class DummyResponse:
    """Lightweight response object for performance tests."""

    def __init__(self, *, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.headers: dict[str, str] = {}

    def json(self) -> Any:
        """Return the stored payload."""
        return self._payload

    def raise_for_status(self) -> None:
        """Raise an error if status code indicates an error."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    @property
    def request(self) -> DummyRequest:
        """Return a dummy request object."""
        return DummyRequest()


class DummyRequest:
    """Lightweight request object for performance tests."""

    def __init__(self) -> None:
        self.url = "https://mock-url.example"
        self.headers: dict[str, str] = {}


class CountingSession:
    """Session stub that tracks discovery and fetch calls."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.auth = None
        self.discovery_calls = 0
        self.page_size_probe_calls = 0
        self.queue: list[
            tuple[Callable[[str, dict[str, Any]], bool], DummyResponse]
        ] = []

    def add_response(
        self,
        matcher: Callable[[str, dict[str, Any]], bool],
        response: DummyResponse,
    ) -> None:
        """Add a response to the queue for matching."""
        self.queue.append((matcher, response))

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | float | None = None,
        verify: bool | None = None,
    ) -> DummyResponse:
        """Make a GET request and return a matching response."""
        _ = headers, timeout, verify  # unused
        params = params or {}
        if params.get("maxResults") == 1 and "query" not in params:
            self.discovery_calls += 1
        if (
            params.get("maxResults") in ZephyrClient.DEFAULT_PAGE_SIZES
            and params.get("maxResults") != 1
            and params.get("startAt", 0) == 0
            and "query" not in params
        ):
            self.page_size_probe_calls += 1

        for index, (matcher, response) in enumerate(self.queue):
            if matcher(url, params):
                self.queue.pop(index)
                return response

        raise AssertionError(f"No queued response for {url} with {params}")

    def post(self, *args: Any, **kwargs: Any) -> None:
        """Raise an assertion error since POST should not be used in discovery test."""
        raise AssertionError("POST should not be used in discovery test")


def _matcher(
    suffix: str,
    *,
    max_results: int | None = None,
    require_query: bool = False,
    start_at: int | None = None,
) -> Callable[[str, dict[str, Any]], bool]:
    """Create a matcher function for API endpoint testing."""

    def _inner(url: str, params: dict[str, Any]) -> bool:
        if not url.endswith(suffix):
            return False
        if max_results is not None and params.get("maxResults") != max_results:
            return False
        has_query = "query" in params
        if require_query != has_query:
            return False
        return not (start_at is not None and params.get("startAt") != start_at)

    return _inner


def test_zephyr_discovery_cached_between_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discovery should only run once to avoid redundant network traffic."""
    base_url = "https://zephyr-perf.example"
    keys_path = "/rest/tests/1.0/testcase/search"
    detail_path = "/rest/atm/1.0/testcase/search"

    session = CountingSession()

    # Mock responses for discovery - working_two_stage pattern succeeds on Bearer auth
    # (4th attempt), but first 3 auth strategies fail
    # First 3 auth strategies fail
    for _ in range(3):
        session.add_response(
            _matcher(keys_path, max_results=1, require_query=True),
            DummyResponse(status_code=401, payload={}),
        )

    # 4th auth strategy (Bearer) succeeds for discovery test
    session.add_response(
        _matcher(keys_path, max_results=1, require_query=True),
        DummyResponse(status_code=200, payload={"results": [{"key": "Z-1"}]}),
    )

    # Page size detection for keys search (Bearer auth)
    session.add_response(
        _matcher(keys_path, max_results=100, require_query=True),
        DummyResponse(status_code=200, payload={"results": [{"key": "Z-1"}]}),
    )

    # Mock responses for actual data fetching
    session.add_response(
        _matcher(keys_path, max_results=100, start_at=0, require_query=True),
        DummyResponse(
            status_code=200,
            payload={"results": [{"key": "Z-1"}, {"key": "Z-2"}], "total": 2},
        ),
    )
    session.add_response(
        _matcher(detail_path, require_query=True),
        DummyResponse(
            status_code=200,
            payload=[
                {"key": "Z-1", "name": "Login"},
                {"key": "Z-2", "name": "Logout"},
            ],
        ),
    )

    # Second run should use cached discovery, so only actual fetching happens
    session.add_response(
        _matcher(keys_path, max_results=100, start_at=0, require_query=True),
        DummyResponse(
            status_code=200,
            payload={"results": [{"key": "Z-1"}, {"key": "Z-2"}], "total": 2},
        ),
    )
    session.add_response(
        _matcher(detail_path, require_query=True),
        DummyResponse(
            status_code=200,
            payload=[
                {"key": "Z-1", "name": "Login"},
                {"key": "Z-2", "name": "Logout"},
            ],
        ),
    )

    monkeypatch.setattr(
        "importobot.integrations.clients.base.requests.Session", lambda: session
    )

    client = ZephyrClient(
        api_url=base_url,
        tokens=["primary-token"],
        user=None,
        project_name="PERF",
        project_id=None,
        max_concurrency=None,
    )

    first_run = list(client.fetch_all(lambda **_: None))
    first_discovery = session.discovery_calls
    first_page_probe = session.page_size_probe_calls

    second_run = list(client.fetch_all(lambda **_: None))

    assert first_run == second_run
    assert session.discovery_calls == first_discovery
    assert session.page_size_probe_calls == first_page_probe
