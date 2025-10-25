# Importobot: Test Framework Converter

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

## What is it?

**Importobot** is a Python library that converts structured test exports from enterprise test management systems (Zephyr, TestRail, TestLink, Xray) into Robot Framework test suites. It eliminates manual test case migration work while preserving step order, metadata, and traceability links.

## Main Features

- **Multi-Format Support**: Convert from Zephyr, TestRail, TestLink, and Xray JSON exports
- **Bulk Processing**: Process entire directories recursively with consistent quality
- **Metadata Preservation**: Retain descriptions, tags, priorities, and traceability for compliance
- **Security Validation**: Built-in XSS sanitization and DoS protection with rate limiting
- **Bayesian Format Detection**: Intelligent format detection with confidence scoring to avoid false positives
- **Performance Tracking**: ASV (Airspeed Velocity) benchmarking tracks performance across releases
- **CI/CD Ready**: Python API designed for automated pipeline integration
- **Medallion Architecture**: Bronze/Silver/Gold data quality layers for enterprise deployments

## Where to get it

Install the latest release from PyPI:

```console
pip install importobot
```

For advanced optimization features and uncertainty quantification:

```console
pip install "importobot[advanced]"
```

## Quick Start

```python
import importobot

converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")
print(summary)
```

Or via the command line:

```console
importobot zephyr_export.json converted_tests.robot
```

Process entire directories:

```console
importobot ./exports/zephyr ./converted
```

## Documentation

The official documentation is hosted on the [project wiki](https://github.com/athola/importobot/wiki):

- **[Home](https://github.com/athola/importobot/wiki/Home)** - Project overview and recent improvements
- **[User Guide](https://github.com/athola/importobot/wiki/User-Guide)** - Comprehensive usage guide with examples
- **[Performance Benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)** - ASV benchmarking and performance metrics
- **[Migration Guide](https://github.com/athola/importobot/wiki/Migration-Guide)** - Version upgrade instructions
- **[Architecture](https://github.com/athola/importobot/wiki/architecture)** - Design decisions and medallion architecture
- **[Deployment Guide](https://github.com/athola/importobot/wiki/Deployment-Guide)** - CI/CD integration and production deployment
- **[Mathematical Foundations](https://github.com/athola/importobot/wiki/Mathematical-Foundations)** - Bayesian format detection deep dive

## Dependencies

Importobot requires Python 3.10 or higher.

Core dependencies:
- [Robot Framework](https://robotframework.org/) - Test automation framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [bleach](https://github.com/mozilla/bleach) - XSS sanitization

Optional dependencies:
- `importobot[advanced]` - SciPy for Bayesian optimizer tuning
- `importobot[viz]` - Matplotlib for visualization features
- `importobot[analytics]` - NumPy and Pandas for data processing

See the [full dependency list](https://github.com/athola/importobot/blob/main/pyproject.toml) in `pyproject.toml`.

## Installation from Source

This project uses [uv](https://github.com/astral-sh/uv) for package management.

Clone the repository and install:

```console
git clone https://github.com/athola/importobot.git
cd importobot
uv sync --dev
```

## Contributing

Importobot is developed using Test-Driven Development (TDD) and Extreme Programming (XP) practices. All contributions are welcome!

Please see the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for:
- Development workflow and branching strategy
- TDD/XP practices
- Code quality standards
- Testing requirements

### Development Quick Start

```console
# Run all tests
make test

# Run linters and type checking
make lint

# Format code
make format

# Run performance benchmarks
uv run asv run
```

See [CLAUDE.md](./CLAUDE.md) for detailed style guidelines and [PLAN.md](./PLAN.md) for the project roadmap.

## License

[BSD 2-Clause](./LICENSE)

## Discussion and Development

- Report bugs and request features via [GitHub Issues](https://github.com/athola/importobot/issues)
- View the [project roadmap](./PLAN.md) for upcoming features
- Check the [wiki](https://github.com/athola/importobot/wiki) for comprehensive documentation
