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
- Write failing test first, make it pass, then refactor
- Maintain unit and integration coverage together (converter touches many layers)
- Use fixtures and helpers instead of copying setup code

### CI/CD Standards
- Full test suite runs on every change; red builds block merges
- Simple design first, refactor once tests protect the behavior
- No module ownership - leave code cleaner than found

### Error Handling
- Validate JSON on load with `load_and_parse_json`, fail immediately on missing fields
- Reject bad CLI input before starting long conversions
- Keep configuration validation and type hints in sync for early error detection

## Recent Improvements

- Parameter conversion now skips comment lines, so literal `{placeholders}` and control characters survive in traceability comments while executable statements still become Robot variables.
- Test generation captures both the original and normalized names, which keeps the Hypothesis fixtures honest even when a source file contains odd control characters.
- The weighted “Bayesian” shim is gone. Evidence flows through `EvidenceMetrics`, required-field gaps apply penalties, and `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py` keeps ambiguous-data ratios capped at 1.5:1.
- Robot Framework dependencies are current, so the `robot.utils` compatibility shim—and the noisy warning suppression around it—has been retired.
- Selenium integration tests still run in deterministic dry-run mode with explicit resource cleanup, so CI remains free of WebDriver start-up flakes.

### 2025 Changes
- **Zephyr Client (Oct 2025):** Redesigned with adaptive API discovery, multiple authentication strategies, and robust payload handling. Works with diverse server configurations.
- **Bayesian scoring (Oct 2025):** Replaced weighted scorer with independent model, quadratic P(E|¬H), and ratio cap tests. Strong evidence reaches 0.8 confidence without tuning.
- **Configuration parsing (Oct 2025):** Enhanced project identifier parsing for control characters and whitespace inputs. CLI arguments fall back to environment variables when invalid.
- **Test coverage (Oct 2025):** Fixed Zephyr client discovery test. All 1,941 tests pass with 0 skips.
- **September cleanup:** Removed 200+ lines of compatibility code, added `data_analysis` helper, updated `__all__` exports to match public API.
- **Interactive demo:** Added `scripts/interactive_demo.py` for customer demonstrations, shares code with CLI.
- **Pattern extraction utilities:** Added step comment generation and SSH validation used by both demo and CLI.

## API Integration Enhancements

### Zephyr Client
The `ZephyrClient` adapts to different server configurations with automatic API discovery, authentication fallbacks, and adaptive pagination. See [User Guide](wiki/User-Guide.md) for detailed usage examples.

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
6. Smoke-test the public API: `uv run python -c "import importobot; print('api ok')"`
7. Validate API boundaries: Ensure new utilities have proper `__all__` declarations
8. Check backwards compatibility: Avoid adding legacy support patterns
9. Push changes will trigger GitHub Actions workflows for automated testing and linting

## Development Guidelines

When contributing to this project:
- Follow established coding patterns and architectural decisions
- Maintain consistency with pandas-inspired API design principles
- Test all changes thoroughly using the provided test framework
