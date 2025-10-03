# ADR-0002: Optimization Preview Service in Gold Layer

## Status

Accepted – August 2025

## Context

- Gold layer needs tunable heuristics before the OptimizedConverter becomes GA.
- Math utilities (`utils.optimization`) already ship with gradient descent,
  simulated annealing, and genetic algorithms but were unused.
- Product requirement: show conversion preview scores without blocking ingest.

## Decision

- Add `OptimizationService` with pluggable algorithms and cached results.
- Invoke it from `GoldLayer._run_optimization_preview` when callers set
  `conversion_optimization` metadata.
- Keep optimizer state cached for quick preview reruns but cap memory via LRU.

## Consequences

- Storage footprint increased slightly (optimizer state), mitigated by caps.
- Optimizer benchmarks added to PLAN.md and wiki for ongoing justification.
- Future OptimizedConverter can reuse the same service without API churn.
