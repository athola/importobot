# Release Notes

## v0.1.3 (October 2025)

This release introduces a new Application Context pattern to improve test isolation and thread safety, a unified caching system, and several new features and bug fixes.

### Highlights

-   **Application Context Pattern:** Replaced global variables with a thread-local context to eliminate global state and improve test isolation.
-   **Unified Caching System:** A new `importobot.caching` module provides a configurable LRU cache.
-   **Template-Driven Conversions:** The conversion engine can now learn patterns from existing Robot Framework files and apply them to new conversions.
-   **Schema-Aware Parsing:** The tool can now extract field definitions from your documentation to improve parsing accuracy.
-   **Code Quality:** Removed pylint and streamlined the linting workflow.

### Technical Changes

-   [ADR-0004: Adopt Application Context Pattern for Dependency Management](architecture/ADR-0004-application-context-pattern.md)
-   [Application Context Implementation Guide](architecture/Application-Context-Implementation.md)

-- -

## v0.1.2 (October 2025)

This release introduces a new in-memory cache for the Bronze layer, resulting in a 50-80% performance improvement for repeated queries. It also includes several performance optimizations and code organization improvements.

### Highlights

-   **Bronze Layer In-Memory Cache:** A new in-memory cache for recently ingested records provides a significant performance boost.
-   **Performance Optimization:** The validation pipeline has been tuned, and the linting workflow now runs through the standard `make lint` (ruff + mypy) sequence after removing pylint.
-   **Code Organization:** The benchmark scripts and test utilities have been reorganized for better clarity and maintainability.

---

## v0.1.1 (September 2025)

This release introduces the Medallion architecture (Bronze, Silver, and Gold layers) to provide distinct checkpoints for data processing. It also expands format detection with a Bayesian confidence scorer and adds support for Xray, TestLink, and TestRail.

## v0.1.0 (September 2025)

Initial release of Importobot, with support for converting Zephyr JSON test cases to Robot Framework format. This release includes batch processing, intent-based parsing, and automatic library detection.
