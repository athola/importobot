# Performance Characteristics

Current performance numbers for Importobot conversions. Use these to spot regressions and plan capacity.

## Baseline Metrics (2025-09)

- Single-file conversion: 0.4s avg, 0.5s p95 (medium complexity)
- Bulk conversion (25 files): 2.8s total (~0.11s per file)
- Parallel conversion (10 workers): 6.1s total
- Memory footprint: Resident Set Size (RSS) increase of 1–3 MB for single conversion, <40 MB during bulk
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

Numbers come from the CI benchmark and full test suite. On slower hardware, expect ±20% variance, but investigate anything exceeding the regression thresholds below.

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

## JSON Cache Serialization Optimization

The `PerformanceCache` implements an important optimization that avoids double serialization for JSON caching operations.

### Implementation Details

**File:** `src/importobot/services/performance_cache.py`

The `_build_cache_key()` method uses a smart strategy to avoid double serialization:

```python
def _build_cache_key(self, namespace: str, data: Any) -> _CacheKey:
    """Build an internal cache key without forcing serialization when possible."""
    if isinstance(data, Hashable):
        return _CacheKey(namespace, data, False)
    return _CacheKey(namespace, id(data), True)
```

**Key insight:**
- **Hashable types** (strings, tuples, numbers): Use the value directly as cache key
- **Unhashable types** (dicts, lists): Use `id(data)` (object identity) as cache key

This optimization provides the following benefits:
- **No serialization needed for cache key generation**
- **Only one serialization happens** (to get the cached JSON string)
- **Cache lookups are O(1) dictionary operations**

### Performance Impact

Based on test coverage:

- **Cache Miss:** 1 serialization (same as no cache)
- **Speedup:** >2x faster than direct serialization for complex nested structures
- **Speedup:** >2x faster than direct serialization for complex nested structures
- **Memory:** Bounded by `max_cache_size`, identity refs cleaned on eviction

### Identity Tracking

For unhashable objects using identity-based keys, the cache maintains:
- `_json_identity_refs`: Stores strong references to objects to prevent false cache hits from Python id reuse
- Identity validation: Checks object identity before returning cached values

### Test Coverage

Six tests in `tests/unit/services/test_json_cache_serialization.py` validate:
1. Single serialization per unique object
2. Identity-based distinction for identical content
3. Performance improvement on cache hits
4. Value-based keying for hashable types
5. Memory safety during evictions
6. Protection against false cache hits

## Validation Pipeline (v0.1.2)

The full validation suite (`make validate`) takes around 4 minutes. Breakdown:

| Step | Duration | Notes |
|------|----------|-------|
| Linting | 120s | pylint dominates at 95s; ruff/pycodestyle/pydocstyle add ~7s |
| Tests | 100s | 1833 tests across unit/integration/performance/invariant suites |
| Type checking | 5s | mypy covers main package plus scripts subproject |
| Security scans | 15s | detect-secrets + bandit |

Pylint's 95-second analysis helps prevent production issues by identifying code duplicates, complexity violations, and import errors before they reach users.

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
