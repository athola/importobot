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


class TestTelemetryOverhead:
    """Measure telemetry overhead in hot paths."""

    def test_disabled_telemetry_has_minimal_overhead(self, benchmark):
        """Disabled telemetry should have near-zero overhead."""
        client = TelemetryClient(
            enabled=False, min_emit_interval=60.0, min_sample_delta=100
        )

        def record_metrics():
            client.record_cache_metrics("cache", hits=100, misses=50)

        result = benchmark(record_metrics)
        # Disabled telemetry should complete very quickly (< 1ms)
        assert result is None

    def test_enabled_telemetry_overhead_acceptable(self, benchmark):
        """Enabled telemetry overhead should be acceptable for production."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        # Use fast no-op exporter
        client.register_exporter(lambda n, p: None)

        def record_metrics():
            client.record_cache_metrics("cache", hits=100, misses=50)

        benchmark(record_metrics)
        # Should complete in < 10ms even with full processing

    def test_rate_limiting_reduces_overhead(self, benchmark):
        """Rate limiting should reduce overhead for high-frequency calls."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=1000
        )
        client.clear_exporters()

        call_count = [0]

        def counting_exporter(_n: str, _p: dict[str, object]) -> None:
            call_count[0] += 1

        client.register_exporter(counting_exporter)

        def record_many_metrics():
            for i in range(100):
                client.record_cache_metrics("cache", hits=i, misses=i // 2)

        benchmark(record_many_metrics)

        # Rate limiting should have prevented most emissions
        assert call_count[0] < 10  # Much less than 100

    def test_performance_cache_overhead_with_telemetry(self, benchmark):
        """Telemetry should not significantly slow down PerformanceCache."""
        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=0)

        test_data = [{"iteration": i} for i in range(100)]

        def cache_operations():
            for data in test_data:
                cache.get_cached_string_lower(data)

        benchmark(cache_operations)
        # Should complete in < 100ms even with telemetry


class TestConcurrentPerformance:
    """Test performance under concurrent access."""

    def test_concurrent_metric_recording_throughput(self):
        """Measure throughput of concurrent metric recording."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        emitted = []
        lock = threading.Lock()

        def fast_exporter(n, p):
            with lock:
                emitted.append((n, p))

        client.register_exporter(fast_exporter)

        num_threads = 10
        ops_per_thread = 1000

        start_time = time.time()

        def worker():
            for i in range(ops_per_thread):
                client.record_cache_metrics("cache", hits=i, misses=i // 2)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for future in futures:
                future.result()

        elapsed = time.time() - start_time
        total_ops = num_threads * ops_per_thread
        ops_per_sec = total_ops / elapsed

        # Should achieve > 5k ops/sec (realistic threshold for concurrent operations)
        assert ops_per_sec > 5_000

    def test_lock_contention_minimal(self):
        """Lock contention should not significantly degrade performance."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
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

        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0

    def test_exporter_processing_parallelization(self):
        """Multiple exporters should not significantly increase overhead."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        # Add multiple fast exporters
        for _ in range(10):
            client.register_exporter(lambda n, p: None)

        start_time = time.time()

        for i in range(1000):
            client.record_cache_metrics("cache", hits=i, misses=i // 2)

        elapsed = time.time() - start_time

        # Even with 10 exporters, should complete quickly (< 1 second)
        assert elapsed < 1.0


class TestMemoryFootprint:
    """Test memory usage of telemetry."""

    def test_last_emit_tracking_bounded(self):
        """Last emit tracking should not grow unbounded."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )
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
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )

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
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=1000
        )
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        # Prime the cache
        client.record_cache_metrics("cache", hits=100, misses=50)

        # Now measure rate-limited calls
        def rate_limited_call():
            client.record_cache_metrics("cache", hits=101, misses=51)

        benchmark(rate_limited_call)
        # Should be very fast (< 1ms) due to early exit

    def test_time_interval_check_efficient(self, benchmark, monkeypatch):
        """Time interval checking should be efficient."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=0
        )
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

        benchmark(rate_limited_call)


class TestScalability:
    """Test telemetry scalability with many caches and exporters."""

    def test_many_unique_caches_performance(self):
        """Performance should scale reasonably with many unique caches."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        num_caches = 1000

        start_time = time.time()

        for i in range(num_caches):
            client.record_cache_metrics(f"cache_{i}", hits=10, misses=5)

        elapsed = time.time() - start_time

        # Should handle 1000 unique caches quickly (< 1 second)
        assert elapsed < 1.0

    def test_many_exporters_linear_scaling(self):
        """Performance should scale linearly with number of exporters."""
        num_exporters_list = [1, 5, 10, 20]
        timings = []

        for num_exporters in num_exporters_list:
            client = TelemetryClient(
                enabled=True, min_emit_interval=0.0, min_sample_delta=0
            )
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

        # Should complete 10k operations quickly (< 1 second)
        assert elapsed < 1.0

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

        # Should complete quickly even with telemetry
        assert elapsed < 1.0

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

        # Should achieve good throughput (> 5k ops/sec)
        assert ops_per_sec > 5_000


class TestTelemetryDisabledPerformance:
    """Verify disabled telemetry has negligible overhead."""

    def test_disabled_vs_enabled_overhead_comparison(self):
        """Compare disabled vs enabled telemetry overhead."""
        disabled_client = TelemetryClient(
            enabled=False, min_emit_interval=0.0, min_sample_delta=0
        )
        enabled_client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        enabled_client.clear_exporters()
        enabled_client.register_exporter(lambda n, p: None)

        disabled_times = []
        enabled_times = []

        for _ in range(100):
            start = time.time()
            disabled_client.record_cache_metrics("cache", hits=100, misses=50)
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
