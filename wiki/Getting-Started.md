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
# For basic usage:
uv sync --dev

# For enhanced security with encrypted credential storage:
uv sync --dev --extra security

# Set up encryption (optional but recommended for production)
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"

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

### Security Configuration (Recommended)

For enhanced security, you can enable encrypted credential storage. This requires installing the security extra and setting up encryption:

```bash
# Install security dependencies
uv sync --dev --extra security

# Generate and set a 32-byte encryption key
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"

# Optional: Use system keyring instead of environment variables
export IMPORTOBOT_KEYRING_SERVICE="importobot"
export IMPORTOBOT_KEYRING_USERNAME="importobot"
```

**Why use encryption?**
- Encrypts sensitive data (API keys, passwords) in memory
- Protects credentials from memory dumps or heap inspection
- Provides additional security for CI/CD environments

### General Configuration

Importobot can also be configured with environment variables for other settings:

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
