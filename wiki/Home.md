# Importobot Wiki

This wiki contains all documentation for Importobot.

Importobot converts Zephyr, Xray, and TestLink exports into Robot Framework test suites. It was built to automate a manual conversion process that took hours for a single export.

Importobot aims to generate Robot files that require no manual edits after conversion. If a step cannot be converted reliably, it is flagged with a comment to prevent silent errors in the final test suite.

If you are new to the project, see the [Getting Started](Getting-Started.md) guide.

## Navigation

**User Documentation**
- [Getting Started](Getting-Started.md)
- [User Guide](User-Guide.md)
- [Blueprint Tutorial](Blueprint-Tutorial.md)
- [Usage Examples](Usage-Examples.md)
- [Migration Guide](Migration-Guide.md)

**Technical Documentation**
- [API Reference](API-Reference.md)
- [Mathematical Foundations](Mathematical-Foundations.md)
- [Performance Benchmarks](Performance-Benchmarks.md)
- [Architecture Decision Records](architecture/ADR-0001-medallion-architecture.md)

**Development**
- [Contributing](Contributing.md)
- [Deployment Guide](Deployment-Guide.md)
- [Security Standards](Security-Standards.md)
- [Testing](Testing.md)
- [Roadmap](Roadmap.md)


## Quick Start

```python
import importobot

# Converts all Zephyr JSON exports in a directory to Robot Framework files.
converter = importobot.JsonToRobotConverter()
result = converter.convert_directory("/zephyr/exports", "/robot/tests")
print(result)
```

## Project Status

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

- **Tests**: 2,105 tests passing
- **Code quality**: ruff & mypy clean
- **Performance**: ~6s to convert 1000 tests (see [Benchmarks](Performance-Benchmarks.md))
