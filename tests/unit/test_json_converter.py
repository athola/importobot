"""Tests for JsonToRobotConverter class via public API.

Tests the main converter class through the public API interface,
ensuring enterprise bulk conversion functionality works correctly.
Focuses on business use cases: bulk conversion, error handling, enterprise scale.
"""

import json

import pytest

from importobot import JsonToRobotConverter, exceptions
from tests.shared_test_data import INTERNATIONAL_CHARACTERS_TEST_DATA


class TestJsonToRobotConverterPublicAPI:
    """Tests for JsonToRobotConverter through public API."""

    def test_converter_instantiation(self):
        """Test that converter can be instantiated via public API."""
        converter = JsonToRobotConverter()
        assert converter is not None

        # Test that it has expected public methods
        assert hasattr(converter, "convert_json_string")
        assert callable(converter.convert_json_string)

    def test_convert_json_string_empty_input(self):
        """Test convert_json_string with empty input."""
        converter = JsonToRobotConverter()

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string("")

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string("   ")

    def test_convert_json_string_invalid_json(self):
        """Test convert_json_string with invalid JSON."""
        converter = JsonToRobotConverter()

        with pytest.raises(exceptions.ParseError):
            converter.convert_json_string("invalid json")

        with pytest.raises(exceptions.ParseError):
            converter.convert_json_string("{invalid: json}")

    def test_convert_json_string_non_dict_json(self):
        """Test convert_json_string with non-dict JSON."""
        converter = JsonToRobotConverter()

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string('["not", "a", "dict"]')

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string('"simple string"')

    def test_convert_json_string_minimal_test_case(self):
        """Test convert_json_string with minimal valid test case."""
        converter = JsonToRobotConverter()

        test_json = json.dumps({"name": "Simple Test", "steps": []})

        result = converter.convert_json_string(test_json)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Simple Test" in result
        assert "*** Test Cases ***" in result

    def test_convert_json_string_enterprise_test_case(self):
        """Test convert_json_string with enterprise-scale test case."""
        converter = JsonToRobotConverter()

        # Enterprise test case with multiple steps and metadata
        test_data = {
            "name": "Enterprise Login Test",
            "description": "Automated login test for enterprise application",
            "steps": [
                {
                    "step": "Navigate to login page",
                    "testData": "https://app.enterprise.com/login",
                    "expectedResult": "Login page displays",
                },
                {
                    "step": "Enter enterprise credentials",
                    "testData": "username: ${ENTERPRISE_USER}, "
                    "password: ${ENTERPRISE_PASS}",
                    "expectedResult": "Credentials accepted",
                },
                {
                    "step": "Verify dashboard access",
                    "expectedResult": "Enterprise dashboard loads",
                },
            ],
        }

        test_json = json.dumps(test_data)
        result = converter.convert_json_string(test_json)

        # Verify enterprise test characteristics
        assert isinstance(result, str)
        assert "Enterprise Login Test" in result
        assert "Automated login test for enterprise application" in result
        assert "Navigate to login page" in result
        assert "Enter enterprise credentials" in result
        assert "Verify dashboard access" in result

        # Should contain Robot Framework structure
        assert "*** Test Cases ***" in result
        assert "[Documentation]" in result

    def test_convert_json_string_bulk_conversion_characteristics(self):
        """Test that conversion supports bulk processing characteristics."""
        converter = JsonToRobotConverter()

        # Test multiple conversions to simulate bulk processing
        test_cases = []
        for i in range(10):
            test_data = {
                "name": f"Bulk Test Case {i + 1}",
                "description": f"Test case {i + 1} for bulk conversion validation",
                "steps": [
                    {
                        "step": f"Execute step {i + 1}",
                        "expectedResult": f"Step {i + 1} completes successfully",
                    }
                ],
            }
            test_cases.append(test_data)

        # Convert all test cases
        results = []
        for test_data in test_cases:
            test_json = json.dumps(test_data)
            result = converter.convert_json_string(test_json)
            results.append(result)

        # Verify all conversions succeeded
        assert len(results) == 10
        for i, result in enumerate(results):
            assert f"Bulk Test Case {i + 1}" in result
            assert "*** Test Cases ***" in result

    def test_convert_json_string_error_handling_for_automation(self):
        """Test error handling suitable for automated pipelines."""
        converter = JsonToRobotConverter()

        # Test that specific exceptions are raised for automation
        test_cases = [
            ("", exceptions.ValidationError),  # Empty input
            ("invalid", exceptions.ParseError),  # Invalid JSON
            ("[]", exceptions.ValidationError),  # Non-dict JSON
        ]

        for test_input, expected_exception in test_cases:
            with pytest.raises(expected_exception):
                converter.convert_json_string(test_input)

    def test_convert_json_string_production_ready_output(self):
        """Test that output is production-ready Robot Framework."""
        converter = JsonToRobotConverter()

        test_data = {
            "name": "Production Test",
            "description": "Test for production readiness",
            "steps": [
                {
                    "step": "Verify system health",
                    "expectedResult": "All systems operational",
                }
            ],
        }

        test_json = json.dumps(test_data)
        result = converter.convert_json_string(test_json)

        # Verify Robot Framework structure
        assert "*** Test Cases ***" in result
        assert "[Documentation]" in result

        # Should not contain TODO or placeholder content
        assert "TODO" not in result
        assert "FIXME" not in result
        assert "placeholder" not in result.lower()

        # Should be immediately executable
        lines = result.split("\n")
        assert any(line.strip().startswith("Production Test") for line in lines)

    def test_converter_handles_special_characters(self):
        """Test converter handles special characters for international use."""
        converter = JsonToRobotConverter()

        test_json = json.dumps(INTERNATIONAL_CHARACTERS_TEST_DATA, ensure_ascii=False)
        result = converter.convert_json_string(test_json)

        # Should handle special characters without errors
        assert "Test Internacionalização" in result
        assert "special characters: åäöüß" in result
        assert "Enter special data: éñü" in result

    def test_converter_memory_efficiency_for_large_input(self):
        """Test converter memory efficiency with large test cases."""
        converter = JsonToRobotConverter()

        # Create a large test case to simulate enterprise scale
        large_test_data = {
            "name": "Large Scale Enterprise Test",
            "description": "Test case with many steps for enterprise automation",
            "steps": [],
        }
        steps: list[dict[str, str]] = large_test_data["steps"]  # type: ignore

        # Add 100 steps to simulate large test case
        for i in range(100):
            step = {
                "step": f"Execute automated step {i + 1} in enterprise workflow",
                "testData": f"enterprise_data_{i + 1}: value for step {i + 1}",
                "expectedResult": f"Step {i + 1} completes within enterprise SLA",
            }
            steps.append(step)

        test_json = json.dumps(large_test_data)

        # Should handle large input without memory issues
        result = converter.convert_json_string(test_json)

        assert isinstance(result, str)
        assert len(result) > 1000  # Should be substantial output
        assert "Large Scale Enterprise Test" in result

        # Verify all steps were processed
        for i in range(1, 101):
            assert f"Execute automated step {i}" in result


class TestBusinessLogicAlignment:
    """Test that converter aligns with business logic requirements."""

    def test_bulk_conversion_business_case(self):
        """Test bulk conversion aligns with business requirements."""
        converter = JsonToRobotConverter()

        # Business requirement: Convert thousands of Zephyr test cases
        # Simulate batch of Zephyr-style test cases
        zephyr_style_tests = []
        for i in range(50):  # Simulate subset of enterprise batch
            test_case = {
                "name": f"ZEPHYR-{1000 + i}",
                "description": (
                    f"Enterprise test case migrated from Zephyr (ID: {1000 + i})"
                ),
                "steps": [
                    {
                        "step": "Open enterprise application",
                        "expectedResult": "Application launches successfully",
                    },
                    {
                        "step": f"Execute business workflow {i + 1}",
                        "testData": f"workflow_id: WF_{1000 + i}",
                        "expectedResult": "Workflow completes without errors",
                    },
                ],
            }
            zephyr_style_tests.append(test_case)

        # Business requirement: All conversions must succeed
        successful_conversions = 0
        for test_case in zephyr_style_tests:
            try:
                test_json = json.dumps(test_case)
                result = converter.convert_json_string(test_json)
                tc_in_res = "*** Test Cases ***" in result
                name_in_res = str(test_case["name"]) in result
                if tc_in_res and name_in_res:
                    successful_conversions += 1
            except Exception:
                pass  # Count only successful conversions

        # Business requirement: 100% conversion success rate
        assert successful_conversions == len(zephyr_style_tests)

    def test_no_manual_intervention_required(self):
        """Test that conversion requires no manual intervention."""
        converter = JsonToRobotConverter()

        # Business requirement: Generated tests must be immediately executable
        test_data = {
            "name": "Automated Enterprise Test",
            "description": "Test must run without manual modification",
            "steps": [
                {
                    "step": "Connect to enterprise database",
                    "testData": "connection_string: ${DB_CONNECTION}",
                    "expectedResult": "Database connection established",
                }
            ],
        }

        test_json = json.dumps(test_data)
        result = converter.convert_json_string(test_json)

        # Should not require manual fixes
        assert "TODO" not in result
        assert "FIXME" not in result
        assert "PLACEHOLDER" not in result.upper()

        # Check for manual intervention markers (but not in descriptions)
        lines = result.split("\n")
        for line in lines:
            line_upper = line.upper()
            if (
                line.strip().startswith("#")
                or "[DOCUMENTATION]" in line_upper
                or "DOCUMENTATION" in line_upper
            ):
                continue  # Skip comments and documentation
            assert "MANUAL" not in line_upper, (
                f"Manual intervention marker found in: {line}"
            )

        # Should have proper Robot Framework structure
        assert "*** Test Cases ***" in result
        assert "[Documentation]" in result

        # Should use variables properly (enterprise requirement)
        assert "${DB_CONNECTION}" in result

    def test_enterprise_metadata_preservation(self):
        """Test that enterprise metadata is preserved during conversion."""
        converter = JsonToRobotConverter()

        test_data = {
            "name": "Enterprise Compliance Test",
            "description": "Critical test for SOX compliance validation",
            "priority": "High",
            "category": "Compliance",
            "owner": "compliance-team@enterprise.com",
            "steps": [
                {
                    "step": "Validate audit trail",
                    "expectedResult": "Audit trail is complete and compliant",
                }
            ],
        }

        test_json = json.dumps(test_data)
        result = converter.convert_json_string(test_json)

        # Critical business metadata should be preserved
        assert "Enterprise Compliance Test" in result
        assert "Critical test for SOX compliance validation" in result

        # Should maintain test structure for traceability
        assert "Validate audit trail" in result
        assert "Audit trail is complete and compliant" in result
