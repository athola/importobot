# Performance Characteristics

This note records the current performance profile so teams know what to expect
under load and can spot regressions quickly.

## Baseline Metrics (2025-09)

- Single-file conversion: 0.4s avg, 0.5s p95 (medium complexity)
- Bulk conversion (25 files): 2.8s total (~0.11s per file)
- Parallel conversion (10 workers): 6.1s total
- Memory footprint: RSS Δ 1–3 MB for single conversion, <40 MB during bulk
- Cache stats (`PerformanceCache`): 85% hit rate in medallion preview runs

Source: `uv run python -m importobot_scripts.benchmarks.performance_benchmark` on
the reference CI runner (Ubuntu 22.04, Python 3.12).

## Scale Profiles

| Data Scale | Typical Payload | Expected Latency | Throughput Target | Memory Delta | Notes |
|------------|-----------------|------------------|-------------------|--------------|-------|
| Small      | Single medium-complexity case (~5 steps) | ≤0.5s avg, ≤0.6s p95 | n/a | ≤5 MB | Covers ad-hoc conversions and unit tests |
| Medium     | 25 cases (benchmark default) | ≤3.0s total | ≥5 files/sec | ≤40 MB | Mirrors CI smoke guard (`--ci-mode`) |
| Large      | 100–250 cases | ≤13s total | ≥8 files/sec | ≤75 MB | Expect near-linear scaling; monitor throughput drop <15% |
| Parallel   | 10 workers × medium cases | ≤7s total | ≥14 files/sec | ≤90 MB | Depends on I/O; watch thread contention |

Numbers derive from the CI smoke benchmark and the comprehensive suite. When
running on slower hardware, allow ±20% variance but investigate anything
exceeding the regression thresholds below.

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

These thresholds are enforced in CI via `make perf-test`, which runs the smoke
benchmark (`performance_benchmark --ci-mode`) against
`ci/performance_thresholds.json`. Update the JSON alongside this document when
raising or tightening limits.

## Validation Pipeline (v0.1.2)

The full validation suite (`make validate`) takes around 4 minutes. Breakdown:

| Step | Duration | Notes |
|------|----------|-------|
| Linting | 120s | pylint dominates at 95s; ruff/pycodestyle/pydocstyle add ~7s |
| Tests | 100s | 1833 tests across unit/integration/performance/invariant suites |
| Type checking | 5s | mypy covers main package plus scripts subproject |
| Security scans | 15s | detect-secrets + bandit |

Pylint's 95-second runtime is reasonable for ~15K lines of code. It runs comprehensive analysis including duplicate detection, complexity metrics, and import graph validation—checks that catch real bugs before they ship.

### Quick validation during development

Use `make lint-fast` to skip pylint and finish in about 10 seconds. Run the full suite before pushing or opening a PR.

### Profiling slowdowns

If validation takes longer than expected:

```bash
# Check what's slow
time make lint
time make test

# Look for flaky tests
pytest --lf

# Clear stale caches
make clean && rm -rf .pytest_cache .mypy_cache
```

Tests run in parallel via pytest-xdist (`-n auto`), so more cores help. Watch for I/O bottlenecks if running in containers with limited disk throughput.

### CI timing

GitHub Actions typically completes in 5–6 minutes including setup. If jobs exceed 10 minutes, check dependency caching and consider splitting lint/test into parallel jobs.
