"""Shared fixtures for format detection tests.

This module provides reusable test fixtures and data generators for format detection
testing across different test modules. It follows TDD principles by providing
well-structured, parameterized test data that covers various scenarios.

Fixtures are organized by format type and complexity level to enable efficient
testing across different test suites while maintaining consistency.
"""

from __future__ import annotations

from typing import Any

import pytest

from importobot.medallion.interfaces.enums import SupportedFormat
from tests.business_requirements import (
    MIN_FORMAT_CONFIDENCE_HIGH_QUALITY,
    MIN_FORMAT_CONFIDENCE_STANDARD,
    MIN_GENERIC_FORMAT_CONFIDENCE,
)
from tests.shared_test_data_bronze import (
    COMMON_TEST_CASE_STRUCTURE,
    COMMON_TEST_SUITE_STRUCTURE,
)


class FormatTestDataGenerator:
    """Generates test data for various formats with configurable complexity."""

    @staticmethod
    def create_zephyr_test_case(  # pylint: disable=too-many-positional-arguments
        test_key: str = "TEST-123",
        name: str = "Sample Test Case",
        priority: str = "Medium",
        component: str = "General",
        steps_count: int = 3,
        with_execution: bool = True,
        with_cycle: bool = True,
    ) -> dict[str, Any]:
        """Create a Zephyr test case with configurable parameters."""
        test_case = {
            "key": test_key,
            "name": name,
            "testCaseKey": test_key,
            "priority": priority,
            "component": component,
            "steps": [
                {
                    "stepDescription": f"Test step {i + 1}",
                    "expectedResult": f"Expected result {i + 1}",
                    "stepNumber": i + 1,
                }
                for i in range(steps_count)
            ],
        }

        data = {"testCase": test_case}

        if with_execution:
            data["execution"] = {
                "status": "PASSED",
                "executedOn": "2024-01-15T10:30:00Z",
                "executedBy": "tester@company.com",
                "executionId": f"EXEC-{test_key.split('-')[1]}",
                "cycleId": "CYCLE-001",
            }

        if with_cycle:
            data["cycle"] = {
                "name": "Test Cycle",
                "cycleId": "CYCLE-001",
                "environment": "Testing",
                "version": "1.0",
            }

        return data

    @staticmethod
    def create_testlink_test_suite(
        suite_name: str = "Test Suite",
        test_cases_count: int = 3,
        with_execution_results: bool = False,
    ) -> dict[str, Any]:
        """Create a TestLink test suite with configurable parameters."""
        test_cases = []
        for i in range(test_cases_count):
            test_case = {
                "name": f"Test Case {i + 1}",
                "summary": f"Test case {i + 1} summary",
                **COMMON_TEST_CASE_STRUCTURE,
            }
            if with_execution_results:
                test_case.update(
                    {
                        "status": "passed" if i % 2 == 0 else "failed",
                        "time": f"{30 + i * 10}.2",
                        "testcaseid": str(i + 1),
                        "priority": "Medium" if i % 2 == 0 else "High",
                        "execution_type": "Automated",
                    }
                )
            test_cases.append(test_case)

        testsuite = {
            "name": suite_name,
            "details": f"Test suite {suite_name} details",
            "testsuiteid": "1",
            "testcase": test_cases,
            **COMMON_TEST_SUITE_STRUCTURE,
        }

        return {"testsuites": {"testsuite": testsuite}}

    @staticmethod
    def create_jira_xray_issue(
        issue_key: str = "XRT-123",
        summary: str = "Test Issue",
        priority: str = "Medium",
        labels: list[str] | None = None,
        with_executions: bool = True,
    ) -> dict[str, Any]:
        """Create a JIRA/Xray issue with configurable parameters."""
        if labels is None:
            labels = ["test", "automation"]

        issue = {
            "key": issue_key,
            "fields": {
                "summary": summary,
                "description": f"Test description for {issue_key}",
                "issuetype": {
                    "name": "Test",
                    "iconUrl": "https://company.atlassian.net/images/test.png",
                },
                "priority": {"name": priority},
                "status": {"name": "Ready for Testing"},
                "labels": labels,
            },
        }

        data = {
            "expand": "renderedFields,names,schema",
            "issues": [issue],
            "maxResults": 50,
            "total": 1,
        }

        if with_executions:
            data["testExecutions"] = [
                {
                    "executionId": f"EXEC-{issue_key.split('-')[1]}",
                    "testKey": issue_key,
                    "status": "PASS",
                    "executedBy": "tester@company.com",
                    "executionDate": "2024-01-15T10:30:00Z",
                }
            ]

        return data

    @staticmethod
    def create_testrail_data(
        runs_count: int = 1,
        tests_count: int = 3,
        cases_count: int = 3,
    ) -> dict[str, Any]:
        """Create TestRail data with configurable parameters."""
        runs = []
        for i in range(runs_count):
            runs.append(
                {
                    "id": 100 + i,
                    "suite_id": 1,
                    "name": f"Test Run {i + 1}",
                    "description": f"Test run {i + 1} description",
                    "milestone_id": 1,
                    "assignedto_id": 1,
                    "include_all": True,
                    "is_completed": False,
                    "created_on": 1640995200 + i * 3600,
                    "created_by": 1,
                }
            )

        tests = []
        for i in range(tests_count):
            tests.append(
                {
                    "id": 200 + i,
                    "case_id": 300 + (i % cases_count),
                    "status_id": 1 if i % 5 != 0 else 5,
                    "title": f"Test Execution {i + 1}",
                    "run_id": runs[0]["id"],
                    "assignedto_id": 1,
                    "created_on": 1640995200 + i * 60,
                    "comment": f"Execution comments for test {i + 1}",
                    "estimate": f"{30 + i * 5}m",
                }
            )

        cases = []
        for i in range(cases_count):
            cases.append(
                {
                    "id": 300 + i,
                    "title": f"Test Case {i + 1}",
                    "section_id": 1,
                    "template_id": 1,
                    "type_id": 3,
                    "priority_id": i % 4 + 1,
                    "milestone_id": 1,
                    "refs": f"REQ-{i + 100}",
                    "custom_steps_separated": [
                        {
                            "content": f"Test step {j + 1} for case {i + 1}",
                            "expected": f"Expected result {j + 1}",
                        }
                        for j in range(i % 3 + 2)
                    ],
                    "estimate": f"{30 + i * 10}m",
                }
            )

        return {
            "runs": runs,
            "tests": tests,
            "cases": cases,
            "project_id": 1,
            "suite_id": 1,
        }

    @staticmethod
    def create_generic_test_data(
        structure_type: str = "simple",
        test_count: int = 3,
    ) -> dict[str, Any]:
        """Create generic test data with various structures."""
        if structure_type == "simple":
            return {
                "tests": [
                    {
                        "name": f"Test {i + 1}",
                        "description": f"Test case {i + 1} description",
                        "steps": [
                            {"action": f"Step {j + 1}", "expected": f"Result {j + 1}"}
                            for j in range(2)
                        ],
                    }
                    for i in range(test_count)
                ]
            }
        if structure_type == "test_cases":
            return {
                "test_cases": [
                    {
                        "id": f"TC{i + 1:03d}",
                        "title": f"Test Case {i + 1}",
                        "procedure": f"Test procedure {i + 1}",
                        "expected_result": f"Expected outcome {i + 1}",
                    }
                    for i in range(test_count)
                ]
            }
        if structure_type == "testcases":
            return {
                "testcases": {
                    "suite": "Test Suite",
                    "cases": [
                        {
                            "name": f"Test {i + 1}",
                            "steps": [f"Step {j + 1}" for j in range(3)],
                        }
                        for i in range(test_count)
                    ],
                }
            }
        raise ValueError(f"Unknown structure type: {structure_type}")


class FormatTestScenarios:
    """Predefined test scenarios covering various edge cases and typical use cases."""

    @staticmethod
    def get_minimal_format_examples() -> dict[SupportedFormat, dict[str, Any]]:
        """Get minimal valid examples for each format."""
        return {
            SupportedFormat.ZEPHYR: FormatTestDataGenerator.create_zephyr_test_case(
                steps_count=1, with_execution=False, with_cycle=False
            ),
            SupportedFormat.TESTLINK: (
                FormatTestDataGenerator.create_testlink_test_suite(
                    test_cases_count=1, with_execution_results=False
                )
            ),
            SupportedFormat.JIRA_XRAY: FormatTestDataGenerator.create_jira_xray_issue(
                with_executions=False
            ),
            SupportedFormat.TESTRAIL: FormatTestDataGenerator.create_testrail_data(
                runs_count=1, tests_count=1, cases_count=1
            ),
            SupportedFormat.GENERIC: FormatTestDataGenerator.create_generic_test_data(
                structure_type="simple", test_count=1
            ),
        }

    @staticmethod
    def get_standard_format_examples() -> dict[SupportedFormat, dict[str, Any]]:
        """Get standard examples for each format with typical complexity."""
        return {
            SupportedFormat.ZEPHYR: FormatTestDataGenerator.create_zephyr_test_case(
                steps_count=5, with_execution=True, with_cycle=True
            ),
            SupportedFormat.TESTLINK: (
                FormatTestDataGenerator.create_testlink_test_suite(
                    test_cases_count=5, with_execution_results=True
                )
            ),
            SupportedFormat.JIRA_XRAY: FormatTestDataGenerator.create_jira_xray_issue(
                labels=["test", "automation", "regression"], with_executions=True
            ),
            SupportedFormat.TESTRAIL: FormatTestDataGenerator.create_testrail_data(
                runs_count=2, tests_count=10, cases_count=5
            ),
            SupportedFormat.GENERIC: FormatTestDataGenerator.create_generic_test_data(
                structure_type="test_cases", test_count=5
            ),
        }

    @staticmethod
    def get_complex_format_examples() -> dict[SupportedFormat, dict[str, Any]]:
        """Get complex examples for each format with maximum features."""
        return {
            SupportedFormat.ZEPHYR: FormatTestDataGenerator.create_zephyr_test_case(
                test_key="PROJ-456",
                name="Complex API Integration Test",
                priority="High",
                component="Authentication",
                steps_count=10,
                with_execution=True,
                with_cycle=True,
            ),
            SupportedFormat.TESTLINK: (
                FormatTestDataGenerator.create_testlink_test_suite(
                    suite_name="Complex Test Suite",
                    test_cases_count=20,
                    with_execution_results=True,
                )
            ),
            SupportedFormat.JIRA_XRAY: FormatTestDataGenerator.create_jira_xray_issue(
                issue_key="XRT-789",
                summary="Complex Test Execution Set",
                priority="High",
                labels=["test", "automation", "regression", "api", "integration"],
                with_executions=True,
            ),
            SupportedFormat.TESTRAIL: FormatTestDataGenerator.create_testrail_data(
                runs_count=5, tests_count=50, cases_count=25
            ),
            SupportedFormat.GENERIC: FormatTestDataGenerator.create_generic_test_data(
                structure_type="testcases", test_count=20
            ),
        }

    @staticmethod
    def get_ambiguous_examples() -> list[dict[str, Any]]:
        """Get examples that could match multiple formats."""
        return [
            # Could be Zephyr or JIRA/Xray
            {"key": "TEST-123", "status": "passed", "execution": {}},
            # Could be TestLink or Generic
            {"testsuite": {"name": "Test"}, "tests": "5"},
            # Could be any format
            {"test": "ambiguous", "case": "example", "data": "unclear format"},
            # Empty but valid
            {},
            # Non-test data
            {
                "user": {"name": "John", "email": "john@test.com"},
                "settings": {"theme": "dark", "language": "en"},
            },
        ]

    @staticmethod
    def get_malformed_examples() -> list[Any]:
        """Get malformed examples that should be handled gracefully."""
        return [
            None,
            [],
            "string instead of dict",
            {
                "deeply": {
                    "nested": {
                        "structure": {"that": {"goes": {"very": {"deep": "value"}}}}
                    }
                }
            },
            {str(i): f"value_{i}" for i in range(1000)},  # Very large dict
            {"": ""},  # Empty key
            {"null": None},  # Null value
            {"empty_list": [], "empty_dict": {}},  # Empty structures
        ]


class ConfidenceTestScenarios:
    """Test scenarios specifically for confidence scoring validation."""

    @staticmethod
    def get_perfect_evidence_scenarios() -> dict[str, Any]:
        """Get scenarios with perfect evidence that should produce high confidence."""
        return {
            "zephyr_perfect": FormatTestDataGenerator.create_zephyr_test_case(
                test_key="PERFECT-001",
                name="Perfect Evidence Test",
                priority="High",
                component="Core",
                steps_count=20,
                with_execution=True,
                with_cycle=True,
            ),
            "testlink_perfect": FormatTestDataGenerator.create_testlink_test_suite(
                suite_name="Perfect Evidence Suite",
                test_cases_count=50,
                with_execution_results=True,
            ),
            "xray_perfect": FormatTestDataGenerator.create_jira_xray_issue(
                issue_key="PERFECT-001",
                summary="Perfect Evidence Test",
                priority="Highest",
                labels=["test", "automation", "critical", "regression", "smoke"],
                with_executions=True,
            ),
        }

    @staticmethod
    def get_zero_evidence_scenarios() -> dict[str, Any]:
        """Get scenarios with no evidence that should produce very low confidence."""
        return {
            "empty_dict": {},
            "null_structure": {"testCase": None, "execution": None},
            "empty_arrays": {
                "testCase": {"steps": [], "customFields": []},
                "execution": {"history": []},
                "cycle": {},
            },
            "minimal_no_indicators": {"data": "no format indicators"},
        }

    @staticmethod
    def get_weak_evidence_scenarios() -> dict[str, Any]:
        """Get scenarios with weak evidence that should produce moderate confidence."""
        return {
            "zephyr_weak": FormatTestDataGenerator.create_zephyr_test_case(
                steps_count=1, with_execution=False, with_cycle=False
            ),
            "testlink_weak": FormatTestDataGenerator.create_testlink_test_suite(
                test_cases_count=1, with_execution_results=False
            ),
            "generic_weak": FormatTestDataGenerator.create_generic_test_data(
                structure_type="simple", test_count=1
            ),
        }


# Pytest fixtures
@pytest.fixture
def format_test_generator():
    """Fixture providing access to FormatTestDataGenerator."""
    return FormatTestDataGenerator()


@pytest.fixture
def format_test_scenarios():
    """Fixture providing access to FormatTestScenarios."""
    return FormatTestScenarios()


@pytest.fixture
def confidence_test_scenarios():
    """Fixture providing access to ConfidenceTestScenarios."""
    return ConfidenceTestScenarios()


@pytest.fixture(
    params=[
        SupportedFormat.ZEPHYR,
        SupportedFormat.TESTLINK,
        SupportedFormat.JIRA_XRAY,
        SupportedFormat.TESTRAIL,
        SupportedFormat.GENERIC,
    ]
)
def all_supported_formats(request):
    """Parametrized fixture providing all supported formats."""
    return request.param


@pytest.fixture(params=["minimal", "standard", "complex"])
def format_complexity_levels(request):
    """Parametrized fixture providing different complexity levels."""
    return request.param


@pytest.fixture
def minimal_format_examples(format_test_scenarios):
    """Fixture providing minimal examples for all formats."""
    return format_test_scenarios.get_minimal_format_examples()


@pytest.fixture
def standard_format_examples(format_test_scenarios):
    """Fixture providing standard examples for all formats."""
    return format_test_scenarios.get_standard_format_examples()


@pytest.fixture
def complex_format_examples(format_test_scenarios):
    """Fixture providing complex examples for all formats."""
    return format_test_scenarios.get_complex_format_examples()


@pytest.fixture
def ambiguous_examples(format_test_scenarios):
    """Fixture providing ambiguous test data examples."""
    return format_test_scenarios.get_ambiguous_examples()


@pytest.fixture
def malformed_examples(format_test_scenarios):
    """Fixture providing malformed test data examples."""
    return format_test_scenarios.get_malformed_examples()


@pytest.fixture
def perfect_evidence_scenarios(confidence_test_scenarios):
    """Fixture providing perfect evidence scenarios."""
    return confidence_test_scenarios.get_perfect_evidence_scenarios()


@pytest.fixture
def zero_evidence_scenarios(confidence_test_scenarios):
    """Fixture providing zero evidence scenarios."""
    return confidence_test_scenarios.get_zero_evidence_scenarios()


@pytest.fixture
def weak_evidence_scenarios(confidence_test_scenarios):
    """Fixture providing weak evidence scenarios."""
    return confidence_test_scenarios.get_weak_evidence_scenarios()


# Performance test fixtures
@pytest.fixture
def performance_dataset_sizes():
    """Fixture providing different dataset sizes for performance testing."""
    return {
        "small": {"test_cases": 1, "steps": 5},
        "medium": {"test_cases": 5, "steps": 20},
        "large": {"test_cases": 10, "steps": 50},
        "very_large": {"test_cases": 20, "steps": 100},
    }


@pytest.fixture
def confidence_thresholds():
    """Fixture providing confidence thresholds for testing."""
    return {
        "standard": MIN_FORMAT_CONFIDENCE_STANDARD,
        "high_quality": MIN_FORMAT_CONFIDENCE_HIGH_QUALITY,
        "generic": MIN_GENERIC_FORMAT_CONFIDENCE,
    }


# Helper functions for test data validation
def validate_format_detection_result(
    detected_format: SupportedFormat,
    expected_format: SupportedFormat,
    confidence: float,
    min_confidence: float = MIN_FORMAT_CONFIDENCE_STANDARD,
) -> tuple[bool, str]:
    """Validate format detection results and return (is_valid, error_message)."""
    if detected_format != expected_format:
        return False, f"Expected {expected_format}, got {detected_format}"

    if confidence < min_confidence:
        return False, f"Confidence {confidence:.3f} below threshold {min_confidence}"

    return True, "Validation passed"


def validate_confidence_bounds(confidence: float) -> tuple[bool, str]:
    """Validate that confidence is within valid bounds."""
    if not 0.0 <= confidence <= 1.0:
        return False, f"Confidence {confidence:.3f} outside valid range [0.0, 1.0]"

    return True, "Confidence bounds valid"


def validate_performance_metrics(
    detection_time: float,
    max_allowed_time: float,
    memory_usage: float | None = None,
    max_allowed_memory: float | None = None,
) -> tuple[bool, list[str]]:
    """Validate performance metrics and return (is_valid, error_messages)."""
    errors = []

    if detection_time > max_allowed_time:
        errors.append(
            f"Detection time {detection_time:.3f}s "
            f"exceeds limit {max_allowed_time:.3f}s"
        )

    if memory_usage is not None and max_allowed_memory is not None:
        if memory_usage > max_allowed_memory:
            errors.append(
                f"Memory usage {memory_usage:.1f}MB "
                f"exceeds limit {max_allowed_memory:.1f}MB"
            )

    return len(errors) == 0, errors
