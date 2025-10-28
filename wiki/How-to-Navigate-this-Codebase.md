# How to Navigate this Codebase

This guide provides a breakdown of the Importobot codebase, focusing on its layered architecture and key modules. The project's structure is influenced by the pandas API pattern: core functionality is exposed through key classes, internal modules are kept private, and an advanced toolkit is available for integration purposes.

```
src/importobot/
├── __init__.py              # Main API - most users only need this
├── api/                     # Advanced integrations (CI/CD, custom tools)
├── core/                    # Conversion engine - don't touch directly
├── medallion/               # Data pipeline - implementation details
├── utils/                   # Shared helpers - mixed visibility
├── services/                # Business logic coordination
├── cli/                     # Command-line interface
└── exceptions.py            # Error types
```

## The Public API

The public API is the primary entry point for users who want to integrate Importobot into their own projects.

### `src/importobot/__init__.py`

This file exposes the main `JsonToRobotConverter` class. The public API surface is intentionally kept small to minimize breaking changes between releases. Dependency validation occurs at import time, providing clear error messages if Robot Framework is not installed.

```python
import importobot
converter = importobot.JsonToRobotConverter()
```

### `src/importobot/api/`

The `api` module provides tools for more advanced integrations, such as CI/CD pipelines or custom validation scripts.

- `validation/`: Programmatic access to JSON structure validation.
- `suggestions/`: Experimental tools for suggesting improvements to test steps.
- `converters/`: Alternative conversion strategies.

## The Core Engine

The `core/` directory contains the conversion pipeline. These modules are intentionally private. They may be refactored as the conversion logic is improved.

### `core/engine.py`

The `GenericConversionEngine.convert()` method is the main pipeline. It runs three phases:

1. Extract test cases from the JSON structure using `find_tests()`
2. Detect Robot Framework libraries by analyzing step patterns
3. Generate the final Robot Framework syntax

The error handling around line 64-74 provides insight into how feedback is provided to users when their JSON doesn't match expected patterns.

### `core/parsers.py`

The `GenericTestFileParser` handles the messiness of real-world JSON exports. Test management systems export slightly different structures, so this module looks for common patterns like `name` + `steps` fields or `testCase` objects.

### `core/keyword_generator.py`

This turns parsed test steps into Robot Framework keywords. The `generate_test_case()` method handles the conversion, while `detect_libraries()` scans for patterns that indicate which Robot Framework libraries to import.

### `core/keywords/generators/`

Each file handles a specific domain:

- `web_keywords.py` - Selenium patterns like "click button" or "enter text"
- `api_keywords.py` - HTTP request patterns
- `ssh_keywords.py` - Command execution patterns
- `database_keywords.py` - SQL query patterns

The pattern matching is regex-based. If adding support for a new type of step, start by looking at the existing patterns in these files.

## The Medallion Architecture

This architecture was adopted from data lakehouse patterns because Importobot needed to handle messy, real-world data exports. The layers are internal implementation details and change frequently.

**Bronze Layer:** Raw data ingestion and format detection
**Silver Layer:** Processed and standardized data
**Gold Layer:** Business-ready outputs

### Bronze Layer Format Detection

The bronze layer figures out what kind of JSON is being dealt with. This matters because customers provide exports from at least five different test management systems, each with slightly different JSON structures.

#### `bronze/format_detector.py`

This runs Bayesian confidence scoring to guess the format. Bayesian methods are chosen because they expose probability scores rather than binary decisions - important when dealing with ambiguous data.

#### `bronze/evidence_collector.py`

Collects signals from the JSON structure. For example, Zephyr exports usually have `testCase` fields, while Xray uses different key names. The evidence accumulator weighs these signals.

#### `bronze/confidence_calculator.py`

The Bayesian math is derived here. Proper temperature scaling was integrated after discovering that the initial implementation couldn't achieve >0.8 confidence for strong evidence - a business requirement from this testing framework. The quadratic decay function for P(E|¬H) estimation was the result of several iterations of testing against real customer data.

#### `bronze/storage/local.py`

Handles file system operations and caching. A query pagination bug was fixed here from an earlier implementation which caused issues with large test suites - it was materializing data prematurely instead of just counting matches.

## Utilities and Services

### `utils/`

Shared helpers used across the codebase:

- `validation/` - Input validation with helpful error messages
- `test_generation/` - Test data generators for development
- Legacy Robot Framework compatibility layers were removed after upgrading dependencies

The validation module is worth understanding - it catches common JSON structure issues early and provides specific feedback about what went wrong.

### `services/`

High-level business logic coordination. Most of this is plumbing for the conversion pipeline.

### `cli/`

Command-line interface using standard argparse patterns. The `handlers.py` file shows how CLI commands are wired to the core conversion logic.

### `exceptions.py`

Custom exception types. When an error is received, check here first - the exception names usually describe exactly what went wrong (e.g., `ValidationError` for bad input, `ConversionError` for processing failures).

## Test Structure

The test suite demonstrates how the codebase is intended to work:

- `unit/` - Component tests
- `integration/` - End-to-end workflows
- `performance/` - Performance benchmarks
- `generative/` - Property-based tests with Hypothesis

The most useful tests to read are in `tests/unit/core/test_engine.py` (shows conversion pipeline) and `tests/unit/medallion/bronze/` (shows format detection logic).

## Getting Started with Development

This section provides a recommended path for learning the codebase, along with guidelines for making changes.

### Learning Path

- **Week 1: Public API & Core Concepts.** Read `__init__.py` to understand the public `JsonToRobotConverter`. Run the examples in the [Getting Started](Getting-Started.md) guide to see how the tool works.
- **Week 2: Core Conversion Pipeline.** Study `core/engine.py` and its `convert()` method. Trace the data flow through `core/parsers.py` (for input handling) and `core/keyword_generator.py` (for Robot Framework output).
- **Week 3: Format Detection & Medallion Architecture.** Read the `medallion/bronze` layer files to understand the Bayesian confidence scoring. The logic for identifying different JSON formats (like Zephyr vs. Xray) is in `medallion/bronze/format_detector.py`.
- **Week 4: Advanced Topics.** Explore the caching system (`importobot.caching`), performance optimizations, and the process for adding new test management system formats.

### Development Guidelines

- **API Stability:** Do not break the public API in `src/importobot/__init__.py`. Internal modules (`core`, `medallion`) can be refactored as needed.
- **Testing:** Write tests before code (TDD is recommended). The test suite in `tests/` provides practical examples of how each component is intended to work. Run `make test` before committing.
- **Debugging:** Use `IMPORTOBOT_ENABLE_TELEMETRY=true` to inspect cache performance and other internal metrics. For input-related issues, `importobot.api.validation` is the best place to start.

### How to...

- **...add support for a new test management system?**
  1. Create a new format definition in `medallion/bronze/formats/`.
  2. Add detection logic to `medallion/bronze/format_detector.py`.
  3. Update `medallion/bronze/evidence_collector.py` to extract signals from the new format.
  4. Write unit tests in `tests/unit/medallion/bronze/formats/`.

- **...understand the Robot Framework code generation?**
  1. Start with `core/keyword_generator.py`.
  2. Examine the domain-specific generators in `core/keywords/generators/`.
  3. See how libraries are detected in `pattern_matcher.py`.
  4. Follow the final assembly in `core/engine.py`.

## Related Documentation

- [Getting Started](Getting-Started) - Installation and usage
- [Mathematical Foundations](Mathematical-Foundations) - Bayesian confidence algorithms
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture) - Design history

