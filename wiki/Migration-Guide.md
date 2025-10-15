# Migration Guide

This guide covers the switch to the medallion architecture introduced in v0.1.1.

## Additional breaking changes in v0.1.1

| Area | Change | Action |
| --- | --- | --- |
| Security Gateway | `sanitize_api_input` / `validate_file_operation` now return typed dictionaries that include an optional `correlation_id`. | Update call sites to read from `result["sanitized_data"]` and propagate `result["correlation_id"]` into logs/metadata where you need request tracing. |
| Data ingestion | `DataIngestionService` automatically generates a correlation id per ingest and stores it in `metadata.custom_metadata` and error details. | If you previously injected your own `correlation_id`, pass it via the new `context={"correlation_id": "..."}` argument on security gateway calls. |
| Caching | Detection/cache limits are now driven by environment variables (`IMPORTOBOT_DETECTION_CACHE_MAX_SIZE`, `IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT`, `IMPORTOBOT_FILE_CACHE_MAX_MB`, `IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE`). | Export the variables in CI/staging to tune cache pressure; omit them to use the previous defaults. |
| Optimization | SciPy dependency downgraded to optional; advanced optimization uses heuristic mode when SciPy is unavailable. | Install the `importobot[advanced]` extra in environments that perform parameter training, or accept heuristic scoring when only runtime confidence is required. |

## Additional changes in v0.1.2

| Area | Change | Action |
| --- | --- | --- |
| Bronze Layer Storage | New in-memory caching with configurable capacity and TTL (`max_in_memory_records`, `in_memory_ttl_seconds`). | See "Bronze Layer In-Memory Cache Configuration" below for tuning guidelines. |
| Test Utilities | Restructured `tests/utils` module into organized package with `test_helpers.py` and `performance_utils.py`. | Existing imports continue to work via re-exports in `__init__.py`. No code changes required. |

### Updating security gateway call sites

```python
# v0.1.1 code
result = gateway.sanitize_api_input(payload, "json")
if not result["is_safe"]:
    raise SecurityError(result["security_issues"])
data = result["sanitized_data"]

# Updated 0.1.1 code
result = gateway.sanitize_api_input(
    payload,
    "json",
    context={"source": "ci-job", "correlation_id": request_id},
)
if not result["is_safe"]:
    logger.warning(
        "security_failed",
        extra={"correlation_id": result["correlation_id"]},
    )
    raise SecurityError(result["security_issues"])
data = result["sanitized_data"]
```

### Configuring cache limits

```bash
export IMPORTOBOT_DETECTION_CACHE_MAX_SIZE="2000"
export IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT="5"
export IMPORTOBOT_FILE_CACHE_MAX_MB="256"
export IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE="5000"
uv run importobot input.json output.robot
```

### Bronze Layer In-Memory Cache Configuration

**New in v0.1.2**: The Bronze layer now includes an in-memory cache for recently ingested records, providing faster retrieval and graceful degradation when storage backends are unavailable.

#### Default Configuration

```python
from importobot.medallion.bronze_layer import BronzeLayer

# Uses default values from config.py
bronze = BronzeLayer(
    storage_path=Path("./storage"),
    storage_backend=storage_backend,
)
```

**Defaults:**
- `max_in_memory_records`: 1024 records (configurable via `IMPORTOBOT_BRONZE_MAX_IN_MEMORY_RECORDS`)
- `in_memory_ttl_seconds`: 0 (disabled, configurable via `IMPORTOBOT_BRONZE_IN_MEMORY_TTL_SECONDS`)
- Memory overhead: ~1KB per record = ~1MB for default 1024 records

#### Custom Configuration

```python
# Programmatic configuration
bronze = BronzeLayer(
    storage_path=Path("./storage"),
    storage_backend=storage_backend,
    max_in_memory_records=2048,      # Double the cache size
    in_memory_ttl_seconds=300,       # 5-minute TTL
)

# Environment variable configuration
export IMPORTOBOT_BRONZE_MAX_IN_MEMORY_RECORDS="2048"
export IMPORTOBOT_BRONZE_IN_MEMORY_TTL_SECONDS="300"
```

#### When to Adjust Parameters

**Increase `max_in_memory_records` when:**
- Working with large test suites (5000+ test cases)
- Frequent repeated queries for the same records
- Storage backend has high latency (network storage, slow disk)
- Available memory is abundant (>8GB)

**Performance impact:** +50-80% faster queries for cached records, but linear memory increase (~1KB per record)

**Decrease `max_in_memory_records` when:**
- Memory-constrained environments (containers with <2GB RAM)
- Infrequent record queries (batch processing)
- Strong consistency requirements (must always read from storage)

**Enable TTL (`in_memory_ttl_seconds > 0`) when:**
- Records are updated externally (concurrent writers)
- Stale data is unacceptable (real-time dashboards)
- Memory pressure needs automatic relief

**Typical values:**
- Short-lived jobs: `ttl_seconds=60` (1 minute)
- Long-running services: `ttl_seconds=300-600` (5-10 minutes)
- High-frequency updates: `ttl_seconds=30` (30 seconds)

**Performance note**: TTL cleanup runs once per ingest (not continuously) and only processes expired records. Setting TTL below your typical ingestion interval (e.g., TTL=5s with 10s between ingests) is inefficient but won't cause issues.

**Disable TTL (default `ttl_seconds=0`) when:**
- Single-writer scenarios (no external updates)
- Records are append-only (immutable)
- Maximum performance required

#### Memory Impact Analysis

| Records | Memory (Typical) | Use Case |
|---------|------------------|----------|
| 512     | ~500KB           | Small projects, CI pipelines |
| 1024    | ~1MB (default)   | Typical enterprise test suite |
| 2048    | ~2MB             | Large organizations (5000+ tests) |
| 4096    | ~4MB             | Very large test repositories |

**Note:** Actual memory usage varies based on record metadata size. Use monitoring to measure actual impact.

#### Example: High-Throughput Configuration

```python
# For processing 10,000+ test cases with frequent queries
from pathlib import Path
from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.storage.local import LocalStorageBackend

storage = LocalStorageBackend({"base_path": "./bronze_storage"})
bronze = BronzeLayer(
    storage_path=Path("./bronze"),
    storage_backend=storage,
    max_in_memory_records=4096,  # Cache 4000 most recent
    in_memory_ttl_seconds=600,   # 10-minute freshness window
)

# Ingest records - most recent 4096 stay in memory
for test_case in large_test_suite:
    bronze.ingest(test_case, metadata)

# Fast retrieval from cache
recent_records = bronze.get_bronze_records(limit=100)  # Cache hit!
```

#### Example: Memory-Constrained Environment

```python
# For Docker containers with 1GB memory limit
bronze = BronzeLayer(
    storage_path=Path("./bronze"),
    storage_backend=storage,
    max_in_memory_records=256,   # Minimal cache
    in_memory_ttl_seconds=60,    # Aggressive eviction
)
```

#### Monitoring Cache Performance

The Bronze layer logs cache metrics when telemetry is enabled:

```python
from importobot.telemetry import TelemetryClient

client = TelemetryClient(enabled=True)
# Bronze layer automatically records cache hit/miss rates

# Check logs for cache effectiveness
# INFO: bronze_cache_hit_rate=0.85 (85% cache hits)
# INFO: bronze_cache_evictions=12 (12 records evicted due to TTL/size)
```

#### Migration Checklist

If upgrading from v0.1.0:

1. ✅ **No code changes required** - defaults preserve existing behavior
2. ⚠️ **Memory usage increase** - Budget ~1MB additional memory (default cache)
3. ✅ **Performance improvement** - Automatic 50-80% speedup for repeated queries
4. 🔧 **Optional tuning** - Profile your workload and adjust if needed

**Breaking change:** If you were directly accessing `bronze._records` (private API), this has moved to `bronze._in_memory_records` with different structure. Use `bronze.get_bronze_records()` instead (public API).

## Breaking changes in v0.1.1

**Version 0.1.1 introduces a new medallion architecture (Bronze/Silver/Gold layers) that replaces previous internal implementations.**

### Who should read this?

- Teams upgrading from v0.1.0 to v0.1.1
- Platform owners wiring Bronze/Silver/Gold workflows
- Contributors touching medallion internals

## Summary of changes

### Architecture migration

**v0.1.1 enforces the medallion architecture:**

| Component | v0.1.0 (Old) | v0.1.1 (New - Required) |
| --- | --- | --- |
| **Format Detection** | Ad-hoc pattern matching | **Medallion Bronze layer** with MVLP Bayesian confidence scoring (upgraded to independent Bayesian in 0.1.2) |
| **Data Validation** | Basic validation | **Security Gateway** with strict validation levels |
| **Confidence Scoring** | Simple heuristics | **MVLP Bayesian optimization** with SciPy-based parameter tuning (optional via `importobot[advanced]`) (upgraded to independent Bayesian in 0.1.2) |
| **Internal APIs** | Mixed public/private | **Clear separation**: Public APIs stable, internal APIs private |

### No backwards compatibility for internals

Previous internal implementations have been removed:
- Old Bayesian confidence implementation removed (replaced by MVLP Bayesian scoring in 0.1.1 and independent Bayesian scoring in 0.1.2)
- Ad-hoc validation replaced by medallion validation layers
- Internal APIs reorganized for clarity

**Public API remains stable**: `JsonToRobotConverter`, the CLI, and `importobot.api.*` continue to work as before, now powered by the medallion layers under the hood.

## Migration Steps

1. **Inventory Current Entry Points**
   - List CLI jobs, batch scripts, and API call sites that invoke Importobot.
   - Identify where raw exports enter the system and where Robot Framework files
     are written.

2. **Introduce Bronze ingestion**
   - Wrap raw JSON ingestion with `BronzeLayer.ingest` to capture metadata,
     validation warnings, and lineage.
   - Persist the returned `ProcessingResult` or propagate the `LayerMetadata`
     to downstream systems.

3. **Plan Silver standardization**
   - Until MR2 ships, keep the existing normalization logic. Once available,
     migrate the logic into `SilverLayer` helpers and feed Gold a curated payload.

4. **Enable Gold previews**
   - Instantiate `GoldLayer` and pass curated suites plus the Bronze/Silver
     metadata.
   - Add a `conversion_optimization` block to metadata when wanting the preview
     optimization to run (see User Guide for a full example).
   - Read the `optimization_preview` payload from `ProcessingResult.details` and
     decide whether to promote the suggested parameters.

5. **Update automation scripts**
   - For CI/CD pipelines, add a job that runs the medallion preview and publishes
     the optimization summary as part of the build artifacts.
   - For bulk migrations, store Bronze/Silver/Gold outputs in workspaces that can
     be audited later.

6. **Roll out gradually**
   - Start with a subset of suites or environments.
   - Compare Gold preview metrics versus existing output before switching
     production exporters over.

## Suggested Timeline

- **Sprint 0** – Add Bronze ingestion wrapper and capture metadata in staging.
- **Sprint 1** – Run Gold preview in parallel; review optimization telemetry.
- **Sprint 2** – Gate production conversions on Bronze validation + Gold preview
  score thresholds.
- **Post-Gold-Layer-Implementation** – Replace custom optimizers with the shipped
  OptimizedConverter once benchmarks confirm the value.

## Alternative Strategy

If the medallion layers uncover blocking issues, revert to the previous
`JsonToRobotConverter` path while undergoing triage. Disable the
`conversion_optimization` metadata flag to skip the optimizer entirely.


## Documentation Map

- [User Guide](User-Guide) – CLI usage and medallion walkthrough.
- [Mathematical Foundations](Mathematical-Foundations) – Optimization benchmark
  plan and algorithm details.
- [Performance Benchmarks](Performance-Benchmarks) – How to run and interpret
  the performance benchmark suite.
- [CHANGELOG](../CHANGELOG.md) – Version history and breaking changes.
