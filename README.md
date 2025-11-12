# Importobot

<div align="center">

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

</div>

Importobot is a Python package for converting test case exports from Zephyr, TestRail, Xray, and TestLink into runnable Robot Framework suites. It was built to automate the tedious process of manually migrating large test libraries.

## What's new

**Recent Improvements:**
- **MongoDB Library Support**: Fixed MongoDB library integration by replacing broken `robotframework-mongodblibrary` with modern `robot-mongodb-library`
- **Type Safety**: Enhanced type checking and fixed enum conversion issues
- **Code Quality**: Improved linting compliance and code organization

See the [changelog](CHANGELOG.md) for a full list of changes.

## Installation

For end-users, install from PyPI:
```sh
pip install importobot
```
For developers contributing to the project, see the [Project Setup](https://github.com/athola/importobot/wiki/Getting-Started#project-setup) instructions.

## Quick Start

```python
import importobot

# Convert a single file from Zephyr JSON to a Robot Framework file
converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")

# Convert an entire directory of exports
result = converter.convert_directory("./exports", "./converted")
```

## Documentation

All documentation is in the [project wiki](https://github.com/athola/importobot/wiki).

- **[Getting Started](https://github.com/athola/importobot/wiki/Getting-Started)**: Install the tool and run your first conversion.
- **[User Guide](https://github.com/athola/importobot/wiki/User-Guide)**: See detailed examples and usage patterns.
- **[How to Navigate this Codebase](https://github.com/athola/importobot/wiki/How-to-Navigate-this-Codebase)**: For developers who want to understand the architecture.

## Community

For questions and discussions, please use the [GitHub issue tracker](https://github.com/athola/importobot/issues).

## Contributing

Contributions are welcome. Please see the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for more information.

## License

[BSD 2-Clause](./LICENSE)
