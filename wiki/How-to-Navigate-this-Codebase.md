# How to Navigate this Codebase

I wrote this guide because the Importobot codebase can look complex at first glance. After watching junior engineers spin up on this project, I noticed common patterns of confusion. This is the guide I wish I'd had when I started.

The project uses a layered architecture. We borrowed the pandas API pattern because it works: import key classes directly, keep internal modules private, and provide an enterprise toolkit for advanced users.

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

Start here. 95% of users never need anything beyond what's in `__init__.py`.

### `src/importobot/__init__.py`

This file exposes the `JsonToRobotConverter` class and a few helpers. We deliberately keep the public surface small because changing APIs breaks user code. The dependency validation happens at import time - you'll get clear errors immediately if Robot Framework is missing.

```python
import importobot
converter = importobot.JsonToRobotConverter()
```

That's it for most use cases.

### `src/importobot/api/`

The API module is for integration work. We built this after a customer needed to hook Importobot into their Jenkins pipeline and wanted programmatic access to validation and suggestions.

- `validation/` - JSON structure validation before conversion
- `suggestions/` - Step improvement suggestions (still experimental)
- `converters/` - Alternative conversion strategies

Use this when you're building tooling, not just converting files.

## The Core Engine

The `core/` directory contains the conversion pipeline. These modules are intentionally private - we refactor them frequently as we improve the conversion logic.

### `core/engine.py`

The `GenericConversionEngine.convert()` method is the main pipeline. It runs three phases:

1. Extract test cases from the JSON structure using `find_tests()`
2. Detect Robot Framework libraries by analyzing step patterns
3. Generate the final Robot Framework syntax

The error handling around line 64-74 is worth reading - it shows how we give users specific feedback when their JSON doesn't match expected patterns.

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

The pattern matching is regex-based. If you're adding support for a new type of step, start by looking at the existing patterns in these files.

## The Medallion Architecture

We adopted the medallion architecture from data lakehouse patterns because Importobot needed to handle messy, real-world data exports. The layers are internal implementation details and change frequently.

**Bronze Layer:** Raw data ingestion and format detection
**Silver Layer:** Processed and standardized data
**Gold Layer:** Business-ready outputs

### Bronze Layer Format Detection

The bronze layer figures out what kind of JSON we're dealing with. This matters because customers send us exports from at least five different test management systems, each with slightly different JSON structures.

#### `bronze/format_detector.py`

This runs Bayesian confidence scoring to guess the format. We chose Bayesian methods because they give us probability scores rather than binary decisions - important when dealing with ambiguous data.

#### `bronze/evidence_collector.py`

Collects signals from the JSON structure. For example, Zephyr exports usually have `testCase` fields, while Xray uses different key names. The evidence accumulator weighs these signals.

#### `bronze/confidence_calculator.py`

The Bayesian math lives here. We implemented proper temperature scaling after discovering that our initial implementation couldn't achieve >0.8 confidence for strong evidence - a hard requirement from our testing framework. The quadratic decay function for P(E|¬H) estimation was the result of several iterations of testing against real customer data.

#### `bronze/storage/local.py`

Handles file system operations and caching. The query pagination bug we fixed here was causing issues with large test suites - it was materializing data prematurely instead of just counting matches.

## Utilities and Services

### `utils/`

Shared helpers used across the codebase:

- `validation/` - Input validation with helpful error messages
- `test_generation/` - Test data generators for development
- `robot_compat.py` - Robot Framework version compatibility shims

The validation module is worth understanding - it catches common JSON structure issues early and provides specific feedback about what went wrong.

### `services/`

High-level business logic coordination. Most of this is plumbing for the conversion pipeline.

### `cli/`

Command-line interface using standard argparse patterns. The `handlers.py` file shows how we wire up CLI commands to the core conversion logic.

### `exceptions.py`

Custom exception types. When you see an error, check here first - the exception names usually tell you exactly what went wrong (e.g., `ValidationError` for bad input, `ConversionError` for processing failures).

## Test Structure

The test suite demonstrates how the codebase is intended to work:

- `unit/` - Component tests
- `integration/` - End-to-end workflows
- `performance/` - Performance benchmarks
- `generative/` - Property-based tests with Hypothesis

The most useful tests to read are in `tests/unit/core/test_engine.py` (shows conversion pipeline) and `tests/unit/medallion/bronze/` (shows format detection logic).

## Learning Path

Based on watching new engineers join the project:

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

**Making changes:** Don't break public APIs, write tests first (we use TDD), ensure Bayesian confidence scores exceed 0.8 for strong evidence, and run `make test` before committing.

**Debugging:** Enable telemetry with `IMPORTOBOT_ENABLE_TELEMETRY=true` to see cache hit rates, use `importobot.api.validation` for input issues, and check confidence scores when format detection seems wrong.

## Related Documentation

- [Getting Started](Getting-Started) - Installation and usage
- [Mathematical Foundations](Mathematical-Foundations) - Bayesian confidence algorithms
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture) - Design history

---

I wrote this guide after watching several engineers struggle with the same parts of the codebase. The medallion architecture and Bayesian confidence scoring took time to get right - the >0.8 confidence requirement came from real testing needs. If you find parts unclear, let me know so I can improve this guide.