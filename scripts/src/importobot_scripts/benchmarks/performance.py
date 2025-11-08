#!/usr/bin/env python3
"""Comprehensive performance benchmarks for Importobot.

This script validates performance across multiple domains:
1. LRU cache cleanup (O(n) → O(log n) per entry removal)
2. Context registry cleanup monitoring
3. JSON to Robot conversion operations
4. Bulk conversion performance
5. API method comparisons
6. Lazy loading performance

Usage:
    python -m importobot_scripts.benchmarks.performance [options]
    # OR
    python scripts/src/importobot_scripts/benchmarks/performance.py [options]
"""

import argparse
import json
import random
import tempfile
import threading
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from importobot.caching.lru_cache import CacheConfig, LRUCache
from importobot.context import (
    cleanup_stale_contexts,
    get_cleanup_performance_stats,
    get_context,
    reset_cleanup_performance_stats,
)
from importobot.core.business_domains import (
    BusinessDomainTemplates,
)
from importobot.core.converter import (
    convert_file,
)


class ComplexityLevel(Enum):
    """Enumeration of test case complexity levels."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class BenchmarkType(Enum):
    """Types of benchmarks that can be run."""

    CACHE = "cache"
    CONTEXT = "context"
    CONVERSION = "conversion"
    ALL = "all"


class CachePerformanceBenchmark:
    """Benchmarks for LRU cache performance optimizations."""

    def benchmark_cache_cleanup(self) -> dict[str, Any]:
        """Benchmark cache cleanup performance with various cache sizes."""
        results = {}
        cache_sizes = [100, 500, 1000, 5000, 10000]
        ttl_seconds = 1  # Short TTL to force frequent cleanup

        for size in cache_sizes:
            # Create cache with short TTL for aggressive cleanup
            config = CacheConfig(
                max_size=size,
                ttl_seconds=ttl_seconds,
                enable_telemetry=False,  # Disable to avoid interference
            )
            cache: LRUCache[str, str] = LRUCache(config)

            # Fill cache with data
            start_time = time.perf_counter()
            for i in range(size):
                cache.set(f"key_{i}", f"value_{i}")
            fill_time = time.perf_counter() - start_time

            # Wait for entries to expire
            time.sleep(ttl_seconds + 0.1)

            # Benchmark cleanup performance
            cleanup_start = time.perf_counter()
            cache._cleanup_expired_entries()  # Force cleanup
            cleanup_time = time.perf_counter() - cleanup_start

            results[f"{size}_entries"] = {
                "fill_time_ms": fill_time * 1000,
                "cleanup_time_ms": cleanup_time * 1000,
                "entries_before": size,
                "entries_after": len(cache),
                "cleanup_rate_per_second": size / cleanup_time
                if cleanup_time > 0
                else 0,
                "time_per_entry_microseconds": (cleanup_time / size) * 1000000
                if cleanup_time > 0
                else 0,
            }

        return results

    def benchmark_cache_operations(self) -> dict[str, Any]:
        """Benchmark general cache operations to ensure no regression."""
        config = CacheConfig(max_size=10000, ttl_seconds=60, enable_telemetry=False)
        cache: LRUCache[str, str] = LRUCache(config)

        results = {}

        # Benchmark set operations
        num_operations = 10000
        start_time = time.perf_counter()
        for i in range(num_operations):
            cache.set(f"key_{i}", f"value_{i}")
        set_time = time.perf_counter() - start_time

        results["set_operations"] = {
            "time_ms": set_time * 1000,
            "operations_per_second": num_operations / set_time,
            "time_per_operation_microseconds": (set_time / num_operations) * 1000000,
        }

        # Benchmark get operations
        start_time = time.perf_counter()
        hits = 0
        for i in range(num_operations):
            value = cache.get(f"key_{i}")
            if value is not None:
                hits += 1
        get_time = time.perf_counter() - start_time

        results["get_operations"] = {
            "time_ms": get_time * 1000,
            "operations_per_second": num_operations / get_time,
            "time_per_operation_microseconds": (get_time / num_operations) * 1000000,
            "cache_hits": hits,
            "hit_rate_percent": (hits / num_operations) * 100,
        }

        # Benchmark mixed operations (simulating real usage)
        cache.clear()  # Start fresh
        start_time = time.perf_counter()

        for i in range(num_operations):
            if i % 3 == 0:
                # Set operation
                cache.set(f"mixed_key_{i}", f"mixed_value_{i}")
            elif i % 3 == 1:
                # Get operation (hit)
                cache.get(f"mixed_key_{i - 3}")
            else:
                # Get operation (miss)
                cache.get(f"nonexistent_key_{i}")

        mixed_time = time.perf_counter() - start_time

        results["mixed_operations"] = {
            "time_ms": mixed_time * 1000,
            "operations_per_second": num_operations / mixed_time,
            "time_per_operation_microseconds": (mixed_time / num_operations) * 1000000,
        }

        # Show final cache statistics
        stats = cache.get_stats()
        results["final_cache_stats"] = {
            "cache_size": stats["cache_size"],
            "hit_rate_percent": stats["hit_rate"] * 100,
            "evictions": stats["evictions"],
        }

        return results


class ContextPerformanceBenchmark:
    """Benchmarks for context registry cleanup performance."""

    def benchmark_context_registry(self) -> dict[str, Any]:
        """Benchmark context registry cleanup performance."""
        results = {}

        def worker_thread(thread_id: int, duration: float) -> None:
            """Worker thread that creates and uses context."""
            get_context()
            # Simulate some work
            time.sleep(random.uniform(0.01, 0.1))
            # Context will be cleaned up when thread dies

        # Test different numbers of threads
        thread_counts = [10, 50, 100, 200, 500]

        for count in thread_counts:
            # Reset performance stats for clean measurement
            reset_cleanup_performance_stats()

            threads = []
            start_time = time.perf_counter()

            # Create and start threads
            for i in range(count):
                thread = threading.Thread(
                    target=worker_thread, args=(i, 0.1), name=f"BenchmarkThread-{i}"
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            creation_time = time.perf_counter() - start_time

            # Force cleanup and measure
            cleanup_start = time.perf_counter()
            removed_count = cleanup_stale_contexts()
            cleanup_time = time.perf_counter() - cleanup_start

            # Get performance stats
            stats = get_cleanup_performance_stats()

            results[f"{count}_threads"] = {
                "thread_creation_time_ms": creation_time * 1000,
                "cleanup_time_ms": cleanup_time * 1000,
                "stale_contexts_removed": removed_count,
                "cleanup_rate_per_second": count / cleanup_time
                if cleanup_time > 0
                else 0,
                "average_cleanup_time_ms": stats.get("average_cleanup_time_ms", 0),
                "max_cleanup_time_ms": stats.get("max_cleanup_duration_ms", 0),
                "total_threads_processed": stats.get("total_threads_processed", 0),
            }

        return results


class ConversionPerformanceBenchmark:
    """Benchmarks for conversion operations (from existing performance_benchmark.py)."""

    def __init__(self) -> None:
        """Initialize benchmark with test data generators."""

    def _get_memory_usage(self) -> int | None:
        """Get current memory usage in bytes."""
        if not PSUTIL_AVAILABLE:
            return None

        process = psutil.Process()
        return int(process.memory_info().rss)

    def _format_memory_size(self, size_bytes: float) -> str:
        """Format memory size in the most appropriate units (B, KB, or MB)."""
        if size_bytes < 1024:
            return f"{size_bytes:.1f} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / 1024 / 1024:.2f} MB"

    def _calculate_statistics(self, values: list[float]) -> dict[str, float]:
        """Calculate statistics for a list of values."""
        if not values:
            return {}

        stats = {
            "mean": mean(values),
            "median": median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": stdev(values) if len(values) > 1 else 0.0,
        }

        # Add percentiles if numpy is available
        if NUMPY_AVAILABLE:
            np_values = np.array(values)
            stats.update(
                {
                    "percentile_25": np.percentile(np_values, 25),
                    "percentile_75": np.percentile(np_values, 75),
                    "percentile_90": np.percentile(np_values, 90),
                    "percentile_95": np.percentile(np_values, 95),
                    "percentile_99": np.percentile(np_values, 99),
                }
            )

        return stats

    def _measure_with_memory(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> tuple[Any, int | None]:
        """Execute a function and measure memory usage difference."""
        memory_before = self._get_memory_usage()
        result = func(*args, **kwargs)
        memory_after = self._get_memory_usage()

        memory_diff = None
        if memory_before is not None and memory_after is not None:
            memory_diff = memory_after - memory_before

        return result, memory_diff

    def generate_test_case(self, complexity: str = "medium") -> dict[str, Any]:
        """Generate test case with varying complexity levels."""
        base_case: dict[str, Any] = {
            "testCase": {
                "name": "Performance Test Case",
                "description": "Benchmark test case for performance measurement",
                "preConditions": "System is running and accessible",
                "postConditions": "System state is restored",
                "priority": "Medium",
                "labels": ["performance", "benchmark"],
                "steps": [],
            }
        }

        # Convert string to enum if needed
        if isinstance(complexity, str):
            try:
                complexity_enum = ComplexityLevel(complexity)
            except ValueError:
                complexity_enum = ComplexityLevel.MEDIUM
        else:
            complexity_enum = complexity

        step_counts = {
            ComplexityLevel.SIMPLE: 3,
            ComplexityLevel.MEDIUM: 10,
            ComplexityLevel.COMPLEX: 25,
            ComplexityLevel.ENTERPRISE: 50,
        }

        step_count = step_counts.get(complexity_enum, 10)

        for i in range(step_count):
            step = {
                "stepDescription": f"Execute operation {i + 1} with test data",
                "expectedResult": f"Operation {i + 1} completes successfully",
                "testData": {
                    "correlation_id": f"perf_test_{i + 1}",
                    "user_id": f"user_{(i % 1000) + 1}",
                    "timestamp": (
                        f"2025-01-01T{str(i % 24).zfill(2)}:"
                        f"{str(i % 60).zfill(2)}:{str(i % 60).zfill(2)}Z"
                    ),
                    "parameters": {
                        "param1": f"value1_{i}",
                        "param2": f"value2_{i}",
                        "param3": f"value3_{i}",
                    },
                },
                "action": "execute_operation",
                "object": f"test_object_{i + 1}",
            }
            base_case["testCase"]["steps"].append(step)

        # Add some metadata for enterprise complexity
        if complexity_enum == ComplexityLevel.ENTERPRISE:
            base_case["testCase"]["metadata"] = {
                "business_domain": "enterprise",
                "compliance_level": "high",
                "security_classification": "confidential",
                "data_sensitivity": "medium",
                "integration_points": ["api1", "api2", "database"],
                "dependencies": ["service_a", "service_b", "service_c"],
            }

        return base_case

    def benchmark_single_conversion(
        self,
        complexity: str = "medium",
        iterations: int = 10,
        warmup_iterations: int = 3,
    ) -> dict[str, Any]:
        """Benchmark single file conversion performance."""
        # Warmup iterations (not measured)
        for _ in range(warmup_iterations):
            input_file = None
            output_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as tmp_input_file:
                    input_file = tmp_input_file.name
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".robot", delete=False
                    ) as tmp_output_file:
                        output_file = tmp_output_file.name
                        # Generate test data
                        test_data = self.generate_test_case(complexity)
                        json.dump(test_data, tmp_input_file)
                        tmp_input_file.flush()

                        # Execute conversion without measuring
                        convert_file(input_file, output_file)
            finally:
                # Cleanup
                if input_file and Path(input_file).exists():
                    Path(input_file).unlink(missing_ok=True)
                if output_file and Path(output_file).exists():
                    Path(output_file).unlink(missing_ok=True)

        # Actual measured iterations
        times = []
        memory_usages = []

        for _ in range(iterations):
            input_file = None
            output_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as tmp_input_file:
                    input_file = tmp_input_file.name
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".robot", delete=False
                    ) as tmp_output_file:
                        output_file = tmp_output_file.name
                        # Generate test data
                        test_data = self.generate_test_case(complexity)
                        json.dump(test_data, tmp_input_file)
                        tmp_input_file.flush()

                        # Measure conversion time and memory
                        start_time = time.perf_counter()
                        _, memory_diff = self._measure_with_memory(
                            convert_file, input_file, output_file
                        )
                        end_time = time.perf_counter()

                        times.append(end_time - start_time)
                        if memory_diff is not None:
                            memory_usages.append(memory_diff)
            finally:
                # Cleanup
                if input_file and Path(input_file).exists():
                    Path(input_file).unlink(missing_ok=True)
                if output_file and Path(output_file).exists():
                    Path(output_file).unlink(missing_ok=True)

        base_stats = self._calculate_statistics(times)
        result: dict[str, Any] = dict(base_stats)
        result["iterations"] = iterations
        result["warmup_iterations"] = warmup_iterations
        result["complexity"] = complexity

        if memory_usages:
            result["memory_usage"] = self._calculate_statistics(
                [float(m) for m in memory_usages]
            )

        return result

    def benchmark_lazy_loading(
        self, warmup_iterations: int = 10, iterations: int = 100
    ) -> dict[str, Any]:
        """Benchmark lazy loading system performance and benefits."""
        # Run individual benchmarks
        cold_times, cold_memory = self._benchmark_cold_start_access(
            warmup_iterations, iterations
        )
        cached_times, cached_memory = self._benchmark_cached_access(
            warmup_iterations, iterations
        )

        # Calculate performance improvement
        improvement = (
            ((mean(cold_times) - mean(cached_times)) / mean(cold_times)) * 100
            if cold_times
            else 0
        )

        # Build result dictionary
        result: dict[str, Any] = {
            "first_access_cold": self._calculate_statistics(cold_times),
            "cached_access": self._calculate_statistics(cached_times),
            "performance_improvement_percent": improvement,
            "cache_effectiveness": "High"
            if improvement > 50
            else "Medium"
            if improvement > 20
            else "Low",
        }

        # Add memory statistics
        if cold_memory:
            result["first_access_cold"]["memory_usage"] = self._calculate_statistics(
                [float(m) for m in cold_memory]
            )
        if cached_memory:
            result["cached_access"]["memory_usage"] = self._calculate_statistics(
                [float(m) for m in cached_memory]
            )

        return result

    def _benchmark_cold_start_access(
        self, warmup_iterations: int, iterations: int
    ) -> tuple[list[float], list[int]]:
        """Benchmark first access (cold start) performance."""
        # Warmup iterations for cold start measurements
        for _ in range(warmup_iterations):
            templates = BusinessDomainTemplates()
            _ = templates.enterprise_scenarios  # First access triggers lazy load

        # Benchmark first access (cold start)
        cold_times = []
        cold_memory = []
        for _ in range(iterations):
            # Create fresh instance each time to simulate cold start
            templates = BusinessDomainTemplates()
            start_time = time.perf_counter()
            _, memory_diff = self._measure_with_memory(
                lambda t=templates: t.enterprise_scenarios
            )
            end_time = time.perf_counter()
            cold_times.append(end_time - start_time)
            if memory_diff is not None:
                cold_memory.append(memory_diff)

        return cold_times, cold_memory

    def _benchmark_cached_access(
        self, warmup_iterations: int, iterations: int
    ) -> tuple[list[float], list[int]]:
        """Benchmark subsequent access (cached) performance."""
        # Warmup iterations for cached access measurements
        templates = BusinessDomainTemplates()
        _ = templates.enterprise_scenarios  # Load once to cache
        for _ in range(warmup_iterations):
            _ = templates.enterprise_scenarios  # Subsequent access from cache

        # Benchmark subsequent access (cached)
        cached_times = []
        cached_memory = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            _, memory_diff = self._measure_with_memory(
                lambda t=templates: t.enterprise_scenarios
            )
            end_time = time.perf_counter()
            cached_times.append(end_time - start_time)
            if memory_diff is not None:
                cached_memory.append(memory_diff)

        return cached_times, cached_memory


class ComprehensivePerformanceBenchmark:
    """Comprehensive performance benchmark suite."""

    def __init__(self) -> None:
        """Initialize all benchmark components."""
        self.cache_benchmark = CachePerformanceBenchmark()
        self.context_benchmark = ContextPerformanceBenchmark()
        self.conversion_benchmark = ConversionPerformanceBenchmark()

    def run_benchmarks(
        self,
        benchmark_types: list[BenchmarkType],
        iterations: int = 10,
        complexity: str = "medium",
    ) -> dict[str, Any]:
        """Run specified benchmark types."""
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmark_types": [bt.value for bt in benchmark_types],
            "iterations": iterations,
            "complexity": complexity,
        }

        if (
            BenchmarkType.CACHE in benchmark_types
            or BenchmarkType.ALL in benchmark_types
        ):
            print("Running cache performance benchmarks...")
            results["cache_performance"] = {
                "cleanup": self.cache_benchmark.benchmark_cache_cleanup(),
                "operations": self.cache_benchmark.benchmark_cache_operations(),
            }

        if (
            BenchmarkType.CONTEXT in benchmark_types
            or BenchmarkType.ALL in benchmark_types
        ):
            print("Running context registry benchmarks...")
            results["context_performance"] = (
                self.context_benchmark.benchmark_context_registry()
            )

        if (
            BenchmarkType.CONVERSION in benchmark_types
            or BenchmarkType.ALL in benchmark_types
        ):
            print("Running conversion performance benchmarks...")
            results["conversion_performance"] = {
                "single_file": self.conversion_benchmark.benchmark_single_conversion(
                    complexity=complexity, iterations=iterations
                ),
                "lazy_loading": self.conversion_benchmark.benchmark_lazy_loading(),
            }

        return results

    def format_results(self, results: dict[str, Any]) -> str:
        """Format benchmark results for display."""
        output = []
        output.append("=" * 70)
        output.append(" IMPORTOBOT COMPREHENSIVE PERFORMANCE BENCHMARK RESULTS")
        output.append("=" * 70)
        output.append(f"Timestamp: {results['timestamp']}")
        output.append(f"Types: {', '.join(results['benchmark_types'])}")
        output.append("")

        # Format cache results
        if "cache_performance" in results:
            output.append(" CACHE PERFORMANCE")
            output.append("-" * 50)

            # Cleanup results
            cleanup_results = results["cache_performance"]["cleanup"]
            for size_key, stats in cleanup_results.items():
                output.append(f"  {size_key.replace('_', ' ').title()}:")
                output.append(f"    Cleanup time: {stats['cleanup_time_ms']:.2f}ms")
                output.append(
                    f"    Cleanup rate: {stats['cleanup_rate_per_second']:,.0f} entries/sec"
                )
                output.append(
                    f"    Time per entry: {stats['time_per_entry_microseconds']:.2f}μs"
                )

            # Operations results
            ops_results = results["cache_performance"]["operations"]
            output.append("\n  Cache Operations:")
            for op_type, stats in ops_results.items():
                if op_type != "final_cache_stats":
                    output.append(f"    {op_type.replace('_', ' ').title()}:")
                    output.append(f"      Time: {stats['time_ms']:.2f}ms")
                    output.append(
                        f"      Rate: {stats['operations_per_second']:,.0f} ops/sec"
                    )
                    output.append(
                        f"      Per operation: {stats['time_per_operation_microseconds']:.2f}μs"
                    )

            final_stats = ops_results.get("final_cache_stats", {})
            if final_stats:
                output.append("\n  Final Cache Stats:")
                output.append(f"    Size: {final_stats['cache_size']}")
                output.append(f"    Hit rate: {final_stats['hit_rate_percent']:.1f}%")
                output.append(f"    Evictions: {final_stats['evictions']}")

            output.append("")

        # Format context results
        if "context_performance" in results:
            output.append(" CONTEXT REGISTRY PERFORMANCE")
            output.append("-" * 50)

            context_results = results["context_performance"]
            for thread_key, stats in context_results.items():
                output.append(f"  {thread_key.replace('_', ' ').title()}:")
                output.append(f"    Cleanup time: {stats['cleanup_time_ms']:.2f}ms")
                output.append(
                    f"    Cleanup rate: {stats['cleanup_rate_per_second']:,.0f} threads/sec"
                )
                output.append(
                    f"    Stale contexts removed: {stats['stale_contexts_removed']}"
                )
                output.append(
                    f"    Average cleanup time: {stats['average_cleanup_time_ms']:.2f}ms"
                )
                output.append(
                    f"    Max cleanup time: {stats['max_cleanup_time_ms']:.2f}ms"
                )

            output.append("")

        # Format conversion results
        if "conversion_performance" in results:
            output.append(" CONVERSION PERFORMANCE")
            output.append("-" * 50)

            conv_results = results["conversion_performance"]

            # Single file conversion
            single_results = conv_results.get("single_file", {})
            if single_results:
                output.append(
                    f"  Single File Conversion ({results.get('complexity', 'medium')}):"
                )
                output.append(
                    f"    Mean time: {single_results.get('mean', 0) * 1000:.2f}ms"
                )
                output.append(
                    f"    Std dev: {single_results.get('std_dev', 0) * 1000:.2f}ms"
                )
                if "percentile_95" in single_results:
                    output.append(
                        f"    95th percentile: {single_results['percentile_95'] * 1000:.2f}ms"
                    )

            # Lazy loading
            lazy_results = conv_results.get("lazy_loading", {})
            if lazy_results:
                output.append("\n  Lazy Loading:")
                cold_mean = (
                    lazy_results.get("first_access_cold", {}).get("mean", 0) * 1000
                )
                cached_mean = (
                    lazy_results.get("cached_access", {}).get("mean", 0) * 1000
                )
                improvement = lazy_results.get("performance_improvement_percent", 0)

                output.append(f"    Cold start: {cold_mean:.3f}ms")
                output.append(f"    Cached access: {cached_mean:.3f}ms")
                output.append(f"    Improvement: {improvement:.1f}%")
                output.append(
                    f"    Effectiveness: {lazy_results.get('cache_effectiveness', 'Unknown')}"
                )

            output.append("")

        # Performance targets
        output.append(" PERFORMANCE TARGETS")
        output.append("-" * 50)
        output.append(" Cache cleanup: < 5μs per entry at scale")
        output.append(" Context cleanup: < 50ms even with 500+ threads")
        output.append(" Single file conversion: < 100ms for medium complexity")
        output.append(" Lazy loading: > 50% improvement over cold start")

        return "\n".join(output)


def main() -> None:
    """Run comprehensive performance benchmarks."""
    parser = argparse.ArgumentParser(
        description="Run Importobot comprehensive performance benchmarks"
    )
    parser.add_argument(
        "--types",
        choices=[bt.value for bt in BenchmarkType],
        nargs="+",
        default=[BenchmarkType.ALL.value],
        help="Types of benchmarks to run (default: all)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations for conversion benchmarks (default: 10)",
    )
    parser.add_argument(
        "--complexity",
        choices=[level.value for level in ComplexityLevel],
        default="medium",
        help="Complexity level for conversion benchmarks (default: medium)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("performance_benchmark_results.json"),
        help="Output file for detailed results (default: performance_benchmark_results.json)",
    )

    args = parser.parse_args()

    # Convert string types to BenchmarkType enum
    benchmark_types = [BenchmarkType(t) for t in args.types]

    # Run benchmarks
    benchmark = ComprehensivePerformanceBenchmark()
    print("Running Importobot Comprehensive Performance Benchmarks...")

    try:
        results = benchmark.run_benchmarks(
            benchmark_types=benchmark_types,
            iterations=args.iterations,
            complexity=args.complexity,
        )

        # Display results
        print("\n" + benchmark.format_results(results))

        # Save results to file
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"\n📁 Detailed results saved to: {args.output}")
        print("=" * 70)
        print(" All benchmarks completed successfully!")

    except Exception as e:
        print(f"\n Benchmark failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
