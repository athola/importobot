# Importobot Wiki

This wiki collects the working notes for Importobot—the tool we built to convert Zephyr, Xray, TestLink, and similar exports into Robot Framework suites. It began as a weekend script to dodge manual copy/paste work and grew into something teams run in CI.

If you are new, start with Getting Started. The other pages cover the conversion workflow, medallion layers, and production chores such as security, deployment, and benchmarks.

## Quick Navigation

- [Getting Started](Getting-Started) - Installation and basic usage
- [How to Navigate this Codebase](How-to-Navigate-this-Codebase) - Architecture and code organization guide
- [User Guide](User-Guide) - Usage instructions
- [Migration Guide](Migration-Guide) - Incremental adoption plan
- [Usage Examples](Usage-Examples) - Quick CLI and API snippets
- [API Reference](API-Reference) - Documentation of functions and classes
- [Mathematical Foundations](Mathematical-Foundations) - Mathematical principles and algorithms
- [Performance Benchmarks](Performance-Benchmarks) - Benchmark harness instructions
- [Performance Characteristics](Performance-Characteristics) - Baseline metrics & thresholds
- [Optimization Implementation](Optimization-Implementation) - Multi-phase performance & security rollout summary
- [Deployment Guide](Deployment-Guide) - Local, container, and CI/CD steps
- [Security Standards](Security-Standards) - Mandatory validation and hardening checklist
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture) - Design history
- [Layer Interactions Diagram](architecture/Layer-Interactions) - Medallion data flow
- [Contributing](Contributing) - Guidelines for contributors
- [FAQ](FAQ) - Common issues and solutions
- [Roadmap](Roadmap) - Future development plans
- [Release Notes](Release-Notes) - Version history and changes

## Why Importobot?

Before Importobot, teams either retyped Zephyr cases by hand or maintaind brittle internal scripts. Importobot provides a structured approach: it converts test suite exports with one command, keeps descriptions and tags intact, and flags the handful of steps that still need human judgment.

The codebase grew out of TDD runs on real customer data, so the philosophy is practical—validate inputs early, preserve traceability, and ship Robot suites that run without edits. The suggestion engine and extra keyword libraries landed because testers asked for them while reviewing generated files.

## Quick Start

### Simple Usage
```python
import importobot

converter = importobot.JsonToRobotConverter()
result = converter.convert_directory("/zephyr/exports", "/robot/tests")
print(result)
```

### Integration hooks
```python
from importobot.api import validation, suggestions

validation.validate_json_dict(test_data)
engine = suggestions.GenericSuggestionEngine()
notes = engine.suggest_improvements(problematic_tests)
```

## Recent Improvements

### Highlights
- Parameter conversion now ignores comment lines, so literal placeholders and odd control characters remain visible for auditors while executable steps still gain Robot variables.
- Test cases include both the original and normalized names, which keeps the Hypothesis invariants honest even when source data contains `\f` or `\b` characters.
- Independent Bayesian scoring replaced the legacy weighted heuristic. Missing required indicators are penalised, ambiguous evidence is capped at 1.5:1, and the new regression suite (`tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`) keeps those guarantees honest.
- Robot Framework dependencies now ship without the deprecated `robot.utils` helpers, so the old shim was removed and SeleniumLibrary runs warning-free.
- Selenium integration tests switched to a deterministic dry-run path with explicit resource cleanup, removing the flaky WebDriver dependency and lingering socket warnings.
- Cache sizing is now configurable through environment variables (`IMPORTOBOT_DETECTION_CACHE_MAX_SIZE`, `IMPORTOBOT_FILE_CACHE_MAX_MB`, etc.) so CI and production environments can tune memory usage.

## Public API vs. internal modules

- **Stable:** `importobot.JsonToRobotConverter`, the CLI entry point, and submodules exported via `importobot.api.*`.
- **Support utilities:** The typed `SecurityGateway` results (`SanitizationResult`, `FileOperationResult`) surface structured metadata such as correlation ids for tracing.
- **Internal:** Modules under `importobot.medallion.*`, `importobot.core.*`, and `importobot.utils.test_generation.*` are implementation details. Consume them only through the public API or helper functions documented above.

## Project Status

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

- **Test coverage**: 1153 checks, green in CI
- **Code quality**: pylint/ruff/mypy all clean
- **Performance**: Converts typical Zephyr exports in under a second per test
