# How to Navigate this Codebase

This guide provides a map of the Importobot codebase, its layered architecture, and key modules. The project's public API is kept small to limit breaking changes.

```
src/importobot/
├── __init__.py              # Public API
├── api/                     # Stable API for integrations
├── core/                    # Internal conversion logic
├── medallion/               # Data cleaning pipeline
├── utils/                   # Utility functions
├── services/                # Connects modules
├── cli/                     # CLI logic
├── security/                # Credential mgr, SIEM, compliance
└── exceptions.py            # Custom exceptions
```

## Public API

The public API is the main entry point for using Importobot as a Python library.

### `src/importobot/__init__.py`

This file exposes the main `JsonToRobotConverter` class. Its public interface is kept small to minimize breaking changes between releases.

### `src/importobot/api/`

This module provides a stable, documented API for deeper integrations, like CI/CD pipelines or custom validation scripts.

## Core Conversion Engine

The `core/` directory contains the internal conversion logic. Its modules are not considered part of the public API and may change between releases.

- `engine.py`: Assembles and executes the steps of the conversion process.
- `parsers.py`: Parses different JSON export formats into a standardized internal model.
- `keyword_generator.py`: Translates the internal representation of test steps into Robot Framework keywords.

## Medallion Architecture

This architecture processes data in three sequential layers to handle inconsistent data from different test management tools.

- **Bronze Layer (Ingestion):** Ingests the raw JSON export and detects its format (e.g., Zephyr, Xray).
- **Silver Layer (Standardization):** Cleans the raw data and transforms it into a consistent internal format.
- **Gold Layer (Generation):** Generates the final `.robot` test suite from the standardized data.

This isolates the parsing logic for each source format.

## Other Key Directories

- **`security/`**: Houses CredentialManager, TemplateSecurityScanner, SecureMemory, HSM connectors, SIEM forwarding, compliance reports, and monitoring. Anything touching secrets moves here first to keep `utils/` lean.
- **`utils/`**: Shared helper functions for file I/O, data manipulation, and other low-level tasks.
- **`services/`**: Coordinates high-level features. For example, a service might take a raw file, pass it through the medallion pipeline, and feed the result to the core conversion engine.
- **`cli/`**: Defines the command-line interface available as the `importobot` command.
- **`exceptions.py`**: Custom exception classes used for specific error handling.

## Test Structure

The `tests/` directory is organized by testing type.

- **`unit/`**: Tests for individual functions and classes in isolation.
- **`integration/`**: Tests that verify workflows between multiple components, such as converting a file and checking the output.
- **`performance/`**: Benchmarks for critical code paths, tracked with `asv`.
- **`generative/`**: Property-based tests using the Hypothesis library to find edge cases.
- **`unit/security/`**: Dedicated to the 0.1.5 security modules (CredentialManager, HSM, monitoring, SIEM, template scanning).

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
