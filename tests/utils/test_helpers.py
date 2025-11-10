"""Test utility functions."""

import subprocess
import time
from collections.abc import Callable
from typing import Any

try:  # pragma: no cover - optional dependency guard
    from robot.api import TestSuite as RobotTestSuite
except ImportError:  # pragma: no cover
    RobotTestSuite: Any = None  # type: ignore[no-redef]


def run_robot_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Execute a Robot Framework command and return the result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Do not raise exception on non-zero exit code
        )
    except FileNotFoundError as err:
        # This handles the case where 'robot' command is not found
        raise RuntimeError(
            "Robot Framework command not found. "
            "Make sure it is installed and in your PATH."
        ) from err
    return result


def parse_robot_file(file_path: str) -> list[dict[str, Any]]:
    """Parse a .robot file and extract test cases, keywords and their arguments."""
    if RobotTestSuite is None:  # pragma: no cover - dependency guard
        raise RuntimeError("Robot Framework is required to parse .robot files")

    suite = RobotTestSuite.from_file_system(file_path)
    result = []

    def _extract_keywords(test_or_suite: Any) -> list[dict[str, Any]]:
        """Recursively extract keywords from a test or suite."""
        keywords: list[dict[str, Any]] = []
        if hasattr(test_or_suite, "body"):
            keywords.extend(
                {
                    "keyword": item.name,
                    "args": [str(arg) for arg in item.args],
                }
                for item in test_or_suite.body
                if hasattr(item, "name") and item.name
            )
        return keywords

    for test in suite.tests:
        test_info = {"name": test.name, "keywords": _extract_keywords(test)}
        result.append(test_info)

    return result


def measure_performance(
    operation: Callable[[], Any],
    expected_result: Any,
    max_time: float = 5.0,
    error_message: str = "Operation should complete within time limit",
) -> float:
    """Measure performance of an operation and validate results.

    Args:
        operation: Function to measure
        expected_result: Expected result from operation
        max_time: Maximum allowed time in seconds
        error_message: Error message for time assertion

    Returns:
        Time taken for the operation
    """
    start_time = time.time()
    result = operation()
    detection_time = time.time() - start_time

    assert result == expected_result, f"Operation returned unexpected result: {result}"
    assert detection_time < max_time, error_message

    return detection_time


def create_test_case_base(
    test_id: int,
    title: str,
    *,
    section_id: int = 101,
    template_id: int = 1,
    type_id: int = 3,
    priority_id: int = 2,
    milestone_id: int = 789,
    refs: str = "REQ-123",
) -> dict[str, Any]:
    """Create a base test case structure with common fields.

    Args:
        test_id: Test case ID
        title: Test case title
        section_id: Section ID (default: 101)
        template_id: Template ID (default: 1)
        type_id: Type ID (default: 3 - Automated)
        priority_id: Priority ID (default: 2 - Medium)
        milestone_id: Milestone ID (default: 789)
        refs: References (default: "REQ-123")

    Returns:
        Base test case dictionary
    """
    return {
        "id": test_id,
        "title": title,
        "section_id": section_id,
        "template_id": template_id,
        "type_id": type_id,
        "priority_id": priority_id,
        "milestone_id": milestone_id,
        "refs": refs,
    }


def validate_test_script_structure(test_script: dict[str, Any]) -> None:
    """Validate the basic structure of a test script.

    Common validation logic extracted from multiple test files.
    """
    assert "type" in test_script
    assert test_script["type"] == "STEP_BY_STEP"
    assert "steps" in test_script
    assert isinstance(test_script["steps"], list)
    assert len(test_script["steps"]) > 0
