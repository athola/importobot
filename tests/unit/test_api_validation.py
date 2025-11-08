"""Tests for importobot.api.validation module.

Tests the enterprise validation toolkit for CI/CD pipeline integration.
Verifies validation functions work correctly for automated processing.
"""

import pytest

from importobot.api import validation
from tests.shared_test_data import INTERNATIONAL_CHARACTERS_TEST_DATA


class TestValidationFunctions:
    """Test validation functions in the API module."""

    def test_validate_json_dict_with_valid_data(self) -> None:
        """Test validate_json_dict with valid test data."""
        valid_data = {
            "name": "Test Case",
            "description": "Valid test case",
            "steps": [{"step": "Execute test", "expectedResult": "Test passes"}],
        }

        # Should not raise exception for valid data
        try:
            validation.validate_json_dict(valid_data)
        except Exception as e:
            pytest.fail(f"Valid data should not raise exception: {e}")

    def test_validate_json_dict_with_invalid_data(self) -> None:
        """Test validate_json_dict with invalid test data."""
        # Test with non-dict input
        with pytest.raises(validation.ValidationError):
            validation.validate_json_dict("not a dict")

        with pytest.raises(validation.ValidationError):
            validation.validate_json_dict(["not", "a", "dict"])

        with pytest.raises(validation.ValidationError):
            validation.validate_json_dict(None)

    def test_validate_json_dict_with_empty_data(self) -> None:
        """Test validate_json_dict with empty data."""
        # Empty dict should be handled gracefully
        try:
            validation.validate_json_dict({})
        except Exception as e:
            pytest.fail(f"Empty dict should not raise exception: {e}")

    def test_validate_safe_path_with_safe_paths(self) -> None:
        """Test validate_safe_path with safe file paths."""
        safe_paths = [
            "/tmp/test.robot",
            "./output/test.robot",
            "output/test.robot",
            "/home/user/tests/suite.robot",
        ]

        for path in safe_paths:
            result = validation.validate_safe_path(path)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_validate_safe_path_with_directory_traversal(self) -> None:
        """Test validate_safe_path prevents directory traversal."""
        dangerous_paths = [
            "../../../etc/passwd",
            "../../secrets.txt",
            "/etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
        ]

        for path in dangerous_paths:
            try:
                result = validation.validate_safe_path(path)
                pytest.fail(
                    f"Path {path} should have raised an exception"
                    f" but returned: {result}"
                )
            except Exception:
                # Expected - path should raise an exception
                pass

    def test_validation_error_inheritance(self) -> None:
        """Test that ValidationError has proper inheritance."""
        assert issubclass(validation.ValidationError, Exception)

        # Test that it can be raised and caught
        with pytest.raises(validation.ValidationError):
            raise validation.ValidationError("Test error")

    def test_validation_functions_are_callable(self) -> None:
        """Test that all validation functions are properly callable."""
        assert callable(validation.validate_json_dict)
        assert callable(validation.validate_safe_path)

    def test_validation_module_exports(self) -> None:
        """Test that validation module exports expected functions."""
        expected_exports = [
            "validate_json_dict",
            "validate_safe_path",
            "ValidationError",
        ]
        assert hasattr(validation, "__all__")
        assert set(validation.__all__) == set(expected_exports)

        for export in expected_exports:
            assert hasattr(validation, export)


class TestCICDIntegrationScenarios:
    """Test validation scenarios for CI/CD pipeline integration."""

    def test_batch_validation_for_pipeline(self) -> None:
        """Test validation of multiple test cases for CI/CD pipeline."""
        test_cases = [
            {"name": "Test 1", "steps": []},
            {"name": "Test 2", "steps": [{"step": "action"}]},
            {"name": "Test 3", "description": "Test case 3", "steps": []},
        ]

        # All test cases should validate successfully
        for i, test_case in enumerate(test_cases):
            try:
                validation.validate_json_dict(test_case)
            except Exception as e:
                pytest.fail(f"Test case {i + 1} should be valid: {e}")

    def test_enterprise_scale_validation(self) -> None:
        """Test validation performance with enterprise-scale data."""
        # Create large test case to simulate enterprise workload
        large_test_case = {
            "name": "Enterprise Scale Test",
            "description": "Large test case for performance testing",
            "steps": [],
        }
        steps: list[dict[str, str]] = large_test_case["steps"]  # type: ignore

        # Add many steps to simulate real enterprise test case
        for i in range(1000):
            step = {
                "step": f"Execute enterprise step {i + 1}",
                "testData": f"enterprise_data_{i + 1}",
                "expectedResult": f"Step {i + 1} completes successfully",
            }
            steps.append(step)

        # Should handle large data efficiently
        try:
            validation.validate_json_dict(large_test_case)
        except Exception as e:
            pytest.fail(f"Large test case should validate successfully: {e}")

    def test_security_validation_for_automated_systems(self) -> None:
        """Test security validation for automated processing systems."""
        # Test path validation for output files in automated systems
        secure_output_paths = [
            "/tmp/automated_output/test_suite.robot",
            "./ci_output/converted_tests.robot",
            "/var/tmp/pipeline_output/enterprise_tests.robot",
        ]

        for path in secure_output_paths:
            try:
                result = validation.validate_safe_path(path)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"Secure path should be valid: {path}, error: {e}")

    def test_error_reporting_for_automation(self) -> None:
        """Test that validation errors provide useful information for automation."""
        # Test that validation errors contain useful information
        try:
            validation.validate_json_dict("invalid data")
        except validation.ValidationError as e:
            error_message = str(e)
            assert len(error_message) > 0
            # Should be informative for automated error handling

        # Test path validation error messages
        try:
            validation.validate_safe_path("../../../dangerous/path")
        except (validation.ValidationError, ValueError) as e:
            error_message = str(e)
            assert len(error_message) > 0

    def test_validation_consistency_across_calls(self) -> None:
        """Test that validation results are consistent across multiple calls."""
        test_data = {"name": "Consistency Test", "steps": [{"step": "test action"}]}

        # Multiple validations should behave consistently
        for _ in range(10):
            try:
                validation.validate_json_dict(test_data)
            except Exception as e:
                pytest.fail(f"Validation should be consistent: {e}")

        # Path validation should also be consistent
        test_path = "/tmp/consistency_test.robot"
        results = []
        for _ in range(5):
            result = validation.validate_safe_path(test_path)
            results.append(result)

        # All results should be identical
        assert all(result == results[0] for result in results)


class TestEnterpriseValidationRequirements:
    """Test validation requirements for enterprise environments."""

    def test_handles_international_characters(self) -> None:
        """Test validation handles international characters in test data."""
        # Should handle international characters without issues
        try:
            validation.validate_json_dict(INTERNATIONAL_CHARACTERS_TEST_DATA)
        except Exception as e:
            pytest.fail(f"International characters should be handled: {e}")

    def test_validates_enterprise_test_structures(self) -> None:
        """Test validation of complex enterprise test structures."""
        enterprise_test = {
            "name": "Enterprise Compliance Test",
            "description": "Complex test for enterprise compliance",
            "priority": "High",
            "category": "Compliance",
            "owner": "compliance-team@enterprise.com",
            "metadata": {
                "requirements": ["REQ-001", "REQ-002"],
                "environment": "production",
                "automation_level": "full",
            },
            "steps": [
                {
                    "step": "Initialize enterprise environment",
                    "testData": "environment: ${ENTERPRISE_ENV}",
                    "expectedResult": "Environment ready for testing",
                },
                {
                    "step": "Execute compliance checks",
                    "testData": "compliance_rules: ${COMPLIANCE_RULESET}",
                    "expectedResult": "All compliance checks pass",
                },
            ],
        }

        # Should handle complex enterprise structures
        try:
            validation.validate_json_dict(enterprise_test)
        except Exception as e:
            pytest.fail(f"Enterprise test structure should be valid: {e}")

    def test_memory_efficiency_with_large_datasets(self) -> None:
        """Test memory efficiency with large enterprise datasets."""
        # Create test case with large amount of test data
        large_enterprise_test = {
            "name": "Large Enterprise Test Suite",
            "description": "Memory efficiency test for large datasets",
            "steps": [],
        }
        steps: list[dict[str, str]] = large_enterprise_test["steps"]  # type: ignore

        # Add substantial test data
        for i in range(5000):
            step = {
                "step": f"Enterprise workflow step {i + 1}",
                "testData": f"large_dataset_{i + 1}: " + "x" * 100,  # Large test data
                "expectedResult": f"Large step {i + 1} processes efficiently",
            }
            steps.append(step)

        # Should handle large datasets without memory issues
        try:
            validation.validate_json_dict(large_enterprise_test)
        except Exception as e:
            pytest.fail(f"Large enterprise dataset should be handled efficiently: {e}")
