# ADR-0001: Adopt Medallion Architecture for Conversion Pipeline

## Status

Accepted – May 2025

## Context

- Pre-medallion Importobot used a monolithic converter with ad-hoc validation.
- Enterprise customers asked for lineage tracking, staged validation, and
  optimization previews.
- Databricks-style Medallion architecture (Bronze/Silver/Gold) maps cleanly onto
  ingestion → curation → export phases.

## Decision

- Introduce `BronzeLayer`, `SilverLayer`, and `GoldLayer` components with shared
  interfaces for metadata, quality metrics, and lineage.
- Keep existing CLI stable; medallion layers are opt-in via API.
- Use `OptimizationService` to preview conversion optimization in Gold before
  OptimizedConverter launches.

## Consequences

- Additional complexity, but delivers traceability + future optimization hooks.
- Requires writers to keep cross-layer metadata consistent.
- Enables degradable rollouts: Bronze-only, Bronze+Silver, full Bronze→Gold.
