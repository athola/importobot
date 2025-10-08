# Importobot - Test Framework Converter

| | |
| --- | --- |
| **Testing** | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| **Package** | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| **Meta** | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

## What is Importobot?

Importobot addresses the massive waste of time that is manually copying Zephyr or TestLink cases into Robot Framework. It reads structured exports (such as JSON) and writes runnable Robot suites without touching the browser or a spreadsheet.

If there is a backlog of legacy tests and a deadline, Importobot keeps step order, migrates metadata, and flags the parts that still need a human decision.

## Main Features

- Convert Zephyr JSON exports into Robot Framework files with a single command
- Walk a directory tree and process discovered supported files
- Preserve descriptions, steps, tags, and priorities instead of flattening them away
- Raise validation errors when inputs look suspicious rather than imposing its own assumptions
- Expose the same functionality as a Python API for CI pipelines and custom tooling
- Ship with a test suite (~1150 checks) that protects the relied-upon conversions 

## Latest updates

- Comment lines now keep their literal placeholders and control characters; executable lines still gain `${param}` replacements, which satisfies the property-based step preservation checks.
- Generated suites annotate both the raw and normalized test names, improving traceability when inputs contain non-printable characters.
- A startup shim preloads deprecated `robot.utils` helpers so SeleniumLibrary tests run quietly, and the Selenium integration path now executes in dry-run mode with explicit cleanup to avoid ResourceWarnings.
- Cache limits and TTLs are now configurable via environment variables such as `IMPORTOBOT_DETECTION_CACHE_MAX_SIZE`, `IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT`, `IMPORTOBOT_DETECTION_CACHE_TTL_SECONDS`, `IMPORTOBOT_FILE_CACHE_MAX_MB`, `IMPORTOBOT_FILE_CACHE_TTL_SECONDS`, and `IMPORTOBOT_OPTIMIZATION_CACHE_TTL_SECONDS`, making prod/dev tuning easier.
- SciPy is now optional; when absent, the MVLP scorer logs a warning and runs in heuristic mode while optimization/training remain disabled until SciPy is installed.
- CI now runs the performance regression suite (`tests/performance`) via a
  dedicated workflow job so hot paths stay within expected bounds.
- Cache hit-rate telemetry can be enabled in production via `IMPORTOBOT_ENABLE_TELEMETRY`, with rate-limited emissions exposed through the central logging channel.
- Asynchronous ingestion helpers (`ingest_file_async`, `ingest_json_string_async`, etc.) allow I/O-bound pipelines to integrate Importobot with event loops using `await` rather than dedicated worker threads.
- Generate shareable performance dashboards with `make benchmark-dashboard`, which compiles the latest JSON benchmark output into a self-contained HTML report.

## API surface & stability

- **Supported:** `importobot.JsonToRobotConverter`, the CLI (`uv run importobot ...`), and modules exposed under `importobot.api.*`.
- **Typed helpers:** `SecurityGateway` now returns structured results (`SanitizationResult` / `FileOperationResult`) with optional `correlation_id` metadata for tracing.
- **Internal:** Packages under `importobot.medallion.*`, `importobot.core.*`, and `importobot.utils.test_generation.*` remain implementation details and may change without notice. Consume them only through the public API above.
- **Configuration:** Tune cache behaviour with environment variables documented in the Configuration section (`IMPORTOBOT_*`), or explicitly pass cache instances to services when tighter control is required.

## Installation

### From PyPI (Recommended)

```sh
pip install importobot
```

To enable SciPy-backed MVLP training and uncertainty intervals, install the
confidence extra:

```sh
pip install "importobot[confidence]"
```


### From Source

The source code is hosted on GitHub: https://github.com/athola/importobot

This project uses [uv](https://github.com/astral-sh/uv) for package management. First, install `uv`:

```sh
# On macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, clone the repository and install the dependencies:

```sh
git clone https://github.com/athola/importobot.git
cd importobot
uv sync --dev
```

## Quick Start

Here’s the minimal workflow used to test conversions:

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

**Conversion Command:**

```sh
uv run importobot zephyr_export.json converted_tests.robot
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

## API Usage

Hooking the converter into another project is straightforward:

```python
import importobot

converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("input.json", "output.robot")
print(summary)
```

For bulk jobs, run this inside CI, validate the payload first, and let the converter walk nested directories.

## Documentation

Docs live in the [project wiki](https://github.com/athola/importobot/wiki). Start with:

- [Medallion workflow walkthrough](https://github.com/athola/importobot/wiki/User-Guide#medallion-workflow-example)
- [Migration guide](https://github.com/athola/importobot/wiki/Migration-Guide)
- [Performance benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)
- [Architecture decision records](https://github.com/athola/importobot/wiki/architecture/ADR-0001-medallion-architecture)
- [Deployment guide](https://github.com/athola/importobot/wiki/Deployment-Guide)

## Contributing

All contributions, bug reports, bug fixes, documentation improvements, enhancements, and ideas are welcome.

Please feel free to open an issue on the [GitHub issue tracker](https://github.com/athola/importobot/issues).

### Mutation testing

Run `make mutation` (or `uv run mutmut run`) to execute mutation tests. The
configuration in `pyproject.toml` targets the high-risk MVLP scorer, detection
cache, and optimization service modules plus their focused unit suites, and uses pytest as
the runner; pass additional flags directly to `mutmut` when profiling a
narrower subset locally.

### Telemetry

Set `IMPORTOBOT_ENABLE_TELEMETRY=1` in production environments to publish cache
hit/miss metrics. Optional tuning knobs `IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS`
and `IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA` control how frequently events are
emitted (defaults: 60s and 100 operations). Telemetry is disabled by default to
avoid noisy logs in local development.

### Benchmarks dashboard

Run `make bench` to capture the latest profiling output, then `make
benchmark-dashboard` to generate `performance_benchmark_dashboard.html`. The
dashboard summarises single-file, bulk, API, and lazy-loading performance
profiles, and embeds the raw JSON for further analysis or sharing.

## License

[BSD 2-Clause](./LICENSE)
