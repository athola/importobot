# Importobot - Universal Test Framework Converter

**Importobot** is a powerful automation tool designed to **fully automate the conversion** of test cases from various test management frameworks (like Atlassian Zephyr, JIRA/Xray, TestLink) into Robot Framework format. This eliminates the time-consuming and error-prone manual migration process that teams typically face when adopting Robot Framework.

## Why Importobot Matters

### The Problem We Solve
Organizations often have thousands of test cases trapped in legacy test management tools. When teams want to adopt Robot Framework for automated testing, they face a daunting choice:
- **Manual Migration**: Weeks or months of copy-paste work, prone to errors and inconsistencies
- **Starting Over**: Losing years of accumulated test knowledge and business logic
- **Status Quo**: Staying with suboptimal tooling due to migration complexity

### Our Solution
Importobot provides **100% automated conversion** with:
- **Zero Manual Intervention**: Convert entire test suites with a single command
- **Preserves Business Logic**: Maintains test structure, metadata, and verification points
- **Ready-to-Execute Tests**: Generates functional Robot Framework files that can run immediately
- **Quality Assurance**: Built using Test-Driven Development to ensure reliability

## Current Capabilities

### Supported Input Formats
- ✅ **Atlassian Zephyr** (JSON export)
- 🚧 **JIRA/Xray** (Roadmap Q4 2024)
- 🚧 **TestLink** (Roadmap Q1 2025)

### What Gets Converted
- Test case structure and hierarchy
- Test steps and expected results
- Metadata (tags, priorities, descriptions)
- Verification points transformed into Robot Framework assertions
- SeleniumLibrary keywords for web testing

## How It Works - Visual Guide

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

## Real-World Example

**Before (Zephyr Test Case):**
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

**After (Generated Robot Framework):**
```robot
*** Test Cases ***
User Login Functionality
    [Documentation]    Verify user can login with valid credentials
    [Tags]    login    authentication
    
    # Navigate to login page
    Go To    ${LOGIN_URL}
    Page Should Contain    Login
    
    # Enter username 'testuser'
    Input Text    id=username_field    testuser
    Textfield Value Should Be    id=username_field    testuser
```

## Business Impact

### Time Savings
- **Before**: 2-3 weeks to manually convert 100 test cases
- **After**: 5 minutes to convert 1000+ test cases

### Quality Improvements
- **Consistency**: All conversions follow the same patterns
- **Completeness**: No missed test steps or verification points
- **Traceability**: Original metadata preserved for audit purposes

### Risk Reduction
- **No Human Error**: Eliminates copy-paste mistakes
- **Validated Output**: Every conversion is tested automatically
- **Reversible Process**: Original test cases remain unchanged

## Installation

To install the project dependencies:

```bash
uv sync
```

## Quick Start Guide

### Basic Usage
```bash
# Convert a single Zephyr JSON file
uv run importobot zephyr_export.json converted_tests.robot

# Batch convert multiple files (coming soon)
uv run importobot --batch input_folder/ output_folder/
```

### Typical Migration Workflow

1. **Export Test Cases**: Export existing test cases from source system (Zephyr, JIRA/Xray, etc.)
2. **Convert**: Single command converts entire test suite to Robot Framework
3. **Validate**: Generated tests are immediately executable for verification
4. **Integrate**: Tests integrate directly into existing CI/CD pipelines

```bash
# Step 1: Export from source system
# → Results in: legacy_tests.json (500+ test cases)

# Step 2: Convert with Importobot
uv run importobot legacy_tests.json automated_suite.robot

# Step 3: Validate conversion
robot --dryrun automated_suite.robot  # Syntax validation
robot automated_suite.robot          # Execute tests

# Step 4: Integrate into CI/CD
# Tests are ready for your existing Robot Framework infrastructure
```

### Sample Files
An example Zephyr JSON file is provided in `example_zephyr.json` to help you understand the expected input format.

## Development

This project uses `uv` for dependency management and follows Test-Driven Development (TDD) and Extreme Programming (XP) principles to ensure reliability and maintainability.

### Setup

```bash
# Install all dependencies
uv sync --dev

# Install the project in editable mode
uv pip install -e .
```

### Test-Driven Development Workflow

The entire codebase is built using TDD, where tests are written before implementation:

```
1. Write Test    →    2. See It Fail    →    3. Implement    →    4. See It Pass    →    5. Refactor
   (Red Phase)         (Validation)          (Green Phase)      (Verification)        (Clean Code)
```

Every feature follows this cycle, ensuring robust and reliable conversion logic.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/        # Fast, isolated component tests
uv run pytest tests/integration/ # End-to-end conversion validation
```

The test suite includes:
- **Unit Tests**: Test individual parsers and converters in isolation with mocked dependencies
- **Integration Tests**: Validate complete conversion workflows with actual file I/O
- **Mock Server Testing**: Verify generated Robot Framework tests against controlled environments

### Code Quality & Standards

All code must pass automated quality gates:

```bash
# Linting and formatting
uv run bash -c "ruff check src tests && pylint src tests"

# Auto-fix common issues
uv run ruff check --fix src tests
```

### Why TDD Matters for This Project

- **Conversion Accuracy**: Complex parsing logic is validated before implementation
- **Regression Prevention**: New format support can't break existing conversions
- **Living Documentation**: Tests serve as executable specifications for conversion behavior
- **Confidence**: Comprehensive test coverage enables safe refactoring and feature additions

For detailed technical guidance on our TDD/XP approach, see [CLAUDE.md](CLAUDE.md).
