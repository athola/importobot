# Performance Characteristics

This document provides an overview of Importobot's performance characteristics.

## Key Performance Indicators

-   **Single-File Conversion:** ~0.4 seconds on average for a medium-complexity file.
-   **Bulk Conversion:** ~2.8 seconds for 25 files (~0.11 seconds per file).
-   **Memory Footprint:** ~1-3 MB increase for a single conversion, and under 40 MB for a bulk conversion.
-   **Cache Hit Rate:** ~85% in typical usage.

These metrics were captured on a standard CI runner (Ubuntu 22.04, Python 3.12). Performance may vary depending on hardware and the complexity of the input files.

## Performance Regressions

Performance regressions are tracked using the following thresholds:

-   **Single conversion time:** >10% increase
-   **Bulk conversion throughput:** >15% decrease
-   **Memory usage:** >5 MB sustained increase
-   **Cache hit rate:** <70%

These thresholds are enforced in CI to prevent performance regressions from being introduced into the codebase.

## Performance Optimizations

### JSON Cache Serialization

The performance cache uses an optimized serialization strategy to avoid unnecessary overhead. For hashable types, the value is used directly as the cache key. For unhashable types, the object's identity is used, avoiding the need for serialization altogether.

### Validation Pipeline

The validation pipeline is designed to be fast and efficient. Routine linting now relies on the consolidated `make lint` target (ruff + mypy) after retiring the old `make lint-fast` shortcut.
