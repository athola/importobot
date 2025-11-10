"""Manage application context for runtime state and dependencies.

This module provides a structured approach to managing application-level singletons
without relying on global variables. The context is thread-local and is
automatically cleaned up when a thread is garbage collected.

For long-running applications or thread pools, it is recommended to call
`clear_context()` when a thread's context is no longer needed to prevent
potential memory leaks.
"""

from __future__ import annotations

import atexit
import os
import threading
import time
from typing import Literal, TypedDict, cast
from weakref import WeakKeyDictionary

from importobot.services.performance_cache import PerformanceCache
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import get_logger

logger = get_logger()


class ApplicationContext:
    """A central, testable registry for application-level dependencies and state."""

    def __init__(self) -> None:
        """Initialize the application context."""
        self._performance_cache: PerformanceCache | None = None
        self._telemetry_client: TelemetryClient | None = None

    @property
    def performance_cache(self) -> PerformanceCache:
        """Get the performance cache instance.

        Returns:
            The performance cache for string/JSON operations.
        """
        if self._performance_cache is None:
            self._performance_cache = PerformanceCache()

        return self._performance_cache

    @property
    def telemetry_client(self) -> TelemetryClient:
        """Get the telemetry client instance.

        Returns:
            The telemetry client for metrics and logging.
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
        """Clear all cached data."""
        if self._performance_cache is not None:
            self._performance_cache.clear_cache()

    def reset(self) -> None:
        """Reset the context to its initial state."""
        self._performance_cache = None
        self._telemetry_client = None

    def __enter__(self) -> ApplicationContext:
        """Enter a runtime context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        """Exit the runtime context and perform cleanup."""
        self.reset()
        clear_context()
        return False


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


class CleanupStats(TypedDict):
    """Define the data structure for cleanup performance statistics."""

    cleanup_count: int
    total_cleanup_time_ms: float
    total_threads_processed: int
    average_cleanup_time_ms: float
    last_cleanup_time: float | None
    last_cleanup_duration_ms: float | None
    max_cleanup_duration_ms: float
    min_cleanup_duration_ms: float


class CleanupPerformanceTracker:
    """Track performance statistics for context cleanup operations."""

    def __init__(self) -> None:
        """Initialize the performance tracker."""
        self._stats = {
            "cleanup_count": 0,
            "total_cleanup_time_ms": 0.0,
            "total_threads_processed": 0,
            "average_cleanup_time_ms": 0.0,
            "last_cleanup_time": None,
            "last_cleanup_duration_ms": None,
            "max_cleanup_duration_ms": 0.0,
            "min_cleanup_duration_ms": float("inf"),
        }
        self._lock = threading.RLock()

    def record_cleanup(self, cleanup_duration_ms: float, total_threads: int) -> None:
        """Record a cleanup operation and its performance metrics.

        Args:
            cleanup_duration_ms: The duration of the cleanup operation in milliseconds.
            total_threads: The number of threads processed during the cleanup.
        """
        with self._lock:
            # Update running totals - cast to ensure proper types
            cleanup_count = int(self._stats["cleanup_count"] or 0)
            total_time = float(self._stats["total_cleanup_time_ms"] or 0.0)
            threads_processed = int(self._stats["total_threads_processed"] or 0)

            self._stats["cleanup_count"] = cleanup_count + 1
            self._stats["total_cleanup_time_ms"] = total_time + cleanup_duration_ms
            self._stats["total_threads_processed"] = threads_processed + total_threads

            # Update average
            new_count = int(self._stats["cleanup_count"] or 0)
            new_total_time = float(self._stats["total_cleanup_time_ms"] or 0.0)
            if new_count > 0:
                self._stats["average_cleanup_time_ms"] = new_total_time / new_count
            else:
                self._stats["average_cleanup_time_ms"] = 0.0

            # Update timestamps
            self._stats["last_cleanup_time"] = time.time()
            self._stats["last_cleanup_duration_ms"] = cleanup_duration_ms

            # Update min/max
            current_max = float(self._stats["max_cleanup_duration_ms"] or 0.0)
            self._stats["max_cleanup_duration_ms"] = max(
                current_max, cleanup_duration_ms
            )

            current_min = float(self._stats["min_cleanup_duration_ms"] or float("inf"))
            self._stats["min_cleanup_duration_ms"] = min(
                current_min, cleanup_duration_ms
            )

    def get_stats(self) -> CleanupStats:
        """Get a copy of the current performance statistics.

        Returns:
            A dictionary containing all performance metrics.
        """
        with self._lock:
            return self._stats.copy()  # type: ignore[return-value]

    def reset(self) -> None:
        """Reset all performance statistics."""
        with self._lock:
            self._stats = {
                "cleanup_count": 0,
                "total_cleanup_time_ms": 0.0,
                "total_threads_processed": 0,
                "average_cleanup_time_ms": 0.0,
                "last_cleanup_time": None,
                "last_cleanup_duration_ms": None,
                "max_cleanup_duration_ms": 0.0,
                "min_cleanup_duration_ms": float("inf"),
            }


# Global performance tracker instance
_performance_tracker = CleanupPerformanceTracker()


def _register_context(context: ApplicationContext) -> None:
    """Register the context for the current thread."""
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
    """Unregister the context for the current thread."""
    thread = threading.current_thread()
    with _context_lock:
        _context_registry.pop(thread, None)


def _temporal_cleanup_stale_contexts() -> None:
    """Run cleanup if enough time has passed since the last one.

    This function must be called while `_context_lock` is held.
    """
    current_time = time.time()
    if current_time - _cleanup_state["last_cleanup_time"] >= _CLEANUP_INTERVAL:
        _cleanup_stale_contexts_locked()
        _cleanup_state["last_cleanup_time"] = current_time


def _cleanup_stale_contexts_locked() -> None:
    """Remove contexts associated with dead threads.

    This function must be called while `_context_lock` is held.
    """
    start_time = time.perf_counter()
    total_threads = len(_context_registry)

    stale_threads = [t for t in list(_context_registry.keys()) if not t.is_alive()]
    for thread in stale_threads:
        _context_registry.pop(thread, None)

    end_time = time.perf_counter()
    cleanup_duration_ms = (end_time - start_time) * 1000

    # Update performance statistics using the tracker
    _performance_tracker.record_cleanup(cleanup_duration_ms, total_threads)

    if stale_threads:
        logger.debug(
            "Cleaned up %d stale context(s) for dead threads: %s in %.2fms "
            "(processed %d total threads)",
            len(stale_threads),
            [t.name for t in stale_threads],
            cleanup_duration_ms,
            total_threads,
        )

        # Log performance warning if cleanup takes too long
        if cleanup_duration_ms > 50.0:  # 50ms threshold
            logger.warning(
                "Context registry cleanup took %.2fms (threshold: 50ms). "
                "Registry size: %d, Stale threads: %d. "
                "Consider reviewing thread lifecycle management.",
                cleanup_duration_ms,
                total_threads,
                len(stale_threads),
            )


def get_context() -> ApplicationContext:
    """Get the application context for the current thread.

    A new context is created if one does not already exist for the current thread.

    Returns:
        The current application context.
    """
    if not hasattr(_context_storage, "context"):
        context = ApplicationContext()
        _context_storage.context = context
        _register_context(context)
    return cast(ApplicationContext, _context_storage.context)


def set_context(context: ApplicationContext) -> None:
    """Set the application context for the current thread.

    Args:
        context: The application context to be used.
    """
    _context_storage.context = context
    _register_context(context)


def clear_context() -> None:
    """Clear the application context for the current thread."""
    if hasattr(_context_storage, "context"):
        _context_storage.context.reset()
        delattr(_context_storage, "context")
        _unregister_context()


def cleanup_stale_contexts() -> int:
    """Manually remove contexts associated with threads that are no longer alive.

    This helps prevent memory leaks in long-running applications that use
    thread pools.

    Returns:
        The number of stale contexts removed.
    """
    with _context_lock:
        before_count = len(_context_registry)
        _cleanup_stale_contexts_locked()
        after_count = len(_context_registry)
        return before_count - after_count


def get_registry_stats() -> dict[str, int | list[str]]:
    """Get statistics about the context registry.

    Returns:
        A dictionary containing registry statistics.
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


def get_cleanup_performance_stats() -> CleanupStats:
    """Get performance statistics for context registry cleanup operations.

    Returns:
        A dictionary containing cleanup performance statistics.
    """
    # Return a copy to prevent external modification
    return _performance_tracker.get_stats()


def reset_cleanup_performance_stats() -> None:
    """Reset cleanup performance statistics."""
    _performance_tracker.reset()


def _cleanup_on_exit() -> None:
    """Clean up all contexts upon application exit."""
    with _context_lock:
        _context_registry.clear()


# Register cleanup handler for application exit
atexit.register(_cleanup_on_exit)


__all__ = [
    "ApplicationContext",
    "cleanup_stale_contexts",
    "clear_context",
    "get_cleanup_performance_stats",
    "get_context",
    "get_registry_stats",
    "reset_cleanup_performance_stats",
    "set_context",
]
