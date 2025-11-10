# How to Navigate this Codebase

This guide explains the Importobot codebase, its layered architecture, and key modules. The project exposes core functionality through a small public API and keeps internal modules private to ensure stability.

```
src/importobot/
├── __init__.py              # Public API for library usage.
├── api/                     # Stable API for external integrations.
├── core/                    # Internal conversion logic.
├── medallion/               # Medallion data cleaning pipeline.
├── utils/                   # General utility functions.
├── services/                # Connects different services and modules.
├── cli/                     # CLI entry point and logic.
└── exceptions.py            # Custom exception classes.
```

## Public API

The public API is the intended entry point for using Importobot as a Python library.

### `src/importobot/__init__.py`

This file exposes the main `JsonToRobotConverter` class. Its public interface is kept small to minimize breaking changes between releases.

### `src/importobot/api/`

This module provides a stable, documented API for deeper integrations, like CI/CD pipelines or custom validation scripts.

## Core Conversion Engine

The `core/` directory holds the internal conversion logic. Its modules are not considered part of the public API and may change between releases.

- `engine.py`: Assembles and executes the steps of the conversion process.
- `parsers.py`: Parses different JSON export formats into a standardized internal model.
- `keyword_generator.py`: Translates the internal representation of test steps into Robot Framework keywords.

## Medallion Architecture

This architecture was adopted from data engineering patterns to manage inconsistent and messy data from different test management tools. It processes data in three sequential layers:

- **Bronze Layer (Ingestion):** Ingests the raw JSON export and detects its format (e.g., Zephyr, Xray).
- **Silver Layer (Standardization):** Cleans the raw data and transforms it into a single, consistent internal format.
- **Gold Layer (Generation):** Generates the final `.robot` test suite from the standardized data.

This layered approach isolates the logic for handling each source format, making the system easier to maintain and extend.

## Other Key Directories

- **`utils/`**: Contains shared helper functions, such as file I/O and data manipulation routines, used across multiple modules.
- **`services/`**: Implements specific, high-level features by connecting different parts of the application. For example, `services/conversion_service.py` might use the `core` engine and `medallion` pipeline to perform a full conversion.
- **`cli/`**: Implements the command-line interface using Python's `argparse`. This is the entry point for the `importobot` command.
- **`exceptions.py`**: Defines custom exception classes, allowing for specific error handling throughout the application.

## Test Structure

The `tests/` directory is organized by testing type. The tests serve as living documentation for how components are expected to behave.

- **`unit/`**: Tests for individual functions and classes in isolation.
- **`integration/`**: Tests that verify workflows between multiple components, such as converting a file and checking the output.
- **`performance/`**: Benchmarks for critical code paths, tracked with `asv`.
- **`generative/`**: Property-based tests using the Hypothesis library to find edge cases.

## Learning the Codebase

A good way to learn the codebase is to trace the data flow of a conversion:

1.  Start with the public API in `src/importobot/__init__.py`. See how it's used in the [Getting Started](Getting-Started.md) guide.
2.  Follow the call into `core/engine.py` to see how the conversion is managed.
3.  Trace the process through the `medallion/` layers (Bronze, Silver, Gold) to see how data is cleaned and standardized.
4.  Examine the `tests/` for the corresponding modules to see concrete examples of their behavior.

### How to...

- **...add support for a new test management system?**
  1. Create a new format definition in `medallion/bronze/formats/`.
  2. Add detection logic to `medallion/bronze/format_detector.py`.
  3. Update `medallion/bronze/evidence_collector.py` to extract signals from the new format.
  4. Write unit tests in `tests/unit/medallion/bronze/formats/`.

- **...understand the Robot Framework code generation?**
  1. Start with `core/keyword_generator.py`.
  2. Examine the domain-specific generators in `core/keywords/generators/`.

## Related Documentation

- [Getting Started](Getting-Started.md)
- [Mathematical Foundations](Mathematical-Foundations.md)
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture.md)
