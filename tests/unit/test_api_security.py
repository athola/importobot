"""Security-focused tests for API ingestion and client behavior."""

from __future__ import annotations

from argparse import Namespace
from typing import Any, ClassVar

import pytest

from importobot.config import _mask, resolve_api_ingest_config
from importobot.integrations.clients import BaseAPIClient
from importobot.medallion.interfaces.enums import SupportedFormat


class _FakeResponse:
    """Minimal response object simulating requests.Response."""

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.status_code = 200
        self._payload = payload or {}
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        """Return stored payload."""
        return self._payload

    def raise_for_status(self) -> None:
        """No-op success response."""
        return None


class _FakeSession:
    """Session stub capturing outgoing requests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.headers: dict[str, str] = {"User-Agent": "stub"}

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, str],
    ) -> _FakeResponse:
        """Record GET request call."""
        self.calls.append((url, "GET"))
        return _FakeResponse({"params": params, "headers": headers})

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> _FakeResponse:
        """Record POST request call."""
        self.calls.append((url, "POST"))
        return _FakeResponse({"json": json, "headers": headers or {}})


class _TrackingLimiter:
    """Rate limiter stub counting acquire calls."""

    instances: ClassVar[list[_TrackingLimiter]] = []

    def __init__(self, max_calls: int, time_window: float) -> None:
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = 0
        _TrackingLimiter.instances.append(self)

    def acquire(self) -> None:
        """Track acquire attempts."""
        self.calls += 1


class _DummyClient(BaseAPIClient):
    """Concrete client for exercising BaseAPIClient helpers."""

    __test__ = False

    def fetch_all(self, progress_cb):  # pragma: no cover - not used in tests
        yield from ()


@pytest.fixture(autouse=True)
def _reset_tracking_limiter() -> None:
    """Ensure limiter tracker state is clean between tests."""
    _TrackingLimiter.instances.clear()


def _make_args(**overrides: object) -> Namespace:
    """Helper to construct CLI args with secure defaults."""
    defaults: dict[str, object] = {
        "fetch_format": SupportedFormat.TESTRAIL,
        "api_url": "https://testrail.example/api",
        "api_tokens": ["token"],
        "api_user": "cli-user",
        "project": "PRJ",
        "input_dir": None,
        "max_concurrency": None,
        "insecure": False,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def test_mask_obscures_all_tokens() -> None:
    """_mask should redact every provided token."""
    masked = _mask(["alpha", "beta", "gamma"])

    assert masked == "***, ***, ***"


def test_insecure_flag_requires_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-whitelisted values must not disable TLS verification."""
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_API_URL", "https://env.example/api")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_TOKENS", "env-token")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_API_USER", "env-user")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_INSECURE", "definitely-not-true")

    config = resolve_api_ingest_config(
        _make_args(api_url=None, api_tokens=None, api_user=None)
    )

    assert config.insecure is False


def test_request_rejects_http_method_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Injected HTTP verbs should be rejected to prevent request smuggling."""
    monkeypatch.setattr("importobot.integrations.clients.RateLimiter", _TrackingLimiter)
    client = _DummyClient(
        api_url="https://api.example",
        tokens=["token"],
        user=None,
        project_name=None,
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )
    client._session = _FakeSession()  # type: ignore[assignment]

    with pytest.raises(ValueError):
        client._request(
            "GET\r\nDELETE",
            "https://api.example/resource",
            headers={},
            params={},
            json=None,
        )


def test_rate_limiter_blocks_request_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every outbound request must pass through the rate limiter."""
    monkeypatch.setattr("importobot.integrations.clients.RateLimiter", _TrackingLimiter)
    client = _DummyClient(
        api_url="https://api.example",
        tokens=["token"],
        user=None,
        project_name=None,
        project_id=None,
        max_concurrency=None,
        verify_ssl=True,
    )
    fake_session = _FakeSession()
    client._session = fake_session  # type: ignore[assignment]

    response = client._request(
        "GET", "https://api.example/resource", headers={}, params={}, json=None
    )

    assert response.status_code == 200
    assert fake_session.calls == [("https://api.example/resource", "GET")]
    limiter = _TrackingLimiter.instances[-1]
    assert limiter.calls == 1
