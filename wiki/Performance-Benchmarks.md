# Performance Benchmarks

Importobot provides two complementary benchmarking systems:

1. **ASV (Airspeed Velocity)**: Track performance trends across releases and commits
2. **Internal Benchmark Script**: Detailed conversion profiling for development

Use ASV for release-to-release comparisons and regression detection. Use the internal script for development profiling and optimization work.

---

## ASV Benchmarks

### Overview

ASV (Airspeed Velocity) tracks performance across releases, detects regressions, and visualizes trends over time. The benchmark suite covers:

- **Conversion Performance**: Single test, multiple tests, large complex suites
- **Memory Usage**: Peak memory consumption for large conversions
- **Directory Operations**: Bulk file processing at scale (5, 10, 25 files)
- **Validation**: Input validation and error handling performance

### Quick Start

```bash
# Run benchmarks on current commit
uv run asv run

# Compare performance between branches
uv run asv continuous main development

# Compare specific commits
uv run asv continuous v0.1.3 HEAD

# Generate and view HTML dashboard
uv run asv publish
uv run asv preview
```

### Benchmark Suites

#### ZephyrConversionSuite
Measures Zephyr JSON → Robot Framework conversion performance:

- `time_convert_simple_single_test`: Single test with 2 steps (~380μs baseline)
- `time_convert_moderate_multiple_tests`: 20 tests × 5 steps each
- `time_convert_large_complex_suite`: 100 tests × 15 steps with metadata
- `peakmem_convert_large_suite`: Memory profiling for large conversions

#### DirectoryConversionSuite
Parameterized benchmarks for bulk operations:

- `time_convert_directory[5]`: Convert 5-file directory
- `time_convert_directory[10]`: Convert 10-file directory
- `time_convert_directory[25]`: Convert 25-file directory

#### ValidationSuite
Input validation and error handling:

- `time_validate_valid_input`: Valid input processing
- `time_validate_invalid_input`: Error detection and handling

### Configuration

ASV configuration is in `asv.conf.json`:

```json
{
    "version": 1,
    "project": "importobot",
    "repo": ".",
    "branches": ["main"],
    "environment_type": "virtualenv",
    "pythons": ["3.12"],
    "benchmark_dir": "benchmarks"
}
```

### Best Practices

1. **Baseline Before Changes**: Run `asv run` before starting performance work
2. **Compare Branches**: Use `asv continuous base-branch feature-branch` to detect regressions
3. **Track Releases**: Benchmark each release tag for historical trends
4. **Machine Consistency**: Run on same hardware for comparable results
5. **Review Dashboard**: Check HTML reports for trends and anomalies

### CI Integration

ASV runs can be integrated into CI pipelines:

```bash
# Fail if performance regresses by >10%
uv run asv continuous --factor 1.1 main HEAD
```

### When to Run ASV

- **Before Release**: Compare release candidate against previous version
- **After Major Changes**: Verify medallion or optimizer refactors don't regress
- **Regular Intervals**: Weekly or monthly tracking for trend analysis
- **Performance Issues**: Diagnose when users report slowdowns

### Benchmark Visualizations

The following charts are automatically updated on each release:

#### Conversion Performance Trends
![Conversion Performance](images/asv-conversion-performance.png)
*Performance trends for simple, moderate, and large test suite conversions across releases*

#### Memory Usage Profile
![Memory Usage](images/asv-memory-usage.png)
*Peak memory consumption when converting 100-test complex suites*

#### Bulk Conversion Scalability
![Bulk Conversion](images/asv-bulk-conversion.png)
*Directory conversion performance at different scales (5, 10, 25 files)*

> **Note**: Charts are regenerated automatically when release tags are pushed. Historical data accumulates over releases to show long-term performance trends.

---

## Internal Benchmark Script

### When to Run Internal Benchmarks

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
