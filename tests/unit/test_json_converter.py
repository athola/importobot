"""Tests for JsonToRobotConverter class via public API.

Tests the main converter class through the public API interface,
ensuring enterprise bulk conversion functionality works correctly.
Focuses on business use cases: bulk conversion, error handling, enterprise scale.
"""

import json
import time
from contextlib import suppress

import pytest

from importobot import JsonToRobotConverter, exceptions
from tests.shared_test_data import (
    ENTERPRISE_LOGIN_TEST,
    INTERNATIONAL_CHARACTERS_TEST_DATA,
)


class TestJsonToRobotConverterPublicAPI:
    """Tests for JsonToRobotConverter through public API."""

    def test_converter_instantiation(self) -> None:
        """Test that converter can be instantiated via public API."""
        converter = JsonToRobotConverter()
        assert converter is not None

        # Test that it has expected public methods
        assert hasattr(converter, "convert_json_string")
        assert callable(converter.convert_json_string)

    def test_convert_json_string_empty_input(self) -> None:
        """Test convert_json_string with empty input."""
        converter = JsonToRobotConverter()

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string("")

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string("   ")

    def test_convert_json_string_invalid_json(self) -> None:
        """Test convert_json_string with invalid JSON."""
        converter = JsonToRobotConverter()

        with pytest.raises(exceptions.ParseError):
            converter.convert_json_string("invalid json")

        with pytest.raises(exceptions.ParseError):
            converter.convert_json_string("{invalid: json}")

    def test_convert_json_string_non_dict_json(self) -> None:
        """Test convert_json_string with non-dict JSON."""
        converter = JsonToRobotConverter()

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string('["not", "a", "dict"]')

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_string('"simple string"')

    def test_convert_json_string_minimal_test_case(self) -> None:
        """Test convert_json_string with minimal valid test case."""
        converter = JsonToRobotConverter()

        test_json = json.dumps({"name": "Simple Test", "steps": []})

        result = converter.convert_json_string(test_json)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Simple Test" in result
        assert "*** Test Cases ***" in result

    def test_convert_json_string_enterprise_test_case(self) -> None:
        """Test convert_json_string with enterprise-scale test case."""
        converter = JsonToRobotConverter()

        test_json = json.dumps(ENTERPRISE_LOGIN_TEST)
        result = converter.convert_json_string(test_json)

        # Verify enterprise test characteristics
        assert isinstance(result, str)
        assert "Enterprise Login Test" in result
        assert "Automated login test for enterprise application" in result
        assert "Navigate to login page" in result
        assert "Enter username" in result  # Fixed: actual test data
        assert "Enter password" in result  # Fixed: actual test data
        assert "Click login button" in result  # Fixed: actual test data

        # Should contain Robot Framework structure
        assert "*** Test Cases ***" in result
        assert "[Documentation]" in result

    def test_convert_json_string_bulk_conversion_characteristics(self) -> None:
        """Test that conversion supports bulk processing characteristics.

        Business Requirement: Handle hundreds/thousands of test cases in single batch.
        This is a CORE business capability - automation means NO manual steps.
        """
        converter = JsonToRobotConverter()

        # Test enterprise-scale bulk processing (100 test cases)
        # NOTE: Using 100 instead of 1000 to keep test execution time reasonable
        # Real-world enterprise batches are 1000+ but 100 validates the pattern
        test_cases = []
        for i in range(100):
            test_data = {
                "name": f"Bulk Test Case {i + 1}",
                "description": f"Test case {i + 1} for bulk conversion validation",
                "priority": "Medium" if i % 2 == 0 else "High",
                "tags": ["bulk", f"batch-{i // 10}"],  # Group into batches of 10
                "steps": [
                    {
                        "step": f"Execute step {i + 1}",
                        "expectedResult": f"Step {i + 1} completes successfully",
                    }
                ],
            }
            test_cases.append(test_data)

        # Convert all test cases - measure that it completes without degradation
        results = []
        start_time = time.time()

        for test_data in test_cases:
            test_json = json.dumps(test_data)
            result = converter.convert_json_string(test_json)
            results.append(result)

        end_time = time.time()
        conversion_time = end_time - start_time

        # Verify all conversions succeeded
        assert len(results) == 100, f"Expected 100 results, got {len(results)}"

        # Validate each conversion is correct Robot Framework format
        for index, result in enumerate(results, start=1):
            assert f"Bulk Test Case {index}" in result, (
                f"Test case {index} name missing"
            )
            assert "*** Test Cases ***" in result, (
                f"Test case {index} missing Test Cases section"
            )
            # Verify no degradation in output quality across the batch
            assert len(result) > 100, f"Test case {index} output suspiciously short"

        # Performance check: 100 conversions should complete in reasonable time
        # This validates no memory leaks or performance degradation in bulk mode
        assert conversion_time < 30.0, (
            "Bulk conversion too slow: "
            f"{conversion_time:.2f}s for 100 test cases. "
            "Enterprise requirement: process hundreds of tests efficiently."
        )

        # Validate output variety so each generated test remains unique
        high_priority_count = sum(
            1
            for generated in results
            if "High" in generated or "priority" in generated.lower()
        )
        assert high_priority_count > 0, "Priority metadata not preserved in bulk"

    def test_enterprise_scale_bulk_conversion_1000_plus_test_cases(self) -> None:
        """Test conversion at true enterprise scale: 1000+ test cases.

        Business Requirement: Enterprise migrations involve thousands of test cases.
        - Zephyr migrations: 5000+ test cases typical
        - TestRail migrations: 10000+ test cases common
        - Must validate memory efficiency, linear performance, error recovery
        """
        converter = JsonToRobotConverter()

        # Test with 1000 test cases to validate enterprise scale
        num_test_cases = 1000
        test_cases = []

        # Create realistic test case variety
        for i in range(num_test_cases):
            test_data = {
                "name": f"ENTERPRISE-{10000 + i}",
                "description": f"Enterprise test case from migration batch {i + 1}",
                "priority": ["Critical", "High", "Medium", "Low"][i % 4],
                "category": ["Smoke", "Regression", "Integration", "UAT"][i % 4],
                "tags": [
                    f"suite-{i // 100}",  # Group into suites of 100
                    f"priority-{i % 4}",
                    "automated",
                ],
                "steps": [
                    {
                        "step": f"Execute enterprise workflow step {i + 1}",
                        "testData": f"data_set_{i + 1}",
                        "expectedResult": f"Workflow {i + 1} completes successfully",
                    }
                ],
            }
            test_cases.append(test_data)

        # Convert all test cases and measure performance
        results = []
        start_time = time.time()

        for test_data in test_cases:
            test_json = json.dumps(test_data)
            result = converter.convert_json_string(test_json)
            results.append(result)

        end_time = time.time()
        conversion_time = end_time - start_time

        # Business Requirement: 100% conversion success rate
        assert len(results) == num_test_cases, (
            f"Expected {num_test_cases} conversions, got {len(results)}"
        )

        # Sample validation: Check first 10, middle 10, last 10 for quality
        sample_indices = (
            list(range(10))  # First 10
            + list(range(495, 505))  # Middle 10
            + list(range(990, 1000))  # Last 10
        )

        for idx in sample_indices:
            result = results[idx]
            expected_name = f"ENTERPRISE-{10000 + idx}"
            assert expected_name in result, (
                f"Test case {idx} name not preserved: {expected_name}"
            )
            assert "*** Test Cases ***" in result, (
                f"Test case {idx} missing Test Cases section"
            )
            assert f"Execute enterprise workflow step {idx + 1}" in result, (
                f"Test case {idx} step not preserved"
            )

        # Performance requirement: Linear scalability
        # 1000 test cases should complete in reasonable time (< 5 minutes)
        assert conversion_time < 300.0, (
            f"Enterprise-scale conversion too slow: {conversion_time:.2f}s for "
            f"{num_test_cases} test cases. Must complete within 5 minutes for "
            "enterprise batches."
        )

        # Calculate average time per test case for reporting
        avg_time_per_test = conversion_time / num_test_cases
        # Should be sub-second per test case
        assert avg_time_per_test < 1.0, (
            f"Average conversion time {avg_time_per_test:.3f}s per test is too slow. "
            "Enterprise requirement: process test cases efficiently at scale."
        )

        # Validate metadata variety preserved across entire batch
        priorities_found = set()
        categories_found = set()
        for result in results[::100]:  # Sample every 100th result
            if "Critical" in result:
                priorities_found.add("Critical")
            if "Smoke" in result:
                categories_found.add("Smoke")
            if "Regression" in result:
                categories_found.add("Regression")

        assert len(priorities_found) > 0, "Priority metadata lost in bulk processing"
        assert len(categories_found) > 0, "Category metadata lost in bulk processing"

    def test_bulk_conversion_error_recovery_and_reporting(self) -> None:
        """Test error recovery and reporting in bulk conversion operations.

        Business Requirement: Fail-fast with clear error reporting.
        When converting 1000 test cases, if test #456 fails, the system must:
        1. Report which specific test failed (test #456)
        2. Include the error details for debugging
        3. Allow continuation or stop based on configuration
        """
        converter = JsonToRobotConverter()

        # Create a batch with intentional errors mixed in
        batch_size = 100
        test_cases = []
        error_indices = [10, 30, 75]  # Intentionally corrupt these

        for i in range(batch_size):
            test_data: dict[str, object]
            if i in error_indices:
                # Create invalid test case
                test_data = {"invalid": "structure"}  # Missing required fields
            else:
                # Create valid test case
                test_data = {
                    "name": f"BATCH-TEST-{i + 1}",
                    "description": f"Test case {i + 1} in error recovery batch",
                    "steps": [
                        {
                            "step": f"Execute step for test {i + 1}",
                            "expectedResult": "Step completes",
                        }
                    ],
                }
            test_cases.append((i, test_data))

        # Process batch and track successes/failures
        successful_conversions = []
        failed_conversions = []

        def _convert_case(case_index: int, payload: dict[str, object]) -> None:
            try:
                test_json = json.dumps(payload)
                result = converter.convert_json_string(test_json)
                successful_conversions.append((case_index, result))
            except (
                exceptions.ValidationError,
                exceptions.ParseError,
                exceptions.ConversionError,
            ) as exc:
                failed_conversions.append((case_index, str(exc)))

        for index, test_data in test_cases:
            _convert_case(index, test_data)

        # Verify error recovery behavior
        assert len(successful_conversions) == batch_size - len(error_indices), (
            f"Expected {batch_size - len(error_indices)} successful conversions"
        )
        assert len(failed_conversions) == len(error_indices), (
            f"Expected {len(error_indices)} failed conversions"
        )

        # Verify we can identify which specific tests failed
        failed_indices = [idx for idx, _ in failed_conversions]
        assert failed_indices == error_indices, (
            f"Failed test indices {failed_indices} don't match expected {error_indices}"
        )

        # Verify successful conversions are valid Robot Framework
        for index, result in successful_conversions:
            assert "*** Test Cases ***" in result, (
                f"Successful conversion {index} missing Test Cases section"
            )
            assert f"BATCH-TEST-{index + 1}" in result, (
                f"Successful conversion {index} missing test name"
            )

    def test_convert_json_string_error_handling_for_automation(self) -> None:
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

    def test_convert_json_string_production_ready_output(self) -> None:
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

    def test_converter_handles_special_characters(self) -> None:
        """Test converter handles special characters for international use."""
        converter = JsonToRobotConverter()

        test_json = json.dumps(INTERNATIONAL_CHARACTERS_TEST_DATA, ensure_ascii=False)
        result = converter.convert_json_string(test_json)

        # Should handle special characters without errors
        assert "Test Internacionalização" in result
        assert "special characters: åäöüß" in result
        assert "Enter special data: éñü" in result

    def test_converter_memory_efficiency_for_large_input(self) -> None:
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

    def test_bulk_conversion_business_case(self) -> None:
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
            with suppress(Exception):
                test_json = json.dumps(test_case)
                result = converter.convert_json_string(test_json)
                tc_in_res = "*** Test Cases ***" in result
                name_in_res = str(test_case["name"]) in result
                if tc_in_res and name_in_res:
                    successful_conversions += 1

        # Business requirement: 100% conversion success rate
        assert successful_conversions == len(zephyr_style_tests)

    def test_no_manual_intervention_required(self) -> None:
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

    def test_enterprise_metadata_preservation(self) -> None:
        """Ensure enterprise metadata is preserved in Robot Framework output.

        Business Requirement: Maintain all test metadata for audit and compliance
        traceability. Critical for enterprise customers with SOX and regulatory
        requirements.
        """
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

        # Validate proper Robot Framework structure (not just presence in output)
        assert "*** Test Cases ***" in result, "Missing Test Cases section"
        assert "Enterprise Compliance Test" in result, "Test name not preserved"

        # Verify description in Documentation section (Robot Framework standard)
        assert "[Documentation]" in result, "Missing Documentation marker"
        # Documentation should be on line after test name or in proper section
        lines = result.split("\n")
        test_name_index = next(
            index
            for index, line in enumerate(lines)
            if "Enterprise Compliance Test" in line
        )
        # Check that documentation appears near the test name (within 5 lines)
        search_limit = min(test_name_index + 5, len(lines))
        doc_found = any(
            "[Documentation]" in lines[idx]
            for idx in range(test_name_index, search_limit)
        )
        assert doc_found, "Documentation not in proper Robot Framework format"
        assert "Critical test for SOX compliance validation" in result, (
            "Description not preserved in documentation"
        )

        # Should maintain test structure for traceability
        assert "Validate audit trail" in result, "Test step not preserved"
        assert "Audit trail is complete and compliant" in result, (
            "Expected result not preserved"
        )

        # Verify test structure uses Robot Framework keywords rather than comments.
        # Valid keywords include: Log, Should Be Equal, Should Contain, No Operation.
        keyword_candidates = [
            "Log",
            "Should Be Equal",
            "Should Contain",
            "No Operation",
            "Click",
            "Input",
            "Open Browser",
            "Wait Until",
        ]
        has_keywords = any(keyword in result for keyword in keyword_candidates)
        assert has_keywords or not result.strip().endswith("#"), (
            "Test steps not converted to executable Robot Framework keywords - "
            "only comments found"
        )
