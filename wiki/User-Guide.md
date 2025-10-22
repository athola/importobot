# User Guide

This guide covers how to use Importobot from the command line and API.

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

### Input Schema Documentation

The schema parser reads your team's documentation (SOPs, READMEs, field guides) to understand organization-specific field naming conventions. This helps when your exports use custom field names that don't match standard Zephyr/TestRail formats.

```bash
# Use your team's SOP
uv run importobot \
    --input-schema docs/test_case_sop.txt \
    input.json output.robot

# Multiple schema files work too
uv run importobot \
    --input-schema docs/field_definitions.md \
    --input-schema docs/zephyr_guide.txt \
    input.json output.robot
```

#### What Schema Files Should Contain

Write your schema files in natural language, describing each field and showing examples:

```
Test Case Name

This field contains the name of the feature being tested. Look for variations like "testName", "case_name", or "title".

Example: "User Login Validation"
Example: "File Upload Permissions"

Description

The test description explains what the test validates. May appear as "description", "desc", or "objective".

Example: "Verify users can login with valid credentials"
Example: "Check file upload fails without permissions"
```

The parser (`src/importobot/core/schema_parser.py`) extracts:
- Field names and their common aliases
- Expected content types and formats
- Example values for pattern matching
- Which fields are required vs optional

This improves field mapping accuracy from ~85% to ~95% on custom exports.

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
- `--input-schema` – documentation describing input test data format (repeatable)
- `--robot-template` – Robot Framework template file or directory (repeatable)

### Enterprise test generators
Helper scripts under `scripts/` can emit large sample suites for demos or benchmarking:

```bash
python scripts/generate_enterprise_tests.py
python scripts/generate_zephyr_tests.py
```

## Migration from 0.1.2

Version 0.1.3 adds major architectural improvements, new features, and documentation cleanup. No breaking changes were introduced.

**New architecture:**
- **Application Context Pattern**: Replaced global variables with thread-local context for better test isolation
- **Unified Caching System**: New `importobot.caching` module with LRU cache implementation

**New features:**
- **JSON Template System**: Learns patterns from your existing Robot files via `--robot-template` flag
- **Schema Parser**: Extracts field definitions from your documentation via `--input-schema` flag
- **Enhanced File Operations**: More JSON examples for system administration tasks
- **API Examples**: New usage examples in `wiki/API-Examples.md`

**Configuration improvements:**
- Better handling of control characters and whitespace in project identifiers
- CLI arguments that don't parse as valid identifiers fall back to environment variables

**Code quality:**
- Removed pylint (now using ruff/mypy only)
- Cleaned up documentation to remove AI-generated content patterns
- All 1,946 tests pass with 0 skips

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

## Conversion Process

```
Zephyr JSON → Importobot → Robot Framework
─────────────┬─────────────┬─────────────────
Parse JSON  → Map Fields  → Generate Robot
            → Validate    → Output .robot
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

The suggestion engine reviews generated tests and flags gaps (missing assertions, weak error handling, security issues) using `importobot.api.suggestions`.

## Validation

Validation checks inputs, configuration, and security rules before conversion. Failures raise `ValidationError`/`SecurityError` with specific error messages.

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

1. Validate JSON exports before conversion
2. Review and dry-run the generated Robot files
3. Use batch mode for large suites
4. Clean artifacts (`make clean`) before committing

### Performance tips

- **Large exports**: Files with 500+ test cases take ~2-3 seconds to convert
- **Memory usage**: Each 1000 test cases uses ~50MB RAM during conversion
- **Batch processing**: Use `--batch` for directories - it's 3-4x faster than individual file calls
- **API rate limits**: Zephyr servers allow 60 requests/minute by default; set `IMPORTOBOT_API_MAX_CONCURRENCY=2` to stay within limits

### Common conversion patterns

**Login test conversion:**
```
Original: "Enter username 'testuser'"
Generated: `Input Text    id=username    testuser`
```

**Navigation steps:**
```
Original: "Navigate to dashboard"
Generated: `Go To    ${DASHBOARD_URL}`
```

We found these patterns after analyzing 200+ real-world test conversions.

## Advanced Features

Internally, Importobot follows a Bronze/Silver/Gold data pipeline, but those modules are private. Use the public API shown below.

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

## Format Detection

Importobot automatically detects which test management system created your export file. If the confidence score is below 0.5, the tool will warn you so you can verify the format is correct.

Common formats:
- **Zephyr/JIRA** - JSON exports with `testCase` fields
- **TestRail** - JSON with case structures and custom fields
- **TestLink** - XML or JSON with test suite hierarchies
- **Generic** - Fallback for unusual or mixed formats

If you get a low confidence warning, check that your export matches the expected format for your test management system.

### Confidence Thresholds

- **Strong evidence (>0.9 likelihood)**: Confidence above 0.8 ✅
- **Zero evidence**: Confidence of 0.0 (evidence of absence)
- **Weak evidence**: Low confidence with uncertainty preserved

### Advanced Features

- **Uncertainty quantification** via Monte Carlo sampling (with SciPy)
- **Cross-validation** for out-of-sample performance assessment
- **Posterior predictive checks** for model validation
- **Adaptive P(E|¬H)** estimation using quadratic decay

Monte Carlo evaluation handles 8+ evidence dimensions in 50ms, where grid evaluation became too slow

For complete mathematical details, see [Mathematical Foundations](https://github.com/athola/importobot/wiki/Mathematical-Foundations).
