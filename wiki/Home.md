# Importobot Wiki

This wiki contains all documentation for Importobot, a tool for converting Zephyr, Xray, and TestLink exports into Robot Framework suites. We built it to automate the conversion of large test suites, after finding that manual conversion was taking hours for single exports.

The goal of Importobot is to generate Robot files that run without any post-conversion editing. When it can't convert a step reliably, it flags the step instead of guessing, which prevents silent errors in generated tests.

If you are new to the project, see the [Getting Started](Getting-Started.md) guide.

## Navigation

### Getting Started
- [Getting Started](Getting-Started.md) - Installation and basic usage.
- [How to Navigate this Codebase](How-to-Navigate-this-Codebase.md) - Code organization and architecture.

### User Guides
- [User Guide](User-Guide.md) - Full usage instructions.
- [Blueprint Tutorial](Blueprint-Tutorial.md) - A step-by-step guide to the template system.
- [Usage Examples](Usage-Examples.md) - CLI and API examples.
- [Migration Guide](Migration-Guide.md) - Upgrade instructions.

### Technical Documentation
- [API Reference](API-Reference.md) - Function and class reference.
- [Mathematical Foundations](Mathematical-Foundations.md) - Algorithms and mathematical principles.
- [Performance Benchmarks](Performance-Benchmarks.md) - Instructions for the benchmark harness.
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture.md) - Design history.

### Development
- [Contributing](Contributing.md) - Contribution guidelines.
- [Deployment Guide](Deployment-Guide.md) - Deployment steps for local, container, and CI/CD.
- [Security Standards](Security-Standards.md) - Validation and hardening checklist.
- [Testing](Testing.md) - Test suite organization.
- [Roadmap](Roadmap.md) - Development roadmap.
- [Release Notes](Release-Notes.md) - Version history.
- [FAQ](FAQ.md) - Common issues and solutions.


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

## Recent Changes

See the [Changelog](Changelog.md) for a detailed history of changes.
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

- **Test coverage**: 2,105 tests pass, 0 skips, green in CI
- **Code quality**: ruff/mypy all clean (pylint removed October 2025)
- **Performance**: Converts typical Zephyr exports in under a second per test (~55ms detection, ~6s for 1000 tests)
