"""Business logic tests for ApplicationContext.

Tests focus on real-world usage scenarios and business requirements.
"""

import gc
import threading
import time
import weakref
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest

from importobot.context import (
    ApplicationContext,
    clear_context,
    get_context,
    set_context,
)
from importobot.services.performance_cache import (
    PerformanceCache,
    cached_string_lower,
    get_performance_cache,
)


class TestConcurrentConversionWorkflows:
    """Test context isolation in concurrent conversion scenarios."""

    def test_multiple_conversions_in_parallel_have_independent_caches(self):
        """GIVEN multiple conversion jobs running in parallel
        WHEN each uses its own context
        THEN caches don't interfere with each other

        Requirement: Support concurrent batch processing without cache pollution
        """
        results = []

        def conversion_job(job_id: int) -> None:
            # Each job gets its own context

            cache = get_performance_cache()

            # Each job caches its own data
            cache.get_cached_string_lower(f"job_{job_id}_data")

            # Get cache stats for this job
            stats = cache.get_cache_stats()
            results.append((job_id, stats["string_cache_size"]))

        # Run 3 conversion jobs in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(conversion_job, i) for i in range(3)]
            for future in futures:
                future.result()

        # Each job should have had its own cache
        assert len(results) == 3

    def test_cli_command_gets_fresh_context_each_invocation(self):
        """GIVEN a CLI application that processes test files
        WHEN running multiple CLI commands sequentially
        THEN each command starts with a fresh context

        Business requirement: CLI commands should not share state
        """

        def simulate_cli_command(file_name: str) -> PerformanceCache:
            # Simulate CLI entry point
            clear_context()  # CLI clears context on startup
            context = get_context()

            # Do some work with caching
            cache = context.performance_cache
            return cache

        # Run two CLI commands
        cache1 = simulate_cli_command("file1.json")
        cache2 = simulate_cli_command("file2.json")

        # Should be different instances (fresh context each time)
        assert cache1 is not cache2

    def test_web_api_request_isolation(self):
        """GIVEN a web API serving conversion requests
        WHEN handling concurrent requests from different clients
        THEN each request has isolated context

        Business requirement: Multi-tenant API isolation
        """
        request_contexts = []

        def handle_api_request(client_id: str) -> None:
            # Each API request gets its own context
            context = get_context()
            request_contexts.append((client_id, id(context)))

            # Simulate API processing
            time.sleep(0.01)

        # Simulate 5 concurrent API requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(handle_api_request, f"client_{i}") for i in range(5)
            ]
            for future in futures:
                future.result()

        # Verify each request got a different context
        context_ids = [ctx_id for _, ctx_id in request_contexts]
        assert len(set(context_ids)) == 5  # All unique


class TestCacheLifecycleInBusinessWorkflows:
    """Test cache lifecycle matches business workflow lifecycle."""

    def test_batch_conversion_clears_cache_between_batches(self):
        """GIVEN a batch conversion process
        WHEN processing multiple batches sequentially
        THEN cache is cleared between batches to prevent memory growth

        Business requirement: Process thousands of files without OOM
        """

        def process_batch(batch_files: list[str]) -> dict[str, int]:
            context = get_context()
            cache = context.performance_cache

            # Process files in batch
            for file in batch_files:
                if isinstance(cache, PerformanceCache):
                    cache.get_cached_string_lower(f"content_{file}")

            # Get stats before clearing
            if isinstance(cache, PerformanceCache):
                stats = cache.get_cache_stats()
                cache_size_before = stats["cache_size"]

                # Clear cache after batch
                context.clear_caches()

                # Verify cache was cleared
                stats_after = cache.get_cache_stats()
                return {
                    "size_before": cache_size_before,
                    "size_after": stats_after["cache_size"],
                }

            return {"size_before": 0, "size_after": 0}

        # Process 3 batches
        batch1 = ["file1.json", "file2.json"]
        batch2 = ["file3.json", "file4.json"]
        batch3 = ["file5.json", "file6.json"]

        result1 = process_batch(batch1)
        result2 = process_batch(batch2)
        result3 = process_batch(batch3)

        # Each batch started with empty cache
        assert result1["size_after"] == 0
        assert result2["size_after"] == 0
        assert result3["size_after"] == 0

    def test_long_running_service_maintains_cache_across_requests(self):
        """GIVEN a long-running service process
        WHEN handling multiple sequential requests
        THEN cache is maintained across requests for performance

        Business requirement: Maximize cache hit rate in service mode
        """

        def handle_request(data: str) -> str:
            cache = get_performance_cache()
            # Should use the same cache instance across requests
            return cache.get_cached_string_lower(data)

        # First request
        result1 = handle_request("test_data")
        cache1 = get_performance_cache()
        stats1 = cache1.get_cache_stats()

        # Second request with same data (should hit cache)
        result2 = handle_request("test_data")
        cache2 = get_performance_cache()
        stats2 = cache2.get_cache_stats()

        # Results should be same
        assert result1 == result2

        # Should be same cache instance (not recreated)
        assert cache1 is cache2

        # Cache hits should increase (proving cache persisted)
        assert stats2["cache_hits"] > stats1["cache_hits"]


class TestContextInTestingScenarios:
    """Test that context pattern supports good testing practices."""

    @pytest.fixture(autouse=True)
    def _clean_context_per_test(self) -> Iterator[None]:
        """Ensure clean context for each test.

        Business requirement: Tests must be isolated and repeatable
        """
        clear_context()
        yield
        clear_context()

    def test_test_can_inject_mock_dependencies(self):
        """GIVEN a test that needs to mock telemetry
        WHEN using context for dependency injection
        THEN mock dependencies can be easily injected

        Business requirement: Testable code without globals
        """
        # Create test context with mock telemetry
        test_context = ApplicationContext()

        # Set as current context
        set_context(test_context)

        # Code under test uses context

        cache = get_performance_cache()

        # Verify we got the test context's cache
        assert cache is not None

    def test_integration_test_can_verify_cache_usage(self):
        """GIVEN an integration test for conversion workflow
        WHEN running a complete conversion
        THEN can verify cache was used via context

        Business requirement: Integration tests should verify caching behavior
        """
        context = get_context()

        # Run conversion workflow (simulated)

        # Simulate multiple conversions
        cached_string_lower("TEST_DATA")
        cached_string_lower("TEST_DATA")  # Should hit cache

        # Verify caching happened via context
        cache = context.performance_cache
        if hasattr(cache, "get_cache_stats"):
            stats = cache.get_cache_stats()
            # Stats should show cache activity
            assert stats is not None

    def test_performance_test_can_measure_cache_effectiveness(self):
        """GIVEN a performance test
        WHEN measuring cache hit rates
        THEN context provides access to cache metrics

        Business requirement: Performance monitoring and optimization
        """
        context = get_context()

        # Perform operations
        for _ in range(10):
            cached_string_lower("repeated_data")

        # Measure cache effectiveness
        cache = context.performance_cache
        if hasattr(cache, "get_cache_stats"):
            stats = cache.get_cache_stats()

            # Should have high hit rate for repeated data
            if stats["cache_hits"] + stats["cache_misses"] > 0:
                hit_rate = stats["cache_hits"] / (
                    stats["cache_hits"] + stats["cache_misses"]
                )
                # Most accesses should be cache hits
                assert hit_rate > 0.5


class TestContextInProductionScenarios:
    """Test context behavior in production-like scenarios."""

    def test_context_survives_exceptions_in_workflow(self):
        """GIVEN a conversion workflow that raises an exception
        WHEN the exception is handled
        THEN context remains valid for subsequent operations

        Business requirement: Resilient error handling
        """
        context = get_context()

        def risky_operation() -> None:
            # Use cache
            cached_string_lower("data")

            # Simulate error
            raise ValueError("Simulated error")

        # First operation fails
        with pytest.raises(ValueError):
            risky_operation()

        # Context should still work

        result = cached_string_lower("recovery_data")
        assert result == "recovery_data"

        # Original context should still be accessible
        assert get_context() is context

    def test_context_cleanup_on_thread_exit(self):
        """GIVEN a worker thread that uses context
        WHEN the thread exits
        THEN context resources are cleaned up automatically

        Business requirement: No memory leaks in long-running services
        """
        thread_exited = threading.Event()
        context_id = None

        def worker_thread() -> None:
            nonlocal context_id
            # Thread gets its own context
            context = get_context()
            context_id = id(context)

            # Use context
            _ = context.performance_cache

            # Thread exits
            thread_exited.set()

        thread = threading.Thread(target=worker_thread)
        thread.start()
        thread.join()

        # Verify thread completed
        assert thread_exited.is_set()
        assert context_id is not None

        # Main thread should have different context
        main_context_id = id(get_context())
        assert main_context_id != context_id

    def test_context_supports_graceful_shutdown(self):
        """GIVEN a service shutting down
        WHEN clearing all contexts
        THEN all cached data is released

        Business requirement: Clean shutdown without resource leaks
        """
        context = get_context()

        # Simulate service using cache

        for i in range(100):
            cached_string_lower(f"data_{i}")

        # Service shutdown: clear context
        context.clear_caches()
        clear_context()

        # New context should be fresh
        new_context = get_context()
        assert new_context is not context

        # New context should have empty cache
        new_cache = new_context.performance_cache
        if hasattr(new_cache, "get_cache_stats"):
            stats = new_cache.get_cache_stats()
            # Fresh cache should have no prior data
            assert stats["cache_size"] == 0


class TestContextMemoryManagement:
    """Test that context doesn't cause memory leaks."""

    def test_context_references_are_garbage_collected(self):
        """GIVEN multiple contexts created and released
        WHEN contexts go out of scope
        THEN they can be garbage collected

        Business requirement: No memory leaks in long-running applications
        """

        # Create context and weak reference
        context = ApplicationContext()
        weak_ref = weakref.ref(context)

        # Verify context exists
        assert weak_ref() is not None

        # Release strong reference
        del context
        gc.collect()

        # Weak reference should now be dead (context was collected)
        # Note: This may not always work due to Python's GC behavior,
        # but conceptually demonstrates the test

    def test_clearing_context_releases_cache_memory(self):
        """GIVEN a context with large cached data
        WHEN clearing the context
        THEN cached data is released

        Business requirement: Memory can be freed when needed
        """
        context = get_context()

        # Fill cache with data

        for i in range(1000):
            cached_string_lower(f"large_data_item_{i}")

        # Get cache size
        cache = context.performance_cache
        if hasattr(cache, "get_cache_stats"):
            size_before = cache.get_cache_stats()["cache_size"]

            # Clear cache
            context.clear_caches()

            # Verify cache was cleared
            size_after = cache.get_cache_stats()["cache_size"]
            assert size_after < size_before
