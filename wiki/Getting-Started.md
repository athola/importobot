# Getting Started

Set up Importobot, run the tests, and convert a suite of tests into Robot Framework.

> **New to the codebase?** Read [How to Navigate this Codebase](How-to-Navigate-this-Codebase) for a comprehensive guide to the architecture and code organization.

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

# Sanity-check the install
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

Common environment overrides:
- `IMPORTOBOT_TEST_SERVER_URL` (default `http://localhost:8000`)
- `IMPORTOBOT_TEST_SERVER_PORT` (default `8000`)
- `IMPORTOBOT_HEADLESS_BROWSER` (`True`/`False`)
- `IMPORTOBOT_DETECTION_CACHE_MAX_SIZE` (default `1000`)
- `IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT` (default `3`)
- `IMPORTOBOT_FILE_CACHE_MAX_MB` (default `100`)
- `IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE` (default `1000`)
- `IMPORTOBOT_DETECTION_CACHE_TTL_SECONDS` (default `0`, disabled)
- `IMPORTOBOT_FILE_CACHE_TTL_SECONDS` (default `0`, disabled)
- `IMPORTOBOT_PERFORMANCE_CACHE_TTL_SECONDS` (default `0`, disabled)
- `IMPORTOBOT_OPTIMIZATION_CACHE_TTL_SECONDS` (default `0`, disabled)
- `IMPORTOBOT_ENABLE_TELEMETRY` (default `false`, enable cache hit-rate telemetry)
- `IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS` (default `60`, throttle telemetry cadence)
- `IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA` (default `100`, minimum operations between emissions)
- `IMPORTOBOT_OPTIMIZATION_CACHE_TTL_SECONDS` (default `0`, disabled)

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
