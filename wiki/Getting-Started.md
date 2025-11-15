# Getting Started

This guide shows how to install Importobot and convert your first test export. For a deeper look at the project's design, see [How to Navigate this Codebase](How-to-Navigate-this-Codebase.md).

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Installing uv

Importobot uses [uv](https://github.com/astral-sh/uv) for package and project management. Install it with one of the following commands.

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

## Converting Tests

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

## Environment Variables

Importobot can be configured with environment variables. For example:

```bash
# Override server settings for API-based formats
export IMPORTOBOT_TEST_SERVER_URL="https://test.example.com"
export IMPORTOBOT_TEST_SERVER_PORT="8080"

# Run browser tests in headless mode
export IMPORTOBOT_HEADLESS_BROWSER="True"
```

### Enabling the New Security Modules

- Generate a Fernet key for the credential manager once and keep it outside version control:

```bash
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

- Ensure `cryptography>=42.0.0` is installed (pulled automatically by `uv sync`, or install manually via `pip install cryptography`) so `importobot.security.CredentialManager` can decrypt stored secrets.

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
