# Importobot Wiki

This wiki contains all documentation for Importobot, a tool for converting Zephyr, Xray, and TestLink exports into Robot Framework suites. We built it to automate the conversion of large test suites after finding that manual conversion was taking hours for single exports.

The goal of Importobot is to generate Robot files that run without any post-conversion editing. When it can't convert a step reliably, it flags the step instead of guessing, which prevents silent errors in generated tests.

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

# Convert a directory of Zephyr exports to Robot tests
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
- **Performance**: ~6s to convert 1000 tests
