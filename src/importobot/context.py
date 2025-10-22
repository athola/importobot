"""Application context for managing runtime state and dependencies.

Provides a clean way to manage application-level singletons without global variables.
"""

from __future__ import annotations

import threading
from typing import cast
from weakref import WeakKeyDictionary

from importobot.services.performance_cache import PerformanceCache
from importobot.telemetry import TelemetryClient, get_telemetry_client


class ApplicationContext:
    """Central registry for application-level dependencies and state.

    This replaces scattered global variables with a single, testable context object.
    Each application instance gets its own context, enabling:
    - Clean testing (no global state pollution)
    - Multiple concurrent instances
    - Explicit dependency management
    """

    def __init__(self) -> None:
        """Initialize application context with lazy-loaded dependencies."""
        self._performance_cache: PerformanceCache | None = None
        self._telemetry_client: TelemetryClient | None = None

    @property
    def performance_cache(self) -> PerformanceCache:
        """Get or create the performance cache instance.

        Returns:
            Performance cache for string/JSON operations
        """
        if self._performance_cache is None:
            self._performance_cache = PerformanceCache()

        return self._performance_cache

    @property
    def telemetry_client(self) -> TelemetryClient:
        """Get or create the telemetry client.

        Returns:
            Telemetry client for metrics/logging
        """
        if self._telemetry_client is None:
            client = get_telemetry_client()
            if client is None:
                client = TelemetryClient(
                    min_emit_interval=60.0,
                    min_sample_delta=100,
                )
            self._telemetry_client = client

        return self._telemetry_client

    def clear_caches(self) -> None:
        """Clear all cached data (useful for testing)."""
        if self._performance_cache is not None:
            self._performance_cache.clear_cache()

    def reset(self) -> None:
        """Reset context to initial state (useful for testing)."""
        self._performance_cache = None
        self._telemetry_client = None


_context_storage = threading.local()
_context_lock = threading.Lock()
_context_registry: WeakKeyDictionary[threading.Thread, ApplicationContext] = (
    WeakKeyDictionary()
)


def _register_context(context: ApplicationContext) -> None:
    thread = threading.current_thread()
    with _context_lock:
        _context_registry[thread] = context


def _unregister_context() -> None:
    thread = threading.current_thread()
    with _context_lock:
        _context_registry.pop(thread, None)


def get_context() -> ApplicationContext:
    """Get the current application context.

    Creates a new context if none exists for this thread.

    Returns:
        Current application context
    """
    context = getattr(_context_storage, "context", None)
    if context is None:
        context = ApplicationContext()
        _context_storage.context = context
        _register_context(context)
    return cast(ApplicationContext, context)


def set_context(context: ApplicationContext) -> None:
    """Set the application context for the current thread.

    Args:
        context: Application context to use
    """
    _context_storage.context = context
    _register_context(context)


def clear_context() -> None:
    """Clear the current thread's context.

    Useful for testing to ensure clean state between tests.
    """
    if hasattr(_context_storage, "context"):
        _context_storage.context.reset()
        delattr(_context_storage, "context")
        _unregister_context()


__all__ = ["ApplicationContext", "clear_context", "get_context", "set_context"]
