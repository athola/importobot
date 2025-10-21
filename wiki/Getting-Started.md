# Getting Started

Install Importobot, verify it works, and convert your first test export.

> **New to the codebase?** Read [How to Navigate this Codebase](How-to-Navigate-this-Codebase) to understand the architecture and code organization.

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

### Other options
- `pip install uv`
- `brew install uv`
- `pipx install uv`

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

# Sanity-check the install (1,946 tests should pass with 0 skips)
uv run pytest
```

## Basic Usage

### Convert a single file
```bash
uv run importobot zephyr_export.json converted_tests.robot
```

### Convert multiple files
```bash
uv run importobot --batch input_dir/ output_dir/
```

## Migration Workflow

1. Export test suite from Zephyr/Xray/etc.
2. Convert it with a single Importobot command.
3. Dry-run and execute the generated Robot tests.
4. Wire the command into a CI job.

```bash
# 1. Export from source system
# → Results in: legacy_tests.json (500+ test cases)

# 2. Convert with Importobot
uv run importobot legacy_tests.json automated_suite.robot

# 3. Validate the conversion
robot --dryrun automated_suite.robot  # Syntax validation
robot automated_suite.robot          # Execute tests

# 4. Integrate into CI/CD
# The tests are ready for an existing Robot Framework infrastructure.
```

## Configuration

The most useful environment variables:

```bash
# Server settings for API-based formats
export IMPORTOBOT_TEST_SERVER_URL="https://test.example.com"
export IMPORTOBOT_TEST_SERVER_PORT="8080"

# Run browser tests in headless mode
export IMPORTOBOT_HEADLESS_BROWSER="True"

# Cache limits for large test suites
export IMPORTOBOT_FILE_CACHE_MAX_MB="200"
```

Run `uv run importobot --help` to see all available options.

## Sample Files

Example Zephyr JSON files are provided in `examples/json/`:
- `examples/json/basic_login.json`
- `examples/json/browser_login.json`
- `examples/json/get_file.json`

## Running Examples

The project includes several examples that demonstrate various conversion scenarios:

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
