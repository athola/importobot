# Performance Benchmarks

Importobot ships a benchmark harness that measures conversion throughput,
latency, and memory usage across representative workloads. Use this guide when
requiring evidence before merging medallion or optimizer changes.

## When to Run Benchmarks

- Before and after major refactors (e.g., OptimizedConverter rollout).
- During release candidates to confirm no regression in conversion speed.
- While tuning optimization settings so you can balance quality and latency.

## Benchmark Script

The entrypoint is in the `importobot_scripts.benchmarks.performance_benchmark` module.

```bash
# Show available options
uv run python -m importobot_scripts.benchmarks.performance_benchmark --help

# Run the full suite with default settings plus the parallel scenario
uv run python -m importobot_scripts.benchmarks.performance_benchmark --parallel

# Focus on complex single-file conversions with 20 iterations
uv run python -m importobot_scripts.benchmarks.performance_benchmark --iterations 20 --complexity complex
```

Key flags:
- `--iterations` – Single-file conversion iterations per level (default 10).
- `--api-iterations` – API helper iterations (default 5).
- `--bulk-files` – File counts for bulk runs (default `5 10 25 50`).
- `--warmup` – Warm-up iterations ignored in stats (default 3).
- `--parallel` – Enable the parallel scenario.
- `--complexity` – Generated test mix (`simple`, `medium`, `complex`, `enterprise`).

## Metrics Captured

Each run prints a summary and writes
`performance_benchmark_results.json` in the project root. The file records
timings, throughput, optional memory deltas (when `psutil` is installed), and
per-scenario iteration data. Call `PerformanceCache().get_cache_stats()` during
custom runs if you also want cache metrics.

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

1. **Baseline** – Keep a known-good JSON result under version control.
2. **Compare** – Diff each new run against the baseline.
3. **Alert** – Flag regressions beyond the SLA (e.g., >10% slowdown) before release.
4. **Report** – Attach the JSON when raising MRs or publishing release notes.

### Memory profiling & cache observability

- When `psutil` is present the JSON adds a `memory_usage` block per scenario.
- Pair it with `PerformanceCache().get_cache_stats()` to monitor cache fill and eviction.
- For deeper dives, wrap the benchmark with `tracemalloc`:

  ```python
  import tracemalloc
  from importobot.services.performance_cache import get_performance_cache

  tracemalloc.start()
  benchmark.run_comprehensive_benchmark()
  hits = get_performance_cache().get_cache_stats()
  ```

## Integration with optimization benchmarks

Align the scenarios here with the optimizer plan from
[Mathematical Foundations](Mathematical-Foundations): reuse the same
small/medium/large suites, track optimization preview latency alongside conversion timing, and store both JSON outputs when making decisions related to the OptimizedConverter.
