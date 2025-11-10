"""Test case field validation and improvement suggestions."""

from typing import Any

from importobot.core.constants import (
    STEP_DESCRIPTION_FIELD_NAMES,
    STEPS_FIELD_NAME,
)
from importobot.core.field_definitions import (
    TEST_DESCRIPTION_FIELDS,
    TEST_NAME_FIELDS,
    TEST_SCRIPT_FIELDS,
    has_field,
)
from importobot.utils.logging import get_logger

logger = get_logger()


class FieldValidator:
    """Validate and suggest improvements for test case fields."""

    def check_test_case_fields(
        self, test_case: dict[str, Any], case_num: int, suggestions: list[str]
    ) -> None:
        """Check if test case has required fields."""
        # Check for test case name using field definitions
        if not has_field(test_case, TEST_NAME_FIELDS):
            suggestions.append(f"Test case {case_num}: Add test case name")

        # Check for description using field definitions
        if not has_field(test_case, TEST_DESCRIPTION_FIELDS):
            suggestions.append(f"Test case {case_num}: Add test case description")

        # Check for test steps using field definitions
        if not self._get_steps(test_case):
            suggestions.append(f"Test case {case_num}: Add test steps")

    def add_default_name(
        self,
        test_case: dict[str, Any],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Add a default name to test case if missing."""
        if not has_field(test_case, TEST_NAME_FIELDS):
            name_field, original_name = TEST_NAME_FIELDS.find_first(test_case)
            if not name_field:
                name_field = "name"
                original_name = ""

            default_name = f"Test Case {test_index + 1}"

            # Try to infer name from description using field definitions
            desc_field, desc_value = TEST_DESCRIPTION_FIELDS.find_first(test_case)
            if desc_field and desc_value:
                desc = str(desc_value)[:50]  # First 50 chars
                default_name = f"Test: {desc}"
            else:
                # Try to get from first step
                steps = self._get_steps(test_case)
                if steps:
                    first_step = steps[0]
                    for field_name in STEP_DESCRIPTION_FIELD_NAMES:
                        if field_name in first_step:
                            action = str(first_step[field_name])[:30]
                            default_name = f"Test: {action}"
                            break

            test_case[name_field] = default_name
            changes_made.append(
                {
                    "type": "field_added",
                    "location": f"test_case_{test_index}",
                    "test_case_index": test_index,
                    "field": name_field,
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
        if not has_field(test_case, TEST_DESCRIPTION_FIELDS):
            desc_field, original_desc = TEST_DESCRIPTION_FIELDS.find_first(test_case)
            if not desc_field:
                desc_field = "description"
                original_desc = ""

            default_desc = "Test case description"

            # Try to infer description from name using field definitions
            name_field, name_value = TEST_NAME_FIELDS.find_first(test_case)
            if name_field and name_value:
                default_desc = f"Description for {name_value}"
            else:
                # Try to infer from steps count
                steps = self._get_steps(test_case)
                if steps:
                    step_count = len(steps)
                    step_suffix = "s" if step_count != 1 else ""
                    default_desc = f"Test case with {step_count} step{step_suffix}"

            test_case[desc_field] = default_desc
            changes_made.append(
                {
                    "type": "field_added",
                    "location": f"test_case_{test_index}",
                    "test_case_index": test_index,
                    "field": desc_field,
                    "original": original_desc,
                    "improved": default_desc,
                    "reason": "Added default test case description",
                }
            )

    @staticmethod
    def _get_steps(test_case: dict[str, Any]) -> list[dict[str, Any]]:
        """Return a normalized list of steps for a test case."""
        script_field, script_data = TEST_SCRIPT_FIELDS.find_first(test_case)
        if not script_field or not isinstance(script_data, dict):
            return []

        steps = script_data.get(STEPS_FIELD_NAME, [])
        if not isinstance(steps, list):
            return []

        return [step for step in steps if isinstance(step, dict)]
