# Importobot Wiki

Importobot converts Zephyr, Xray, and TestLink exports into Robot Framework test suites. It was built to automate a manual conversion process that previously took hours for a single export. Version 0.1.5 introduced a dedicated `importobot.security` package (credential manager, template scanner, SIEM connectors, compliance engine) so security-critical code is now grouped under one namespace.

The goal is to generate Robot files that require no manual edits after conversion. If a step cannot be converted reliably, it is flagged with a `TODO` comment to guide manual review.

## Documentation

If you are new to the project, start with the **[Getting Started](Getting-Started.md)** guide to install the tool and run your first conversion. The **[User Guide](User-Guide.md)** provides detailed examples, while the **[Blueprint Tutorial](Blueprint-Tutorial.md)** explains how to customize the conversion logic for your specific needs. See the **[Usage Examples](Usage-Examples.md)** for a collection of sample scripts, or the **[Migration Guide](Migration-Guide.md)** for help upgrading from a previous version.

For a deeper technical understanding, the **[API Reference](API-Reference.md)** offers detailed documentation for all modules. You can also explore the **[Mathematical Foundations](Mathematical-Foundations.md)** of the conversion engine, review **[Performance Benchmarks](Performance-Benchmarks.md)**, or read the **[Architecture Decision Records](architecture/ADR-0001-medallion-architecture.md)** that shaped the tool.

If you want to contribute, see the **[Contributing](Contributing.md)** guide. It works with our **[Testing](Testing.md)** and **[Security Standards](Security-Standards.md)** documents to explain the development process. The **[Deployment Guide](Deployment-Guide.md)** covers how to release a new version, and the **[Roadmap](Roadmap.md)** outlines our future plans.
For security operations, the **[SIEM Integration](SIEM-Integration.md)** page walks through Splunk, Elastic, and Microsoft Sentinel connector setup.

## Quick Start

```python
import importobot

# Convert all Zephyr JSON exports in a directory
converter = importobot.JsonToRobotConverter()
result = converter.convert_directory("/zephyr/exports", "/robot/tests")
print(result)
```

## Project Status

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

- **Tests**: 2,644 collected via `UV_CACHE_DIR=.uv-cache uv run pytest --collect-only --quiet`
- **Security**: 13 new security-focused modules (unit + integration) exercise CredentialManager, HSM adapters, SIEM connectors, and template scanning
- **Performance**: Converts 1,000 test cases in approximately 6 seconds. See [Benchmarks](Performance-Benchmarks.md).
