# Project Interpretation Guide for Claude

This document provides guidance for Claude when analyzing or working with this Python project that follows Test-Driven Development (TDD) and Extreme Programming (XP) principles.

## Project Overview

**Importobot** is a Python automation tool designed to **fully automate the conversion process** from various test management frameworks (Atlassian Zephyr, JIRA/Xray, TestLink, etc.) into Robot Framework format. The project eliminates manual migration work by providing 100% automated conversion with zero human intervention required.

### Core Mission
- **Complete Automation**: No manual conversion steps - entire test suites convert with single commands
- **Preserve Business Logic**: Maintain all test structure, metadata, and verification points during conversion
- **Production-Ready Output**: Generate immediately executable Robot Framework files
- **Universal Compatibility**: Support multiple input formats with consistent conversion quality

The project strictly follows TDD and XP practices to ensure conversion reliability and maintainability.

### Why Full Automation Matters
In the context of test framework conversion, "full automation" means:
1. **Zero Manual Steps**: No copy-paste, no field-by-field mapping, no manual verification
2. **Batch Processing**: Handle hundreds or thousands of test cases in a single operation
3. **Consistent Quality**: Every conversion follows identical patterns and standards
4. **Immediate Executability**: Generated Robot Framework files run without modification
5. **Preserve Traceability**: Original test metadata and structure maintained for audit purposes

This automation focus drives every architectural decision and feature implementation.

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
- `src/importobot/`: Main source code following the Python package structure
  - `core/`: Contains core business logic separated by concern
    - `parser.py`: Handles parsing of input format data (currently Zephyr JSON)
    - `converter.py`: Manages file conversion operations, including loading and saving data
  - `__main__.py`: Entry point for the command-line interface

The modular structure is designed to easily accommodate new input formats while maintaining consistent conversion patterns.

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
- Follow the existing code style as enforced by ruff, black, pycodestyle, pydocstyle, and pylint
- Ensure all new code passes automated quality gates (enforced by GitHub Actions)
- All linting tools are configured in pyproject.toml and run automatically in CI
- Maintain consistent docstring style (enforced by pydocstyle)
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
2. Check code quality: `make lint` (runs all linting tools matching CI configuration)
3. Format code: `make format`
4. Verify no regressions were introduced
5. Push changes will trigger GitHub Actions workflows for automated testing and linting

### Commit Signing
This project uses GPG signing for commit verification:
- All commits should be signed with your GPG key for security and authenticity
- GPG signing is configured locally for this repository
- See the "GPG Commit Signing" section in README.md for setup instructions

## Project-Specific Conventions

1. **Error Handling**: Core library functions (e.g., in `converter.py`, `parser.py`) should raise specific exceptions on failure. The main executable (`__main__.py`) is responsible for catching these exceptions and exiting with an appropriate status code. The `parser.py` module includes:
   - `load_and_parse_json` for robust handling of JSON string inputs, raising `ValueError` for malformed JSON and `TypeError` if the parsed content is not a dictionary
   - Comprehensive input validation with proper handling of None values and invalid data structures
   - Enhanced Chrome browser setup with headless configuration for cross-platform compatibility
   - Intelligent SSHLibrary import logic based on test content analysis
2. **CLI Argument Testing**: When testing command-line argument handling, do not mock `sys.exit`. Instead, use `pytest.raises(SystemExit)` and assert the `e.value.code` of the resulting exception. This correctly tests the behavior of `argparse` without causing unexpected side effects in the test's execution flow.
3. **File Operations**: Use the dedicated functions in `converter.py` for file I/O operations.
4. **Command-Line Interface**: All CLI functionality should be in `__main__.py` with core logic in separate modules.
5. **Test Cleanup**: Tests should not leave behind artifacts; use pytest fixtures or try/finally blocks for cleanup.

### Generating Functional Robot Framework Tests

To ensure the generated `.robot` files are executable and verifiable, the conversion process now includes:

1.  **Concrete Keyword Mapping**: `No Operation` placeholders are replaced with specific `SeleniumLibrary` keywords (e.g., `Go To`, `Input Text`, `Click Button`).
2.  **Generic Locators**: Since Zephyr JSON does not provide UI element locators, generic `id` locators (e.g., `id=username_field`, `id=login_button`) are hardcoded into the generated Robot Framework steps. These are intended to be used with a controlled test environment (like a mock web server) where elements with these IDs are present.
3.  **Basic Verification**: `expectedResult` fields from the Zephyr JSON are translated into `Page Should Contain` or `Textfield Value Should Be` keywords for basic assertion.
4.  **Mock Server Integration**: Functional tests of the generated `.robot` files are performed against a mock web server (`tests/mock_server.py`) that serves a simple HTML page with the expected UI elements. This allows for end-to-end verification of the generated Robot Framework logic without relying on a live application.
5.  **Handling Unmapped Steps**: Steps that cannot be mapped to a concrete Robot Framework keyword will generate a `Log` warning in the `.robot` file, indicating that manual implementation is required.

## Dependencies and Tooling

### Package Management
1. **uv**: Fast, reliable package management and virtual environment management

### Testing Framework
2. **pytest**: Testing framework with fixture support and comprehensive test discovery
3. **coverage**: Code coverage reporting integrated with Codecov
4. **PyYAML**: YAML parsing for workflow validation testing

### Code Quality Tools (CI/CD Enforced)
1. **ruff**: Primary linting and formatting tool
2. **black**: Uncompromising code formatter
3. **pycodestyle**: PEP 8 style guide enforcement (max-line-length: 88 characters)
4. **pydocstyle**: Docstring style checking
5. **pylint**: Comprehensive code analysis

### Target Framework
6. **Robot Framework**: Target output format for converted tests

### CI/CD Infrastructure
- **GitHub Actions**: Comprehensive automated testing across Python 3.10, 3.11, 3.12 with enhanced workflows:
  - **Test Workflow**: JUnit XML test reports uploaded as artifacts, fail-fast: false strategy, enhanced caching with Python version isolation
  - **Lint Workflow**: Optimized permissions configuration, proper secret validation
  - **Claude Code Review**: AI-powered code review with conditional CLAUDE_CODE_OAUTH_TOKEN validation
  - **Claude Integration**: Advanced development assistance with CI result analysis
- **Dependabot**: Weekly automated dependency updates for GitHub Actions and Python packages
- **Workflow Validation**: Comprehensive testing of all GitHub Actions workflows for YAML syntax, structure, and best practices
- **Coverage Reporting**: Integrated with Codecov (conditional on CODECOV_TOKEN availability)

### Project Structure
- **examples/json/**: Contains sample input files for testing and documentation
- **.github/workflows/**: Enhanced GitHub Actions configuration with comprehensive CI/CD pipelines
- **.github/dependabot.yml**: Automated dependency management configuration
- **tests/unit/test_workflows.py**: Comprehensive workflow validation testing
- **setup.cfg**: Additional project configuration

This project is designed to be maintainable, testable, and extensible following industry best practices for TDD and XP.