# User Guide

This guide provides instructions for using Importobot to convert your test cases.

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
- `--help`: Display help message.
- `--batch`: Enable batch processing mode.
- `--verbose`: Enable verbose output.

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

Importobot automatically detects which Robot Framework libraries are needed based on the test steps, including:

- SeleniumLibrary
- SSHLibrary
- RequestsLibrary
- DatabaseLibrary
- OperatingSystem
- Process

## Intent-Based Conversion

Importobot uses an intent-driven approach to convert test cases. It analyzes test step descriptions to identify the intended action, rather than relying on a specific format.

## Artifact Management

Importobot generates various artifacts during the conversion process. To keep your workspace clean:

### Cleaning Artifacts
```bash
# Clean common temporary files and directories
make clean

# Perform thorough cleanup including all generated artifacts
make deep-clean
```

### What Gets Cleaned
- Python cache files (`.pyc`, `__pycache__/`)
- Test cache directories (`.pytest_cache/`, `.coverage`, `htmlcov/`)
- Package info directories (`*.egg-info/`)
- Generated Robot Framework files (`examples/robot/*.robot`)
- Robot Framework output files (`output.xml`, `log.html`, `report.html`, `selenium-screenshot-*.png`)
- Common artifact files (`compile.log`, `coverage.xml`, `test-results.xml`, `texput.log`)
- Generated test directories (`robot-tests/`, `zephyr-tests/`)

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

## Best Practices

1. **Validate Input**: Ensure your JSON files are valid before conversion.
2. **Review Output**: Review the generated Robot Framework files before execution.
3. **Test Generated Code**: Run the converted tests in a test environment before production use.
4. **Use Examples**: Refer to the provided examples to understand the expected input formats.
5. **Use Batch Processing**: For large test suites, use batch processing for efficiency.
6. **Clean Artifacts**: Regularly clean generated artifacts using `make clean` or `make deep-clean`.
7. **Maintain Repository Cleanliness**: Ensure no artifacts are accidentally committed to the repository.
