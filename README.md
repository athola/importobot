# Importobot

<div align="center">

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

</div>

## What is it?

**Importobot** is a Python package for converting structured test exports from Zephyr, TestRail, Xray, and TestLink into Robot Framework test files. We built it to automate the tedious process of manually migrating large test suites, which often involves re-typing thousands of test steps and losing valuable metadata.

This tool preserves test metadata (descriptions, tags, priorities) and converts test steps into clean Robot Framework syntax. Our goal is to make test migration faster, more accurate, and less painful.

## Main Features

- **Bulk Conversion** - Process entire directories with a single command
- **API Integration** - Fetch test data directly from Zephyr, TestRail, JIRA/Xray, and TestLink
- **Template Learning** - Learn patterns from existing Robot Framework files to maintain consistency
- **Schema-Aware Parsing** - Read field definitions from your documentation to improve accuracy (85% → 95%)
- **Confidence Scoring** - Bayesian inference to detect unusual input formats and reduce incorrect conversions
- **Performance** - Convert 1,000 tests in ~6 seconds with ~20KB memory per test case

## Where to get it

The source code is currently hosted on GitHub at: https://github.com/athola/importobot

Binary installers for the latest released version are available at the [Python Package Index (PyPI)](https://pypi.org/project/importobot):

```sh
pip install importobot
```

## Quick Start

```python
import importobot

# Convert a single file
converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")
print(summary)

# Convert a directory
result = converter.convert_directory("./exports", "./converted")
```

### Command Line Interface

```sh
# Basic conversion
importobot zephyr_export.json converted_tests.robot

# API integration
importobot \
    --fetch-format zephyr \
    --api-url https://your-zephyr.example.com \
    --tokens your-api-token \
    --project PROJECT_KEY \
    --output converted.robot

# Template-based conversion
importobot --robot-template templates/ input.json output.robot

# Schema-driven parsing
importobot --input-schema docs/field_guide.md input.json output.robot
```

## Documentation

The official documentation is hosted on the [project wiki](https://github.com/athola/importobot/wiki):

- **[Getting Started](https://github.com/athola/importobot/wiki/Getting-Started)** - Installation and basic usage
- **[User Guide](https://github.com/athola/importobot/wiki/User-Guide)** - Complete usage instructions including API retrieval
- **[Blueprint Tutorial](https://github.com/athola/importobot/wiki/Blueprint-Tutorial)** - Step-by-step guide to the template learning system
- **[API Examples](https://github.com/athola/importobot/wiki/API-Examples)** - Detailed API usage examples
- **[API Reference](https://github.com/athola/importobot/wiki/API-Reference)** - Function and class reference
- **[Migration Guide](https://github.com/athola/importobot/wiki/Migration-Guide)** - Upgrade instructions and version compatibility
- **[Performance Benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)** - Performance characteristics and optimization details
- **[FAQ](https://github.com/athola/importobot/wiki/FAQ)** - Common issues and solutions

## Development

Install [uv](https://github.com/astral-sh/uv) for package management:

```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Clone the repository and install dependencies:

```sh
git clone https://github.com/athola/importobot.git
cd importobot
uv sync --dev
```

Run tests:

```sh
make test              # Run test suite
make test-all          # Run all test categories
make mutation          # Mutation testing
make perf-test         # Performance benchmarks
```

See the **[Contributing Guide](https://github.com/athola/importobot/wiki/Contributing)** for detailed development guidelines.

## Getting Help

For usage questions and discussions, please open an issue on the [GitHub issue tracker](https://github.com/athola/importobot/issues).

## Contributing

We welcome contributions! Please see the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for guidelines on:

- Reporting bugs
- Suggesting features
- Submitting pull requests
- Code style and testing requirements

## License

[BSD 2-Clause](./LICENSE)
