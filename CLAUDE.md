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

### Latest Developments (September 2025)

#### Interactive Demo System & Business Case Visualization
- **Added `scripts/` directory** with comprehensive interactive demo infrastructure for showcasing business benefits and conversion capabilities
- **Created modular demo architecture** with separate components for configuration, logging, validation, scenarios, and visualization
- **Implemented `interactive_demo.py`** - A sophisticated demo script featuring:
  - Business case analysis with cost/time comparisons and ROI calculations
  - Performance testing at enterprise scale with real-time visualization
  - Eight distinct demo scenarios covering basic conversion, user registration, SSH operations, database/API integration, and intelligent suggestions
  - Executive dashboard with KPI cards, performance curves, competitive positioning, and risk/return analysis
  - Portfolio analysis across different business scenarios and scales

#### Enhanced Test Coverage & TDD Implementation
- **Expanded unit test suite** covering business domains, error handling, field definitions, JSON conversion, keywords, security, suggestions, and SSH operations
- **New architectural components**: Suggestions engine, validation framework, enhanced keywords system, and generative testing capabilities
- **Improved test reliability** with comprehensive validation patterns and fail-fast principles

#### Performance & Quality Improvements
- **Enterprise-scale performance benchmarks** with linear scalability validation
- **Interactive business case modeling** with configurable scenarios and real-time cost analysis
- **Enhanced security validation** including SSH parameter extraction and security compliance

#### Code Quality & Architecture Enhancements (September 2025)
- **Achieved 10.00/10 lint score** through systematic code quality improvements and comprehensive linting standards compliance
- **Complete test suite reliability**: Fixed all failing tests, achieving 1153 passing tests with comprehensive coverage
- **Shared utilities implementation**: Created reusable components for pattern extraction (`utils/pattern_extraction.py`) and step comment generation (`utils/step_comments.py`)
- **Duplicate code elimination**: Replaced duplicate patterns across keyword generators with shared utilities, reducing maintenance overhead
- **Enhanced SSH test infrastructure**: Comprehensive test coverage for all 42 SSH keywords with generative testing capabilities
- **Improved import organization**: Standardized imports across modules with proper dependency management
- **Security-focused parameter extraction**: Robust handling of sensitive data in SSH authentication and file operations
- **Modular keyword architecture**: Enhanced separation of concerns in keyword generation with shared base functionality

#### Latest Quality Improvements (September 2025)
- **Perfect Code Quality Standards**: Achieved and maintained 10.00/10.00 pylint score across entire codebase
- **Complete Style Compliance**: Fixed all pycodestyle (PEP 8) violations and pydocstyle (PEP 257) docstring issues
- **Enhanced Type Safety**: Resolved all mypy type checking errors for improved code reliability
- **Test Suite Robustness**: All 1153 tests passing with resolved import errors, fixture issues, and test data consistency
- **Library Detection Refinement**: Improved Robot Framework library detection while maintaining proper BuiltIn library handling
- **Shared Test Infrastructure**: Eliminated code duplication through centralized test data management
- **Documentation Standards**: All docstrings now comply with Python PEP 257 conventions

## CI/CD

Importobot is designed to be run in a CI/CD pipeline. It includes support for running in a headless environment by using a headless Chrome browser.

## MCP Agent Usage Guidelines

When using MCP agents (like qwen-code) for task delegation, consider token efficiency:

### Current MCP approach is likely NOT saving tokens because:

1. **Context still flows through me**: When I use `mcp__qwen-code__ask-qwen`, the file contents and analysis still get processed through my context window first
2. **Double processing**: The content gets analyzed by both me (for coordination) and qwen-code (for detailed analysis)
3. **Overhead**: Each MCP call adds metadata and formatting overhead

### The approach would save tokens if:
- Qwen-code could directly access files without me reading them first
- I could delegate entire complex tasks without needing to coordinate the results
- The analysis stayed entirely within qwen-code's context

### For specific tasks, the traditional approach is more efficient:
1. I read the failing files directly
2. Analyze the import structure myself
3. Apply fixes directly

### The MCP approach is more valuable for:
- Complex brainstorming/ideation tasks
- Large-scale code analysis across many files
- Tasks requiring specialized domain knowledge
- When I need to stay focused on high-level coordination while qwen-code handles deep implementation details

## Public API Design Principles

Importobot follows pandas-inspired API design patterns to provide a professional, enterprise-ready interface while maintaining internal implementation flexibility.

### API Architecture Overview

**Public Interface Structure:**
```python
# Primary business interface
import importobot
converter = importobot.JsonToRobotConverter()  # Core bulk conversion

# Enterprise toolkit access
from importobot.api import validation, converters, suggestions

# Configuration and error handling
importobot.config  # Enterprise configuration
importobot.exceptions  # Comprehensive error handling
```

### Design Patterns Applied

#### 1. **Pandas-Style Organization**
- **Dedicated API Module**: `importobot.api` provides enterprise toolkit (like `pandas.api`)
- **Dependency Validation**: Import-time checks with informative error messages
- **Type-Safe Imports**: `TYPE_CHECKING` pattern for development support
- **Controlled Namespace**: Clean `__all__` exports throughout the codebase

#### 2. **Namespace Management Techniques**
Based on analysis of pandas, numpy, requests, and flask:

```python
# Industry-validated pattern used in importobot
from importobot import config as _config
from importobot import exceptions as _exceptions
from importobot import api as _api

# Expose through clean interface
config = _config
exceptions = _exceptions
api = _api

# Clean up namespace (pandas uses similar del cleanup)
del _config, _exceptions, _api
```

**Pattern Analysis Verdict**: ✅ **Acceptable Industry Practice**
- Pandas uses `del` cleanup for temporary variables
- Requests cleans up warning configurations similarly
- Pattern is explicit, readable, and functionally safe
- Only removes namespace pollution, not functionality

#### 3. **Business-Focused API Surface**

**Enterprise Use Cases Addressed:**
1. **Bulk Conversion Pipeline**: `JsonToRobotConverter` for hundreds/thousands of test cases
2. **CI/CD Integration**: `importobot.api.validation` for automated pipeline validation
3. **QA Suggestion Engine**: `importobot.api.suggestions` for ambiguous test case handling

**Security & Maintainability:**
- Core implementation modules marked as private (empty `__all__` lists)
- Public API isolated from internal refactoring
- Controlled access prevents misuse of internal utilities

### API Evolution Guidelines

#### **What Should Remain Public**
- `JsonToRobotConverter` - Primary business functionality
- `config` - Enterprise configuration needs
- `exceptions` - Programmatic error handling
- `api.*` modules - Advanced enterprise features

#### **What Should Stay Private**
- Core engine internals (`core/engine.py`, `core/parsers.py`)
- CLI implementation details (`cli/handlers.py`)
- Internal utilities (`utils/file_operations.py`)

#### **Version Stability Promise**
Following pandas model:
- Public API contracts remain stable across versions
- Internal implementation can be refactored freely
- Deprecation warnings for any breaking changes
- Migration guides for major version updates

## When Modifying Code

### Before Making Changes
1. Run existing tests to ensure they pass: `make test`
2. Check code quality: `make lint`
3. Understand the existing architecture and patterns
4. Review public API impact if changing exposed functionality

### During Development
1. Write tests first (TDD)
2. Implement minimal code to pass tests
3. Refactor while keeping all tests green
4. Ensure code quality standards are maintained
5. Maintain public API contracts when modifying exposed functionality

### After Changes
1. Run all tests: `make test`
2. Check code quality: `make lint` (runs all linting tools matching CI configuration)
3. Format code: `make format`
4. Clean artifacts: `make clean` or `make deep-clean`
5. Verify no regressions were introduced
6. Test public API remains functional: `uv run python -c "import importobot; print('✅ API works')"`
7. Push changes will trigger GitHub Actions workflows for automated testing and linting

## Development Guidelines

When contributing to this project, please ensure you:
- Follow the established coding patterns and architectural decisions documented above
- Maintain consistency with the pandas-inspired API design principles
- Test all changes thoroughly using the provided test framework