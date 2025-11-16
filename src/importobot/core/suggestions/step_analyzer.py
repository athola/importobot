"""Step analysis and validation suggestions."""

import re
from typing import Any

from importobot.core.constants import (
    EXPECTED_RESULT_FIELD_NAMES,
    STEP_DESCRIPTION_FIELD_NAMES,
    STEPS_FIELD_NAME,
    TEST_DATA_FIELD_NAMES,
)
from importobot.core.field_definitions import TEST_SCRIPT_FIELDS
from importobot.utils.logging import get_logger
from importobot.utils.step_processing import collect_command_steps

logger = get_logger()


class StepAnalyzer:
    """Analyzes and suggests improvements for test steps."""

    def check_steps(
        self, steps: list[dict[str, Any]], case_num: int, suggestions: list[str]
    ) -> None:
        """Check individual steps for required fields and formatting."""
        if not steps:
            suggestions.append(
                f"Test case {case_num}: Add test steps to define actions"
            )
            return

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue

            self._check_step_fields(step, case_num, i + 1, suggestions)
            self._check_brace_matching(step, case_num, i + 1, suggestions)

    def check_step_ordering(
        self, steps: list[dict[str, Any]], case_num: int, suggestions: list[str]
    ) -> None:
        """Check if steps have proper sequential ordering."""
        if len(steps) < 2:
            return

        # Look for step index/number fields
        indices = []
        for step in steps:
            if isinstance(step, dict):
                for index_field in ["index", "step_number", "order", "sequence"]:
                    if index_field in step:
                        try:
                            index = int(step[index_field])
                            indices.append(index)
                        except (ValueError, TypeError):
                            continue

        if len(indices) < 2:
            return

        # Check if indices are sequential starting from 0 or 1
        expected_sequence_0 = list(range(len(indices)))  # [0, 1, 2, ...]
        expected_sequence_1 = list(range(1, len(indices) + 1))  # [1, 2, 3, ...]

        if indices not in (expected_sequence_0, expected_sequence_1):
            suggestions.append(
                f"Test case {case_num}: Step indices are not in sequential order: "
                f"{indices}. Consider reordering steps to follow sequence: "
                f"{expected_sequence_0} or {expected_sequence_1}"
            )

    def collect_command_steps(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Collect steps that contain command execution."""
        return collect_command_steps(steps)

    def improve_steps(
        self,
        test_case: dict[str, Any],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Improve step definitions and structure."""
        # Get or create test script structure using field definitions
        script_field, script_data = TEST_SCRIPT_FIELDS.find_first(test_case)
        if not script_field:
            script_field = "testScript"  # Use canonical name
            test_case[script_field] = {STEPS_FIELD_NAME: []}
            script_data = test_case[script_field]
        elif not isinstance(script_data, dict):
            script_data = {STEPS_FIELD_NAME: []}
            test_case[script_field] = script_data

        if STEPS_FIELD_NAME not in script_data:
            script_data[STEPS_FIELD_NAME] = []

        steps = script_data[STEPS_FIELD_NAME]
        if not steps:
            # Add a default step if none exist
            default_step = {
                "action": "Execute test action",
                "expectedResult": "Test completes successfully",
                "index": 1,
            }
            steps.append(default_step)
            changes_made.append(
                {
                    "type": "step_added",
                    "location": f"test_case_{test_index}_step_1",
                    "test_case_index": test_index,
                    "step_index": 1,
                    "field": "step",
                    "original": None,
                    "improved": default_step,
                    "reason": "Added default step structure",
                }
            )
            return

        # Improve existing steps
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                original_step = step.copy()
                improved = self._improve_single_step(step)
                if improved:
                    changes_made.append(
                        {
                            "type": "step_improved",
                            "location": f"test_case_{test_index}_step_{i + 1}",
                            "test_case_index": test_index,
                            "step_index": i + 1,
                            "field": "step",
                            "original": original_step,
                            "improved": step,
                            "reason": "Improved step structure and content",
                        }
                    )

    def _check_step_fields(
        self,
        step: dict[str, Any],
        case_num: int,
        step_num: int,
        suggestions: list[str],
    ) -> None:
        """Check if step has required fields."""
        # Check for action/description field
        has_action = any(field in step for field in STEP_DESCRIPTION_FIELD_NAMES)
        if not has_action:
            suggestions.append(
                f"Test case {case_num}, Step {step_num}: Add action description field"
            )

        # Check for expected result
        has_result = any(field in step for field in EXPECTED_RESULT_FIELD_NAMES)
        if not has_result:
            suggestions.append(
                f"Test case {case_num}, Step {step_num}: Add expected result field"
            )

        # Check for test data
        has_data = any(field in step for field in TEST_DATA_FIELD_NAMES)
        if not has_data:
            suggestions.append(
                f"Test case {case_num}, Step {step_num}: Add test data field"
            )

    def _check_brace_matching(
        self,
        step: dict[str, Any],
        case_num: int,
        step_num: int,
        suggestions: list[str],
    ) -> None:
        """Check for unmatched braces in step content."""
        for field_name, field_value in step.items():
            if not isinstance(field_value, str):
                continue

            # Count different types of braces
            brace_counts = {
                "curly": field_value.count("{") - field_value.count("}"),
                "square": field_value.count("[") - field_value.count("]"),
                "round": field_value.count("(") - field_value.count(")"),
            }

            for brace_type, count in brace_counts.items():
                if count != 0:
                    suggestions.append(
                        f"Test case {case_num}, Step {step_num}: "
                        f"Fix unmatched {brace_type} braces in '{field_name}' field"
                    )

    def _improve_single_step(self, step: dict[str, Any]) -> bool:
        """Improve a single step and return True if changes were made."""
        improved = False

        # Add missing action field
        if not any(field in step for field in STEP_DESCRIPTION_FIELD_NAMES):
            improved |= self._add_default_action(step)

        # Add missing expected result
        if not any(field in step for field in EXPECTED_RESULT_FIELD_NAMES):
            improved |= self._add_default_expected_result(step)

        # Fix unmatched braces
        improved |= self._fix_unmatched_braces(step)

        return improved

    def _add_default_action(self, step: dict[str, Any]) -> bool:
        """Add default action description to step."""
        # Try to infer action from existing fields
        action = "Execute step action"

        # Look for data that might indicate the action
        for field_name in TEST_DATA_FIELD_NAMES:
            if field_name in step and isinstance(step[field_name], str):
                data = step[field_name].lower()
                if "login" in data:
                    action = "Perform login action"
                elif "click" in data:
                    action = "Click element"
                elif "enter" in data or "input" in data:
                    action = "Enter data"
                elif "verify" in data or "check" in data:
                    action = "Verify result"
                elif "command" in data or "execute" in data:
                    action = "Execute command"
                break

        # Use the first available action field name
        for field_name in STEP_DESCRIPTION_FIELD_NAMES:
            if field_name not in step:
                step[field_name] = action
                return True

        return False

    def _add_default_expected_result(self, step: dict[str, Any]) -> bool:
        """Add default expected result to step."""
        # Use the first available expected result field name
        for field_name in EXPECTED_RESULT_FIELD_NAMES:
            if field_name not in step:
                step[field_name] = "Step completes successfully"
                return True

        return False

    def _fix_unmatched_braces(self, step: dict[str, Any]) -> bool:
        """Fix unmatched braces in step fields."""
        improved = False

        for field_name, field_value in step.items():
            if not isinstance(field_value, str):
                continue

            original_value = field_value
            fixed_value = self._fix_brace_mismatches(field_value)

            if fixed_value != original_value:
                step[field_name] = fixed_value
                improved = True

        return improved

    def _fix_brace_mismatches(self, text: str) -> str:
        """Fix brace mismatches in text."""
        # Fix common parameter format issues
        fixes = [
            # Convert (param) to ${param}
            (r"\(([^)]+)\)", r"${\1}"),
            # Convert <param> to ${param}
            (r"<([^>]+)>", r"${\1}"),
            # Convert [param] to ${param}
            (r"\[([^\]]+)\]", r"${\1}"),
        ]

        fixed_text = text
        for pattern, replacement in fixes:
            # Only apply if the parameter looks like a variable name
            matches = re.findall(pattern, fixed_text)
            for match in matches:
                if match and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", match.strip()):
                    fixed_text = re.sub(pattern, replacement, fixed_text)

        # Fix incomplete {param sequences (missing closing brace)
        # Look for { followed by a word character and no closing }
        # before end of line or space
        incomplete_braces = re.findall(
            r"\{([a-zA-Z_][a-zA-Z0-9_]*)\b(?![^}]*\})", fixed_text
        )
        for param in incomplete_braces:
            # Replace {param with {param}
            fixed_text = re.sub(
                rf"\{{{re.escape(param)}\b(?![^}}]*\}})", f"{{{param}}}", fixed_text
            )

        return fixed_text
