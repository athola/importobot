"""Application context for managing runtime state and dependencies.

Provides a clean way to manage application-level singletons without global variables.

Thread Lifecycle and Memory Management
--------------------------------------
The context registry uses WeakKeyDictionary to automatically clean up contexts when
threads are garbage collected. However, in practice, thread objects may be kept alive
by the Python interpreter or external references, which can delay or prevent cleanup.

To mitigate potential memory leaks:

1. **Explicit Cleanup**: Call clear_context() when done with a thread's context,
   especially in long-running applications or thread pools.

2. **Thread Pool Usage**: When using thread pools (ThreadPoolExecutor, etc.),
   contexts will accumulate for worker threads. Consider:
   - Calling clear_context() at the end of each task
   - Using cleanup_stale_contexts() periodically
   - Setting IMPORTOBOT_CONTEXT_CLEANUP_INTERVAL to enable automatic cleanup

3. **Monitoring**: Use get_registry_stats() to monitor context accumulation in
   production. If registry size grows unbounded, investigate thread lifecycle.

4. **Testing**: In tests, always use clear_context() in teardown to prevent
   cross-test pollution.

Example usage in thread pool:
    ```python
    from importobot.context import get_context, clear_context

    def worker_task():
        try:
            context = get_context()
            # ... use context ...
        finally:
            clear_context()  # Explicit cleanup
    ```

Environment Variables
---------------------
- IMPORTOBOT_CONTEXT_CLEANUP_INTERVAL: Seconds between automatic cleanup
  (default: disabled)
- IMPORTOBOT_CONTEXT_MAX_SIZE: Warn when registry exceeds this size
  (default: 100)
"""

from __future__ import annotations

import atexit
import os
import threading
import time
from typing import cast
from weakref import WeakKeyDictionary

from importobot.services.performance_cache import PerformanceCache
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import get_logger

logger = get_logger()


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

# Configuration for monitoring and cleanup
_CONTEXT_MAX_SIZE = int(os.getenv("IMPORTOBOT_CONTEXT_MAX_SIZE", "100"))
_CLEANUP_INTERVAL = float(os.getenv("IMPORTOBOT_CONTEXT_CLEANUP_INTERVAL", "0"))
_cleanup_state = {"last_cleanup_time": time.time()}
_cleanup_enabled = _CLEANUP_INTERVAL > 0


def _register_context(context: ApplicationContext) -> None:
    """Register context for current thread with monitoring."""
    thread = threading.current_thread()
    with _context_lock:
        _context_registry[thread] = context
        registry_size = len(_context_registry)

        # Automatic cleanup if enabled and interval elapsed
        if _cleanup_enabled:
            _temporal_cleanup_stale_contexts()

        # Warn if registry size exceeds threshold
        if registry_size > _CONTEXT_MAX_SIZE:
            logger.warning(
                "Context registry size (%d) exceeds threshold (%d). "
                "Consider calling cleanup_stale_contexts() or clear_context() "
                "in thread cleanup handlers. Active threads: %s",
                registry_size,
                _CONTEXT_MAX_SIZE,
                [t.name for t in list(_context_registry.keys())[:10]],
            )


def _unregister_context() -> None:
    """Unregister context for current thread."""
    thread = threading.current_thread()
    with _context_lock:
        _context_registry.pop(thread, None)


def _temporal_cleanup_stale_contexts() -> None:
    """Run cleanup if enough time has elapsed since last cleanup.

    Must be called with _context_lock held.
    """
    current_time = time.time()
    if current_time - _cleanup_state["last_cleanup_time"] >= _CLEANUP_INTERVAL:
        _cleanup_stale_contexts_locked()
        _cleanup_state["last_cleanup_time"] = current_time


def _cleanup_stale_contexts_locked() -> None:
    """Remove contexts for dead threads.

    Must be called with _context_lock held.

    WeakKeyDictionary should handle this automatically, but in practice
    thread objects may be kept alive by the interpreter. This explicitly
    removes contexts for threads that are no longer alive.
    """
    stale_threads = [t for t in list(_context_registry.keys()) if not t.is_alive()]
    for thread in stale_threads:
        _context_registry.pop(thread, None)

    if stale_threads:
        logger.debug(
            "Cleaned up %d stale context(s) for dead threads: %s",
            len(stale_threads),
            [t.name for t in stale_threads],
        )


def get_context() -> ApplicationContext:
    """Get the current application context.

    Creates a new context if none exists for this thread.

    Returns:
        Current application context
    """
    if not hasattr(_context_storage, "context"):
        context = ApplicationContext()
        _context_storage.context = context
        _register_context(context)
    return cast(ApplicationContext, _context_storage.context)


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


def cleanup_stale_contexts() -> int:
    """Manually remove contexts for threads that are no longer alive.

    This is useful in long-running applications with thread pools to prevent
    memory leaks when threads are kept alive by the interpreter but are no
    longer active.

    Returns:
        Number of stale contexts removed

    Example:
        >>> from importobot.context import cleanup_stale_contexts
        >>> removed = cleanup_stale_contexts()
        >>> print(f"Cleaned up {removed} stale contexts")
    """
    with _context_lock:
        before_count = len(_context_registry)
        _cleanup_stale_contexts_locked()
        after_count = len(_context_registry)
        return before_count - after_count


def get_registry_stats() -> dict[str, int | list[str]]:
    """Get statistics about the context registry for monitoring.

    Returns:
        Dictionary with registry statistics:
        - size: Number of contexts in registry
        - alive_threads: Number of threads that are still alive
        - dead_threads: Number of threads that are dead but still in registry
        - thread_names: Names of first 10 threads in registry

    Example:
        >>> from importobot.context import get_registry_stats
        >>> stats = get_registry_stats()
        >>> if stats['dead_threads'] > 10:
        ...     cleanup_stale_contexts()
    """
    with _context_lock:
        threads = list(_context_registry.keys())
        alive = [t for t in threads if t.is_alive()]
        dead = [t for t in threads if not t.is_alive()]

        return {
            "size": len(threads),
            "alive_threads": len(alive),
            "dead_threads": len(dead),
            "thread_names": [t.name for t in threads[:10]],
        }


def _cleanup_on_exit() -> None:
    """Clean up all contexts on application exit."""
    with _context_lock:
        _context_registry.clear()


# Register cleanup handler for application exit
atexit.register(_cleanup_on_exit)


__all__ = [
    "ApplicationContext",
    "cleanup_stale_contexts",
    "clear_context",
    "get_context",
    "get_registry_stats",
    "set_context",
]
