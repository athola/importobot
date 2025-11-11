"""Base API client with shared functionality for all platform clients.

This module provides BaseAPIClient with retry logic, circuit breaker, rate limiting,
and error handling hooks used by all platform-specific API clients.
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Callable, Iterator
from http import HTTPStatus
from importlib import metadata
from typing import Any, ClassVar, NamedTuple, Protocol, runtime_checkable

import requests

from importobot.utils.logging import get_logger
from importobot.utils.rate_limiter import RateLimiter

logger = get_logger()

BACKOFF_BASE = 2.0
MAX_RETRY_DELAY_SECONDS = 30.0


ProgressCallback = Callable[..., None]


class _KeyBatch(NamedTuple):
    """Container for key batches in Zephyr two-stage fetches."""

    keys: list[str]
    total: int | None
    page: int


def _default_user_agent() -> str:
    """Generate a descriptive User-Agent string for outbound API calls."""
    try:
        version = metadata.version("importobot")
    except metadata.PackageNotFoundError:
        version = "dev"
    return f"importobot-client/{version}"


@runtime_checkable
class APISource(Protocol):
    """Defines the protocol for platform-specific API clients."""

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Retrieve paginated payloads while reporting progress."""
        ...


class BaseAPIClient:
    """Provides shared functionality for API clients.

    **Retry Behavior**:
        - Maximum retries: 3 attempts per request.
        - Backoff strategy: Exponential with base 2.0.
        - Maximum retry delay: 30 seconds.
        - Respects `Retry-After` headers from the server.

    **Circuit Breaker**:
        - Failure threshold: 5 consecutive failures.
        - Half-open timeout: 60 seconds.
        - Resets upon a successful request.

    **Error Handler Hooks**:
        - Custom error handlers can be registered via `set_error_handler()`.
        - Handlers receive error context (URL, attempt, status code, timestamp).
        - Handlers can suppress exceptions by returning `True`.
    """

    _max_retries = 3
    _circuit_breaker_threshold = 5  # Open circuit after 5 consecutive failures
    _circuit_breaker_timeout = 60.0  # Half-open state after 60 seconds

    def __init__(
        self,
        *,
        api_url: str,
        tokens: list[str],
        user: str | None,
        project_name: str | None,
        project_id: int | None,
        max_concurrency: int | None,
        verify_ssl: bool,
    ) -> None:
        """Initialize the BaseAPIClient with API connection parameters."""
        self.api_url = api_url
        self.tokens = tokens
        self.user = user
        self.project_name = project_name
        self.project_id = project_id
        self.max_concurrency = max_concurrency
        self._verify_ssl = verify_ssl
        self._session = requests.Session()
        self._session.verify = verify_ssl
        headers = getattr(self._session, "headers", None)
        if headers and hasattr(headers, "update"):
            headers.clear()
            headers.update(
                {
                    "User-Agent": _default_user_agent(),
                    "Accept": "application/json",
                }
            )
        if not verify_ssl:
            warning_msg = (
                f"TLS certificate verification disabled for API client "
                f"targeting {api_url}. This is insecure and should only be "
                "used in development/testing. Set verify_ssl=True or fix "
                "certificate issues in production."
            )
            # Use Python warnings to ensure visibility even without logger configuration
            # UserWarning is the standard category for security-related user warnings
            warnings.warn(warning_msg, category=UserWarning, stacklevel=2)
            # Also log for those who have logging configured
            logger.warning(
                "TLS certificate verification disabled for client targeting %s",
                api_url,
            )
        self._rate_limiter = RateLimiter(max_calls=100, time_window=60.0)

        # Circuit breaker state
        self._circuit_failure_count = 0
        self._circuit_last_failure_time: float | None = None
        self._circuit_open = False

        # Error handler hook
        self._error_handler: Callable[[dict[str, Any]], bool | None] | None = None

    def set_error_handler(
        self, handler: Callable[[dict[str, Any]], bool | None]
    ) -> None:
        """Register a custom error handler.

        The handler receives error context and can optionally suppress exceptions.

        Args:
            handler: Callable receiving `error_info` dictionary with following fields:
                - `url`: The request URL.
                - `status_code`: The HTTP status code.
                - `error`: The error message or payload.
                - `attempt`: The current retry attempt number.
                - `timestamp`: The error timestamp.

        Returns:
            `None` if the exception should be raised, `True` to suppress the exception.

        Example:
            ```python
            from http import HTTPStatus

            def log_and_suppress_503(error_info):
                if error_info['status_code'] == HTTPStatus.SERVICE_UNAVAILABLE:
                    logger.warning("Service unavailable, gracefully degrading")
                    return True  # Suppress exception
                return None  # Let exception propagate

            client.set_error_handler(log_and_suppress_503)
            ```
        """
        self._error_handler = handler

    def _check_circuit_breaker(self) -> None:
        """Check circuit-breaker state and raises exception if circuit is open."""
        if not self._circuit_open:
            return

        # Check if we should transition to half-open state
        if self._circuit_last_failure_time is not None:
            elapsed = time.time() - self._circuit_last_failure_time
            if elapsed >= self._circuit_breaker_timeout:
                # Transition to half-open - allow one probe request
                logger.info(
                    "Circuit breaker entering half-open state after %.1fs timeout",
                    elapsed,
                )
                self._circuit_open = False
                return

        # Circuit is still open - reject request
        raise RuntimeError(
            f"Circuit breaker is open for {self.api_url} after "
            f"{self._circuit_failure_count} consecutive failures. "
            f"Will retry after timeout."
        )

    def _record_failure(self) -> None:
        """Record a failure for circuit breaker tracking."""
        self._circuit_failure_count += 1
        self._circuit_last_failure_time = time.time()

        if self._circuit_failure_count >= self._circuit_breaker_threshold:
            self._circuit_open = True
            logger.warning(
                "Circuit breaker opened for %s after %d failures",
                self.api_url,
                self._circuit_failure_count,
            )

    def _record_success(self) -> None:
        """Record a successful request, which resets the circuit breaker."""
        if self._circuit_failure_count > 0:
            logger.debug(
                "Resetting circuit breaker after successful request (had %d failures)",
                self._circuit_failure_count,
            )
        self._circuit_failure_count = 0
        self._circuit_open = False
        self._circuit_last_failure_time = None

    def _auth_headers(self) -> dict[str, str]:
        """Return the default authorization headers."""
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens[0]}"
        return headers

    def _compute_retry_delay(
        self, response: requests.Response | None, attempt: int
    ) -> float:
        """Determine retry delay using Retry-After header or exponential backoff.

        Args:
            response: HTTP response (or `None` if request failed before response).
            attempt: The current retry attempt number.

        Returns:
            The delay in seconds before the next retry.
        """
        if response:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    value = float(retry_after)
                    if value >= 0:
                        return value
                except ValueError:
                    logger.debug("Invalid Retry-After header %s", retry_after)
        return float(min(BACKOFF_BASE**attempt, MAX_RETRY_DELAY_SECONDS))

    def _sleep(self, seconds: float) -> None:
        """Pauses execution for the specified number of seconds.

        Args:
            seconds: The number of seconds to sleep.
        """
        time.sleep(seconds)

    def _project_value(self) -> str | int | None:
        """Return the preferred project identifier."""
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
        """Perform HTTP request with retry, circuit breaker, and error handling."""
        # Check circuit breaker before attempting request
        self._check_circuit_breaker()

        headers = headers or {}
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._dispatch_request(
                    method, url, params=params, headers=headers, json=json
                )

                # Handle rate limiting with retry (not a circuit breaker failure)
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    if attempt < self._max_retries:
                        delay = self._compute_retry_delay(response, attempt)
                        logger.info(
                            "Rate limited by %s (attempt %s/%s); retrying in %.2fs",
                            url,
                            attempt + 1,
                            self._max_retries,
                            delay,
                        )
                        self._sleep(delay)
                        continue
                    # Exhausted retries on rate limit
                    raise RuntimeError(f"Exceeded retry budget for {url}")

                # Check for HTTP errors (4xx client errors, 5xx server errors)
                if response.status_code >= HTTPStatus.BAD_REQUEST:
                    should_suppress = self._handle_http_error(response, url, attempt)
                    if should_suppress:
                        return self._create_empty_response()
                    # Error not suppressed - continue to next retry attempt
                    continue

                # Success - update circuit breaker and return response
                self._record_success()
                return response

            except Exception as err:
                last_error = err
                # Check if this is a circuit breaker error - don't retry these
                if "circuit breaker" in str(err).lower():
                    logger.error("Circuit breaker error not retryable: %s", err)
                    raise

                if attempt < self._max_retries:
                    delay = self._compute_retry_delay(None, attempt)
                    logger.warning(
                        "Request to %s failed (attempt %s/%s): %s; retrying in %.2fs",
                        url,
                        attempt + 1,
                        self._max_retries,
                        err,
                        delay,
                    )
                    self._sleep(delay)
                    continue

        # All retries exhausted
        self._record_failure()
        # Check if circuit breaker just opened due to final retry failure
        if self._circuit_open:
            raise RuntimeError(
                f"Circuit breaker is open for {self.api_url} after "
                f"{self._circuit_failure_count} consecutive failures"
            )
        raise last_error or RuntimeError(f"Request to {url} failed")

    def _handle_http_error(
        self, response: requests.Response, url: str, attempt: int
    ) -> bool:
        """Handle HTTP error responses.

        Returns `True` if the error should be suppressed (leading to an empty response),
        `False` if the error should be raised.
        """
        error_info = {
            "url": url,
            "status_code": response.status_code,
            "error": response.text,
            "attempt": attempt,
            "timestamp": time.time(),
        }

        # Call custom error handler if registered
        should_suppress = False
        if self._error_handler:
            result = self._error_handler(error_info)
            should_suppress = result is True

        # Record failure for circuit breaker
        self._record_failure()

        # Check if circuit just opened - raise circuit breaker error instead
        if self._circuit_open:
            logger.error(
                "Circuit breaker is OPEN - raising circuit breaker error for %s",
                self.api_url,
            )
            raise RuntimeError(
                f"Circuit breaker is open for {self.api_url} after "
                f"{self._circuit_failure_count} consecutive failures"
            )

        return should_suppress

    def _create_empty_response(self) -> requests.Response:
        """Create an empty response object to facilitate graceful degradation."""

        class EmptyResponse:
            status_code = 0  # Non-standard: indicates suppressed/empty response
            headers: ClassVar[dict[str, str]] = {}

            def json(self) -> dict[str, Any]:
                return {}

        return EmptyResponse()  # type: ignore

    def _dispatch_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None,
        headers: dict[str, str],
        json: dict[str, Any] | None,
    ) -> requests.Response:
        """Dispatches the HTTP request using the underlying session."""
        self._rate_limiter.acquire()
        if method.upper() == "GET":
            return self._session.get(url, params=params or {}, headers=headers)
        if method.upper() == "POST":
            try:
                return self._session.post(url, json=json or {}, headers=headers)
            except TypeError:
                return self._session.post(url, json=json or {})
        raise ValueError(f'Unsupported HTTP method "{method}"')


__all__ = [
    "BACKOFF_BASE",
    "MAX_RETRY_DELAY_SECONDS",
    "APISource",
    "BaseAPIClient",
    "ProgressCallback",
    "_KeyBatch",
    "_default_user_agent",
]
