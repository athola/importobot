# Style Guide

This guide explains how to work with Importobot, a Python project built with Test-Driven Development (TDD) and Extreme Programming (XP) practices.

## Project Philosophy

Importobot converts Zephyr and TestRail suites to Robot Framework without manual rebuilding. One command processes entire directories, generated files maintain source readability, and output runs without cleanup. Conversions that don't meet this standard are treated as bugs.

Key principles from experience:
- Bulk conversions need predictable behavior over clever heuristics
- Validate early and fail fast on schema, security, or format detection
- Preserve names, priorities, and comments for reviewer context
- Every parser/optimizer change starts with a failing test
- Leave modules cleaner than you found them

## Development Practices

### Test-Driven Development
Write failing test first, make it pass, then refactor. The converter touches many layers (parsing, validation, rendering), so maintain both unit and integration coverage. Use the existing fixtures in `tests/fixtures/` instead of copying setup code across test files.

### CI/CD Standards
The full test suite (1,946 tests) runs on every change. Red builds block merges. Start with simple design, then refactor once tests protect the behavior. No module ownership—leave the code cleaner than you found it.

### Error Handling
Validate JSON immediately with `load_and_parse_json` and fail fast on missing fields. Reject bad CLI input before starting long conversions to avoid wasting time. Keep configuration validation and type hints in sync—this catches many issues during development instead of runtime.

## Recent Improvements

We fixed several specific issues that were causing problems in production:

- **Parameter conversion**: Comment lines with `${PLACEHOLDER}` syntax now survive as-is in traceability comments, while executable statements still get converted to Robot variables. This fixed a bug where important context was being lost.

- **Test generation**: We now capture both original and normalized names when processing source files with control characters. This prevents Hypothesis from generating failing fixtures due to unexpected character sequences.

- **Bayesian scoring**: Replaced the weighted evidence heuristic with proper Bayesian inference. Evidence now flows through `EvidenceMetrics`, missing fields get penalties, and we cap ambiguous input ratios at 1.5:1. Tests verify these constraints in `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`.

- **Robot Framework compatibility**: Removed the `robot.utils` compatibility shim since Robot Framework updated its dependencies. This eliminated the noisy deprecation warnings we were seeing in CI.

- **Selenium tests**: Fixed WebDriver start-up flakes by running Selenium integration tests in deterministic dry-run mode with explicit resource cleanup.

### 2025 Changes

**October 2025: Application Context Pattern**
We had race conditions in our tests due to global state. Replaced global variables with thread-local context, which fixed the concurrent instance support issues. Added `importobot.caching` module with unified LRU cache implementation.

**October 2025: Template Learning**
Instead of hardcoding Robot Framework patterns, we now learn them from existing files using `--robot-template`. The system extracts patterns from your team's Robot files and applies them consistently. This replaced our old template system that required manual pattern definitions.

**October 2025: Schema Parser**
Added `schema_parser.py` to read customer documentation (SOPs, READMEs) with `--input-schema`. This improved parsing accuracy from ~85% to ~95% on custom exports where customers use non-standard field names.

**October 2025: API Integration**
Unified platform fetching under `--fetch-format` parameter. The Zephyr client now does automatic API discovery and adapts to different server configurations. We tested this against 4 different Zephyr instances and they all work with the same client code.

**October 2025: Documentation**
Wrote proper Migration Guide for 0.1.2→0.1.3 since there were no breaking changes, documented the breaking changes that did exist in previous versions, and created a step-by-step Blueprint Tutorial.

**October 2025: Configuration**
Fixed project identifier parsing that was failing on control characters and whitespace. CLI arguments that don't parse to valid identifiers now use environment variables as default values instead of crashing.

**September 2025: Code cleanup**
Removed 200+ lines of compatibility code that were no longer needed, added `data_analysis` helper for performance profiling, and updated `__all__` exports to match our actual public API surface.

**September 2025: Demo script**
Added `scripts/interactive_demo.py` for customer demonstrations. It shares code with the CLI so we don't duplicate the conversion logic.

**Test status**: All 2,105 tests pass with 0 skips.
**Code quality**: Removed pylint from the project (now using ruff/mypy only) and improved test isolation.

## API Integration Enhancements

### Zephyr Client
The `ZephyrClient` adapts to different server configurations with automatic API discovery, authentication defaults, and adaptive pagination. See [User Guide](wiki/User-Guide.md) for detailed usage examples.

## CI/CD

Importobot works in CI/CD pipelines and supports headless environments with headless Chrome.

## MCP agent usage

Use MCP agents (like qwen-code) when their context window improves efficiency and reduces token cost. Every call flows through the main session, so simple file edits waste tokens.

Use MCP agents for:
- Broad explorations and codebase surveys
- Analyses requiring dozens of manual file opens
- Brainstorming with parallel thinking

Use built-in tools for:
- Easily understood failures
- Small file edits
- Determinable outputs

## Public API Design

Importobot uses pandas-style API patterns for a professional interface with flexible internal implementation.

### API Structure
```python
# Primary interface
import importobot
converter = importobot.JsonToRobotConverter()  # Core conversion

# Enterprise features
from importobot.api import validation, converters, suggestions

# Configuration and errors
importobot.config
importobot.exceptions
```

### Design Patterns

**1. API Organization**
- `importobot.api` provides enterprise toolkit (like `pandas.api`)
- Import-time validation with clear error messages
- `TYPE_CHECKING` pattern for development support
- Clean `__all__` exports throughout codebase

**2. Namespace Management**
Based on pandas/requests patterns:
```python
from importobot import config as _config
from importobot import exceptions as _exceptions
from importobot import api as _api

config = _config
exceptions = _exceptions
api = _api

del _config, _exceptions, _api  # Clean up temporary imports
```

**3. Use Cases**
- Bulk conversion: `JsonToRobotConverter` for thousands of test cases
- API integration: `importobot.api.validation` and platform fetching
- CI/CD: Pipeline validation with real-time data fetching
- QA suggestions: `importobot.api.suggestions` for ambiguous test cases

**4. Security**
- Core implementation modules are private (empty `__all__` lists)
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
2. Check code quality: `make lint` (runs ruff and mypy)
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
2. Check code quality: `make lint` (runs ruff and mypy for linting and type checking)
3. Format code: `make format`
4. Clean artifacts: `make clean` or `make deep-clean`
5. Verify no regressions were introduced
6. Smoke-test the public API: `uv run python -c "import importobot; print('api ok')"`
7. Validate API boundaries: Ensure new utilities have proper `__all__` declarations
8. Check backwards compatibility: Avoid adding legacy support patterns
9. Push changes will trigger GitHub Actions workflows for automated testing and linting

## Development Guidelines

When contributing to this project:
- Follow established coding patterns and architectural decisions
- Maintain consistency with pandas-inspired API design principles
- Test all changes thoroughly using the provided test framework
