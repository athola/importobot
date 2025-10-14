# User Guide

Use this guide to refer to CLI flags, input formats, and supporting tools for Importobot.

## Supported Input Formats

### Current
- **Zephyr JSON**
- **Generic JSON**

### Planned
- **JIRA/Xray** (XML and JSON)
- **TestLink** (XML)
- **CSV**
- **Excel**

## Command-Line Interface

### Basic Conversion
```bash
uv run importobot input.json output.robot
```

### Batch Processing
```bash
uv run importobot --batch input_folder/ output_folder/
```

### Options
- `--help` – show CLI help
- `--batch` – enable directory mode
- `--verbose` – print extra diagnostics

### Enterprise test generators
Helper scripts under `scripts/` can emit large sample suites for demos or benchmarking:

```bash
python scripts/generate_enterprise_tests.py
python scripts/generate_zephyr_tests.py
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

- `IMPORTOBOT_TEST_SERVER_URL`: Overrides the default test server URL.
- `IMPORTOBOT_TEST_SERVER_PORT`: Overrides the default test server port.
- `IMPORTOBOT_HEADLESS_BROWSER`: Set to `True` to run in headless mode.

### Example
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
