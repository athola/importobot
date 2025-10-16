"""Comparison and result analysis suggestions."""

import re
from typing import Any

from importobot.core.constants import STEPS_FIELD_NAME
from importobot.core.field_definitions import (
    STEP_ACTION_FIELDS,
    STEP_DATA_FIELDS,
    TEST_SCRIPT_FIELDS,
    get_field_value,
)
from importobot.utils.logging import setup_logger
from importobot.utils.step_processing import collect_command_steps

logger = setup_logger(__name__)


class ComparisonAnalyzer:
    """Analyzes and suggests improvements for result comparisons."""

    def check_result_comparison_opportunities(
        self, steps: list[dict[str, Any]], case_num: int, suggestions: list[str]
    ) -> None:
        """Check for opportunities to add result comparison steps."""
        command_steps = self._collect_command_steps(steps)
        hash_commands = self._group_hash_commands(command_steps)

        if len(hash_commands) >= 2:
            self._suggest_hash_comparison(hash_commands, case_num, suggestions)

    def add_comparison_steps(
        self,
        test_case: dict[str, Any],
        steps: list[dict[str, Any]],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Automatically add comparison steps for similar commands.

        Note: Comparison steps are complex Robot Framework keywords that don't
        fit the CLI command pattern. They're better left as suggestions for
        users to add manually with proper context and variable names.
        """
        # Disabled: Automatic comparison steps generate invalid syntax
        # when rendered through CLI blueprints. Users should add these
        # manually based on suggestions.
        return

    def _collect_command_steps(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Collect steps that contain command execution."""
        return collect_command_steps(steps)

    def _group_hash_commands(
        self, command_steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Group commands that are hash/checksum related."""
        hash_commands = []
        for step in command_steps:
            if not isinstance(step, dict):
                continue
            command_text = get_field_value(step, STEP_DATA_FIELDS)
            if not command_text:
                command_text = get_field_value(step, STEP_ACTION_FIELDS)

            if command_text:
                content = command_text.lower()
                hash_terms = ["hash", "sha", "md5", "checksum"]
                if any(hash_cmd in content for hash_cmd in hash_terms):
                    hash_commands.append({"step": step, "command": command_text})
        return hash_commands

    def _suggest_hash_comparison(
        self,
        hash_commands: list[dict[str, Any]],
        case_num: int,
        suggestions: list[str],
    ) -> None:
        """Suggest comparison keywords for hash commands."""
        all_hash_related = hash_commands

        if len(all_hash_related) >= 2:
            suggestions.append(
                f"Test case {case_num}: Consider adding comparison step after "
                "hash/checksum commands to verify results match expectations"
            )

            # Suggest specific comparison logic
            files_involved = []
            for cmd_info in all_hash_related:
                # Extract file references from commands
                command = cmd_info.get("command", "")
                if isinstance(command, str):
                    param_matches = re.findall(r"\{([^}]*)\}", command)
                    files_involved.extend(param_matches)

            if len(set(files_involved)) >= 2:
                files_list = ", ".join(set(files_involved))
                suggestions.append(
                    f"Test case {case_num}: Add Robot Framework comparison keywords "
                    f"like 'Should Be Equal' or 'Should Not Be Equal' to compare "
                    f"hash results from different files: {files_list}"
                )

    def _create_comparison_step(
        self, test_index: int, next_index: int
    ) -> dict[str, Any]:
        """Create a comparison step for hash/checksum commands."""
        return {
            "testData": "Should Be Equal    ${hash_result_1}    ${hash_result_2}",
            "description": "Compare hash results to verify they match as expected",
            "expectedResult": "Hash results match",
            "index": next_index,
            "id": f"generated_comparison_{test_index}_{next_index}",
        }

    def _add_comparison_step_to_test_case(
        self,
        test_case: dict[str, Any],
        comparison_step: dict[str, Any],
        change_info: dict[str, Any],
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Add the comparison step to the test case and record the change."""
        script_field, script_data = TEST_SCRIPT_FIELDS.find_first(test_case)
        if not script_field or not isinstance(script_data, dict):
            script_field = TEST_SCRIPT_FIELDS.fields[0]
            script_data = {STEPS_FIELD_NAME: []}
            test_case[script_field] = script_data

        steps = script_data.get(STEPS_FIELD_NAME)
        if not isinstance(steps, list):
            steps = []
            script_data[STEPS_FIELD_NAME] = steps

        steps.append(comparison_step)

        change_record = {
            "type": "step_added",
            "reason": "Added comparison step for hash/checksum commands",
            "field": "step",
            "original": None,
            "improved": comparison_step["description"],
            **change_info,
        }
        changes_made.append(change_record)
