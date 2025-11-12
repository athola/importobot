# Getting Started

This guide walks through installing Importobot and converting your first test export.

> If you are new to the codebase, read [How to Navigate this Codebase](How-to-Navigate-this-Codebase.md) to understand the architecture and code organization.

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Installing uv

Importobot uses [uv](https://github.com/astral-sh/uv) for package and project management. The official documentation recommends the following installation methods.

### macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell):
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the installation by checking the version:
```bash
uv --version
```

## Project Setup

Once uv is installed, you can set up the project.

```bash
# Clone the repository
git clone https://github.com/athola/importobot.git
cd importobot

# Create the virtual environment and install dependencies
uv sync --dev

# Run the test suite to confirm the setup
uv run pytest
```

## Basic Usage

To convert a single file, provide the input and output paths:
```bash
uv run importobot zephyr_export.json converted_tests.robot
```

To convert all files in a directory, use the `--batch` flag:
```bash
uv run importobot --batch input_dir/ output_dir/
```

## Example Workflow

A common workflow is to export a test suite, convert it, and then run the generated Robot tests:

```bash
# Convert the export
uv run importobot legacy_tests.json automated_suite.robot

# Validate and run the tests
robot --dryrun automated_suite.robot
robot automated_suite.robot
```

## Configuration

Importobot can be configured with environment variables. For example:

```bash
# Override server settings for API-based formats
export IMPORTOBOT_TEST_SERVER_URL="https://test.example.com"
export IMPORTOBOT_TEST_SERVER_PORT="8080"

# Run browser tests in headless mode
export IMPORTOBOT_HEADLESS_BROWSER="True"
```

Run `uv run importobot --help` to see all available options.

## Examples

Example Zephyr JSON files are in `examples/json/`. You can run them with `make`:

```bash
# Run all examples
make examples

# Run individual examples
make example-user-registration
make example-file-transfer
```
