# Performance Characteristics

This document summarises Importobot’s performance profile so teams know what to
expect under load and have a place to stash benchmark deltas.

## Baseline Metrics (2025-09)

- **Single-file conversion**: 0.4s avg, 0.5s p95 (medium complexity)
- **Bulk conversion (25 files)**: 2.8s total (~0.11s per file)
- **Parallel conversion (10 workers)**: 6.1s total
- **Memory footprint**: RSS Δ 1–3 MB for single conversion, <40 MB during bulk
- **Cache stats** (`PerformanceCache`): 85% hit rate in medallion preview runs

Source: `uv run python scripts/src/importobot_scripts/performance_benchmark.py` on
the reference CI runner (Ubuntu 22.04, Python 3.12).

## Ongoing Tracking

When running benchmarks:
- Capture `performance_benchmark_results.json`.
- Call `PerformanceCache().get_cache_stats()` to log hit/miss ratios.
- Note the commit hash and hardware profile.

## Regression Thresholds

- Single conversion avg time increase >10%
- Bulk conversion throughput drop >15%
- Memory delta increase >5 MB sustained
- Cache hit rate drop below 70%
