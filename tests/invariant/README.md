# Importobot Invariant Tests

This directory contains **system-wide invariant tests** using [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing. These tests explore edge cases and validate fundamental properties that should hold true regardless of input.

## 🎯 Purpose

Rather than testing specific scenarios, invariant tests define **properties the code must uphold** and use Hypothesis to generate diverse inputs to try and break those properties. This approach helps discover:

- Edge cases that manual testing might miss
- Unexpected input combinations that cause failures
- Inconsistencies in error handling across the system
- Performance degradation under various conditions

## 📁 Test Organization

### Core System Tests (`test_core_invariants.py`)
- **JSON Safety**: JSON parsing and serialization robustness
- **File Operations**: Safe handling of various file content
- **Path Validation**: Cross-platform path handling
- **Error Consistency**: Uniform error handling patterns

### Format Detection Tests (`test_format_detection_invariants.py`)
- **Confidence Bounds**: Scores always between 0.0 and 1.0
- **Determinism**: Same input produces same detection results
- **Invalid Input**: Graceful handling of malformed data
- **Performance**: Consistent detection timing

### Conversion Pipeline Tests (`test_conversion_pipeline_invariants.py`)
- **Data Preservation**: Essential test information maintained
- **Output Validity**: Generated Robot Framework syntax is valid
- **Determinism**: Same input produces identical output
- **Character Handling**: Safe processing of special characters

### Configuration Tests (`test_configuration_invariants.py`)
- **Validation Completeness**: All invalid configs are caught
- **Serialization Safety**: Config objects survive serialization round-trips
- **Type Safety**: Proper handling of various data types
- **Logical Consistency**: Related config values make sense together

### Medallion Architecture Tests (`test_medallion_invariants.py`)
- **Record Integrity**: Bronze records always have valid structure
- **Data Lineage**: Source information preserved through processing
- **Quality Metrics**: Scores within valid ranges and meaningful
- **Scalability**: Performance doesn't degrade with load

## Running Invariant Tests

### Quick Run (CI Profile - 20 examples per test)
```bash
# Run all invariant tests
uv run python -m pytest tests/invariant/ -v

# Run specific test module
uv run python -m pytest tests/invariant/test_core_invariants.py -v

# Run with coverage
uv run python -m pytest tests/invariant/ --cov=importobot --cov-report=term-missing
```

### Development Profile (100 examples per test)
```bash
# Set development profile for more thorough testing
HYPOTHESIS_PROFILE=dev uv run python -m pytest tests/invariant/ -v
```

### Thorough Testing (500 examples per test)
```bash
# Maximum thoroughness (use for comprehensive validation)
HYPOTHESIS_PROFILE=thorough uv run python -m pytest tests/invariant/ -v
```

### Individual Test Categories
```bash
# Core system invariants
uv run python -m pytest tests/invariant/test_core_invariants.py -v

# Format detection
uv run python -m pytest tests/invariant/test_format_detection_invariants.py -v

# Conversion pipeline
uv run python -m pytest tests/invariant/test_conversion_pipeline_invariants.py -v

# Configuration validation
uv run python -m pytest tests/invariant/test_configuration_invariants.py -v

# Medallion architecture
uv run python -m pytest tests/invariant/test_medallion_invariants.py -v
```

## Hypothesis Configuration

The tests use three predefined profiles:

- **`ci`** (default): 20 examples, 5s timeout - for CI/CD pipelines
- **`dev`**: 100 examples, 10s timeout - for development testing
- **`thorough`**: 500 examples, 30s timeout - for comprehensive validation

You can switch profiles using the `HYPOTHESIS_PROFILE` environment variable.

## Understanding Test Output

### Successful Tests
```
tests/invariant/test_core_invariants.py::TestCoreInvariants::test_json_roundtrip_invariant PASSED
```

### Failed Tests (Found Invariant Violation)
When Hypothesis finds an input that breaks an invariant, it will:
1. Show the **minimal failing example**
2. Provide the **exact input** that caused the failure
3. Display the **assertion or exception** that occurred

Example:
```
FAILED tests/invariant/test_format_detection_invariants.py::test_confidence_bounds_invariant
>   assert 0.0 <= confidence <= 1.0
E   assert False
E    +  where False = (0.0 <= -0.5)

Falsifying example: test_confidence_bounds_invariant(data={'invalid_key': 'invalid_value'})
```

This tells you exactly what input caused the problem, making debugging straightforward.

## Adding New Invariant Tests

### 1. Identify the Invariant Property
Ask: "What should **always** be true about this code, regardless of input?"

Examples:
- "Confidence scores are always between 0 and 1"
- "JSON serialization is always reversible for valid data"
- "File operations never corrupt data"

### 2. Write the Test
```python
from hypothesis import given, strategies as st

@given(st.text())  # Generate random text
def test_my_invariant(self, input_text):
    """Invariant: My function should never crash on text input."""
    try:
        result = my_function(input_text)
        assert result is not None  # Your invariant here
    except MyExpectedException:
        pass  # Expected failures are okay
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
```

### 3. Use Appropriate Strategies
Hypothesis provides many built-in strategies:
- `st.text()` - random strings
- `st.integers()` - random integers
- `st.dictionaries()` - random dictionaries
- `st.lists()` - random lists
- Custom composite strategies for domain-specific data

## 🎯 Best Practices

### 1. Focus on Properties, Not Examples
❌ **Don't**: Test specific inputs
✅ **Do**: Test properties that should always hold

### 2. Handle Expected Exceptions
```python
try:
    result = function_under_test(input_data)
    # Test your invariant on the result
except ExpectedException:
    pass  # This is fine
except Exception as e:
    pytest.fail(f"Unexpected: {e}")
```

### 3. Use `assume()` to Filter Invalid Inputs
```python
from hypothesis import assume

@given(st.integers())
def test_positive_division(self, x):
    assume(x > 0)  # Only test with positive integers
    result = 100 / x
    assert result > 0
```

### 4. Make Tests Fast
- Use reasonable limits on generated data size
- Set appropriate timeouts
- Focus on logic, not performance-intensive operations

## 🐛 Debugging Failed Invariant Tests

When a test fails:

1. **Look at the minimal example** - Hypothesis shows the simplest input that breaks your invariant
2. **Reproduce manually** - Run your function with that exact input
3. **Check your assumptions** - Maybe your invariant isn't actually always true
4. **Fix the code or the test** - Either the code has a bug, or your invariant is too strict

## 🔄 Integration with CI/CD

These tests run as part of the regular test suite:
- **Fast profile** in CI for quick feedback
- **Thorough profile** can be run nightly or before releases
- Tests are deterministic (same seed = same generated inputs)

## 📚 Further Reading

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing](https://increment.com/testing/in-praise-of-property-based-testing/)
- [Hypothesis Strategies](https://hypothesis.readthedocs.io/en/latest/data.html)