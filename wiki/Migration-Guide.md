# Migration Guide

This guide covers the switch to the medallion architecture introduced in v0.1.1.

## Additional breaking changes in v0.1.1

| Area | Change | Action |
| --- | --- | --- |
| Security Gateway | `sanitize_api_input` / `validate_file_operation` now return typed dictionaries that include an optional `correlation_id`. | Update call sites to read from `result["sanitized_data"]` and propagate `result["correlation_id"]` into logs/metadata where you need request tracing. |
| Data ingestion | `DataIngestionService` automatically generates a correlation id per ingest and stores it in `metadata.custom_metadata` and error details. | If you previously injected your own `correlation_id`, pass it via the new `context={"correlation_id": "..."}` argument on security gateway calls. |
| Caching | Detection/cache limits are now driven by environment variables (`IMPORTOBOT_DETECTION_CACHE_MAX_SIZE`, `IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT`, `IMPORTOBOT_FILE_CACHE_MAX_MB`, `IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE`). | Export the variables in CI/staging to tune cache pressure; omit them to use the previous defaults. |
| Optimization | SciPy dependency downgraded to optional; MVLP optimization falls back to heuristic mode when SciPy is absent. | Install SciPy in environments that perform parameter training, or accept heuristic scoring when only runtime confidence is required. |

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
| **Format Detection** | Ad-hoc pattern matching | **Medallion Bronze layer** with MVLP Bayesian confidence scoring |
| **Data Validation** | Basic validation | **Security Gateway** with strict validation levels |
| **Confidence Scoring** | Simple heuristics | **MVLP Bayesian optimization** with SciPy-based parameter tuning (optional via `importobot[confidence]`) |
| **Internal APIs** | Mixed public/private | **Clear separation**: Public APIs stable, internal APIs private |

### No backwards compatibility for internals

Previous internal implementations have been removed:
- Old Bayesian confidence implementation removed (replaced by MVLP)
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

## Fallback Strategy

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
