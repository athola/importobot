# ADR-0001: Adopt Medallion Architecture for Conversion Pipeline

## Status

Accepted – May 2025

## Context

- The original conversion process was a single, monolithic function with validation logic scattered throughout.
- Key customers required features like data lineage tracking, multi-stage validation, and the ability to preview optimizations.
- The Medallion architecture (Bronze/Silver/Gold), common in data engineering, provides a structured model for our data processing stages: ingestion, standardization, and export.

## Decision

- We will refactor the conversion pipeline into three distinct components: `BronzeLayer`, `SilverLayer`, and `GoldLayer`.
- These components will share a common interface for handling metadata, quality metrics, and data lineage.
- The existing CLI will not change. The Medallion pipeline will initially be an internal implementation detail, exposed only through a new programmatic API.
- A new `OptimizationService` will be used to preview changes in the Gold layer before they are finalized.

## Consequences

- **Positive:** This change provides the necessary structure for implementing data lineage, staged validation, and future optimizations.
- **Negative:** The new architecture is more complex than the previous monolithic converter. Developers must ensure that metadata is passed consistently between layers.
- **Neutral:** The layers can be run independently (e.g., Bronze-only for ingestion, or Bronze+Silver for standardization), which can be useful for debugging and phased rollouts.
