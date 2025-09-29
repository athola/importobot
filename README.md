# Importobot - Test Framework Converter

| | |
| --- | --- |
| **Testing** | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| **Package** | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| **Meta** | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

## What is Importobot?

**Importobot** converts test cases from test management frameworks (like Zephyr, JIRA/Xray, and TestLink) into executable Robot Framework format. It automates migration of legacy test suites to modern automation frameworks.

Organizations often have thousands of test cases in legacy systems. Manual migration is slow, error-prone, and expensive. Importobot automates this conversion, saving time and resources while preserving test knowledge and business logic.

## Main Features

- **Automated Conversion**: Convert entire test suites with a single command
- **Bulk Processing**: Recursively find and convert test cases in a directory
- **Intelligent Field Mapping**: Automatically map test steps, expected results, tags, and priorities
- **Extensible**: Modular architecture supports adding new input formats and conversion strategies
- **API Integration**: Python API for CI/CD pipelines and enterprise workflows
- **Validation and Suggestions**: Input data validation with suggestions for ambiguous test cases
- **Quality Standards**: Maintains code quality with complete test coverage
- **Production Ready**: Over 1150 tests validate enterprise-scale performance
- **Medallion Architecture**: Data processing with Bronze/Silver/Gold layer quality gates
- **Code Quality**: Maintains 10.00/10 pylint score with complete linting compliance

## Installation

### From PyPI (Recommended)

```sh
pip install importobot
```


### From Source

The source code is hosted on GitHub: https://github.com/athola/importobot

This project uses [uv](https://github.com/astral-sh/uv) for package management. First, install `uv`:

```sh
# On macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, clone the repository and install the dependencies:

```sh
git clone https://github.com/athola/importobot.git
cd importobot
uv sync --dev
```

## Quick Start

Example of converting a Zephyr JSON export to a Robot Framework file:

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

**Conversion Command:**

```sh
# Convert a single file
uv run importobot zephyr_export.json converted_tests.robot
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

## API Usage

Importobot provides a Python API for integration:

### Simple Usage
```python
import importobot

# Core bulk conversion
converter = importobot.JsonToRobotConverter()
result = converter.convert_file("input.json", "output.robot")
```

### Enterprise Integration
```python
from importobot.api import validation, converters, suggestions

# CI/CD pipeline validation
try:
    validation.validate_json_dict(test_data)
    converter = converters.JsonToRobotConverter()
    result = converter.convert_directory("/input", "/output")
except importobot.exceptions.ValidationError as e:
    print(f"Validation failed: {e}")

# QA suggestion engine
engine = suggestions.GenericSuggestionEngine()
improvements = engine.suggest_improvements(problematic_tests)
```

### Configuration
```python
import importobot

# Configure for enterprise security
importobot.config.security_level = "strict"
importobot.config.max_batch_size = 1000

# Bulk processing with error handling
converter = importobot.JsonToRobotConverter()
results = converter.convert_directory(
    input_dir="/test/exports",
    output_dir="/robot/tests",
    recursive=True
)

print(f"Converted: {results['success_count']} files")
print(f"Failed: {results['error_count']} files")
```

## Documentation

The official documentation, including a full API reference, is available in the [project wiki](https://github.com/athola/importobot/wiki).

## Contributing

All contributions, bug reports, bug fixes, documentation improvements, enhancements, and ideas are welcome.

Please feel free to open an issue on the [GitHub issue tracker](https://github.com/athola/importobot/issues).

## License

[BSD 2-Clause](./LICENSE)