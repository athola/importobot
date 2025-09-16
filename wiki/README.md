# Importobot - Test Framework Converter

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Importobot** converts test cases from test management tools (Zephyr, JIRA/Xray, TestLink) into Robot Framework format. It automates the migration process that would otherwise require manual conversion.

## Why Importobot?

Organizations often have thousands of test cases in legacy test management tools. When teams want to adopt Robot Framework for automated testing, they face a choice:
- **Manual Migration**: Weeks or months of copy-paste work, prone to errors and inconsistencies.
- **Starting Over**: Losing years of accumulated test knowledge and business logic.
- **Status Quo**: Staying with suboptimal tooling due to migration complexity.

Importobot automates the conversion process:
- Convert test suites with a single command.
- **Bulk convert** entire directories of test cases.
- Maintain test structure and metadata during conversion.
- Generate Robot Framework files that run without modification.
- Built using TDD practices for reliability.

## Current Capabilities

### Supported Input Formats
- ✅ **Atlassian Zephyr** (JSON export)
- 🚧 **JIRA/Xray** (Roadmap Q4 2025)
- 🚧 **TestLink** (Roadmap Q1 2026)

### What Gets Converted
- Test case structure and hierarchy
- Test steps and expected results
- Metadata (tags, priorities, descriptions)
- Multi-line comments
- Verification points transformed into Robot Framework assertions
- SeleniumLibrary keywords for web testing

## How It Works

```
Input (Zephyr JSON)           →    Importobot Process    →    Output (Robot Framework)
┌─────────────────────┐            ┌─────────────────┐           ┌──────────────────────────┐
│ {                   │            │ 1. Parse JSON   │           │ *** Test Cases ***       │
│   "testCase": {     │     →      │ 2. Map Fields   │    →      │ Login Test               │
│     "name": "Login" │            │ 3. Generate     │           │   Go To    ${LOGIN_URL}  │
│     "steps": [...]  │            │    Keywords     │           │   Input Text  id=user   │
│   }                 │            │ 4. Validate     │           │   Click Button  Login    │
│ }                   │            └─────────────────┘           └──────────────────────────┘
└─────────────────────┘
```

## Example

**Before (Zephyr Test Case):**
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

**After (Generated Robot Framework):**
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

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installing uv

This project uses [uv](https://github.com/astral-sh/uv) for package management. Install uv first:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the installation:
```bash
uv --version
```

### Project Setup

Once uv is installed, set up the project:

```bash
# Clone the repository
git clone https://github.com/athola/importobot.git
cd importobot

# Install project dependencies
uv sync --dev

# Verify the installation by running tests
uv run pytest
```

## Quick Start

### Basic Usage
```bash
# Convert a single Zephyr JSON file
uv run importobot zephyr_export.json converted_tests.robot

# Batch convert multiple files
uv run importobot --batch input_folder/ output_folder/
```

### Migration Workflow

1. **Export**: Export test cases from your source system.
2. **Convert**: Use a single command to convert the test suite to Robot Framework.
3. **Validate**: The generated tests are immediately executable for verification.
4. **Integrate**: The tests can be integrated directly into your existing CI/CD pipelines.

### Configuration

Importobot can be configured with environment variables:

- `IMPORTOBOT_TEST_SERVER_URL`: Overrides the default test server URL.
- `IMPORTOBOT_TEST_SERVER_PORT`: Overrides the default test server port.

## CI/CD

Importobot is designed to be run in a CI/CD pipeline. It includes support for running in a headless environment by using a headless Chrome browser.

## Development

This project uses `uv` for dependency management and follows Test-Driven Development (TDD) and Extreme Programming (XP) principles.

### Setup

```bash
# Install all dependencies
uv sync --dev

# Install the project in editable mode
uv pip install -e .
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Code Quality

```bash
# Run all linting tools
make lint

# Auto-fix common issues
uv run ruff check --fix .
uv run ruff format .
```
