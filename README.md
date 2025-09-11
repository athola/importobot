# Importobot - Universal Test Framework Converter

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Package manager: uv](https://img.shields.io/badge/package%20manager-uv-blue.svg)](https://github.com/astral-sh/uv)

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

## Prerequisites & Installation

### Installing uv Package Manager

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management. Install uv first:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative installation methods:**
```bash
# Using pip
pip install uv

# Using Homebrew (macOS)
brew install uv

# Using pipx
pipx install uv
```

Verify installation:
```bash
uv --version
```

### Project Setup

Once uv is installed, set up the project:

```bash
# Clone the repository
git clone https://github.com/athola/importobot.git
cd importobot

# Install project dependencies (including dev dependencies)
uv sync --dev

# Verify installation by running tests
uv run pytest
```

**Why uv?**
- **Speed**: 10-100x faster than pip for dependency resolution
- **Reliability**: Deterministic builds with lock file support
- **Python Management**: Automatically manages Python versions
- **Modern Standards**: Built-in support for pyproject.toml and modern Python packaging

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
Example Zephyr JSON files are provided in `examples/json/` to help you understand the expected input format:
- `examples/json/example_zephyr.json` - Basic Zephyr export format
- `examples/json/new_zephyr_test_data.json` - Enhanced format with metadata

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
- **Workflow Validation Tests**: Comprehensive GitHub Actions workflow testing ensuring YAML syntax, structure, and CI/CD best practices

### Code Quality & Standards

All code must pass automated quality gates (enforced by GitHub Actions):

```bash
# Run all linting tools (same as CI)
uv run ruff check .                    # Code linting and formatting checks
uv run black --check .                # Uncompromising code formatting check
uv run pycodestyle src/ tests/        # PEP 8 style guide compliance
uv run pydocstyle src/                 # Docstring standards compliance
uv run pylint src/ tests/              # Comprehensive static analysis

# Auto-fix common issues
uv run ruff check --fix .
uv run ruff format .
uv run black .
```

### Continuous Integration

The project uses GitHub Actions for comprehensive automated testing and quality assurance:

- **Test Workflow** (`.github/workflows/test.yml`): Runs complete test suite across Python 3.10, 3.11, and 3.12 with coverage reporting, Codecov integration, and uploads JUnit XML test reports as artifacts for detailed analysis
- **Lint Workflow** (`.github/workflows/lint.yml`): Enforces code quality using ruff, pycodestyle, pydocstyle, and pylint with optimized caching and proper permissions
- **Claude Code Review** (`.github/workflows/claude-code-review.yml`): Automated AI-powered code review with conditional secret validation
- **Claude Integration** (`.github/workflows/claude.yml`): Advanced AI development assistance with comprehensive CI result analysis

### Automated Dependency Management

- **Dependabot** (`.github/dependabot.yml`): Weekly automated updates for GitHub Actions and Python dependencies with controlled PR limits
- **Workflow Validation Tests**: Comprehensive test coverage for all GitHub Actions workflows ensuring YAML syntax, structure, and best practices compliance

All pull requests must pass automated workflows before merging. Workflow status and security are ensured through proper permissions configuration and conditional secret validation.

#### Required Repository Secrets

For full CI/CD functionality, configure these repository secrets in GitHub Settings > Secrets and variables > Actions:

- `CODECOV_TOKEN`: Token for uploading test coverage reports to Codecov
- `CLAUDE_CODE_OAUTH_TOKEN`: OAuth token for Claude Code Review workflow (if using claude-code-review.yml)

### GPG Commit Signing

This project requires GPG-signed commits for security and authenticity verification.

**Setup GPG signing:**

1. **Generate a GPG key** (if you don't have one):
   ```bash
   gpg --full-generate-key
   # Choose RSA, 4096 bits, set expiration, provide name/email
   ```

2. **Get your GPG key ID**:
   ```bash
   gpg --list-secret-keys --keyid-format=long
   # Copy the key ID after 'sec   rsa4096/'
   ```

3. **Configure Git to use GPG signing**:
   ```bash
   # Set your GPG key (replace with your key ID)
   git config --global user.signingkey YOUR_GPG_KEY_ID
   
   # Enable commit signing globally
   git config --global commit.gpgsign true
   
   # For this project only (already configured)
   git config --local commit.gpgsign true
   ```

4. **Add GPG key to GitHub**:
   ```bash
   # Export your public key
   gpg --armor --export YOUR_GPG_KEY_ID
   # Copy the output and add it to GitHub Settings > SSH and GPG keys
   ```

**Verify signing is working:**
```bash
git commit -m "test: verify GPG signing"
# Should show "gpg: using RSA key..." in output
```

### Why TDD Matters for This Project

- **Conversion Accuracy**: Complex parsing logic is validated before implementation
- **Regression Prevention**: New format support can't break existing conversions
- **Living Documentation**: Tests serve as executable specifications for conversion behavior
- **Confidence**: Comprehensive test coverage enables safe refactoring and feature additions

For detailed technical guidance on our TDD/XP approach, see [CLAUDE.md](CLAUDE.md).
