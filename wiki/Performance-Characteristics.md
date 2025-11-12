# Performance Characteristics

This document outlines Importobot's performance characteristics.

## Key Performance Indicators

-   **Single-File Conversion**: Approximately 0.4 seconds on average for a medium-complexity file.
-   **Bulk Conversion**: Approximately 2.8 seconds for 25 files (averaging 0.11 seconds per file).
-   **Memory Footprint**: Increases by 1-3 MB for a single conversion and remains under 40 MB for a bulk conversion.
-   **Cache Hit Rate**: Achieves approximately 85% in typical usage.

These metrics were captured on a standard CI runner (Ubuntu 22.04, Python 3.12). Actual performance may vary based on hardware and input file complexity.

## Performance Regressions

Performance regressions are tracked using the following thresholds:

-   **Single conversion time**: Greater than a 10% increase.
-   **Bulk conversion throughput**: Greater than a 15% decrease.
-   **Memory usage**: Greater than a 5 MB sustained increase.
-   **Cache hit rate**: Below 70%.

These thresholds are enforced in CI to prevent performance regressions from being introduced into the codebase.

## Performance Optimizations

### JSON Cache Serialization

The performance cache employs an optimized serialization strategy to minimize overhead. For hashable types, the value serves directly as the cache key. For unhashable types, the object's identity is used, eliminating the need for serialization.

### Validation Pipeline

The validation pipeline is optimized for speed and efficiency.
