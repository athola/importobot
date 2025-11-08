# Importobot

<div align="center">

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

</div>

Importobot is a Python package that converts test exports from Zephyr, TestRail, Xray, and TestLink into executable Robot Framework files.

## What's new

See the [changelog](CHANGELOG.md) for a full list of changes.

## Installation

```sh
pip install importobot
```

## Quick Start

```python
import importobot

# Convert a single file
converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")

# Convert a directory
result = converter.convert_directory("./exports", "./converted")
```

See the [User Guide](https://github.com/athola/importobot/wiki/User-Guide) for more examples.

## Documentation

The official documentation is hosted on the [project wiki](https://github.com/athola/importobot/wiki).

## Community

For questions and discussions, please use the [GitHub issue tracker](https://github.com/athola/importobot/issues).

## Contributing

Contributions are welcome. Please see the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for more information.

## License

[BSD 2-Clause](./LICENSE)
