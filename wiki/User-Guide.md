# User Guide

Use this guide to refer to CLI flags, input formats, and supporting tools for Importobot.

## Supported Input Formats

- **Zephyr** JSON exports
- **JIRA/Xray** JSON
- **TestLink** XML/JSON conversions
- **TestRail** API payloads
- **Generic** dictionaries for ad-hoc conversions

## Command-Line Interface

### Basic Conversion
```bash
uv run importobot input.json output.robot
```

### Batch Processing
```bash
uv run importobot --batch input_folder/ output_folder/
```

### API Retrieval and Conversion

Importobot can fetch test suites directly from supported platforms before conversion:

#### Fetch and Convert in One Step
```bash
uv run importobot \
    --fetch-format testrail \
    --api-url https://testrail.example/api/v2/get_runs/42 \
    --api-user automation@example.com \
    --tokens api-token-value \
    --project QA \
    --output suite.robot
```

#### Zephyr with Automatic Discovery
```bash
uv run importobot \
    --fetch-format zephyr \
    --api-url https://your-zephyr.example.com \
    --tokens your-api-token \
    --project PROJECT_KEY \
    --output converted.robot
```

#### Fetch Only (Save Payload)
```bash
uv run importobot \
    --fetch-format jira_xray \
    --api-url https://jira.example/rest/api/2/search \
    --tokens jira-api-token \
    --project ENG-QA
# Saved to: ./jira_xray-eng-qa-20250314-103205.json
```

### Options
- `--help` – show CLI help
- `--batch` – enable directory mode
- `--verbose` – print extra diagnostics
- `--fetch-format` – fetch from API (values: `jira_xray`, `zephyr`, `testrail`, `testlink`)
- `--api-url` – API endpoint URL for fetching
- `--tokens` – authentication tokens (comma-separated or repeatable)
- `--api-user` – username for API authentication
- `--project` – project name or ID
- `--input-dir` – directory for downloaded payloads (default: current directory)

### Enterprise test generators
Helper scripts under `scripts/` can emit large sample suites for demos or benchmarking:

```bash
python scripts/generate_enterprise_tests.py
python scripts/generate_zephyr_tests.py
```

## Migration from 0.1.2

Version 0.1.3 adds configuration resilience improvements and achieves complete test coverage. No breaking changes were introduced.

**Configuration improvements:**
- Enhanced project identifier parsing to handle control characters and whitespace-only inputs gracefully
- Improved fallback logic ensures CLI arguments that don't parse to valid identifiers fall back to environment variables

**Test coverage:**
- Unskipped and completely rewrote the Zephyr client discovery test
- All 1,941 tests now pass with 0 skips

For legacy migration notes from 0.1.1:
Version 0.1.2 removes the legacy `WeightedEvidenceBayesianScorer`. If you imported it
directly, switch to `FormatDetector` or the new
`importobot.medallion.bronze.independent_bayesian_scorer.IndependentBayesianScorer`.
The behaviour is covered by `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`.

Security rate limiting was improved with exponential backoff. Existing deployments work
unchanged, but can be tuned with:

```bash
export IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=256
export IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2.0
export IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=8.0
```

## How It Works

```
Input (Zephyr JSON)           →    Importobot Process    →    Output (Robot Framework)
┌─────────────────────┐            ┌─────────────────┐           ┌──────────────────────────┐
│ {                   │            │ 1. Parse JSON   │           │ *** Test Cases ***       │
│   "testCase": {     │     →      │ 2. Map Fields   │    →      │ Login Test               │
│     "name": "Login" │            │ 3. Generate     │           │   Go To    ${LOGIN_URL}  │
│     "steps": [...]  │            │    Keywords     │           │   Input Text  id=user   │
│   }                 │            │ 4. Validate     │           │   Click Button  Login    │
│ }                   │            └─────────────────┘           └──────────────────────────┘
└─────────────────────┘
```

## Example

### Before (Zephyr Test Case):
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

### After (Generated Robot Framework):
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

## Library Detection

Importobot infers required Robot libraries from step text, including SeleniumLibrary, SSHLibrary, RequestsLibrary, DatabaseLibrary, OperatingSystem, and Process.

## Intent-Based Conversion

Step text is parsed for intent (e.g., “navigate”, “assert”), which drives keyword selection instead of rigid templates.

## Suggestion Engine

The suggestion engine reviews generated tests and flags gaps (missing assertions, weak error handling, security red flags) using `importobot.api.suggestions`.

## Validation Framework

Validation checks inputs, configuration, and security rules before a conversion completes. Failures raise `ValidationError`/`SecurityError` with actionable messages.

## Artifact Management

### Cleaning artifacts

Run `make clean` for common temp files or `make deep-clean` to remove generated Robot outputs and coverage artifacts. The targets cover caches (`__pycache__`, `.pytest_cache`), coverage reports, and generated example suites.

## Configuration

### Environment Variables

#### API Integration Configuration
Environment variables mirror CLI flags and are prefixed with the target format. CLI arguments always take precedence:

| Format | API URL | Tokens | User | Project |
| --- | --- | --- | --- | --- |
| Jira/Xray | `IMPORTOBOT_JIRA_XRAY_API_URL` | `IMPORTOBOT_JIRA_XRAY_TOKENS` | `IMPORTOBOT_JIRA_XRAY_API_USER` | `IMPORTOBOT_JIRA_XRAY_PROJECT` |
| Zephyr for Jira | `IMPORTOBOT_ZEPHYR_API_URL` | `IMPORTOBOT_ZEPHYR_TOKENS` | `IMPORTOBOT_ZEPHYR_API_USER` | `IMPORTOBOT_ZEPHYR_PROJECT` |
| TestRail | `IMPORTOBOT_TESTRAIL_API_URL` | `IMPORTOBOT_TESTRAIL_TOKENS` | `IMPORTOBOT_TESTRAIL_API_USER` | `IMPORTOBOT_TESTRAIL_PROJECT` |
| TestLink | `IMPORTOBOT_TESTLINK_API_URL` | `IMPORTOBOT_TESTLINK_TOKENS` | `IMPORTOBOT_TESTLINK_API_USER` | `IMPORTOBOT_TESTLINK_PROJECT` |

**Shared settings:**
- `IMPORTOBOT_API_INPUT_DIR` – default directory for downloaded payloads
- `IMPORTOBOT_API_MAX_CONCURRENCY` – experimental limit for concurrent requests

#### Test Configuration
- `IMPORTOBOT_TEST_SERVER_URL`: Overrides the default test server URL
- `IMPORTOBOT_TEST_SERVER_PORT`: Overrides the default test server port
- `IMPORTOBOT_HEADLESS_BROWSER`: Set to `True` to run in headless mode

### Configuration Examples

#### API Integration with Environment Variables
```bash
# Configure Zephyr API access
export IMPORTOBOT_ZEPHYR_API_URL="https://your-zephyr.example.com"
export IMPORTOBOT_ZEPHYR_TOKENS="your-api-token"
export IMPORTOBOT_ZEPHYR_PROJECT="PROJECT_KEY"

# Configure input directory
export IMPORTOBOT_API_INPUT_DIR="./api_payloads"

# Run with environment configuration
uv run importobot --fetch-format zephyr --output converted.robot
```

#### Test Server Configuration
```bash
export IMPORTOBOT_TEST_SERVER_URL="https://test.example.com"
export IMPORTOBOT_TEST_SERVER_PORT="8080"
export IMPORTOBOT_HEADLESS_BROWSER="True"
uv run importobot input.json output.robot
```

## Best practices

1. Validate JSON exports before conversion.
2. Review and dry-run the generated Robot files.
3. Use batch mode for large suites.
4. Clean artifacts (`make clean`) before committing.

## Advanced Features

Internally, Importobot follows a Bronze/Silver/Gold pipeline to keep data quality high, but those modules stay private. Use the public API shown below.

### Using the Public API

```python
import importobot

# Primary conversion interface
converter = importobot.JsonToRobotConverter()

# Convert a test case
test_data = {
    "testCase": {
        "name": "Checkout Smoke",
        "steps": [
            {"stepDescription": "Open checkout", "expectedResult": "Checkout loads"},
            {"stepDescription": "Submit order", "expectedResult": "Order created"},
        ],
    }
}

# Convert to Robot Framework format
robot_content = converter.convert_json_data(test_data)
print(robot_content)

# For validation features
from importobot.api import validation

# Validate test data structure
validation_result = validation.validate_test_structure(test_data)
if validation_result.is_valid:
    print("Test structure is valid")
else:
    print(f"Validation errors: {validation_result.errors}")
```

### API Integration for Programmatic Use

The Python API provides direct access to platform integrations:

```python
from importobot.integrations.clients import get_api_client, SupportedFormat
from importobot.api import validation

# Fetch directly from Zephyr with automatic discovery
client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://your-zephyr.example.com",
    tokens=["your-token"],
    user=None,
    project_name="PROJECT",
    project_id=None,
    max_concurrency=None,
)

# Process results as they stream in
for payload in client.fetch_all(progress_callback=lambda **kw: print(f"Fetched {kw.get('items', 0)} items")):
    validation.validate_json_dict(payload)
    # Process or convert the payload
```

#### Zephyr Client Features

The enhanced Zephyr client provides automatic discovery and adaptation to different server configurations. For complete technical details, see [ADR-0003: API Integration Architecture](architecture/ADR-0003-api-integration).

#### Integration Hooks

```python
from importobot.api import validation, suggestions

validation.validate_json_dict(test_data)
engine = suggestions.GenericSuggestionEngine()
notes = engine.suggest_improvements(problematic_tests)
```

**Internal layers (FYI only):** Bronze handles schema checks, Silver standardises data (in development), Gold prepares the Robot output. Stick to `importobot.*` and `importobot.api.*`; internal modules (`importobot.medallion.*`, `importobot.core.*`) are unsupported.

## Confidence Scoring and Format Detection

Importobot uses mathematically rigorous Bayesian confidence scoring to determine the most likely format of input data:

### Bayesian Confidence Calculation

The system calculates confidence using proper Bayesian inference:

```
P(Format|Evidence) = P(Evidence|Format) × P(Format) / P(Evidence)
```

Where:
- **P(Format|Evidence)**: Final confidence score (posterior probability)
- **P(Evidence|Format)**: Evidence strength given the format (likelihood)
- **P(Format)**: Prior probability based on format prevalence
- **P(Evidence)**: Normalization factor (marginal probability)

### Evidence Metrics

The system evaluates multiple evidence dimensions:

| Metric | Description | Range |
|--------|-------------|-------|
| **Completeness** | How much required evidence is present | [0, 1] |
| **Quality** | Average confidence of individual evidence items | [0, 1] |
| **Uniqueness** | How distinctive the evidence is for the format | [0, 1] |
| **Evidence Count** | Total number of evidence items found | [0, ∞] |
| **Unique Count** | Number of unique evidence items | [0, ∞] |

### Format-Specific Adjustments

Different formats receive specialized treatment:

- **XML formats (TestLink)**: More tolerant of structural errors
- **JSON formats (TestRail)**: Stricter on field matching
- **JIRA formats (Xray/Zephyr)**: Moderate tolerance with custom fields
- **Generic formats**: Higher ambiguity factors

### Confidence Thresholds

- **Strong evidence (>0.9 likelihood)**: Confidence above 0.8 ✅
- **Zero evidence**: Confidence of 0.0 (evidence of absence)
- **Weak evidence**: Appropriately low confidence with uncertainty preserved

### Advanced Features

- **Uncertainty quantification** via Monte Carlo sampling (with SciPy)
- **Cross-validation** for out-of-sample performance assessment
- **Posterior predictive checks** for model validation
- **Adaptive P(E|¬H)** estimation using quadratic decay

For complete mathematical details, see [Mathematical Foundations](https://github.com/athola/importobot/wiki/Mathematical-Foundations).
