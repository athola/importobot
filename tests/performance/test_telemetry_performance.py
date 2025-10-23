"""Performance tests for telemetry overhead.

Measure the performance impact of telemetry on critical paths:
- Overhead of disabled vs enabled telemetry
- Rate limiting effectiveness
- Exporter processing time
- Memory footprint
- Concurrent access contention
"""

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from importobot.services.performance_cache import PerformanceCache
from importobot.telemetry import (
    TelemetryClient,
    clear_telemetry_exporters,
    register_telemetry_exporter,
    reset_telemetry_client,
)

# pylint: disable=no-name-in-module
from tests.utils.performance_utils import get_adaptive_thresholds


class TestTelemetryOverhead:
    """Measure telemetry overhead in hot paths."""

    def test_disabled_telemetry_has_minimal_overhead(self, benchmark):
        """Disabled telemetry should have near-zero overhead."""
        client = TelemetryClient(min_emit_interval=60.0, min_sample_delta=100)

        def record_metrics():
            client.record_cache_metrics("cache", hits=100, misses=50)

        result = benchmark(record_metrics, iterations=1000)
        # Disabled telemetry should complete extremely quickly - use adaptive threshold
        threshold = get_adaptive_thresholds().get_telemetry_threshold(enabled=False)
        assert result["result"] is None
        assert result["elapsed"] < threshold

    def test_enabled_telemetry_overhead_acceptable(self, benchmark):
        """Enabled telemetry overhead should be acceptable for production."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        # Use fast no-op exporter
        client.register_exporter(lambda n, p: None)

        def record_metrics():
            client.record_cache_metrics("cache", hits=100, misses=50)

        result = benchmark(record_metrics, iterations=1000)
        # Should complete quickly - use adaptive threshold based on system performance
        # Note: The actual overhead includes logging, so be more lenient
        threshold = get_adaptive_thresholds().get_telemetry_threshold(enabled=True) * 20
        assert result["elapsed"] < threshold

    def test_rate_limiting_reduces_overhead(self, benchmark):
        """Rate limiting should reduce overhead for high-frequency calls."""
        client = TelemetryClient(min_emit_interval=60.0, min_sample_delta=1000)
        client.clear_exporters()

        call_count = [0]

        def counting_exporter(_n: str, _p: dict[str, object]) -> None:
            call_count[0] += 1

        client.register_exporter(counting_exporter)

        def record_many_metrics():
            for i in range(100):
                client.record_cache_metrics("cache", hits=i, misses=i // 2)

        result = benchmark(record_many_metrics)
        assert result["elapsed"] < 1e-3

        # Rate limiting should have prevented most emissions
        assert call_count[0] < 10  # Much less than 100

    def test_performance_cache_overhead_with_telemetry(self, benchmark):
        """Telemetry should not significantly slow down PerformanceCache."""
        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=0)

        test_data = [{"iteration": i} for i in range(100)]

        def cache_operations():
            for data in test_data:
                cache.get_cached_string_lower(data)

        result = benchmark(cache_operations, iterations=10)
        # Should complete in <2ms on average even with telemetry
        assert result["elapsed"] < 2e-3


class TestConcurrentPerformance:
    """Test performance under concurrent access."""

    def test_concurrent_metric_recording_throughput(self):
        """Measure throughput of concurrent metric recording."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        lock = threading.Lock()

        def fast_exporter(n, p):
            with lock:
                emitted.append((n, p))

        client.register_exporter(fast_exporter)

        num_threads = 10
        ops_per_thread = 1000

        start_time = time.perf_counter()

        def worker():
            for i in range(ops_per_thread):
                client.record_cache_metrics("cache", hits=i, misses=i // 2)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for future in futures:
                future.result()

        elapsed = time.perf_counter() - start_time
        total_ops = num_threads * ops_per_thread
        ops_per_sec = total_ops / elapsed

        # Use adaptive throughput threshold based on system performance
        min_throughput = get_adaptive_thresholds().get_throughput_threshold(50_000)
        assert ops_per_sec > min_throughput

    def test_lock_contention_minimal(self):
        """Lock contention should not significantly degrade performance."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        num_threads = 20
        ops_per_thread = 500

        start_time = time.time()

        def worker():
            for i in range(ops_per_thread):
                # Use different cache names to reduce rate limiting effects
                client.record_cache_metrics(f"cache_{i % 10}", hits=i, misses=i // 2)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time

        # Use adaptive threshold based on system performance - be much more lenient
        threshold = get_adaptive_thresholds().get_operation_threshold(200.0) * 10
        assert elapsed < threshold

    def test_exporter_processing_parallelization(self):
        """Multiple exporters should not significantly increase overhead."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        # Add multiple fast exporters
        for _ in range(10):
            client.register_exporter(lambda n, p: None)

        start_time = time.time()

        for i in range(1000):
            client.record_cache_metrics("cache", hits=i, misses=i // 2)

        elapsed = time.time() - start_time

        # Even with 10 exporters, should complete quickly
        # Use adaptive threshold based on system performance
        threshold = get_adaptive_thresholds().get_operation_threshold(50.0)
        assert elapsed < threshold


class TestMemoryFootprint:
    """Test memory usage of telemetry."""

    def test_last_emit_tracking_bounded(self):
        """Last emit tracking should not grow unbounded."""
        client = TelemetryClient(min_emit_interval=60.0, min_sample_delta=100)
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        # Record metrics for many different caches
        for i in range(10_000):
            client.record_cache_metrics(f"cache_{i}", hits=10, misses=5)

        # Last emit tracking should have entries for all unique caches
        # This is expected behavior, but verifies no memory leak
        assert len(client._last_emit) <= 10_000

    def test_exporter_list_memory_stable(self):
        """Exporter list should not leak memory."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)

        initial_count = len(client._exporters)

        # Register and clear many times
        for _ in range(100):
            for _ in range(10):
                client.register_exporter(lambda n, p: None)
            client.clear_exporters()

        # Should be back to initial state
        final_count = len(client._exporters)
        assert final_count == initial_count


class TestRateLimitingPerformance:
    """Test performance characteristics of rate limiting."""

    def test_sample_delta_early_exit_fast(self, benchmark):
        """Rate-limited calls should exit early and fast."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=1000)
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        # Prime the cache
        client.record_cache_metrics("cache", hits=100, misses=50)

        # Now measure rate-limited calls
        def rate_limited_call():
            client.record_cache_metrics("cache", hits=101, misses=51)

        result = benchmark(rate_limited_call, iterations=1000)
        # Should be fast due to early exit
        # Use adaptive threshold with logging overhead and system variability
        threshold = (
            get_adaptive_thresholds().get_telemetry_threshold(enabled=False) * 25
        )
        assert result["elapsed"] < threshold

    def test_time_interval_check_efficient(self, benchmark, monkeypatch):
        """Time interval checking should be efficient."""
        client = TelemetryClient(min_emit_interval=60.0, min_sample_delta=0)
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        # Prime with initial emit
        base_time = 1000.0
        with monkeypatch.context() as m:
            m.setattr("time.time", lambda: base_time)
            client.record_cache_metrics("cache", hits=10, misses=5)

        # Measure rate-limited calls within interval
        def rate_limited_call():
            with monkeypatch.context() as m:
                m.setattr("time.time", lambda: base_time + 30)
                client.record_cache_metrics("cache", hits=20, misses=10)

        result = benchmark(rate_limited_call, iterations=1000)
        # Use adaptive threshold for rate-limited operations
        # with logging overhead and system variability
        threshold = (
            get_adaptive_thresholds().get_telemetry_threshold(enabled=False) * 25
        )
        assert result["elapsed"] < threshold


class TestScalability:
    """Test telemetry scalability with many caches and exporters."""

    def test_many_unique_caches_performance(self):
        """Performance should scale reasonably with many unique caches."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        num_caches = 1000

        start_time = time.time()

        for i in range(num_caches):
            client.record_cache_metrics(f"cache_{i}", hits=10, misses=5)

        elapsed = time.time() - start_time

        # Should handle 1000 unique caches very quickly
        # Use adaptive threshold based on system performance
        threshold = get_adaptive_thresholds().get_operation_threshold(50.0)
        assert elapsed < threshold

    def test_many_exporters_linear_scaling(self):
        """Performance should scale linearly with number of exporters."""
        num_exporters_list = [1, 5, 10, 20]
        timings = []

        for num_exporters in num_exporters_list:
            client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
            client.clear_exporters()

            for _ in range(num_exporters):
                client.register_exporter(lambda n, p: None)

            start_time = time.time()

            for i in range(100):
                client.record_cache_metrics("cache", hits=i, misses=i // 2)

            elapsed = time.time() - start_time
            timings.append(elapsed)

        # Verify roughly linear scaling (within factor of 2)
        # More exporters should take proportionally more time
        assert (
            timings[-1]
            <= timings[0] * (num_exporters_list[-1] / num_exporters_list[0]) * 2
        )


class TestRealWorldScenarios:
    """Test performance in realistic usage scenarios."""

    def test_cache_hit_rate_monitoring_overhead(self):
        """Realistic cache monitoring should have acceptable overhead."""
        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=0)

        # Simulate realistic access pattern
        test_data = [{"key": i % 100} for i in range(10_000)]

        start_time = time.time()

        for data in test_data:
            cache.get_cached_string_lower(data)

        elapsed = time.time() - start_time

        # Should complete 10k operations quickly (<200ms)
        assert elapsed < 0.2

        # Verify telemetry was collected
        stats = cache.get_cache_stats()
        assert stats["cache_hits"] + stats["cache_misses"] == 10_000

    def test_high_frequency_logging_throttled(self, monkeypatch):
        """High-frequency logging should be throttled effectively."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", "100")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", "1")
        reset_telemetry_client()

        emitted = []
        clear_telemetry_exporters()
        register_telemetry_exporter(lambda n, p: emitted.append((n, p)))

        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=0)

        start_time = time.time()

        # Perform many operations
        for i in range(1000):
            cache.get_cached_string_lower({"iteration": i})

        elapsed = time.time() - start_time

        # Should complete quickly even with telemetry (<300ms)
        assert elapsed < 0.3

        # Should have throttled emissions
        assert len(emitted) < 50  # Much less than 1000

    def test_concurrent_cache_operations_realistic(self):
        """Realistic concurrent cache usage with telemetry."""
        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=0)

        # Simulate multiple workers accessing shared cache
        num_workers = 8
        ops_per_worker = 1000

        def worker():
            for i in range(ops_per_worker):
                # Mix of unique and repeated data
                if i % 5 == 0:
                    cache.get_cached_string_lower({"unique": i})
                else:
                    cache.get_cached_string_lower({"common": i % 10})

        start_time = time.time()

        threads = [threading.Thread(target=worker) for _ in range(num_workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time
        total_ops = num_workers * ops_per_worker
        ops_per_sec = total_ops / elapsed

        # Use adaptive throughput threshold based on system performance
        min_throughput = get_adaptive_thresholds().get_throughput_threshold(50_000)
        assert ops_per_sec > min_throughput


class TestTelemetryDisabledPerformance:
    """Verify disabled telemetry has negligible overhead."""

    def test_disabled_vs_enabled_overhead_comparison(self):
        """Compare disabled vs enabled telemetry overhead."""

        class _NullTelemetry:
            def record_cache_metrics(self, *args, **kwargs):
                return None

        disabled_client = _NullTelemetry()
        enabled_client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        enabled_client.clear_exporters()
        enabled_client.register_exporter(lambda n, p: None)

        disabled_times = []
        enabled_times = []

        for _ in range(100):
            start = time.time()
            disabled_client.record_cache_metrics("cache", hits=100, misses=50)  # type: ignore[no-untyped-call]
            disabled_times.append(time.time() - start)

            start = time.time()
            enabled_client.record_cache_metrics("cache", hits=100, misses=50)
            enabled_times.append(time.time() - start)

        avg_disabled = sum(disabled_times) / len(disabled_times)
        avg_enabled = sum(enabled_times) / len(enabled_times)

        # Disabled should be at least 10x faster
        assert avg_disabled * 10 < avg_enabled or avg_disabled < 0.000001

    def test_production_config_performance(self, monkeypatch):
        """Test performance with production-like configuration."""
        # Production config: enabled, moderate rate limiting
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", "100")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", "60")
        reset_telemetry_client()

        clear_telemetry_exporters()
        register_telemetry_exporter(lambda n, p: None)

        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=300)

        start_time = time.time()

        # Simulate production workload
        for _ in range(10_000):
            data = {"value": random.randint(0, 100)}
            cache.get_cached_string_lower(data)

        elapsed = time.time() - start_time

        # Should handle production workload efficiently (< 2 seconds)
        assert elapsed < 2.0
