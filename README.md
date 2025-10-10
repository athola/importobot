# Importobot: Test Framework Converter

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

Importobot converts structured test exports (Zephyr, TestLink, Xray) into Robot Framework files. It eliminates the manual work of copying test cases while preserving step order, metadata, and traceability.

```python
>>> import importobot
>>> converter = importobot.JsonToRobotConverter()
>>> summary = converter.convert_file("zephyr_export.json", "output.robot")
>>> print(summary)
```

## Features

- Convert Zephyr, TestLink, and Xray JSON exports to Robot Framework
- Process entire directories recursively
- Preserve descriptions, steps, tags, and priorities
- Validate inputs and flag suspicious data
- Python API for CI/CD integration
- Mathematically rigorous Bayesian confidence scoring
- Comprehensive test suite (~1150 checks)

## Installation

Install via pip:

```console
$ pip install importobot
```

For advanced optimization features and uncertainty quantification, install the optional dependencies:

```console
$ pip install "importobot[advanced]"
```

## Development Version

The source code is hosted on GitHub: https://github.com/athola/importobot

This project uses [uv](https://github.com/astral-sh/uv) for package management. First, install `uv`:

```console
# On macOS / Linux
$ curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
$ powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, clone the repository and install the dependencies:

```console
$ git clone https://github.com/athola/importobot.git
$ cd importobot
$ uv sync --dev
```

## Quick Start

Convert Zephyr JSON exports to Robot Framework:

```console
$ uv run importobot zephyr_export.json converted_tests.robot
```

**Input (Zephyr JSON):**
```json
{
  "testCase": {
    "name": "User Login Functionality",
    "description": "Verify user can login with valid credentials",
    "steps": [
      {
        "stepDescription": "Navigate to login page",
        "expectedResult": "Login page displays"
      },
      {
        "stepDescription": "Enter username 'testuser'",
        "expectedResult": "Username field populated"
      }
    ]
  }
}
```

**Output (Robot Framework):**
```robot
*** Test Cases ***
User Login Functionality
    [Documentation]    Verify user can login with valid credentials
    [Tags]    login    authentication

    # Navigate to login page
    Go To    ${LOGIN_URL}
    Page Should Contain    Login

    # Enter username 'testuser'
    Input Text    id=username    testuser
    Textfield Value Should Be    id=username    testuser
```

## Documentation

Documentation is available on the [project wiki](https://github.com/athola/importobot/wiki):

- [User Guide and Medallion workflow](https://github.com/athola/importobot/wiki/User-Guide)
- [Migration guide](https://github.com/athola/importobot/wiki/Migration-Guide)
- [Performance benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)
- [Architecture decisions](https://github.com/athola/importobot/wiki/architecture)
- [Deployment guide](https://github.com/athola/importobot/wiki/Deployment-Guide)

## Contributing

We welcome contributions! Please open an issue on [GitHub](https://github.com/athola/importobot/issues) to report bugs or suggest features.

### Running Tests

```console
$ make test
```

### Mutation Testing

```console
$ make mutation
```

### Performance Benchmarks

```console
$ make perf-test
$ make benchmark-dashboard
```

## License

[BSD 2-Clause](./LICENSE)
