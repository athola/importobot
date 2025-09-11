"""JSON parsing functionality."""

import io
import json
from typing import Any, Dict, List

from ..utils.validation import sanitize_robot_string, validate_json_size
from .step_generators import (
    generate_browser_setup_lines,
    generate_web_step_keyword,
    needs_ssh_library_optimized,
)


def _build_settings_section(json_data: Dict[str, Any]) -> List[str]:
    """Build the Robot Framework settings section."""
    lines = [
        "*** Settings ***",
        "Documentation    Tests converted from JSON",
        "Library    SeleniumLibrary",
    ]

    # Add SSHLibrary only if SSH-related keywords are detected
    if _needs_ssh_library(json_data):
        lines.append("Library    SSHLibrary")

    return lines


def _needs_ssh_library(json_data: Dict[str, Any]) -> bool:
    """Detect if SSH library is needed based on content analysis."""
    return needs_ssh_library_optimized(json_data)


def _extract_tests(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract test cases from JSON data with robust error handling."""
    if not json_data:
        return []

    try:
        tests = json_data.get("tests")
        if not isinstance(tests, list):
            if "name" in json_data and isinstance(json_data, dict):
                # Handle Zephyr-style single test case if json_data is a dict
                return [json_data]
            # Return empty list if 'tests' is not a list and not a single
            # Zephyr-style test
            return []
        return tests
    except (AttributeError, TypeError) as e:
        # Handle cases where json_data might not be a dict or have get method
        raise ValueError(f"Invalid JSON data structure for test extraction: {e}") from e


def _generate_ssh_steps(steps: List[Dict[str, Any]]) -> List[str]:
    """Generate Robot Framework steps for SSH test cases with error handling."""
    if not isinstance(steps, list):
        return [
            "    # Invalid steps data: expected list, got " + type(steps).__name__,
            "    No Operation  # TODO: Fix step data"
        ]

    lines = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            lines.extend([
                (
                    f"    # Step {i+1}: Invalid step format "
                    f"(expected dict, got {type(step).__name__})"
                ),
                "    No Operation  # TODO: Fix step format",
                "",
            ])
            continue

        try:
            action = step.get("description", "No action specified")
            test_data = step.get("testData", "N/A")
            expected = step.get("expectedResult", "")

            # Use centralized sanitization
            action = sanitize_robot_string(action)
            test_data = sanitize_robot_string(test_data)
            expected = sanitize_robot_string(expected)

            lines.extend([
                f"    # Description: {action}",
                f"    # Action: {test_data}",
                f"    # Expected: {expected}",
                "    No Operation  # TODO: Implement step",
                "",
            ])
        except Exception as e:
            lines.extend([
                f"    # Step {i+1}: Error processing step data: {e}",
                "    No Operation  # TODO: Fix step processing error",
                "",
            ])
    return lines


# This function is now handled by the step_generators module
# Keeping a wrapper for backward compatibility
def _generate_web_step_keyword(
    action: Any, expected: str, test_data: str
) -> tuple[List[str], bool]:
    """Generate Robot Framework keyword for a web test step."""
    return generate_web_step_keyword(action, expected, test_data)


def _should_add_browser_setup(steps: Any) -> bool:
    """Check if browser setup/teardown should be added."""
    if not isinstance(steps, list):
        return False
    return any(
        isinstance(step, dict) and "navigate to" in step.get("description", "").lower()
        for step in steps
    )


def _generate_web_steps(steps: Any) -> List[str]:
    """Generate Robot Framework steps for web test cases."""
    lines = []

    if not isinstance(steps, list):
        lines.append("    # Invalid steps data provided")
        return lines

    # Open browser at the start of the test
    if _should_add_browser_setup(steps):
        lines.extend(generate_browser_setup_lines())

    for step in steps:
        if not isinstance(step, dict):
            lines.append("    # Invalid step format, skipping")
            continue

        action = step.get("action", step.get("description", "No action specified"))
        expected = step.get("expectedResult", "")
        test_data = step.get("testData", "")

        # Sanitize all output strings
        action = sanitize_robot_string(action)
        expected = sanitize_robot_string(expected)
        test_data = sanitize_robot_string(test_data)

        lines.extend([
            f"    # Description: {action}",
        ])
        if test_data and test_data != "N/A":
            lines.append(f"    # Action: {test_data}")
        lines.append(f"    # Expected: {expected}")

        keyword_lines, keyword_generated = _generate_web_step_keyword(
            action, expected, test_data
        )
        lines.extend(keyword_lines)

        if not keyword_generated:
            lines.append("    No Operation  # TODO: Implement step")
        lines.append("")

    # Close browser at the end of the test
    if _should_add_browser_setup(steps):
        lines.append("    Close Browser")

    return lines


def _generate_test_case(test_case_data: Any) -> List[str]:
    """Generate Robot Framework test case from JSON test case data."""
    lines = []
    if not isinstance(test_case_data, dict):
        return ["Invalid Test Case Data", "    No Operation", ""]

    test_name = test_case_data.get("name", "Unnamed Test")
    description = test_case_data.get("description", test_case_data.get("objective", ""))

    lines.append(f"{test_name}")
    if description and isinstance(description, str):
        lines.append(f"    [Documentation]    {description}")

    steps = test_case_data.get("steps")
    if "testScript" in test_case_data and isinstance(
        test_case_data["testScript"], dict
    ):
        script_steps = test_case_data["testScript"].get("steps")
        if isinstance(script_steps, list):
            if steps is None:
                steps = []
            steps.extend(script_steps)

    if not isinstance(steps, list) or not steps:
        lines.append("    No Operation  # Placeholder for missing or invalid steps")
    elif test_name == "Retrieve File From Remote Host":
        lines.extend(_generate_ssh_steps(steps))
    else:
        lines.extend(_generate_web_steps(steps))

    lines.append("")
    return lines


def parse_json(json_data: Dict[str, Any]) -> str:
    """Convert JSON data into the Robot Framework format."""
    if not isinstance(json_data, dict):
        raise TypeError("Input to parse_json must be a dictionary.")

    # Use StringIO for efficient string building
    output = io.StringIO()

    # Build settings section
    settings_lines = _build_settings_section(json_data)
    for line in settings_lines:
        output.write(line)
        output.write("\n")

    output.write("\n*** Test Cases ***\n\n")

    tests = _extract_tests(json_data)

    if not tests:
        output.write("Empty Test Case\n    No Operation\n\n")
    else:
        for test_case_data in tests:
            test_lines = _generate_test_case(test_case_data)
            for line in test_lines:
                output.write(line)
                output.write("\n")

    return output.getvalue()


def load_and_parse_json(json_string: str) -> str:
    """Load JSON string and convert to Robot Framework format."""
    if not isinstance(json_string, str):
        raise TypeError(f"Input must be a string, got {type(json_string).__name__}")

    if not json_string.strip():
        raise ValueError("Empty JSON string provided")

    # Validate JSON size to prevent memory exhaustion attacks
    validate_json_size(json_string)

    try:
        json_data = json.loads(json_string)
        return parse_json(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Malformed JSON input at line {e.lineno}, column {e.colno}: {e.msg}"
        ) from e
    except (TypeError, ValueError):
        # Re-raise our own validation errors
        raise
    except Exception as e:
        # Catch any unexpected errors during processing
        raise ValueError(f"Unexpected error processing JSON: {e}") from e
