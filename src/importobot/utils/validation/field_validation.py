"""Test case field validation and improvement suggestions."""

from typing import Any

from importobot.core.constants import STEP_DESCRIPTION_FIELD_NAMES
from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)


class FieldValidator:
    """Validates and suggests improvements for test case fields.

    Consolidated from the original core/suggestions/field_validator.py
    to provide centralized field validation capabilities.
    """

    def check_test_case_fields(
        self, test_case: dict[str, Any], case_num: int, suggestions: list[str]
    ) -> None:
        """Check if test case has required fields."""
        # Check for test case name
        if "name" not in test_case or not test_case["name"]:
            suggestions.append(f"Test case {case_num}: Add test case name")

        # Check for description
        if "description" not in test_case or not test_case["description"]:
            suggestions.append(f"Test case {case_num}: Add test case description")

        # Check for test steps
        has_steps = False
        if "testScript" in test_case and "steps" in test_case["testScript"]:
            steps = test_case["testScript"]["steps"]
            if isinstance(steps, list) and steps:
                has_steps = True

        if not has_steps:
            suggestions.append(f"Test case {case_num}: Add test steps")

    def add_default_name(
        self,
        test_case: dict[str, Any],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Add a default name to test case if missing."""
        if "name" not in test_case or not test_case["name"]:
            original_name = test_case.get("name", "")
            default_name = f"Test Case {test_index + 1}"

            # Try to infer name from description or steps
            if "description" in test_case and test_case["description"]:
                desc = test_case["description"][:50]  # First 50 chars
                default_name = f"Test: {desc}"
            elif "testScript" in test_case and "steps" in test_case["testScript"]:
                steps = test_case["testScript"]["steps"]
                if steps and isinstance(steps[0], dict):
                    # Try to get action from first step
                    for field_name in STEP_DESCRIPTION_FIELD_NAMES:
                        if field_name in steps[0]:
                            action = str(steps[0][field_name])[:30]
                            default_name = f"Test: {action}"
                            break

            test_case["name"] = default_name
            changes_made.append(
                {
                    "type": "field_added",
                    "location": f"test_case_{test_index}",
                    "test_case_index": test_index,
                    "field": "name",
                    "original": original_name,
                    "improved": default_name,
                    "reason": "Added default test case name",
                }
            )

    def add_default_description(
        self,
        test_case: dict[str, Any],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Add a default description to test case if missing."""
        if "description" not in test_case or not test_case["description"]:
            original_desc = test_case.get("description", "")
            default_desc = "Test case description"

            # Try to infer description from name or steps
            if "name" in test_case and test_case["name"]:
                default_desc = f"Description for {test_case['name']}"
            elif "testScript" in test_case and "steps" in test_case["testScript"]:
                steps = test_case["testScript"]["steps"]
                if steps:
                    step_count = len(steps)
                    step_suffix = "s" if step_count != 1 else ""
                    default_desc = f"Test case with {step_count} step{step_suffix}"

            test_case["description"] = default_desc
            changes_made.append(
                {
                    "type": "field_added",
                    "location": f"test_case_{test_index}",
                    "test_case_index": test_index,
                    "field": "description",
                    "original": original_desc,
                    "improved": default_desc,
                    "reason": "Added default test case description",
                }
            )
