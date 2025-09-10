# Project Interpretation Guide for Claude

This document provides guidance for Claude when analyzing or working with this Python project that follows Test-Driven Development (TDD) and Extreme Programming (XP) principles.

## Project Overview

This is a Python project that converts various test framework formats into Robot Framework format. The project strictly follows TDD and XP practices.

## TDD/XP Principles in This Project

### Test-Driven Development (TDD)
1. **Red-Green-Refactor Cycle**: All functionality is developed by first writing failing tests, then implementing code to pass those tests, and finally refactoring while keeping tests green.
2. **Comprehensive Test Coverage**: Every piece of functionality has corresponding unit and integration tests.
3. **Test Organization**: Tests are organized into unit tests (for individual components) and integration tests (for complete workflows).

### Extreme Programming (XP)
1. **Continuous Integration**: Automated testing ensures code quality with every change.
2. **Refactoring**: Code can be confidently refactored due to comprehensive test coverage.
3. **Simple Design**: Implementation follows the simplest approach that works, avoiding over-engineering.
4. **Collective Code Ownership**: Consistent coding standards and practices make the codebase accessible to all team members.

## Project Structure Interpretation

### Source Code Organization
- `src/zephyr_to_robot/`: Main source code following the Python package structure
  - `core/`: Contains core business logic separated by concern
    - `parser.py`: Handles parsing of Zephyr JSON data
    - `converter.py`: Manages file conversion operations, including loading and saving data
  - `__main__.py`: Entry point for the command-line interface

### Test Organization
- `tests/`: Comprehensive test suite following TDD principles
  - `unit/`: Unit tests for individual functions and classes
    - Focused on testing isolated components
    - Fast execution with minimal dependencies
    - Heavy use of mocking for external dependencies
  - `integration/`: Integration tests for complete workflows
    - Test the interaction between multiple components
    - Perform actual file I/O operations
    - Verify end-to-end functionality

### Development Tooling
- `Makefile`: Centralized commands for common development tasks
- `pyproject.toml`: Project configuration including dependencies and tool settings
- `ruff`: Code formatting and linting tool
- `pylint`: Additional code quality checks
- `pytest`: Testing framework with comprehensive test discovery

## Development Workflow for Claude

When working with this project, Claude should follow these guidelines:

### 1. Understand the TDD Process
- Before implementing any new feature or fixing any bug, first look for existing tests
- If tests don't exist for the functionality being modified, they should be created first
- Follow the pattern: Write test → See it fail → Implement minimal code → See it pass → Refactor

### 2. Code Organization Principles
- Maintain separation of concerns in the `core/` module
- Keep functions small and focused on a single responsibility
- Follow existing patterns for error handling and return values
- Preserve the modular structure that enables testing

### 3. Testing Standards
- All new functionality must have corresponding tests
- Unit tests should be fast and not depend on file I/O or external services
- Integration tests can perform actual file operations but should clean up after themselves
- Test names should clearly describe what is being tested
- Use pytest fixtures for setup and teardown when appropriate

### 4. Code Quality
- Follow the existing code style as enforced by ruff
- Ensure all new code passes linting checks
- Maintain consistent docstring style
- Use type hints where appropriate
- Keep dependencies minimal and well-justified

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
2. Check code quality: `make lint`
3. Format code: `make format`
4. Verify no regressions were introduced

## Project-Specific Conventions

1. **Error Handling**: Core library functions (e.g., in `converter.py`, `parser.py`) should raise specific exceptions on failure. The main executable (`__main__.py`) is responsible for catching these exceptions and exiting with an appropriate status code.
2. **CLI Argument Testing**: When testing command-line argument handling, do not mock `sys.exit`. Instead, use `pytest.raises(SystemExit)` and assert the `e.value.code` of the resulting exception. This correctly tests the behavior of `argparse` without causing unexpected side effects in the test's execution flow.
3. **File Operations**: Use the dedicated functions in `converter.py` for file I/O operations.
4. **Command-Line Interface**: All CLI functionality should be in `__main__.py` with core logic in separate modules.
5. **Test Cleanup**: Tests should not leave behind artifacts; use pytest fixtures or try/finally blocks for cleanup.

## Dependencies and Tooling

1. **uv**: Used for package management and virtual environment management
2. **pytest**: Testing framework with fixture support
3. **ruff**: Primary linting and formatting tool
4. **pylint**: Additional code quality checks
5. **Robot Framework**: Target output format for converted tests

This project is designed to be maintainable, testable, and extensible following industry best practices for TDD and XP. and XP.