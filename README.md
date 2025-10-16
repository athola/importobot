# Importobot: Test Framework Converter

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

Importobot converts structured test exports (Zephyr, TestLink, Xray) into Robot Framework files. The converter processes entire directories, maintains the original step order, and preserves metadata for audit trails.

```python
>>> import importobot
>>> converter = importobot.JsonToRobotConverter()
>>> summary = converter.convert_file("zephyr_export.json", "output.robot")
>>> print(summary)
```

## Features

- Convert Zephyr, TestLink, and Xray JSON exports to Robot Framework
- Process entire directories recursively for bulk conversions
- Preserve descriptions, steps, tags, and priorities for audit trails
- Validate JSON structure and flag format mismatches before conversion
- Python API for CI/CD pipelines and automated workflows
- Bayesian format detection with 1.5:1 likelihood ratio caps for ambiguous data
- Test suite with 1,941 tests covering conversion paths and edge cases

## Installation

Install via pip:

```console
$ pip install importobot
```

For optimization features with SciPy-based uncertainty quantification:

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

## API Retrieval

Importobot fetches test suites directly from supported platforms, then converts them using the standard pipeline. The Zephyr client discovers working API patterns and adapts to different server configurations.

- Fetch and convert in one step:
  ```console
  $ uv run importobot \
      --fetch-format testrail \
      --api-url https://testrail.example/api/v2/get_runs/42 \
      --api-user automation@example.com \
      --tokens api-token-value \
      --project QA \
      --output suite.robot
  ```
- Zephyr with automatic discovery:
  ```console
  $ uv run importobot \
      --fetch-format zephyr \
      --api-url https://your-zephyr.example.com \
      --tokens your-api-token \
      --project PROJECT_KEY \
      --output converted.robot
  ```
- Fetch only (the payload is stored in the current directory unless `--input-dir`
  is provided):
  ```console
  $ uv run importobot \
      --fetch-format jira_xray \
      --api-url https://jira.example/rest/api/2/search \
      --tokens jira-api-token \
      --project ENG-QA
  Saved API payload to ./jira_xray-eng-qa-20250314-103205.json
  ```
- Tokens can be supplied as repeated flags (`--tokens alpha --tokens beta`) or as a
  comma-separated list (`--tokens alpha,beta`).
- `--project` accepts either a human-readable project name (e.g., `QA`) or a numeric
  project ID (e.g., `12345`); Importobot automatically detects which form you provided.

### Zephyr Client Features

The Zephyr client automatically discovers working API configurations and adapts to different server setups. See [User Guide](wiki/User-Guide.md) for detailed features and usage examples.

Environment variables mirror CLI flags with format-specific prefixes. CLI arguments take precedence. See [User Guide](wiki/User-Guide.md) for complete configuration reference and examples.

## Examples

- Convert an entire directory while preserving structure:
  ```console
  $ uv run importobot ./exports/zephyr ./converted
  ```
- Enable Bayesian optimiser tuning with SciPy installed via `importobot[advanced]`:
  ```python
  from importobot.medallion.bronze import optimization

  optimizer = optimization.MVLPConfidenceOptimizer()
  optimizer.tune_parameters("fixtures/complex_suite.json")
  ```
- Render conversion metrics if rich numerical plots are desired:
  ```console
  $ uv run python scripts/src/importobot_scripts/example_advanced_features.py
  ```

## Confidence Scoring

Importobot uses Bayesian inference to detect input formats:

```
P(H|E) = P(E|H) × P(H) / [P(E|H) × P(H) + P(E|¬H) × P(¬H)]
```

Implementation details:

- Likelihood mapping: `P = 0.05 + 0.85 × value` keeps weak evidence near zero, caps strong evidence at 0.9
- Wrong-format penalty: `P(E|¬H) = 0.01 + 0.49 × (1 - likelihood)²`
- Ambiguous evidence capped at 1.5:1 likelihood ratio; strong evidence can reach 3:1
- Regression tests in `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py` enforce these constraints

Format-specific adjustments:
- TestLink (XML): Higher ambiguity tolerance
- TestRail (JSON): Stricter ID requirements
- Generic formats: Higher ambiguity factors

See [Mathematical Foundations](https://github.com/athola/importobot/wiki/Mathematical-Foundations) for complete details.

## Migration Notes

See [User Guide](wiki/User-Guide.md#migration-from-012) for migration details from version 0.1.2, including the weighted evidence scorer replacement and new rate limiting controls.

## Documentation

Documentation is available on the [project wiki](https://github.com/athola/importobot/wiki):

- [User Guide and Medallion workflow](https://github.com/athola/importobot/wiki/User-Guide)
- [Migration guide](https://github.com/athola/importobot/wiki/Migration-Guide)
- [Performance benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)
- [Architecture decisions](https://github.com/athola/importobot/wiki/architecture/ADR-0001-medallion-architecture)
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
