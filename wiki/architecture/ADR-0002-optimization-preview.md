# ADR-0002: Optimization Preview Service in Gold Layer

## Status

Accepted – August 2025

## Context

- The Gold layer requires a way to test and tune different optimization strategies before the `OptimizedConverter` is released for general availability.
- The `utils.optimization` module already contained several optimization algorithms (gradient descent, simulated annealing, genetic algorithms) that were not being used.
- There is a product requirement to show users a preview of optimization results without blocking the main conversion process.

## Decision

- We will introduce a new `OptimizationService` that can be configured with different optimization algorithms.
- This service will be called from `GoldLayer._run_optimization_preview` when the `conversion_optimization` flag is set in the input metadata.
- The service will cache the results of optimization runs to allow for fast previews. The cache size will be limited using a Least Recently Used (LRU) eviction policy to control memory usage.

## Consequences

- The in-memory cache for the optimizer state will slightly increase the application's memory usage, but this is controlled by the LRU cache limit.
- We will add benchmarks for the optimization algorithms to track their performance over time.
- The future `OptimizedConverter` can use this same service, which avoids the need to introduce breaking changes to the API later.
