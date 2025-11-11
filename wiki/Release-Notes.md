# Release Notes

## v0.1.4 (November 2025)

This release focuses on test suite improvements, client module architecture refactoring, and enhanced type safety.

### Highlights

- **Test Constants**: Introduced 55 named constants across 9 categories to eliminate magic numbers in tests.

- **Test Patterns**: Adopted pytest best practices, including `tmp_path` fixtures, type annotations, and Arrange-Act-Assert documentation.

- **Client Module Refactoring**: Restructured `importobot.integrations.clients` into separate modules while maintaining backward compatibility.

- **Type Safety**: Expanded Mypy type checking to cover the entire test suite.

### Technical Changes

- **Client Module Refactoring**: Split client integration into focused modules (base.py, jira_xray.py, testlink.py, testrail.py, zephyr.py) and implemented lazy loading for a 3x import speed improvement.

- **Legacy Code Cleanup**: Removed unnecessary backwards compatibility shims (Python < 3.8 support, deprecated APIs).

- **Documentation Refinement**: Replaced subjective marketing language with factual, technical descriptions.

- **Test Infrastructure**: Fixed 24 syntax errors and standardized import patterns across all test files.

## v0.1.3 (October 2025)

This release introduces an Application Context pattern for improved test isolation and thread safety, a unified caching system, and various new features and bug fixes.

### Highlights

-   **Application Context Pattern**: Global variables were replaced with a thread-local context, eliminating global state and improving test isolation.

-   **Unified Caching System**: A new `importobot.caching` module provides a configurable LRU cache.

-   **Template-Driven Conversions**: The conversion engine can now extract patterns from existing Robot Framework files and apply them to new conversions.

-   **Schema-Aware Parsing**: The tool can extract field definitions from documentation to improve parsing accuracy.

-   **Code Quality**: Pylint was removed, and the linting workflow was streamlined.

### Technical Changes

-   [ADR-0004: Adopt Application Context Pattern for Dependency Management](architecture/ADR-0004-application-context-pattern.md)

-   [Application Context Implementation Guide](architecture/Application-Context-Implementation.md)

## v0.1.2 (October 2025)

This release introduces a new in-memory cache for the Bronze layer, providing a 50-80% performance improvement for repeated queries. It also includes several performance optimizations and code organization improvements.

### Highlights

-   **Bronze Layer In-Memory Cache**: A new in-memory cache for recently ingested records significantly boosts performance.

-   **Performance Optimization**: The validation pipeline was tuned, and the linting workflow now uses `make lint` (ruff + mypy) after Pylint removal.

-   **Code Organization**: Benchmark scripts and test utilities were reorganized for clarity and maintainability.

---

## v0.1.1 (September 2025)

This release introduces the Medallion architecture (Bronze, Silver, and Gold layers) to provide distinct checkpoints for data processing. It also expands format detection with a Bayesian confidence scorer and adds support for Xray, TestLink, and TestRail.

## v0.1.0 (September 2025)

Initial release of Importobot, supporting conversion of Zephyr JSON test cases to Robot Framework format. This release includes batch processing, intent-based parsing, and automatic library detection.
