"""Shared utilities for processing test steps."""

from typing import Any

from importobot.core.constants import (
    EXPECTED_RESULT_FIELD_NAMES,
    STEP_DESCRIPTION_FIELD_NAMES,
    TEST_DATA_FIELD_NAMES,
)
from importobot.utils.field_extraction import extract_field


def combine_step_text(steps: list[dict[str, Any]]) -> str:
    """Convert steps to combined text for analysis.

    Args:
        steps: List of step dictionaries

    Returns:
        Combined lowercase text from all step values
    """
    combined_text = [
        value.lower()
        for step in steps
        for value in step.values()
        if isinstance(value, str)
    ]
    return " ".join(combined_text)


def extract_step_information(step: dict[str, Any]) -> tuple[str, str, str]:
    """Extract common step information for keyword generation.

    Args:
        step: Step dictionary containing test step information

    Returns:
        Tuple of (description, test_data, expected_result)
    """
    description = extract_field(step, ["step", "description", "action", "instruction"])
    test_data = extract_field(step, TEST_DATA_FIELD_NAMES)
    expected = extract_field(step, EXPECTED_RESULT_FIELD_NAMES)

    return description, test_data, expected


def format_step_comments(
    description: str, test_data: str, expected: str, indent_level: int = 0
) -> list[str]:
    """Format step comments with consistent structure.

    Args:
        description: Step description
        test_data: Test data content
        expected: Expected result
        indent_level: Number of spaces to indent (0 for no indent, 4 for step-level)

    Returns:
        List of formatted comment lines
    """
    lines = []
    indent = " " * indent_level if indent_level > 0 else ""

    if description:
        lines.append(f"{indent}# Step: {description}")
    if test_data:
        lines.append(f"{indent}# Test Data: {test_data}")
    if expected:
        lines.append(f"{indent}# Expected Result: {expected}")

    return lines


def collect_command_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect steps that contain command execution.

    Args:
        steps: List of step dictionaries

    Returns:
        List of steps containing command-related content
    """
    command_steps = []
    for step in steps:
        if isinstance(step, dict):
            # Look for command-related content in step data or description
            for field_name in TEST_DATA_FIELD_NAMES + STEP_DESCRIPTION_FIELD_NAMES:
                if field_name in step and isinstance(step[field_name], str):
                    content = step[field_name].lower()
                    # Check for command patterns
                    keywords = {
                        "command:",
                        "execute",
                        "run",
                        "hash",
                        "blake",
                        "sha",
                        "md5",
                        "checksum",
                        "sum",
                        "compare",
                        "diff",
                        "echo",
                        "cat",
                        "ls",
                        "curl",
                    }
                    if any(token in content for token in keywords):
                        command_steps.append(step)
                        break
    return command_steps
