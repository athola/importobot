"""Performance regression tests for caching system.

Uses adaptive thresholds to account for machine performance differences.
"""

import random
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor

import pytest

from importobot.caching import CacheConfig, LRUCache, SecurityPolicy
from importobot.context import clear_context, get_context
from importobot.services.performance_cache import cached_string_lower
from tests.utils.performance_utils import get_adaptive_thresholds

# All performance tests are marked as slow
pytestmark = pytest.mark.slow


class TestCachePerformanceCharacteristics:
    """Test cache performance meets business requirements."""

    @pytest.fixture(autouse=True)
    def setup(self) -> Generator[None, None, None]:
        """Set up adaptive thresholds for this test session."""
        self.thresholds = get_adaptive_thresholds()
        clear_context()
        yield
        clear_context()

    def test_cache_lookup_is_fast(self) -> None:
        """GIVEN a cache with 1000 entries
        WHEN looking up a cached value
        THEN lookup completes within adaptive threshold

        Business requirement: Cache shouldn't add significant latency
        """
        cache = LRUCache[str, str]()

        # Populate cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        # Measure lookup time
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            _ = cache.get("key_500")
        end = time.perf_counter()

        avg_lookup_time_ms = ((end - start) / iterations) * 1000

        # Use adaptive threshold (base: 1ms, adjust for system)
        threshold = self.thresholds.get_operation_threshold(1.0)

        assert avg_lookup_time_ms < threshold, (
            f"Cache lookup too slow: {avg_lookup_time_ms:.3f}ms > {threshold:.3f}ms "
            f"(perf factor: {self.thresholds.system.performance_factor:.2f})"
        )

    def test_cache_scales_to_large_datasets(self) -> None:
        """GIVEN a cache handling 10,000 entries
        WHEN accessing entries randomly
        THEN performance remains consistent

        Business requirement: Cache performance doesn't degrade with size
        """
        config = CacheConfig(max_size=10000)
        cache = LRUCache[int, str](config=config)

        # Populate with 10k entries
        for i in range(10000):
            cache.set(i, f"value_{i}")

        times = []
        for _ in range(20):
            key = random.randint(0, 9999)
            start = time.perf_counter()
            _ = cache.get(key)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Use adaptive thresholds
        avg_threshold = self.thresholds.get_operation_threshold(1.0)
        max_threshold = self.thresholds.get_operation_threshold(2.0)

        assert avg_time < avg_threshold, (
            f"Average lookup time too slow: {avg_time:.3f}ms > {avg_threshold:.3f}ms"
        )
        assert max_time < max_threshold, (
            f"Max lookup time too slow: {max_time:.3f}ms > {max_threshold:.3f}ms"
        )

    @pytest.mark.timeout(10)
    def test_cache_eviction_performance(self) -> None:
        """GIVEN a cache at capacity
        WHEN continuously adding new entries (causing evictions)
        THEN eviction overhead is minimal

        Business requirement: Eviction shouldn't block operations
        """
        config = CacheConfig(max_size=100)
        cache = LRUCache[int, str](config=config)

        # Fill cache
        for i in range(100):
            cache.set(i, f"value_{i}")

        # Measure time for evictions
        eviction_count = 1000
        start = time.perf_counter()
        for i in range(100, 100 + eviction_count):
            cache.set(i, f"value_{i}")
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_eviction_time_ms = total_time_ms / eviction_count

        # Evictions should be fast (base: 0.1ms per eviction)
        threshold = self.thresholds.get_operation_threshold(0.1)

        assert avg_eviction_time_ms < threshold, (
            f"Eviction too slow: {avg_eviction_time_ms:.4f}ms > {threshold:.4f}ms"
        )


class TestCacheMemoryEfficiency:
    """Test cache memory usage meets requirements."""

    def test_cache_respects_size_limits(self) -> None:
        """GIVEN a cache with max_size=100
        WHEN adding 1000 entries
        THEN cache never exceeds 100 entries

        Business requirement: Bounded memory usage
        """
        config = CacheConfig(max_size=100)
        cache = LRUCache[int, str](config=config)

        for i in range(1000):
            cache.set(i, f"value_{i}")
            stats = cache.get_stats()
            assert stats["cache_size"] <= 100

    def test_ttl_prevents_unbounded_memory_growth(self) -> None:
        """GIVEN a cache with TTL=1 second
        WHEN entries expire
        THEN memory is freed automatically

        Business requirement: Long-running processes don't leak memory
        """
        config = CacheConfig(max_size=1000, ttl_seconds=1)
        cache = LRUCache[int, str](config=config)

        # Add entries
        for i in range(100):
            cache.set(i, f"value_{i}")

        initial_size = cache.get_stats()["cache_size"]
        assert initial_size == 100

        # Wait for TTL
        time.sleep(1.2)

        # Trigger cleanup and check cache size (without accessing entries, which would refresh TTL)
        cache._cleanup_expired_entries()

        # Most entries should have expired and been cleaned up
        final_size = cache.get_stats()["cache_size"]
        assert final_size < 10, (
            f"Expected <10 entries after expiration, got {final_size}"
        )

    def test_security_limits_prevent_dos(self) -> None:
        """GIVEN a cache with content size limits
        WHEN attempting to cache extremely large values
        THEN large values are rejected to prevent DoS

        Business requirement: Protect against memory exhaustion attacks
        """
        config = CacheConfig()
        security = SecurityPolicy(max_content_size=1000)
        cache = LRUCache[str, str](config=config, security_policy=security)

        # Try to cache huge value
        huge_value = "x" * 10000  # 10KB
        cache.set("huge", huge_value)

        # Should be rejected
        assert cache.get("huge") is None
        stats = cache.get_stats()
        assert stats["rejections"] >= 1


class TestConcurrentCachePerformance:
    """Test cache performance under concurrent load."""

    @pytest.fixture(autouse=True)
    def setup(self) -> Generator[None, None, None]:
        """Set up adaptive thresholds."""
        self.thresholds = get_adaptive_thresholds()
        clear_context()
        yield
        clear_context()

    def test_cache_handles_concurrent_reads(self) -> None:
        """GIVEN a cache shared across threads
        WHEN multiple threads read simultaneously
        THEN all reads complete quickly without blocking

        Business requirement: Read-heavy workloads should be fast
        """
        cache = LRUCache[int, str]()

        # Populate cache
        for i in range(100):
            cache.set(i, f"value_{i}")

        def read_operations() -> float:
            start = time.perf_counter()
            for i in range(100):
                _ = cache.get(i % 100)
            end = time.perf_counter()
            return end - start

        # Run concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_operations) for _ in range(10)]
            times = [f.result() for f in futures]

        # All threads should complete quickly
        avg_time = sum(times) / len(times)

        # Base threshold: 100ms, adjusted for system
        threshold = self.thresholds.get_operation_threshold(100.0) / 1000.0

        assert avg_time < threshold, (
            f"Concurrent reads too slow: {avg_time:.3f}s > {threshold:.3f}s"
        )

    def test_context_isolation_has_minimal_overhead(self) -> None:
        """GIVEN multiple threads each with own context
        WHEN accessing context and cache
        THEN overhead is minimal

        Business requirement: Context pattern shouldn't slow down multi-threaded apps
        """

        def worker_task() -> float:
            start = time.perf_counter()

            # Get context (thread-local)
            context = get_context()
            _ = context.performance_cache

            # Do some work
            for i in range(10):
                _ = cached_string_lower(f"data_{i}")

            end = time.perf_counter()
            return end - start
            return end - start

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_task) for _ in range(20)]
            times = [f.result() for f in futures]

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Base thresholds: 50ms average, 200ms worst case
        avg_threshold = self.thresholds.get_operation_threshold(50.0) / 1000.0
        max_threshold = self.thresholds.get_operation_threshold(200.0) / 1000.0

        assert avg_time < avg_threshold, (
            f"Average context overhead too high: {avg_time:.3f}s > {avg_threshold:.3f}s"
        )
        assert max_time < max_threshold, (
            f"Max context overhead too high: {max_time:.3f}s > {max_threshold:.3f}s"
        )


class TestCacheHitRateOptimization:
    """Test cache achieves good hit rates in realistic scenarios."""

    def test_conversion_workflow_achieves_high_hit_rate(self) -> None:
        """GIVEN a typical conversion workflow with repeated strings
        WHEN processing multiple test cases
        THEN cache hit rate is > 50%

        Business requirement: Cache should be effective for real workloads
        """
        clear_context()

        # Simulate realistic conversion workflow
        common_actions = ["Initialize", "Login", "Navigate", "Verify", "Logout"]
        common_expectations = ["Success", "Pass", "Complete", "Ready"]

        for test_num in range(20):
            for action in common_actions:
                _ = cached_string_lower(action)
            for expectation in common_expectations:
                _ = cached_string_lower(expectation)
            _ = cached_string_lower(f"Test_{test_num}")

        # Check hit rate
        context = get_context()
        cache = context.performance_cache

        if hasattr(cache, "get_stats"):
            stats = cache.get_stats()
            total = stats["cache_hits"] + stats["cache_misses"]

            if total > 0:
                hit_rate = stats["cache_hits"] / total
                assert hit_rate > 0.5, (
                    f"Cache hit rate too low: {hit_rate:.2%} "
                    f"(hits: {stats['cache_hits']}, misses: {stats['cache_misses']})"
                )

    def test_batch_processing_improves_hit_rate_over_time(self) -> None:
        """GIVEN a batch of files being processed
        WHEN processing files sequentially
        THEN hit rate improves with each batch

        Business requirement: Batch processing should benefit from cache warming
        """
        clear_context()

        hit_rates = []

        for _batch in range(5):
            # Process batch with repeated patterns
            for _ in range(10):
                _ = cached_string_lower("common_pattern_shared")

            # Measure hit rate
            context = get_context()
            cache = context.performance_cache

            if hasattr(cache, "get_stats"):
                stats = cache.get_stats()
                total = stats["cache_hits"] + stats["cache_misses"]
                if total > 0:
                    hit_rates.append(stats["cache_hits"] / total)

        # Hit rate should improve over time
        if len(hit_rates) >= 2:
            assert hit_rates[-1] > hit_rates[0], (
                f"Hit rate didn't improve: first={hit_rates[0]:.2%}, "
                f"last={hit_rates[-1]:.2%}"
            )
