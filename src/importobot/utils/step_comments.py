"""Shared utilities for generating step comments in keyword generators."""

from typing import Any

from importobot.core.constants import EXPECTED_RESULT_FIELD_NAMES, TEST_DATA_FIELD_NAMES
from importobot.utils.field_extraction import extract_field


def generate_step_comments(step: dict[str, Any]) -> list[str]:
    """Generate standardized comments for a test step.

    Args:
        step: Test step dictionary

    Returns:
        List of comment lines for the step
    """
    lines = []

    # Extract step information
    description = extract_field(step, ["step", "description", "action", "instruction"])
    test_data = _get_test_data_fields(step)
    expected = _get_expected_result_fields(step)

    # Add traceability comments
    if description:
        lines.append(f"# Step: {description}")
    if test_data:
        lines.append(f"# Test Data: {test_data}")
    if expected:
        lines.append(f"# Expected Result: {expected}")

    return lines


def _get_test_data_fields(step: dict[str, Any]) -> str:
    """Extract test data from step fields."""
    return extract_field(step, TEST_DATA_FIELD_NAMES)


def _get_expected_result_fields(step: dict[str, Any]) -> str:
    """Extract expected result from step fields."""
    return extract_field(step, EXPECTED_RESULT_FIELD_NAMES)
