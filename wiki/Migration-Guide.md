# Migration Guide

This guide helps users migrate to the **medallion architecture** introduced in v0.1.1.

## ⚠️ Breaking Changes in v0.1.1

**Version 0.1.1 introduces a new medallion architecture (Bronze/Silver/Gold layers) that replaces previous internal implementations.**

### Who Should Read This?

- Teams upgrading from v0.1.0 to v0.1.1
- Platform owners implementing Bronze/Silver/Gold layer workflows
- Contributors working with the new medallion architecture

## What Changed

### Architecture Migration (BREAKING)

**v0.1.1 enforces medallion architecture:**

| Component | v0.1.0 (Old) | v0.1.1 (New - Required) |
| --- | --- | --- |
| **Format Detection** | Ad-hoc pattern matching | **Medallion Bronze layer** with MVLP Bayesian confidence scoring |
| **Data Validation** | Basic validation | **Security Gateway** with strict validation levels |
| **Confidence Scoring** | Simple heuristics | **MVLP Bayesian optimization** with scipy-based parameter tuning |
| **Internal APIs** | Mixed public/private | **Clear separation**: Public APIs stable, internal APIs private |

### No Backwards Compatibility

**This is an intentional breaking change.** Previous internal implementations have been removed:
- Old Bayesian confidence implementation removed (replaced by MVLP)
- Ad-hoc validation replaced by medallion validation layers
- Internal APIs reorganized for clarity

**Public API remains stable**: `JsonToRobotConverter` CLI and Python API continue to work as before, but now use medallion architecture internally.

## Migration Steps

1. **Inventory Current Entry Points**
   - List CLI jobs, batch scripts, and API call sites that invoke Importobot.
   - Identify where raw exports enter the system and where Robot Framework files
     are written.

2. **Introduce Bronze Ingestion**
   - Wrap raw JSON ingestion with `BronzeLayer.ingest` to capture metadata,
     validation warnings, and lineage.
   - Persist the returned `ProcessingResult` or propagate the `LayerMetadata`
     to downstream systems.

3. **Plan Silver Standardization**
   - Until MR2 ships, keep your existing normalization logic. Once available,
     migrate the logic into `SilverLayer` helpers and feed Gold a curated payload.

4. **Enable Gold Previews**
   - Instantiate `GoldLayer` and pass curated suites plus the Bronze/Silver
     metadata.
   - Add a `conversion_optimization` block to metadata when you want the preview
     optimization to run (see User Guide for a full example).
   - Read the `optimization_preview` payload from `ProcessingResult.details` and
     decide whether to promote the suggested parameters.

5. **Update Automation Scripts**
   - For CI/CD pipelines, add a job that runs the medallion preview and publishes
     the optimization summary as part of the build artifacts.
   - For bulk migrations, store Bronze/Silver/Gold outputs in workspaces that can
     be audited later.

6. **Roll Out Gradually**
   - Start with a subset of suites or environments.
   - Compare Gold preview metrics versus your existing output before switching
     production exporters over.

## Suggested Timeline

- **Sprint 0** – Add Bronze ingestion wrapper and capture metadata in staging.
- **Sprint 1** – Run Gold preview in parallel; review optimization telemetry.
- **Sprint 2** – Gate production conversions on Bronze validation + Gold preview
  score thresholds.
- **Post-Gold-Layer-Implementation** – Replace custom optimizers with the shipped
  OptimizedConverter once benchmarks confirm the value.

## Fallback Strategy

If the medallion layers uncover blocking issues, revert to the classic
`JsonToRobotConverter` path while you triage. No irreversible migrations are
required; you can disable the `conversion_optimization` metadata flag to skip
the optimizer entirely.

## Breaking Changes in v0.1.1

**IMPORTANT**: Version 0.1.1 introduces the medallion architecture as the **required** data processing model. There is **no backwards compatibility** with internal implementations from v0.1.0.

### What Changed

1. **Medallion Architecture is Mandatory**
   - All data processing flows through Bronze → Silver → Gold layers
   - Internal modules completely restructured
   - No fallback to pre-0.1.1 implementations

2. **Service Layer Required**
   - Security gateway validates all inputs
   - Validation service provides quality assessment
   - Format detection uses medallion-based evidence accumulation

3. **Internal APIs Changed**
   - `importobot.core.*` modules refactored for medallion architecture
   - `importobot.medallion.*` modules are implementation details, not public API
   - Private modules may change between any version without notice

### What Stayed Stable

**Public APIs remain unchanged**:
- `JsonToRobotConverter` - Works exactly as before
- `importobot.api.*` - Enterprise toolkit unchanged
- CLI command: `importobot <input> <output>` - Same interface
- `importobot.config` - Configuration API stable
- `importobot.exceptions` - Error handling unchanged

### Migration Required For

**If you were using internal APIs** (not recommended):
- Direct imports from `importobot.core.*` → Use public `JsonToRobotConverter` API
- Direct imports from `importobot.medallion.*` → These are private, use public API
- Custom extensions of internal classes → Refactor to use composition with public API

**If you were using only public APIs**:
- **No migration needed** - Your code continues to work without changes

### API Stability Policy

Following [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR version** (X.0.0): Breaking changes to **public** API
- **MINOR version** (0.X.0): New features, public API backward-compatible; **internal APIs may break**
- **PATCH version** (0.0.X): Bug fixes only

**Public APIs** (stable across minor versions):
- `JsonToRobotConverter` - Primary conversion interface
- `importobot.config` - Configuration management
- `importobot.exceptions` - Error handling
- `importobot.api.*` - Enterprise toolkit
- CLI: `importobot <input> <output>`

**Private APIs** (can change any time):
- Modules with empty `__all__` declarations
- Functions/classes prefixed with `_`
- `importobot.core.*` - Engine internals
- `importobot.medallion.*` - Implementation details
- `importobot.services.*` - Internal services (except exposed via public API)

### No Backwards Compatibility

Version 0.1.1 **intentionally breaks** backwards compatibility with internal implementations:
- Forces adoption of medallion architecture
- Ensures all users benefit from improved validation and security
- Prevents reliance on unstable internal APIs

**This is by design.** We want all users on the medallion architecture, not maintaining legacy code paths.

## Documentation Map

- [User Guide](User-Guide) – CLI usage and medallion walkthrough.
- [Mathematical Foundations](Mathematical-Foundations) – Optimization benchmark
  plan and algorithm details.
- [Performance Benchmarks](Performance-Benchmarks) – How to run and interpret
  the performance benchmark suite.
- [CHANGELOG](../CHANGELOG.md) – Version history and breaking changes.
