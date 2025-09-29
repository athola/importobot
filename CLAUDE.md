# Style Guide

This guide explains how to work with Importobot, a Python project built with Test-Driven Development (TDD) and Extreme Programming (XP) practices.

## Project Philosophy

**Importobot** converts test cases from various test management frameworks (Atlassian Zephyr, JIRA/Xray, TestLink, etc.) into Robot Framework format. It automates what would otherwise be a manual migration process.

### Core Mission
- **Automation**: Convert entire test suites with single commands, no manual steps
- **Bulk Processing**: Handle hundreds or thousands of test cases at once
- **Preserve Business Logic**: Keep all test structure, metadata, and verification points
- **Production-Ready Output**: Generate Robot Framework files that run immediately
- **Compatibility**: Support multiple input formats with consistent quality

We use TDD and XP to ensure the conversion process is reliable and maintainable.

### Why Automation Matters
For test framework conversion, automation means:
1. **No Manual Steps**: Skip the copy-paste and field-by-field mapping
2. **Batch Processing**: Convert hundreds or thousands of tests in one go
3. **Consistent Quality**: Every conversion follows the same patterns
4. **Immediate Executability**: Generated files run without changes
5. **Preserve Traceability**: Keep original test metadata for audits

This focus on automation shapes our architectural decisions and features.

## TDD/XP in This Project

### Test-Driven Development (TDD)
1. **Red-Green-Refactor**: Write failing tests first, then code to pass them, then refactor
2. **Test Coverage**: Every feature has unit and integration tests
3. **Test Organization**: Unit tests for components, integration tests for workflows

### Extreme Programming (XP)
1. **Continuous Integration**: Test every change automatically
2. **Refactoring**: Improve code confidently with full test coverage
3. **Simple Design**: Use the simplest approach that works
4. **Collective Code Ownership**: Consistent standards make code accessible to everyone

### Fail-Fast Principles
We catch and report errors immediately:

1. **Early Detection**: Find problems as soon as they occur
2. **Input Validation**: Check all inputs, configs, and dependencies upfront
3. **Clear Errors**: Report failures visibly and right away
4. **Prevent Cascades**: Fail fast to stop problems from spreading
5. **Save Time**: Early error detection reduces debugging costs

We implement fail-fast throughout the codebase:
- JSON parsing with validation (`load_and_parse_json` in `parser.py`)
- Command-line argument validation with immediate exit on invalid inputs
- Configuration validation at startup
- Type checking and data structure validation
- Specific exception types for different error cases

## Recent Improvements

### Artifact Management
- Updated `.gitignore` to exclude generated artifacts and test output files
- Added `clean` and `deep-clean` Makefile targets to remove temporary files
- Removed accidentally committed artifacts and cleaned up the repository

### Code Quality
- Fixed linting issues with `ruff` and other tools
- Removed unused imports and variables
- Standardized code formatting
- Improved error handling and validation patterns

### Test Reliability
- Fixed failing tests related to missing test data files
- Improved test data management and file organization
- Enhanced test suite reliability

### Makefile Updates
- Added missing targets to help menu for better discoverability
- Documented all Makefile targets in the help section

### Recent Work (September 2025)

#### Interactive Demo System
- Added `scripts/` directory with demo infrastructure for business benefits and conversion capabilities
- Built modular demo architecture with separate components for configuration, logging, validation, scenarios, and visualization
- Created `interactive_demo.py` with:
  - Business case analysis with cost/time comparisons and ROI calculations
  - Performance testing at enterprise scale with real-time visualization
  - Eight demo scenarios covering conversion, user registration, SSH operations, database/API integration, and suggestions
  - Executive dashboard with KPI cards, performance curves, competitive positioning, and risk/return analysis
  - Portfolio analysis across different business scenarios and scales

#### Test Coverage & TDD
- Expanded unit test suite for business domains, error handling, field definitions, JSON conversion, keywords, security, suggestions, and SSH operations
- Added new components: suggestions engine, validation framework, enhanced keywords system, and generative testing
- Improved test reliability with validation patterns and fail-fast principles

#### Performance & Quality
- Enterprise-scale performance benchmarks with linear scalability validation
- Interactive business case modeling with configurable scenarios and real-time cost analysis
- Enhanced security validation for SSH parameter extraction and compliance

#### Code Quality (September 2025)
- Achieved 10.00/10 lint score through systematic improvements
- Fixed all failing tests, reaching 1153 passing tests with comprehensive coverage
- Created shared utilities for pattern extraction and step comment generation
- Eliminated duplicate code across keyword generators
- Enhanced SSH test infrastructure with coverage for all 42 SSH keywords
- Standardized imports and improved dependency management
- Added security-focused parameter extraction for SSH authentication
- Improved modular keyword architecture with shared base functionality

#### Quality Improvements (September 2025)
- Maintained 10.00/10 pylint score across entire codebase
- Fixed all pycodestyle (PEP 8) and pydocstyle (PEP 257) violations
- Resolved all mypy type checking errors
- All 1153 tests passing with fixed import errors, fixture issues, and test data consistency
- Improved Robot Framework library detection
- Centralized test data management to eliminate duplication
- Updated docstrings to comply with Python PEP 257 conventions

#### Codebase Cleanup (January 2025)
- Removed 200+ lines of legacy support code across utils/defaults.py, core/converter.py, and medallion architecture
- Created shared utilities (data_analysis.py) to eliminate duplicate data processing patterns
- Added proper `__all__` declarations to core and utils modules for clean public/private separation
- Streamlined validation utilities by removing redundant wrapper functions
- Organized imports and removed unused backwards compatibility aliases
- Optimized performance by reducing function call overhead and memory footprint

## CI/CD

Importobot works in CI/CD pipelines and supports headless environments with headless Chrome.

## MCP Agent Usage Guidelines

When using MCP agents (like qwen-code) for task delegation, consider token efficiency:

### Current MCP approach likely wastes tokens because:

1. **Context flows through me**: When I use `mcp__qwen-code__ask-qwen`, file contents and analysis still get processed through my context window first
2. **Double processing**: Content gets analyzed by both me (for coordination) and qwen-code (for detailed analysis)
3. **Overhead**: Each MCP call adds metadata and formatting overhead

### The approach would save tokens if:
- Qwen-code could directly access files without me reading them first
- I could delegate entire complex tasks without coordinating results
- Analysis stayed entirely within qwen-code's context

### Traditional approach works better for:
1. I read failing files directly
2. Analyze import structure myself
3. Apply fixes directly

### MCP approach is better for:
- Complex brainstorming and ideation tasks
- Large-scale code analysis across many files
- Tasks requiring specialized domain knowledge
- When I need to focus on high-level coordination while qwen-code handles implementation details

## Public API Design Principles

Importobot follows pandas-inspired API design patterns to provide a professional interface while keeping internal implementation flexible.

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

### Design Patterns

#### 1. Pandas-Style Organization
- **Dedicated API Module**: `importobot.api` provides enterprise toolkit (like `pandas.api`)
- **Dependency Validation**: Import-time checks with informative error messages
- **Type-Safe Imports**: `TYPE_CHECKING` pattern for development support
- **Controlled Namespace**: Clean `__all__` exports throughout codebase

#### 2. Namespace Management
Based on pandas, numpy, requests, and flask patterns:

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

**Pattern Analysis**: ✅ **Acceptable Industry Practice**
- Pandas uses `del` cleanup for temporary variables
- Requests cleans up warning configurations similarly
- Pattern is explicit, readable, and functionally safe
- Only removes namespace pollution, not functionality

#### 3. Business-Focused API Surface

**Enterprise Use Cases:**
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
1. Run existing tests: `make test`
2. Check code quality: `make lint`
3. Understand existing architecture and patterns
4. Review public API impact if changing exposed functionality

### During Development
1. Write tests first (TDD)
2. Implement minimal code to pass tests
3. Refactor while keeping all tests green
4. Maintain code quality standards
5. Keep public API contracts intact when modifying exposed functionality

### After Changes
1. Run all tests: `make test`
2. Check code quality: `make lint` (runs all linting tools matching CI configuration)
3. Format code: `make format`
4. Clean artifacts: `make clean` or `make deep-clean`
5. Verify no regressions were introduced
6. Test public API: `uv run python -c "import importobot; print('✅ API works')"`
7. Validate API boundaries: Ensure new utilities have proper `__all__` declarations
8. Check backwards compatibility: Avoid adding legacy support patterns
9. Push changes will trigger GitHub Actions workflows for automated testing and linting

## Development Guidelines

When contributing to this project:
- Follow established coding patterns and architectural decisions
- Maintain consistency with pandas-inspired API design principles
- Test all changes thoroughly using the provided test framework