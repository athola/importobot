# Testing Guide

How tests are organized and executed within Importobot.

## Table of Contents

- [Overview](#overview)
- [Test Organization](#test-organization)
- [Invariant Tests](#invariant-tests)
- [Integration Tests](#integration-tests)
- [Unit Tests](#unit-tests)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)

## Overview

Importobot uses layered testing:

1. **Invariant tests** — property-based runs with Hypothesis.
2. **Integration tests** — end-to-end workflows.
3. **Unit tests** — component-level checks.
4. **Generative tests** — automated case generation.

Current count: 1,941 tests across modules with 0 skips.

## Test Organization

```
tests/
├── invariant/          # Property-based invariant tests
├── integration/        # End-to-end workflow tests
├── unit/              # Component-level tests
│   ├── core/          # Core conversion logic
│   ├── medallion/     # Data architecture tests
│   ├── services/      # Service layer tests
│   └── utils/         # Utility function tests
└── generative/        # Automated test generation
```

## Invariant Tests

### What Are Invariant Tests?

Property-based tests validate rules that must hold regardless of input. Define a ruleset and allow Hypothesis to crack it.

### Key Invariants

**Core System Invariants**
- JSON parsing never corrupts data (roundtrip safety)
- File operations handle all valid content safely
- Path validation works across platforms
- Error handling is consistent

**Format Detection Invariants**
- Confidence scores always between 0.0 and 1.0
- Same input produces same detection result (determinism)
- Invalid input handled gracefully
- Detection timing is consistent

**Conversion Pipeline Invariants**
- Essential test information is preserved
- Generated Robot Framework syntax is always valid
- Conversions are deterministic
- Special characters handled safely

**Security Invariants**
- Sanitization never raises unexpected exceptions
- HTML/script tags are always stripped
- Dangerous command patterns trigger alerts
- Path traversal attempts are caught

### Running Invariant Tests

```bash
# Quick run (CI profile: 20 examples per test)
pytest tests/invariant/ -v

# Development profile (100 examples)
HYPOTHESIS_PROFILE=dev pytest tests/invariant/ -v

# Thorough validation (500 examples)
HYPOTHESIS_PROFILE=thorough pytest tests/invariant/ -v

# Specific test module
pytest tests/invariant/test_security_invariants.py -v
```

### Hypothesis Profiles

Three predefined profiles control test thoroughness:

| Profile | Examples | Timeout | Use Case |
|---------|----------|---------|----------|
| `ci` (default) | 20 | 5s | CI/CD pipelines |
| `dev` | 100 | 10s | Development testing |
| `thorough` | 500 | 30s | Pre-release validation |

### Writing Invariant Tests

**1. Identify the Property**

Ask: "What should **always** be true about this code?"

Examples:
- "Confidence scores are always between 0 and 1"
- "JSON serialization is always reversible"
- "File operations never corrupt data"

**2. Write the Test**

```python
from hypothesis import given, strategies as st
import pytest

class TestMyInvariants:
    @given(st.dictionaries(st.text(), st.text()))
    def test_json_roundtrip_invariant(self, data):
        """Invariant: JSON serialization preserves all data."""
        import json

        try:
            serialized = json.dumps(data)
            deserialized = json.loads(serialized)
            assert deserialized == data
        except (TypeError, ValueError):
            # Expected for non-serializable types
            pass
```

**3. Use Appropriate Strategies**

Common Hypothesis strategies:

```python
from hypothesis import strategies as st

# Basic types
st.text()                    # Random strings
st.integers()                # Random integers
st.floats()                  # Random floats
st.booleans()                # True/False

# Collections
st.lists(st.text())          # Lists of strings
st.dictionaries(             # Random dictionaries
    st.text(),               # Keys
    st.integers()            # Values
)

# Custom strategies
@st.composite
def test_data(draw):
    """Generate realistic test case data."""
    return {
        "name": draw(st.text(min_size=1, max_size=100)),
        "steps": draw(st.lists(st.dictionaries(
            st.text(), st.text()
        ), min_size=1, max_size=10))
    }
```

**4. Handle Expected Exceptions**

```python
@given(st.text())
def test_safe_parsing(self, input_text):
    """Invariant: Parser handles all text without crashing."""
    try:
        result = parse_function(input_text)
        assert result is not None
    except ParserException:
        # Expected for invalid input
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
```

**5. Use assume() to Filter Inputs**

```python
from hypothesis import assume

@given(st.integers())
def test_positive_division(self, x):
    assume(x > 0)  # Only test with positive integers
    result = 100 / x
    assert result > 0
```

### Debugging Failed Invariants

When Hypothesis finds a failing case:

```
FAILED test_confidence_bounds_invariant
>   assert 0.0 <= confidence <= 1.0
E   assert False
E    +  where False = (0.0 <= -0.5)

Falsifying example: test_confidence_bounds_invariant(
    data={'malformed_key': 'unexpected_value'}
)
```

**Steps to Debug**:

1. **Examine the minimal example** - Hypothesis automatically shrinks to simplest failing case
2. **Reproduce manually** - Run the function with that exact input
3. **Verify the invariant** - Is the property actually always true?
4. **Fix the code or test**:
   - Code bug: Fix the implementation
   - Test too strict: Adjust the invariant or add expected exception handling

### Best Practices

✅ **Do**:
- Focus on properties, not specific examples
- Test edge cases (empty collections, None, special characters)
- Use `assume()` to filter invalid inputs
- Handle expected exceptions explicitly
- Keep tests fast (reasonable size limits)

❌ **Don't**:
- Test implementation details
- Ignore expected exceptions
- Generate extremely large data structures
- Write non-deterministic tests
- Mix unit testing with invariant testing

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
- Test security validation in CI/CD environments
- Verify dangerous operations are blocked
- Validate safe operations pass through

### Running Integration Tests

```bash
# All integration tests
pytest tests/integration/ -v

# Specific test file
pytest tests/integration/test_selenium_execution.py -v

# With coverage
pytest tests/integration/ --cov=importobot
```

## Unit Tests

### Organization

```
tests/unit/
├── core/              # Core conversion logic
│   ├── keywords/      # Keyword generators
│   └── suggestions/   # Suggestion engine
├── medallion/         # Data architecture
│   └── bronze/        # Bronze layer tests
├── services/          # Service layer
└── utils/            # Utilities
```

### Running Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific module
pytest tests/unit/core/ -v
pytest tests/unit/services/ -v

# Single test file
pytest tests/unit/test_converter.py -v

# Single test
pytest tests/unit/test_converter.py::TestConverter::test_convert_file -v
```

## Running Tests

### Quick Commands

```bash
# All tests
make test

# With coverage report
make test-coverage

# Lint + Test
make lint && make test

# Specific test types
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/invariant/ -v
```

### Test Profiles

```bash
# Fast CI profile (default)
pytest tests/

# Development profile (more thorough)
HYPOTHESIS_PROFILE=dev pytest tests/

# Maximum thoroughness
HYPOTHESIS_PROFILE=thorough pytest tests/
```

### Advanced Options

```bash
# Run tests matching pattern
pytest -k "test_security" -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Parallel execution (if pytest-xdist installed)
pytest -n auto

# Generate HTML coverage report
pytest --cov=importobot --cov-report=html
open htmlcov/index.html
```

## Writing Tests

### Test Structure

Follow the **Arrange-Act-Assert** pattern:

```python
def test_example():
    # Arrange - Set up test conditions
    converter = JsonToRobotConverter()
    test_data = {"name": "Test Case"}

    # Act - Execute the behavior
    result = converter.convert(test_data)

    # Assert - Verify the outcome
    assert "Test Case" in result
    assert "*** Test Cases ***" in result
```

### Fixtures

Use pytest fixtures for common setup:

```python
import pytest

@pytest.fixture
def sample_json():
    """Provide sample test data."""
    return {
        "name": "Login Test",
        "steps": [
            {"description": "Navigate to login page"},
            {"description": "Enter credentials"}
        ]
    }

def test_conversion(sample_json):
    result = convert(sample_json)
    assert "Login Test" in result
```

### Temporary Files

Use `tmp_path` for file operations:

```python
def test_file_conversion(tmp_path):
    # tmp_path is automatically cleaned up
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.robot"

    input_file.write_text('{"name": "Test"}')
    convert_file(str(input_file), str(output_file))

    assert output_file.exists()
```

### Parameterized Tests

Test multiple cases efficiently:

```python
import pytest

@pytest.mark.parametrize("input_data,expected", [
    ({"name": "Test1"}, "Test1"),
    ({"name": "Test2"}, "Test2"),
    ({"name": "Test3"}, "Test3"),
])
def test_multiple_cases(input_data, expected):
    result = process(input_data)
    assert expected in result
```

## CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Scheduled nightly builds

**Workflow**: `.github/workflows/tests.yml`

```yaml
- name: Run tests
  run: |
    make lint
    make test
    make test-coverage
```

### Test Requirements

All tests must:
- ✅ Pass linting (10.00/10 pylint score)
- ✅ Pass all test cases
- ✅ Maintain or improve code coverage
- ✅ Run in < 2 minutes for fast feedback

### Coverage Requirements

- Minimum coverage: 80% (current: >90%)
- New code should have 100% coverage
- Coverage reports uploaded to Codecov

## Best Practices

### General Guidelines

1. **Test Behavior, Not Implementation**
   - Focus on what the code does, not how
   - Avoid testing private methods directly
   - Use public API for tests

2. **One Assertion Per Test** (when possible)
   - Makes failures easier to diagnose
   - Each test should verify one behavior

3. **Tests Should Be Independent**
   - No test should depend on another test's state
   - Order of execution shouldn't matter
   - Use fixtures for shared setup

4. **Keep Tests Fast**
   - Unit tests: < 100ms each
   - Integration tests: < 5s each
   - Use mocks/stubs for expensive operations

5. **Clear Test Names**
   - `test_converts_json_to_robot_format()` ✅
   - `test_1()` ❌

### TDD Workflow

Importobot follows Test-Driven Development:

1. **Red** - Write failing test
2. **Green** - Write minimal code to pass
3. **Refactor** - Clean up with tests green

Example workflow:
```bash
# 1. Write test
vim tests/unit/test_new_feature.py

# 2. Run test (should fail)
pytest tests/unit/test_new_feature.py -v

# 3. Implement feature
vim src/importobot/core/new_feature.py

# 4. Run test (should pass)
pytest tests/unit/test_new_feature.py -v

# 5. Refactor and verify
pytest tests/unit/test_new_feature.py -v
```

## Further Reading

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Property-Based Testing](https://increment.com/testing/in-praise-of-property-based-testing/)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
- [Importobot Contributing Guide](Contributing.md)
