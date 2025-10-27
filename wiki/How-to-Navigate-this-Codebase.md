# How to Navigate this Codebase

This guide provides a breakdown of the Importobot codebase, focusing on its layered architecture and key modules. It is intended to help new engineers get started with development.

The project's structure is influenced by the pandas API pattern: core functionality is exposed through key classes, internal modules are kept private, and an advanced toolkit is available for integration purposes.

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

A public API is exposed for users looking to tie this into their project.

### `src/importobot/__init__.py`

This file exposes the `JsonToRobotConverter` class and a few helpers. The public surface is kept small because changing APIs can frequently break user code. The dependency validation happens at import time - clear errors display immediately if Robot Framework is missing.

```python
import importobot
converter = importobot.JsonToRobotConverter()
```

### `src/importobot/api/`

The API module is for integration work. This was built to address the need to plug Importobot into a CI/CD pipeline and provide programmatic access to validation and suggestions.

- `validation/` - JSON structure validation before conversion
- `suggestions/` - Step improvement suggestions (still experimental)
- `converters/` - Alternative conversion strategies

Use this when building tooling to call the script to perform analysis on test suite infrastructure.

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

## Learning Path

Based on mentoring new engineers who join the project:

### Week 1: Public API
Read `__init__.py` completely, understand `JsonToRobotConverter`, try the basic examples from Getting-Started.

### Week 2: Core Pipeline
Study `core/engine.py`'s `convert()` method, look at how parsing works in `core/parsers.py`, understand keyword generation.

### Week 3: Format Detection
Read the bronze layer files, understand the Bayesian confidence scoring, look at real test data to see how evidence collection works.

### Week 4: Advanced Topics
Study the caching system, performance optimizations, and how to add new test management system formats.

## Common Questions

**How is Zephyr format handled?**
Start at `medallion/bronze/formats/zephyr_format.py`, then trace through `format_detector.py` and `evidence_collector.py`. The confidence scoring in `confidence_calculator.py` shows how we measure certainty.

**How does Robot Framework code generation work?**
Begin with `core/keyword_generator.py`, check the domain-specific generators in `core/keywords/generators/`, see library detection in `pattern_matcher.py`, and study the final assembly in `core/engine.py`.

**Where should I look when errors occur?**
Check `exceptions.py` for error types, look at validation in `utils/validation/`, and examine how errors are raised in `core/engine.py`.

**How do I add support for a new test management system?**
Create a format file in `medallion/bronze/formats/`, add detection logic to `format_detector.py`, update evidence collection in `evidence_collector.py`, and write tests in `tests/unit/medallion/bronze/formats/`.

## Development Guidelines

**Reading the code:** Start with `core/interfaces.py` for contracts, follow the data flow from `engine.py`, and use the tests to understand intended usage.

**Making changes:** Don't break public APIs, write tests first (TDD is a recommended practice), ensure Bayesian confidence scores exceed 0.8 for strong evidence, and run `make test` before committing.

**Debugging:** Enable telemetry with `IMPORTOBOT_ENABLE_TELEMETRY=true` to see cache hit rates, use `importobot.api.validation` for input issues, and check confidence scores when format detection seems wrong.

## Related Documentation

- [Getting Started](Getting-Started) - Installation and usage
- [Mathematical Foundations](Mathematical-Foundations) - Bayesian confidence algorithms
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture) - Design history

---

This guide was written to provide essential guidance for engineers learning this codebase. The medallion architecture and Bayesian confidence scoring took time to get right - the >0.8 confidence requirement came from real testing needs. If parts are unclear, raise the flag so this guide can be improved.
