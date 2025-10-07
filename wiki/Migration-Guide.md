# Migration Guide

This guide covers the switch to the medallion architecture introduced in v0.1.1.

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
| **Confidence Scoring** | Simple heuristics | **MVLP Bayesian optimization** with scipy-based parameter tuning |
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
