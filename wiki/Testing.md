# Testing Guide

This guide details how tests are organized, executed, and written within the Importobot project.

## Table of Contents

- [Overview](#overview)
- [Invariant Tests](#invariant-tests)
- [Integration Tests](#integration-tests)
- [Unit Tests](#unit-tests)
- [Running Tests](#running-tests)

## Overview

The Importobot test suite is structured to provide comprehensive coverage:

- **Unit tests**: Verify individual components in isolation.
- **Integration tests**: Validate end-to-end workflows and interactions between components.
- **Invariant tests**: Use property-based testing to ensure core rules hold true across a wide range of inputs.

For a detailed breakdown of test types and their locations, see the [Test Structure](How-to-Navigate-this-Codebase.md#test-structure) section in the codebase navigation guide.

Current status: 1,946 tests across modules with 0 skips.

## Invariant Tests

Invariant tests, also known as property-based tests, are used to validate rules that must always hold true, regardless of the input. We use the [Hypothesis](https://hypothesis.readthedocs.io/) library to automatically generate a wide range of inputs and search for counterexamples that break our invariants.

This is particularly useful for testing things like:

- **Data serialization:** Ensuring that data is not lost or corrupted when it is serialized and deserialized.
- **Format detection:** Verifying that the confidence scores for format detection are always within a valid range.
- **Security:** Checking that sanitization functions correctly remove malicious input.

By using invariant tests, we can catch a wide range of bugs that would be difficult to find with traditional example-based testing.

## Integration Tests

### Purpose

Validate end-to-end workflows and component interactions:
- JSON → Robot Framework conversion pipeline
- Selenium test execution
- API integration workflows
- Security validation in CI/CD
- Bulk conversion operations

### Key Integration Tests

**Full Pipeline Tests** (`test_conversion_process.py`)
```python
def test_end_to_end_conversion(tmp_path):
    """Test complete JSON to Robot Framework conversion."""
    # Create input JSON
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps({...}))

    # Convert
    output_file = tmp_path / "output.robot"
    convert_file(str(json_file), str(output_file))

    # Validate output
    assert output_file.exists()
    assert "*** Test Cases ***" in output_file.read_text()
```

**Selenium Execution** (`test_selenium_execution.py`)
```python
def test_json_to_robot_selenium_execution(tmp_path, mock_server):
    """Full integration: JSON → Robot → Selenium execution."""
    # 1. Create JSON test case
    # 2. Convert to Robot Framework
    # 3. Execute against mock server
    # 4. Verify results
```

**Security Workflows** (`test_security_validation_cicd.py`)
- These tests validate security controls within CI/CD environments.
- They verify that dangerous operations are correctly blocked.
- They also ensure that safe operations pass through as expected.

## Running Tests

### Basic Commands

```bash
# Run all tests
make test

# Run all tests with a coverage report
make test-coverage

# Run linting and tests together
make lint && make test
```

### Running Specific Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run all integration tests
pytest tests/integration/ -v

# Run all invariant tests
pytest tests/invariant/ -v

# Run a specific test file
pytest tests/unit/core/test_converter.py -v

# Run a single test class
pytest tests/unit/core/test_converter.py::TestConverter -v

# Run a single test method
pytest tests/unit/core/test_converter.py::TestConverter::test_convert_file -v

# Run tests with a name matching a keyword
pytest -k "security" -v
```

### Advanced Options

```bash
# Stop on the first failure
pytest -x

# Show print statements in the output
pytest -s

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate an HTML coverage report
pytest --cov=importobot --cov-report=html
open htmlcov/index.html
```

### Hypothesis Test Profiles

For the invariant tests, you can control the thoroughness of the search with Hypothesis profiles:

```bash
# Quick run for CI (default)
pytest tests/invariant/

# More thorough run for development
HYPOTHESIS_PROFILE=dev pytest tests/invariant/

# The most thorough run for pre-release validation
HYPOTHESIS_PROFILE=thorough pytest tests/invariant/
```

## Further Reading

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Property-Based Testing](https://increment.com/testing/in-praise-of-property-based-testing/)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
- [Importobot Contributing Guide](Contributing.md)
