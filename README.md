# Importobot - Test Framework Converter

| | |
| --- | --- |
| **Testing** | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| **Package** | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| **Meta** | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

## What is Importobot?

**Importobot** is a Python automation tool that converts test cases from test management frameworks (like Zephyr, JIRA/Xray, and TestLink) into executable Robot Framework format. It is a powerful and flexible open-source tool for migrating legacy test suites to modern automation frameworks.

Organizations often have thousands of test cases in legacy systems. Migrating them manually is a slow, error-prone, and expensive process. Importobot automates this conversion process, saving time and resources while preserving test knowledge and business logic.

## Main Features

- **Automated Conversion**: Convert entire test suites with a single command.
- **Bulk Processing**: Recursively find and convert test cases in a directory.
- **Intelligent Field Mapping**: Automatically map test steps, expected results, tags, and priorities.
- **Extensible**: A modular architecture allows for adding new input formats and conversion strategies.
- **Pandas-inspired API**: A `pandas`-inspired API for seamless integration into CI/CD pipelines and enterprise workflows.
- **Validation and Suggestions**: Proactively validate input data and provide suggestions for ambiguous or poorly-defined test cases.
- **High-Quality Output**: Maintains a high code quality standard with comprehensive test coverage.
- **Production Ready**: The project has over 1150 tests and has been validated for enterprise-scale performance.

## Installation

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

Here's a simple example of converting a Zephyr JSON export to a Robot Framework file.

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

Importobot provides a pandas-inspired API for easy integration:

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

### Advanced Configuration
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