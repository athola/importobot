# Importobot Wiki

This wiki contains all documentation for Importobot, a tool for converting Zephyr, Xray, and TestLink exports into Robot Framework suites. It started as a script to avoid manual copy-paste work and is now used in our team's CI pipelines.

If you are new to the project, see the [Getting Started](Getting-Started.md) guide.

## Navigation

### Getting Started
- [Getting Started](Getting-Started.md) - Installation and basic usage.
- [How to Navigate this Codebase](How-to-Navigate-this-Codebase.md) - Code organization and architecture.

### User Documentation
- [User Guide](User-Guide.md) - Complete usage instructions.
- [Blueprint Tutorial](Blueprint-Tutorial.md) - A step-by-step guide to the template system.
- [Migration Guide](Migration-Guide.md) - Upgrade instructions.
- [Usage Examples](Usage-Examples.md) - CLI and API examples.

### API
- [API Examples](API-Examples.md) - Detailed API usage.
- [API Reference](API-Reference.md) - Function and class reference.
- [Breaking Changes](Breaking-Changes.md) - Version compatibility notes.

### Technical Details
- [Mathematical Foundations](Mathematical-Foundations.md) - Algorithms and mathematical principles.
- [Performance Benchmarks](Performance-Benchmarks.md) - Instructions for the benchmark harness.
- [Performance Characteristics](Performance-Characteristics.md) - Baseline metrics.
- [Optimization Implementation](Optimization-Implementation.md) - Performance and security rollout summary.

### Architecture
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture.md) - Design history.
- [Application Context Pattern](architecture/ADR-0004-application-context-pattern.md) - Dependency management architecture.
- [Layer Interactions Diagram](architecture/Layer-Interactions.md) - Medallion data flow.
- [Blueprint Learning](architecture/Blueprint-Learning.md) - Template learning pipeline details.

### Operations & Development
- [Deployment Guide](Deployment-Guide.md) - Deployment steps for local, container, and CI/CD.
- [Security Standards](Security-Standards.md) - Validation and hardening checklist.
- [Contributing](Contributing.md) - Contribution guidelines.
- [Testing](Testing.md) - Test suite organization.

### Reference
- [FAQ](FAQ.md) - Common issues and solutions.
- [Roadmap](Roadmap.md) - Development roadmap.
- [Release Notes](Release-Notes.md) - Version history.

## Why Importobot?

Our team was spending hours manually converting Zephyr test cases into Robot Framework suites. One export had 700 test cases with 10-15 steps each—that's over 10,000 steps to re-type by hand. Existing scripts produced Robot files that still required manual cleanup.

The core problem is that every test management system generates slightly different JSON. Zephyr exports have different field names than TestRail, which differ from JIRA/Xray. We needed a tool that could handle these variations without custom scripts for each system.

Importobot converts entire test suites with one command, retaining original descriptions and tags for easier tracking. When it encounters a step it can't convert reliably, it flags the step instead of guessing. This prevents silent errors in the generated tests.

We built this using test-driven development on real customer exports. The goal was to create Robot files that run without post-conversion editing.

## Quick Start

### Simple Usage
```python
import importobot

converter = importobot.JsonToRobotConverter()
result = converter.convert_directory("/zephyr/exports", "/robot/tests")
print(result)
```

### API Integration
```python
from importobot.api import validation, suggestions
from importobot.integrations.clients import get_api_client, SupportedFormat

# Fetch directly from Zephyr with automatic discovery
client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://your-zephyr.example.com",
    tokens=["your-token"],
    user=None,
    project_name="PROJECT",
    project_id=None,
    max_concurrency=None,
)

# Process results as they stream in
for payload in client.fetch_all(progress_callback=lambda **kw: print(f"Fetched {kw.get('items', 0)} items")):
    validation.validate_json_dict(payload)
    # Process or convert the payload
```

### Integration hooks
```python
from importobot.api import validation, suggestions

validation.validate_json_dict(test_data)
engine = suggestions.GenericSuggestionEngine()
notes = engine.suggest_improvements(problematic_tests)
```

## Recent Changes (October 2025)

### 🚀 Version 0.1.3 Release

**Application Context Pattern**: Replaced global variables with thread-local context to improve test isolation and support concurrent operations. New `importobot.caching` module with unified LRU cache implementation.

**Enhanced Template Learning**: Blueprint system now learns from your existing Robot files using `--robot-template` flag. Cross-template learning identifies and applies consistent patterns across templates for new conversions.

**Schema Parser**: New `--input-schema` flag reads your team's documentation (SOPs, READMEs) to understand organization-specific field naming conventions. Improves parsing accuracy from ~85% to ~95% on custom exports.

**Unified API Integration**: Enhanced `--fetch-format` parameter supporting Zephyr, TestRail, JIRA/Xray, and TestLink with improved format detection and flexible authentication methods.

**Detailed Documentation**: Added Migration Guide for 0.1.2→0.1.3 (no breaking changes), consolidated Breaking Changes documentation, and created Blueprint Tutorial with step-by-step guides.

### Previous Improvements

**Public API Formalization**: Stabilized pandas-style API surface with controlled `__all__` exports. Core implementation remains private while `importobot.api` provides a robust set of tools for integration.

**Template System**: The blueprint system learns from your existing Robot files. If you have a consistent way of writing test cases, Importobot will apply that pattern to new conversions. This replaced the old hardcoded templates.

**Format Detection**: Replaced the weighted heuristic scoring with proper Bayesian confidence calculation. The new system caps ambiguous ratios at 1.5:1 and applies penalties when required fields are missing.

**Test Generation**: Parameter conversion skips comment lines, so placeholders like `${USERNAME}` stay visible in traceability comments. Test cases now track both original and normalized names to handle cases involving control characters.

**Code Quality**: Removed pylint from the project (now using ruff/mypy only) and enhanced test isolation through automatic context cleanup.

## Public API

Use these modules in your code:

- `importobot.JsonToRobotConverter` - Main conversion class
- `importobot.api.*` - Validation, suggestions, and converters
- CLI entry point for command-line usage

### Internal modules
Don't import these directly - they may change between releases:

- `importobot.medallion.*` - Format detection and data pipeline
- `importobot.core.*` - Conversion engine
- `importobot.utils.test_generation.*` - Test data generators

## Project Status

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

- **Test coverage**: 1,946 checks, green in CI
- **Code quality**: pylint/ruff/mypy all clean
- **Performance**: Converts typical Zephyr exports in under a second per test
