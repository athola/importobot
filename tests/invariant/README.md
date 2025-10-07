# Invariant Tests

Property-based tests using [Hypothesis](https://hypothesis.readthedocs.io/) to validate system-wide invariants.

## Purpose

Tests fundamental properties that must always hold true, regardless of input:
- Confidence scores remain within valid bounds (0.0-1.0)
- JSON parsing/serialization is robust and reversible
- Conversion pipeline preserves essential test data
- Security sanitization handles all inputs safely
- Configuration validation catches all invalid states

## Quick Start

```bash
# Run all invariant tests (CI profile: 20 examples)
make test

# Development profile (100 examples)
HYPOTHESIS_PROFILE=dev pytest tests/invariant/ -v

# Thorough validation (500 examples)
HYPOTHESIS_PROFILE=thorough pytest tests/invariant/ -v
```

## Test Coverage

- `test_core_invariants.py` - JSON safety, file operations, path validation
- `test_format_detection_invariants.py` - Detection confidence and determinism
- `test_conversion_pipeline_invariants.py` - Data preservation and output validity
- `test_configuration_invariants.py` - Config validation and consistency
- `test_medallion_invariants.py` - Data lineage and quality metrics
- `test_security_invariants.py` - Sanitization and dangerous pattern detection

## Documentation

For detailed information on writing invariant tests, debugging failures, and best practices, see:

**📖 [Testing Guide in Wiki](../../wiki/Testing.md#invariant-tests)**

Covers:
- How property-based testing works
- Writing effective invariant tests
- Debugging Hypothesis failures
- Integration with CI/CD
- Advanced strategies and patterns
