# Importobot Wiki

Documentation for Importobot, a tool that converts Zephyr, Xray, TestLink exports into Robot Framework suites. Started as a script to avoid manual copy/paste work, now used in team CI pipelines.

If you are new, start with Getting Started. The other pages cover the conversion workflow, medallion layers, and production chores such as security, deployment, and benchmarks.

## Quick Navigation

- [Getting Started](Getting-Started) - Installation and basic usage
- [How to Navigate this Codebase](How-to-Navigate-this-Codebase) - Architecture and code organization guide
- [User Guide](User-Guide) - Usage instructions
- [Migration Guide](Migration-Guide) - Incremental adoption plan
- [Usage Examples](Usage-Examples) - Quick CLI and API snippets
- [API Examples](API-Examples) - Detailed API usage with newest features
- [API Reference](API-Reference) - Documentation of functions and classes
- [Mathematical Foundations](Mathematical-Foundations) - Mathematical principles and algorithms
- [Performance Benchmarks](Performance-Benchmarks) - Benchmark harness instructions
- [Performance Characteristics](Performance-Characteristics) - Baseline metrics & thresholds
- [Optimization Implementation](Optimization-Implementation) - Multi-phase performance & security rollout summary
- [Deployment Guide](Deployment-Guide) - Local, container, and CI/CD steps
- [Security Standards](Security-Standards) - Mandatory validation and hardening checklist
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture) - Design history
- [Application Context Pattern](architecture/ADR-0004-application-context-pattern) - Dependency management architecture
- [Layer Interactions Diagram](architecture/Layer-Interactions) - Medallion data flow
- [Contributing](Contributing) - Guidelines for contributors
- [FAQ](FAQ) - Common issues and solutions
- [Roadmap](Roadmap) - Future development plans
- [Release Notes](Release-Notes) - Version history and changes

## Why Importobot?

We started Importobot because our team was spending hours manually retyping Zephyr test cases into Robot Framework. One export might have 700 test cases, each with 10-15 steps that needed to be converted by hand.

The tool converts entire test suites with one command while keeping the original descriptions and tags intact. When it encounters steps that need human judgment, it flags them instead of making bad guesses.

We developed this using test-driven development on real customer exports because every test management system generates slightly different JSON. The main goal: create Robot files that actually run without requiring manual cleanup after conversion.

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

### Template System
The blueprint system now learns from your existing Robot files. If you have a consistent way of writing test cases, Importobot will apply that pattern to new conversions. This replaced the old hardcoded templates.

### Format Detection
We replaced the weighted heuristic scoring with proper Bayesian confidence calculation. The new system caps ambiguous ratios at 1.5:1 and applies penalties when required fields are missing. Tests verify these constraints in `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`.

### Test Generation
Parameter conversion skips comment lines, so placeholders like `${USERNAME}` stay visible in traceability comments. Test cases now track both original and normalized names to catch edge cases with control characters.

### Dependencies
Removed the `robot.utils` compatibility shim since Robot Framework updated its dependencies. Selenium tests run in dry-run mode to avoid WebDriver flakes in CI.

### Performance
Cache sizes are now configurable via environment variables:
- `IMPORTOBOT_DETECTION_CACHE_MAX_SIZE` - Format detection cache entries
- `IMPORTOBOT_FILE_CACHE_MAX_MB` - File cache memory limit

### Code Quality
Removed pylint from the project (now using ruff/mypy only) and improved test isolation with automatic context cleanup.

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

- **Test coverage**: 1,941 checks, green in CI
- **Code quality**: pylint/ruff/mypy all clean
- **Performance**: Converts typical Zephyr exports in under a second per test
