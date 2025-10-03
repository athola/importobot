# Performance Benchmarks

Importobot ships a benchmark harness that measures conversion throughput,
latency, and memory usage across representative workloads. Use this guide to run
the benchmarks and interpret the results, especially when validating medallion
and optimizer changes.

## When to Run Benchmarks

- Before and after major refactors (e.g., OptimizedConverter rollout).
- During release candidates to confirm no regression in conversion speed.
- While tuning optimization settings so you can balance quality and latency.

## Benchmark Script

The entrypoint lives at `scripts/src/importobot_scripts/performance_benchmark.py`.

```bash
# Show available options
uv run python scripts/src/importobot_scripts/performance_benchmark.py --help

# Run the full suite with default settings plus the parallel scenario
uv run python scripts/src/importobot_scripts/performance_benchmark.py --parallel

# Focus on complex single-file conversions with 20 iterations
uv run python scripts/src/importobot_scripts/performance_benchmark.py --iterations 20 --complexity complex
```

Key flags:
- `--iterations` – Number of single-file conversion iterations per level (default 10).
- `--api-iterations` – Iterations for API helper benchmarks (default 5).
- `--bulk-files` – File counts used for bulk directory benchmarks (default `5 10 25 50`).
- `--warmup` – Warm-up iterations excluded from timing stats (default 3).
- `--parallel` – Enable the parallel conversion scenario.
- `--complexity` – Choose the generated test complexity (`simple`, `medium`, `complex`, `enterprise`).

## Metrics Captured

Each benchmark run produces a human-readable summary and writes
`performance_benchmark_results.json` in the project root containing:
- Wall-clock timings (mean/median/min/max, percentiles with NumPy installed).
- Conversion throughput (files per second) per scenario.
- Memory deltas for each run when `psutil` is available.
- Iteration-level timings for single conversion, bulk, API method calls, and
  optional parallel runs.
- Cache hit/miss rates when you call `PerformanceCache().get_cache_stats()` or
  the `LazyEvaluator` helpers as part of custom harness extensions.

Sample JSON structure:

```json
{
  "single_conversion": {
    "complexity": "medium",
    "iterations": 10,
    "timings": {"mean": 0.41, "median": 0.39, "max": 0.52},
    "memory_diff_bytes": 1048576
  },
  "bulk_conversion": {
    "10": {"duration": 2.8, "files_per_second": 3.57}
  }
}
```

## Using Benchmark Data

1. **Baseline** – Store a baseline JSON result and check it into your internal
   benchmarking repo.
2. **Compare** – Run the suite after code changes and diff against the baseline.
3. **Alert** – Flag regressions beyond your acceptable thresholds (e.g., >10%
   slowdown) and investigate before releasing.
4. **Report** – Attach the JSON artifacts to MR documentation or release notes.

### Memory Profiling & Cache Observability

- Every section of the benchmark JSON includes an optional `memory_usage`
  dictionary with `mean`, `median`, and `max` RSS deltas. When printing the
  summary, the CLI highlights the average memory footprint for each scenario.
- Example snippet:

  ```json
  {
    "single_conversion": {
      "timings": {"mean": 0.41},
      "memory_usage": {"mean": 1048576, "max": 3145728}
    }
  }
  ```

  Combine this with `PerformanceCache().get_cache_stats()` during runs to watch
  cache population, hit rates, and eviction behaviour.
- To drill deeper, wrap any conversion call with `tracemalloc` or `psutil`
  sampling while the benchmark is running:

  ```python
  import tracemalloc
  from importobot.services.performance_cache import get_performance_cache

  tracemalloc.start()
  benchmark.run_comprehensive_benchmark()
  snapshot = tracemalloc.take_snapshot()
  top_stats = snapshot.statistics("lineno")[:10]
  cache_stats = get_performance_cache().get_cache_stats()
  ```

  This surfaces hot spots and validates that eviction policies keep memory
  bounded.

## Integration with Optimization Benchmarks

Pair the performance script with the optimization benchmark plan from the
[Mathematical Foundations](Mathematical-Foundations) doc:

- Use the same small/medium/large suite definitions when feeding the optimizer.
- Record the optimization preview latency alongside conversion timing to keep
  overall pipeline SLAs visible.
- Archive both outputs when making go/no-go decisions for the OptimizedConverter
  release.
