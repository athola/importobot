# How to Navigate this Codebase

This guide provides a breakdown of the Importobot codebase, focusing on its layered architecture and key modules. The project follows a structure where core functionality is exposed through a small public API, while internal modules are kept private.

```
src/importobot/
├── __init__.py              # Main API - most users only need this
├── api/                     # Advanced integrations (CI/CD, custom tools)
├── core/                    # Conversion engine
├── medallion/               # Data pipeline
├── utils/                   # Shared helpers
├── services/                # Business logic coordination
├── cli/                     # Command-line interface
└── exceptions.py            # Error types
```

## Public API

The public API is the primary entry point for users who want to integrate Importobot into their own projects.

### `src/importobot/__init__.py`

This file exposes the main `JsonToRobotConverter` class. The public API surface is intentionally kept small to minimize breaking changes between releases.

### `src/importobot/api/`

The `api` module provides tools for integrations, such as CI/CD pipelines or custom validation scripts.

## Core Engine

The `core/` directory contains the conversion pipeline. These modules are internal and subject to change.

- `engine.py`: The main pipeline that orchestrates the conversion process.
- `parsers.py`: Handles the messy details of parsing different JSON export formats.
- `keyword_generator.py`: Converts parsed test steps into Robot Framework keywords.

## Medallion Architecture

This architecture was adopted from data lakehouse patterns to handle messy, real-world data exports. It consists of three layers:

- **Bronze Layer:** Raw data ingestion and format detection. This layer is responsible for identifying the type of JSON export (e.g., Zephyr, Xray).
- **Silver Layer:** Processed and standardized data. This layer cleans up the raw data and transforms it into a consistent format.
- **Gold Layer:** Business-ready outputs. This layer generates the final Robot Framework files.

This layered approach allows us to isolate the complexity of handling different JSON formats.

## Utilities and Services

- `utils/`: Shared helpers used across the codebase.
- `services/`: High-level business logic coordination.
- `cli/`: Command-line interface.
- `exceptions.py`: Custom exception types.

## Test Structure

The test suite demonstrates how the codebase is intended to work:

- `unit/`: Component tests
- `integration/`: End-to-end workflows
- `performance/`: Performance benchmarks
- `generative/`: Property-based tests with Hypothesis

## Getting Started with Development

A good way to learn the codebase is to follow the data flow:

1.  Start with the public API in `__init__.py` and the examples in the [Getting Started](Getting-Started.md) guide.
2.  Trace the conversion process from `core/engine.py` through the `core/parsers.py` and `core/keyword_generator.py`.
3.  Explore the `medallion/` layers to understand how data is ingested, cleaned, and transformed.
4.  The tests in `tests/` are a great resource for understanding how each component is intended to work.

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
