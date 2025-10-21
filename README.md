# Importobot: Test Framework Converter

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

Importobot converts structured test exports (Zephyr, TestLink, Xray) into Robot Framework files. Our team was spending hours manually retyping Zephyr test cases—one export might have 700 test cases with 10-15 steps each. Importobot processes entire directories in a single command while preserving the original descriptions and tags.

```python
>>> import importobot
>>> converter = importobot.JsonToRobotConverter()
>>> summary = converter.convert_file("zephyr_export.json", "output.robot")
>>> print(summary)
```

## How It Works

Importobot can convert single files, process entire directories, or fetch data directly from test management systems. It preserves test metadata (descriptions, tags, priorities) while converting the executable steps to Robot Framework syntax.

The template system learns patterns from your existing Robot files. If your team has consistent coding conventions, Importobot will apply those patterns to new conversions instead of using generic templates.

The schema parser reads your team's documentation (SOPs, READMEs) to understand custom field names. We've seen this improve parsing accuracy from ~85% to ~95% on exports where customers use non-standard field names.

For system administration tasks, Importobot generates SSH commands, file operations, and validation steps that match patterns in your existing test library. The Bayesian format detection caps ambiguous ratios at 1.5:1 to avoid false positives when the input format isn't clear.

**Performance measured on our test suite:**
- 100 tests convert in 0.8s
- 1000 tests convert in 6.2s
- 10000 tests convert in 45s
- Memory usage: ~20KB per test case

See the [API Reference](wiki/API-Reference) for detailed documentation of functions and classes.

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

### Enhanced Features (v0.1.3)

**Template Learning**: Learn patterns from your existing Robot files
```console
$ uv run importobot --robot-template templates/ zephyr_export.json converted_tests.robot
```

**Schema Documentation**: Improve parsing with your team's field descriptions
```console
$ uv run importobot --input-schema docs/field_guide.md input.json output.robot
```

**API Integration**: Fetch directly from test management systems
```console
$ uv run importobot \
    --fetch-format zephyr \
    --api-url https://your-zephyr.example.com \
    --tokens your-api-token \
    --project PROJECT_KEY \
    --output converted.robot
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

Importobot can fetch test suites directly from Zephyr, TestRail, JIRA/Xray and other supported platforms. The Zephyr client automatically discovers working API patterns and adapts to different server configurations.

For complete API retrieval examples, configuration options, and troubleshooting, see the [User Guide](wiki/User-Guide#api-retrieval).

## Examples

### Basic Directory Conversion
Convert an entire directory while preserving structure:
```console
$ uv run importobot ./exports/zephyr ./converted
```

### Schema-Driven Conversion
Use your organization's documentation to improve parsing accuracy:
```console
$ uv run importobot --input-schema docs/test_field_guide.md input.json output.robot
```

### Template-Based Conversion
Apply learned patterns from existing Robot files:
```console
$ uv run importobot --robot-template templates/standard.robot input.json output.robot
```

#### Template Learning

The template system works in four phases:

1. **Source ingestion** – Scans your `templates/` directory for Robot files. Unreadable files generate warnings but don't stop processing. Typical processing time: ~50ms per template file.

2. **Pattern extraction** – Normalizes Robot content to capture step patterns (connection, command token, command body) and keyword imports using regex matching defined in `src/importobot/core/templates/blueprints/pattern_application.py`.

3. **Context matching** – Matches step text against extracted patterns during conversion. Reverts to default renderer when no pattern matches are found. This handles edge cases like custom commands or unusual syntax.

4. **Rendering** – Builds suites with learned settings and keywords, adding setup/teardown based on discovered patterns. The renderer preserves your team's coding style.

For troubleshooting template issues, check `src/importobot/core/templates/blueprints/expectations.py` for pattern matching rules.

### Advanced Features

For Bayesian optimization, conversion metrics, and performance analysis, see [API Examples](wiki/API-Examples) and [Performance Benchmarks](wiki/Performance-Benchmarks).


## Confidence Scoring

Importobot uses Bayesian inference to detect input formats and avoid false positives. See [Mathematical Foundations](wiki/Mathematical-Foundations) for the complete implementation details and [Performance Characteristics](wiki/Performance-Characteristics) for accuracy metrics.

## Migration Notes

See [Migration Guide](wiki/Migration-Guide) for upgrade instructions and version compatibility details.

## Documentation

Complete documentation is available on the [project wiki](https://github.com/athola/importobot/wiki):

- **Getting Started**: [Installation](wiki/Getting-Started) and basic usage
- **User Guides**: [User Guide](wiki/User-Guide), [API Examples](wiki/API-Examples), and [Blueprint Tutorial](wiki/Blueprint-Tutorial)
- **Technical Details**: [Mathematical Foundations](wiki/Mathematical-Foundations) and [Architecture](wiki/architecture/)
- **Operations**: [Deployment Guide](wiki/Deployment-Guide) and [Performance Benchmarks](wiki/Performance-Benchmarks)
- **Reference**: [Migration Guide](wiki/Migration-Guide), [Breaking Changes](wiki/Breaking-Changes), and [FAQ](wiki/FAQ)

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
