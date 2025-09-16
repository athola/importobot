# Getting Started

This guide will help you install and set up Importobot.

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Installing uv

Importobot uses [uv](https://github.com/astral-sh/uv) for package management. Install uv first:

### macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell):
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Other installation methods:
```bash
# Using pip
pip install uv

# Using Homebrew (macOS)
brew install uv

# Using pipx
pipx install uv
```

Verify the installation:
```bash
uv --version
```

## Project Setup

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

## Basic Usage

### Convert a single file
```bash
uv run importobot zephyr_export.json converted_tests.robot
```

### Convert multiple files
```bash
uv run importobot --batch input_folder/ output_folder/
```

## Migration Workflow

1. **Export**: Export test cases from your source system (Zephyr, JIRA/Xray, etc.).
2. **Convert**: Use a single command to convert the test suite to Robot Framework.
3. **Validate**: The generated tests are immediately executable for verification.
4. **Integrate**: The tests can be integrated directly into your existing CI/CD pipelines.

```bash
# 1. Export from your source system
# → Results in: legacy_tests.json (500+ test cases)

# 2. Convert with Importobot
uv run importobot legacy_tests.json automated_suite.robot

# 3. Validate the conversion
robot --dryrun automated_suite.robot  # Syntax validation
robot automated_suite.robot          # Execute tests

# 4. Integrate into your CI/CD
# The tests are ready for your existing Robot Framework infrastructure.
```

## Configuration

Importobot can be configured with environment variables:

- `IMPORTOBOT_TEST_SERVER_URL`: Overrides the default test server URL (default: `http://localhost:8000`).
- `IMPORTOBOT_TEST_SERVER_PORT`: Overrides the default test server port (default: `8000`).
- `IMPORTOBOT_HEADLESS_BROWSER`: Set to `True` to run in headless mode (default: `False`).

### Example
```bash
export IMPORTOBOT_TEST_SERVER_URL="https://test.example.com"
export IMPORTOBOT_TEST_SERVER_PORT="8080"
export IMPORTOBOT_HEADLESS_BROWSER="True"
uv run importobot input.json output.robot
```

## Sample Files

Example Zephyr JSON files are provided in `examples/json/`:
- `examples/json/basic_login.json`
- `examples/json/browser_login.json`
- `examples/json/get_file.json`

## Running Examples

The project includes several examples that demonstrate different conversion scenarios:

```bash
# Run all examples
make examples

# Individual examples
make example-user-registration
make example-file-transfer
make example-database-api
make example-login
make example-suggestions
```
