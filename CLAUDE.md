# Style Guide

This guide explains how to work with Importobot, a Python project built with Test-Driven Development (TDD) and Extreme Programming (XP) practices.

## Project Philosophy

Importobot exists so we do not rebuild Zephyr or TestRail suites by hand. One command should process an entire directory, the generated files should still read like the source material, and the output must run under Robot Framework without a clean-up pass. When a conversion misses that bar we treat it as a bug, not an acceptable trade-off.

The workflow leans on a few rules of thumb learned the hard way:
- Conversions usually arrive in bulk, so predictable behaviour beats clever heuristics.
- Earlier validation saves time. Fail fast on schema, security, or format detection rather than shipping half-converted suites.
- Reviewers need context. Preserve names, priorities, and comments instead of hiding them behind abstractions.

Disciplined TDD means every parser or optimizer tweak starts with a failing test in the suite, and we expect contributors to leave touched modules tidier for the next engineer who picks up the trail.

## TDD/XP in This Project

### Test-Driven Development (TDD)
- Start with the failing test, make it pass, then refactor to work towards a green state.
- Keep both unit and integration coverage in step; the converter touches many layers at once.
- Prefer fixtures and helpers to copy/pasting setup blocks.

### Extreme Programming (XP)
- Run the full test suite in CI on every change; red builds block merges.
- Reach for the simplest design first and refactor aggressively once tests protect the behaviour.
- Treat the codebase as shared turf—nobody “owns” a module, so leave it tidier than you found it.

### Fail-fast principles in practice
- Validate JSON on load (see `load_and_parse_json`) and fail immediately when fields are missing.
- Reject bad CLI input before spinning up long-running conversions.
- Keep configuration validation and type hints in sync so errors surface during startup, not mid-run.

## Recent Improvements

- Parameter conversion now skips comment lines, so literal `{placeholders}` and control characters survive in traceability comments while executable statements still become Robot variables.
- Test generation captures both the original and normalized names, which keeps the Hypothesis fixtures honest even when a source file contains odd control characters.
- The weighted “Bayesian” shim is gone. Evidence flows through `EvidenceMetrics`, required-field gaps apply penalties, and `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py` keeps ambiguous-data ratios capped at 1.5:1.
- Robot Framework dependencies are current, so the `robot.utils` compatibility shim—and the noisy warning suppression around it—has been retired.
- Selenium integration tests still run in deterministic dry-run mode with explicit resource cleanup, so CI remains free of WebDriver start-up flakes.

### 2025 highlights worth remembering
- **ASV benchmarking integration (Oct 2025):** ASV (Airspeed Velocity) now tracks performance across releases with automated chart generation. CI workflow publishes benchmark visualizations to wiki on tagged releases. Three benchmark suites cover conversion performance, memory usage, and bulk operations with ~55ms average detection time.
- **Tag-based release workflow (Oct 2025):** PyPI publishing now triggers only on version tags (v*.*.*), preventing accidental releases from main branch pushes. Ensures controlled releases with proper versioning.
- **Development branch workflow (Oct 2025):** Established development branch as integration target for all MRs. Main branch receives only tested releases from development. Documented in wiki/Contributing.md with clear feature/release/hotfix workflows.
- **Bayesian revamp (Oct 2025):** replaced the weighted scorer with an independent model, quadratic P(E|¬H), and regression tests for ratio caps. Strong evidence now clears the 0.8 confidence bar without hand tuning.
- **Wiki consolidation (Oct 2025):** removed verbose Bayesian-specific documentation (Bayesian-Redesign.md, Bayesian-Scorer-Mathematical-Review.md) in favor of concise technical content in Mathematical-Foundations.md.
- September's cleanup retired ~200 lines of compatibility hacks and replaced them with a shared `data_analysis` helper; `__all__` exports now match our actual public API.
- `scripts/interactive_demo.py` landed after customers kept asking for a demo harness that shares code with the CLI.
- The same cycle produced utilities for pattern extraction/step comments and tightened SSH validation so the interactive demo and the CLI share logic instead of diverging.

## CI/CD

Importobot works in CI/CD pipelines and supports headless environments with headless Chrome.

## MCP agent usage

MCP agents (like qwen-code) are only utilized when their context window increases our efficiency while simultaneously reducing token cost.
Every call still flows through the main session, so simple file edits cost extra tokens without saving time.

Good fits:
- Broad explorations, codebase surveys, or brainstorming where parallel thinking helps.
- Analyses that would otherwise require opening dozens of files manually.

Stick with the built-in tools when the failure is easily understood, a small collection of files need to be edited, or the results/output can be easily determined.

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

**Pattern notes**
- Pandas and requests both clean up temporary imports this way, so the approach is familiar to most contributors.
- The pattern keeps the public namespace tidy without hiding functionality.

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
6. Smoke-test the public API: `uv run python -c "import importobot; print('api ok')"`
7. Validate API boundaries: Ensure new utilities have proper `__all__` declarations
8. Check backwards compatibility: Avoid adding legacy support patterns
9. Push changes will trigger GitHub Actions workflows for automated testing and linting

## Development Guidelines

When contributing to this project:
- Follow established coding patterns and architectural decisions
- Maintain consistency with pandas-inspired API design principles
- Test all changes thoroughly using the provided test framework
