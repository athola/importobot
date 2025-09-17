# Style Guide

This document provides guidance for analyzing or working with this Python project that follows Test-Driven Development (TDD) and Extreme Programming (XP) principles.

## Project Philosophy

**Importobot** is a Python automation tool designed to automate the conversion process from various test management frameworks (Atlassian Zephyr, JIRA/Xray, TestLink, etc.) into Robot Framework format. The project eliminates manual migration work by providing automated conversion.

### Core Mission
- **Automation**: No manual conversion steps - entire test suites convert with single commands.
- **Bulk Processing**: Handle hundreds or thousands of test cases in a single operation.
- **Preserve Business Logic**: Maintain all test structure, metadata, and verification points during conversion.
- **Production-Ready Output**: Generate immediately executable Robot Framework files.
- **Compatibility**: Support multiple input formats with consistent conversion quality.

The project follows TDD and XP practices to ensure conversion reliability and maintainability.

### Why Automation Matters
In the context of test framework conversion, automation means:
1. **No Manual Steps**: No copy-paste, no field-by-field mapping, no manual verification.
2. **Batch Processing**: Handle hundreds or thousands of test cases in a single operation.
3. **Consistent Quality**: Every conversion follows identical patterns and standards.
4. **Immediate Executability**: Generated Robot Framework files run without modification.
5. **Preserve Traceability**: Original test metadata and structure maintained for audit purposes.

This automation focus drives every architectural decision and feature implementation.

## TDD/XP Principles in This Project

### Test-Driven Development (TDD)
1. **Red-Green-Refactor Cycle**: All functionality is developed by first writing failing tests, then implementing code to pass those tests, and finally refactoring while keeping tests green.
2. **Test Coverage**: Every piece of functionality has corresponding unit and integration tests.
3. **Test Organization**: Tests are organized into unit tests (for individual components) and integration tests (for complete workflows).

### Extreme Programming (XP)
1. **Continuous Integration**: Automated testing ensures code quality with every change.
2. **Refactoring**: Code can be confidently refactored due to full test coverage.
3. **Simple Design**: Implementation follows the simplest approach that works, avoiding over-engineering.
4. **Collective Code Ownership**: Consistent coding standards and practices make the codebase accessible to all team members.

### Fail-Fast Principles
This project adheres to fail-fast design principles:

1. **Immediate Error Detection**: Problems are detected and reported as soon as possible.
2. **Early Validation**: All inputs, configurations, and dependencies are validated immediately.
3. **Explicit Error Reporting**: When failures occur, they are reported immediately and visibly.
4. **Input Validation**: All external inputs undergo validation before processing begins.
5. **System Stability Through Early Failure**: By failing immediately when problems are detected, the system prevents cascading failures and maintains overall stability.
6. **Development Efficiency**: Early error detection reduces debugging time and development costs.

The fail-fast approach is implemented throughout the codebase in:
- JSON parsing with validation (`load_and_parse_json` in `parser.py`)
- Command-line argument validation with immediate exit on invalid inputs
- Configuration validation at application startup
- Type checking and data structure validation
- Error handling with specific exception types

## Recent Improvements

### Artifact Management
- Enhanced `.gitignore` to properly exclude generated artifacts and test output files
- Added comprehensive `clean` and `deep-clean` Makefile targets to remove temporary files
- Removed accidentally committed artifacts and ensured repository cleanliness

### Code Quality Standards
- Fixed linting issues throughout the codebase using `ruff` and other tools
- Removed unused imports and variables to reduce code clutter
- Standardized code formatting with automated tools
- Improved error handling and validation patterns

### Test Reliability
- Fixed failing tests related to missing test data files
- Improved test data management and file organization
- Enhanced test suite reliability and consistency

### Makefile Improvements
- Added missing targets to help menu for better discoverability
- All Makefile targets now documented in the help section

## CI/CD

Importobot is designed to be run in a CI/CD pipeline. It includes support for running in a headless environment by using a headless Chrome browser.

## When Modifying Code

### Before Making Changes
1. Run existing tests to ensure they pass: `make test`
2. Check code quality: `make lint`
3. Understand the existing architecture and patterns

### During Development
1. Write tests first (TDD)
2. Implement minimal code to pass tests
3. Refactor while keeping all tests green
4. Ensure code quality standards are maintained

### After Changes
1. Run all tests: `make test`
2. Check code quality: `make lint` (runs all linting tools matching CI configuration)
3. Format code: `make format`
4. Clean artifacts: `make clean` or `make deep-clean`
5. Verify no regressions were introduced
6. Push changes will trigger GitHub Actions workflows for automated testing and linting