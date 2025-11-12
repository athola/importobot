"""
Importobot ASV Benchmark Suite.

This package contains Airspeed Velocity (ASV) benchmarks for measuring
the performance of importobot's test conversion and format detection operations.

Benchmark Suites
----------------

conversion:
    - ZephyrConversionSuite: Tests Zephyr JSON to Robot Framework conversion
    - DirectoryConversionSuite: Tests bulk directory conversion operations
    - ValidationSuite: Tests input validation and error detection

Running Benchmarks
------------------
Run all benchmarks:
    $ asv run

Run specific suite:
    $ asv run --bench ZephyrConversionSuite

Run with verbose output:
    $ asv run --verbose --show-stderr

Compare performance:
    $ asv continuous main HEAD

Generate HTML reports:
    $ asv publish
    $ asv preview

Performance Targets
-------------------
Based on the 0.1.2 release notes, importobot targets:
- Average detection latency: ~0.055s per request
- No loss of throughput compared to previous versions
- Memory efficiency for large test suites (100+ test cases)

Notes
-----
- Benchmarks use temporary files that are cleaned up after each
- All benchmarks should complete within their defined timeout (60-180s)
"""

from .conversion import (
    DirectoryConversionSuite,
    ValidationSuite,
    ZephyrConversionSuite,
)

__all__ = [
    # Conversion benchmarks
    "DirectoryConversionSuite",
    "ValidationSuite",
    "ZephyrConversionSuite",
]
