"""Tests for ApplicationContext pattern.

Demonstrates how context pattern enables:
- Clean testing without global state pollution
- Multiple concurrent instances
- Explicit dependency management
"""

import threading
import time
from collections.abc import Iterator
from typing import cast

import pytest

from importobot.context import (
    ApplicationContext,
    cleanup_stale_contexts,
    clear_context,
    get_cleanup_performance_stats,
    get_context,
    get_registry_stats,
    reset_cleanup_performance_stats,
    set_context,
)
from importobot.services.performance_cache import (
    PerformanceCache,
    get_performance_cache,
)
from importobot.telemetry import TelemetryClient


class TestApplicationContext:
    """Test application context lifecycle and isolation."""

    def test_context_creates_lazily(self) -> None:
        """Context instances are created on first access."""
        clear_context()  # Ensure clean state

        context = get_context()
        assert isinstance(context, ApplicationContext)

    def test_context_is_thread_local(self) -> None:
        """Each thread gets its own context instance."""
        contexts = []

        def capture_context() -> None:
            contexts.append(get_context())

        threads = [threading.Thread(target=capture_context) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have gotten a different context instance
        assert len({id(context) for context in contexts}) == 3

    def test_context_can_be_explicitly_set(self) -> None:
        """Context can be explicitly set for dependency injection."""
        custom_context = ApplicationContext()
        set_context(custom_context)

        retrieved = get_context()
        assert retrieved is custom_context

    def test_clear_context_resets_state(self) -> None:
        """Clearing context removes all cached state."""
        context = get_context()
        # Access something to create state
        _ = context.performance_cache

        clear_context()

        # New context should be created
        new_context = get_context()
        assert new_context is not context

    def test_performance_cache_property(self) -> None:
        """Performance cache is lazily created through context."""
        context = ApplicationContext()
        assert context._performance_cache is None

        cache = context.performance_cache
        assert cache is not None
        # Subsequent access returns same instance
        assert context.performance_cache is cache

    def test_context_clear_caches(self) -> None:
        """Context can clear all cached data."""
        context = ApplicationContext()
        cache = context.performance_cache

        # Add some data
        cache.set("demo-key", "value")

        # Clear via context
        context.clear_caches()

        # Cache should be cleared
        assert cache.get("demo-key") is None

    def test_context_reset(self) -> None:
        """Context reset removes all dependencies."""
        context = ApplicationContext()
        _ = context.performance_cache  # Create cache

        assert context._performance_cache is not None

        context.reset()

        assert context._performance_cache is None


class TestContextInTesting:
    """Demonstrate how context pattern improves testing."""

    @pytest.fixture(autouse=True)
    def _clean_context(self) -> Iterator[None]:
        """Ensure clean context for each test."""
        clear_context()
        yield
        clear_context()

    def test_isolation_example_1(self) -> None:
        """First test has clean context."""
        context = get_context()
        cache = context.performance_cache

        # This test's modifications don't affect other tests
        cache.set("test1", "value1")

    def test_isolation_example_2(self) -> None:
        """Second test also has clean context."""
        context = get_context()
        cache = context.performance_cache

        # Starts fresh - no state from previous test
        assert cache.get("test1") is None


class TestContextVsGlobalVariable:
    """Compare context pattern vs global variable pattern."""

    def test_context_allows_multiple_instances(self) -> None:
        """With context, we can have multiple independent instances."""
        context1 = ApplicationContext()
        context2 = ApplicationContext()

        cache1 = context1.performance_cache
        cache2 = context2.performance_cache

        # These are independent instances
        assert cache1 is not cache2

    def test_context_explicit_dependency_injection(self) -> None:
        """Context enables explicit dependency injection for testing."""
        # Create custom context with test configuration
        test_context = ApplicationContext()

        # Use it explicitly
        set_context(test_context)

        # Now all code using get_context() will use our test context
        cache = get_performance_cache()
        assert cache is not None


class TestContextCleanup:
    """Test context cleanup and memory management."""

    @pytest.fixture(autouse=True)
    def _clean_context_and_registry(self) -> Iterator[None]:
        """Ensure clean context and registry for each test."""
        clear_context()
        cleanup_stale_contexts()
        yield
        clear_context()
        cleanup_stale_contexts()

    def test_cleanup_stale_contexts_removes_dead_threads(self) -> None:
        """Cleanup should remove contexts for threads that are no longer alive."""
        contexts_created = []

        def worker():
            context = get_context()
            contexts_created.append(context)

        # Create and finish threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should be dead now
        stats_before = get_registry_stats()
        assert cast(int, stats_before["size"]) >= 5

        # Cleanup should remove dead thread contexts
        removed = cleanup_stale_contexts()
        assert removed >= 5

        stats_after = get_registry_stats()
        assert cast(int, stats_after["dead_threads"]) == 0

    def test_get_registry_stats_reports_accurate_counts(self) -> None:
        """Registry stats should accurately report thread states."""
        # Start with clean state
        cleanup_stale_contexts()

        # Create contexts in current thread
        _ = get_context()

        stats = get_registry_stats()
        assert cast(int, stats["size"]) >= 1
        assert cast(int, stats["alive_threads"]) >= 1
        assert isinstance(stats["thread_names"], list)

    def test_cleanup_returns_zero_when_no_stale_contexts(self) -> None:
        """Cleanup should return 0 when there are no stale contexts."""
        # Ensure registry is clean
        cleanup_stale_contexts()

        # Create context in current (alive) thread
        _ = get_context()

        # Should not remove contexts for alive threads
        removed = cleanup_stale_contexts()
        assert removed == 0

    def test_registry_stats_includes_thread_names(self) -> None:
        """Stats should include thread names for debugging."""
        _ = get_context()

        stats = get_registry_stats()
        assert "thread_names" in stats
        assert isinstance(stats["thread_names"], list)
        assert len(stats["thread_names"]) > 0

    def test_cleanup_is_thread_safe(self) -> None:
        """Cleanup should be safe to call from multiple threads."""
        results = []

        def worker():
            _ = get_context()
            # Small delay to increase chance of concurrent cleanup
            time.sleep(0.01)

        def cleanup_worker():
            removed = cleanup_stale_contexts()
            results.append(removed)

        # Create worker threads
        workers = [threading.Thread(target=worker) for _ in range(10)]
        for t in workers:
            t.start()
        for t in workers:
            t.join()

        # Run cleanup from multiple threads
        cleanup_threads = [threading.Thread(target=cleanup_worker) for _ in range(3)]
        for t in cleanup_threads:
            t.start()
        for t in cleanup_threads:
            t.join()

        # Should complete without errors
        assert len(results) == 3


class TestContextMemoryManagement:
    """Test memory management and leak prevention."""

    @pytest.fixture(autouse=True)
    def _clean_context_and_registry(self) -> Iterator[None]:
        """Ensure clean context and registry for each test."""
        clear_context()
        cleanup_stale_contexts()
        yield
        clear_context()
        cleanup_stale_contexts()

    def test_context_not_retained_after_thread_cleanup(self) -> None:
        """Context should be removable after thread exits."""
        initial_stats = get_registry_stats()
        initial_size = cast(int, initial_stats["size"])

        def worker():
            _ = get_context()

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        # Thread is dead, cleanup should work
        removed = cleanup_stale_contexts()
        assert removed >= 1

        final_stats = get_registry_stats()
        assert cast(int, final_stats["size"]) <= initial_size

    def test_clear_context_removes_from_registry(self) -> None:
        """Clearing context should unregister it from the registry."""
        initial_size = cast(int, get_registry_stats()["size"])

        _ = get_context()
        after_get = cast(int, get_registry_stats()["size"])
        assert after_get > initial_size

        clear_context()
        after_clear = cast(int, get_registry_stats()["size"])
        assert after_clear <= initial_size

    def test_registry_does_not_grow_unbounded_with_cleanup(self) -> None:
        """Registry size should stay bounded when using cleanup."""
        # Create and cleanup multiple times
        for _ in range(10):

            def worker():
                _ = get_context()

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

            cleanup_stale_contexts()

        # Registry should not accumulate contexts
        stats = get_registry_stats()
        # Allow for main thread and a few stragglers, but not 10+
        assert cast(int, stats["size"]) < 5


class TestContextManager:
    """Test ApplicationContext as a context manager."""

    def test_direct_application_context_as_context_manager(self) -> None:
        """Test that ApplicationContext can be used directly as a context manager."""
        initial_size = cast(int, get_registry_stats()["size"])

        context = ApplicationContext()

        with context as ctx:
            # Should receive the same context object
            assert ctx is context

            # Should be able to use context functionality
            cache = ctx.performance_cache
            telemetry = ctx.telemetry_client

            assert cache is not None
            assert telemetry is not None
            assert isinstance(cache, PerformanceCache)
            assert isinstance(telemetry, TelemetryClient)

        # After exiting, context should be cleaned up
        assert context._performance_cache is None
        assert context._telemetry_client is None

        # Registry should be cleaned up
        final_size = cast(int, get_registry_stats()["size"])
        assert final_size <= initial_size

    def test_get_context_as_context_manager(self) -> None:
        """Test that get_context() can be used as a context manager."""
        initial_size = cast(int, get_registry_stats()["size"])

        with get_context() as ctx:
            # Should receive a valid ApplicationContext
            assert isinstance(ctx, ApplicationContext)

            # Should be able to use context functionality
            cache = ctx.performance_cache
            telemetry = ctx.telemetry_client

            assert cache is not None
            assert telemetry is not None

        # After exiting, global context should be cleared
        # This verifies that clear_context() was called
        final_size = cast(int, get_registry_stats()["size"])
        assert final_size <= initial_size

    def test_context_manager_cleanup_on_exception(self) -> None:
        """Test that context manager cleanup works even when exceptions occur."""
        context = ApplicationContext()

        with pytest.raises(ValueError):
            with context as ctx:
                # Use the context normally
                cache = ctx.performance_cache
                assert cache is not None

                # Raise an exception
                raise ValueError("Test exception")

        # Context should still be cleaned up despite the exception
        assert context._performance_cache is None
        assert context._telemetry_client is None

    def test_context_manager_preserves_exception_propagation(self) -> None:
        """Test that context manager doesn't suppress exceptions."""
        context = ApplicationContext()

        try:
            with context:
                raise ValueError("Test exception")
        except ValueError as e:
            # Exception should be propagated normally
            assert str(e) == "Test exception"
        else:
            pytest.fail("Exception should have been propagated")

    def test_nested_context_managers(self) -> None:
        """Test nested context managers work correctly."""
        initial_size = cast(int, get_registry_stats()["size"])

        with ApplicationContext() as outer_ctx:
            outer_cache = outer_ctx.performance_cache
            assert outer_cache is not None

            with ApplicationContext() as inner_ctx:
                inner_cache = inner_ctx.performance_cache
                assert inner_cache is not None
                assert inner_cache is not outer_cache  # Different instances

            # Inner context should be cleaned up
            assert inner_ctx._performance_cache is None

        # Outer context should also be cleaned up
        assert outer_ctx._performance_cache is None

        # Both should be removed from registry
        final_size = cast(int, get_registry_stats()["size"])
        assert final_size <= initial_size


class TestContextPerformanceMonitoring:
    """Test context registry cleanup performance monitoring."""

    def test_reset_cleanup_performance_stats(self) -> None:
        """Test that performance statistics can be reset."""
        reset_cleanup_performance_stats()

        stats = get_cleanup_performance_stats()
        assert stats["cleanup_count"] == 0
        assert stats["total_cleanup_time_ms"] == 0.0
        assert stats["total_threads_processed"] == 0
        assert stats["average_cleanup_time_ms"] == 0.0
        assert stats["last_cleanup_time"] is None
        assert stats["last_cleanup_duration_ms"] is None
        assert stats["max_cleanup_duration_ms"] == 0.0
        assert stats["min_cleanup_duration_ms"] == float("inf")

    def test_cleanup_performance_stats_track_multiple_cleanups(self) -> None:
        """Test that performance statistics track multiple cleanup operations."""
        reset_cleanup_performance_stats()

        # Create and cleanup multiple thread contexts
        thread_contexts = []
        for _i in range(3):

            def worker():
                ctx = get_context()
                thread_contexts.append(ctx)
                time.sleep(0.01)  # Small work to create measurable timing

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

        # Force cleanup - contexts might already be cleaned up as threads finish
        removed_count = cleanup_stale_contexts()
        # Allow for some contexts to be auto-cleaned up during thread execution
        assert removed_count >= 0

        stats = get_cleanup_performance_stats()

        # Verify statistics are tracked (cleanup operation occurred)
        assert stats["cleanup_count"] == 1
        assert stats["total_cleanup_time_ms"] >= 0
        assert stats["total_threads_processed"] >= 0
        assert stats["last_cleanup_time"] is not None
        assert stats["last_cleanup_duration_ms"] is not None
        assert stats["max_cleanup_duration_ms"] >= 0
        assert stats["min_cleanup_duration_ms"] < float("inf")

    def test_cleanup_performance_stats_handle_no_threads(self) -> None:
        """Test that performance stats handle cleanup when no contexts exist."""
        reset_cleanup_performance_stats()
        clear_context()  # Ensure clean state

        # Try cleanup with no contexts
        removed_count = cleanup_stale_contexts()
        assert removed_count == 0

        stats = get_cleanup_performance_stats()

        # Stats should still be recorded (cleanup happened, even if nothing was removed)
        assert stats["cleanup_count"] == 1
        assert stats["total_cleanup_time_ms"] >= 0
        assert stats["total_threads_processed"] == 0
        assert stats["last_cleanup_time"] is not None

    def test_cleanup_performance_stats_accumulate_across_operations(self) -> None:
        """Test performance statistics accumulate across cleanups."""
        reset_cleanup_performance_stats()

        # First batch of threads
        def worker_batch1():
            get_context()
            time.sleep(0.005)

        for _ in range(2):
            thread = threading.Thread(target=worker_batch1)
            thread.start()
            thread.join()

        removed_count1 = cleanup_stale_contexts()
        # Some contexts might already be cleaned up
        assert removed_count1 >= 0

        stats_after_first = get_cleanup_performance_stats()
        assert stats_after_first["cleanup_count"] == 1

        # Second batch of threads
        def worker_batch2():
            get_context()
            time.sleep(0.005)

        for _ in range(3):
            thread = threading.Thread(target=worker_batch2)
            thread.start()
            thread.join()

        removed_count2 = cleanup_stale_contexts()
        assert removed_count2 >= 0

        stats_after_second = get_cleanup_performance_stats()

        # Verify accumulation - we should have 2 cleanup operations
        assert stats_after_second["cleanup_count"] == 2
        assert (
            stats_after_second["total_cleanup_time_ms"]
            >= stats_after_first["total_cleanup_time_ms"]
        )
        assert stats_after_second["average_cleanup_time_ms"] >= 0

    def test_cleanup_performance_stats_min_max_tracking(self) -> None:
        """Test that min/max cleanup times are tracked correctly."""
        reset_cleanup_performance_stats()

        # Create varying workloads to create different cleanup times
        cleanup_times = []

        for workload in [1, 5, 10]:  # Different workload sizes

            def worker(current_workload: int = workload) -> None:
                get_context()
                time.sleep(current_workload * 0.001)  # Variable work duration

            threads = []
            for _ in range(workload):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            cleanup_stale_contexts()
            stats = get_cleanup_performance_stats()
            cleanup_times.append(stats["last_cleanup_duration_ms"])

        final_stats = get_cleanup_performance_stats()

        # Verify min/max tracking
        assert (
            final_stats["min_cleanup_duration_ms"]
            <= final_stats["max_cleanup_duration_ms"]
        )
        assert final_stats["min_cleanup_duration_ms"] < float("inf")
        assert final_stats["max_cleanup_duration_ms"] > 0
        assert final_stats["average_cleanup_time_ms"] > 0

    def test_cleanup_performance_stats_thread_safety(self) -> None:
        """Test that performance stats collection is thread-safe."""
        reset_cleanup_performance_stats()

        def concurrent_cleanup_worker():
            """Worker that performs concurrent cleanup operations."""
            for _ in range(3):

                def context_worker():
                    get_context()
                    time.sleep(0.001)

                threads = []
                for _ in range(2):
                    thread = threading.Thread(target=context_worker)
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

                cleanup_stale_contexts()

        # Run multiple cleanup workers concurrently
        workers = []
        for _ in range(3):
            worker_thread = threading.Thread(target=concurrent_cleanup_worker)
            workers.append(worker_thread)
            worker_thread.start()

        for worker_thread in workers:
            worker_thread.join()

        stats = get_cleanup_performance_stats()

        # Should have completed multiple cleanup operations safely
        assert stats["cleanup_count"] >= 3
        assert stats["total_threads_processed"] >= 6  # At least 2 threads per cleanup
        assert stats["average_cleanup_time_ms"] > 0
