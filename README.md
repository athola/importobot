# Importobot

<div align="center">

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

</div>

## What is it?

Importobot converts test exports from Zephyr, TestRail, Xray, and TestLink into Robot Framework files. We process entire directories in one command, keep original metadata like descriptions and tags, and generate Robot files that run without manual editing.

## Table of Contents

- [Main Features](#main-features)
- [Where to get it](#where-to-get-it)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Development](#development)
- [Getting Help](#getting-help)
- [Contributing](#contributing)
- [License](#license)

## Main Features

- **[Bulk Conversion][bulk]** - Process entire directories with one command. We've tested this on exports with 700+ test cases and 10,000+ steps.
- **[API Integration][api]** - Fetch directly from Zephyr, TestRail, JIRA/Xray, and TestLink. The Zephyr client adapts to different server configurations automatically.
- **[Template Learning][blueprint]** - Learn patterns from your existing Robot Framework files. Tested on 3 customer suites, reduced manual post-conversion editing by about 70%.
- **[Schema-Aware Parsing][schema]** - Read field definitions from your documentation to handle custom field names like `test_title` instead of standard `name`.
- **[Bayesian Confidence Scoring][math]** - Detect input formats using Bayesian inference with proper ratio constraints (1.5:1 cap for ambiguous cases).
- **[Performance Tracking][perf]** - ASV benchmarking tracks performance across releases. Current benchmarks show ~55ms detection time and ~6s for 1000 tests.

[bulk]: https://github.com/athola/importobot/wiki/User-Guide#bulk-conversion
[api]: https://github.com/athola/importobot/wiki/User-Guide#api-integration
[blueprint]: https://github.com/athola/importobot/wiki/Blueprint-Tutorial
[schema]: https://github.com/athola/importobot/wiki/User-Guide#schema-driven-parsing
[math]: https://github.com/athola/importobot/wiki/Mathematical-Foundations
[perf]: https://github.com/athola/importobot/wiki/Performance-Benchmarks

## Where to get it

The source code is hosted on GitHub at: https://github.com/athola/importobot

Binary installers are available at the [Python Package Index (PyPI)](https://pypi.org/project/importobot):

```sh
pip install importobot
```

## Quick Start

### Python API

```python
import importobot

# Convert a single file
converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")

# Convert a directory
result = converter.convert_directory("./exports", "./converted")
```

### Command Line Interface

```sh
# Basic conversion
importobot zephyr_export.json converted_tests.robot

# API integration with automatic discovery
importobot --fetch-format zephyr --api-url https://your-zephyr.example.com \
    --tokens your-api-token --project PROJECT_KEY --output converted.robot

# Template-based conversion
importobot --robot-template templates/ input.json output.robot

# Schema-driven parsing
importobot --input-schema docs/field_guide.md input.json output.robot
```

See the [User Guide](https://github.com/athola/importobot/wiki/User-Guide) for detailed usage examples.

## Documentation

The official documentation is hosted on the [project wiki](https://github.com/athola/importobot/wiki):

**User Documentation**
- [Getting Started](https://github.com/athola/importobot/wiki/Getting-Started) - Installation and basic usage
- [User Guide](https://github.com/athola/importobot/wiki/User-Guide) - Full usage instructions
- [Blueprint Tutorial](https://github.com/athola/importobot/wiki/Blueprint-Tutorial) - Template learning system guide
- [API Examples](https://github.com/athola/importobot/wiki/API-Examples) - Detailed API usage

**Technical Documentation**
- [API Reference](https://github.com/athola/importobot/wiki/API-Reference) - Function and class reference
- [Mathematical Foundations](https://github.com/athola/importobot/wiki/Mathematical-Foundations) - Bayesian scoring algorithms
- [Performance Benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks) - ASV benchmarking and optimization
- [Architecture Decision Records](https://github.com/athola/importobot/wiki/architecture/ADR-0001-medallion-architecture.md) - Design history

**Reference**
- [Migration Guide](https://github.com/athola/importobot/wiki/Migration-Guide) - Version upgrade instructions
- [FAQ](https://github.com/athola/importobot/wiki/FAQ) - Common issues and solutions
- [Roadmap](https://github.com/athola/importobot/wiki/Roadmap) - Development roadmap

## Development

Importobot uses [uv](https://github.com/astral-sh/uv) for package management:

```sh
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install dependencies
git clone https://github.com/athola/importobot.git
cd importobot
uv sync --dev

# Run tests
make test              # Full test suite (2,105 tests, 0 skips)
make lint              # Code quality checks (ruff + mypy)
make format            # Auto-format code
```

See the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for development workflow, TDD practices, and code standards we follow.

## Getting Help

- **Usage questions**: Open an issue on the [GitHub issue tracker](https://github.com/athola/importobot/issues)
- **Bug reports**: See [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing#reporting-bugs)
- **Feature requests**: See [Roadmap](https://github.com/athola/importobot/wiki/Roadmap) and open an issue

## Background

We built Importobot to automate the conversion of large test suites from legacy test management systems to Robot Framework. Our team was spending hours manually converting single exports, which was a bottleneck in our CI/CD pipeline. This tool was developed to solve that problem, using test-driven development against real customer exports to ensure the generated Robot files run without post-conversion editing.

## Contributing

We welcome contributions! Please see the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for:

- Reporting bugs and requesting features
- Development setup and workflow (TDD, branching strategy)
- Code style and testing requirements
- Pull request guidelines

## License

[BSD 2-Clause](./LICENSE)
