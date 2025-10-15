# Importobot: Test Framework Converter

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

Importobot converts structured test exports (Zephyr, TestLink, Xray) into Robot Framework files. It eliminates the manual work of copying test cases while preserving step order, metadata, and traceability.

```python
>>> import importobot
>>> converter = importobot.JsonToRobotConverter()
>>> summary = converter.convert_file("zephyr_export.json", "output.robot")
>>> print(summary)
```

## Features

- Convert Zephyr, TestLink, and Xray JSON exports to Robot Framework.
- Process entire directories recursively so large imports stay hands-off.
- Preserve descriptions, steps, tags, and priorities for auditors.
- Validate inputs and flag suspicious data before generating Robot code.
- Provide a Python API for CI/CD integration and scripted workflows.
- Use an independent Bayesian scorer with explicit ratio caps to keep ambiguous evidence honest.
- Ship with roughly 1,800 unit and integration tests (currently 1,813; `uv run pytest`).

## Installation

Install via pip:

```console
$ pip install importobot
```

For advanced optimization features and uncertainty quantification, install the optional dependencies:

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

Importobot uses an independent Bayesian scorer to detect file formats:

```
P(H|E) = P(E|H) × P(H) / [P(E|H) × P(H) + P(E|¬H) × P(¬H)]
```

Key details:

- Likelihood mapping: `P = 0.05 + 0.85 × value`, which keeps weak evidence near zero and caps strong evidence at 0.9 before amplification.
- Quadratic decay for wrong-format estimates: `P(E|¬H) = 0.01 + 0.49 × (1 - likelihood)²`.
- Ambiguous evidence is clamped to a 1.5:1 likelihood ratio; confident samples can reach 3:1 against the nearest competitor.
- Dedicated tests in `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py` prevent regressions in these guarantees.

Format-specific adjustments keep things realistic—XML-heavy TestLink data tolerates a little more ambiguity, while JSON-first TestRail requires explicit IDs.

For complete mathematical details, see [Mathematical Foundations](https://github.com/athola/importobot/wiki/Mathematical-Foundations).

## Migration Notes

The 0.1.2 release retires the weighted evidence scorer in favour of the independent
Bayesian pipeline. If you previously imported
`importobot.medallion.bronze.weighted_evidence_bayesian_confidence`, switch to the
runtime-facing `FormatDetector` or use
`importobot.medallion.bronze.independent_bayesian_scorer.IndependentBayesianScorer`
directly. The regression tests in
`tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py` illustrate the new
behaviour and are a good starting point when adjusting custom integrations.

Rate limiting at the security gateway gained exponential backoff. Existing
environments continue to work without changes, but you can tune the behaviour with:

```bash
export IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=256
export IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2.0
export IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=8.0
```

With these defaults we observed average detection latency of ~0.055 s per request
and no loss of throughput compared to 0.1.1 when benchmarking 200 conversions on a
single core.

## Documentation

Documentation is available on the [project wiki](https://github.com/athola/importobot/wiki):

- [User Guide and Medallion workflow](https://github.com/athola/importobot/wiki/User-Guide)
- [Migration guide](https://github.com/athola/importobot/wiki/Migration-Guide)
- [Performance benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)
- [Architecture decisions](https://github.com/athola/importobot/wiki/architecture)
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
