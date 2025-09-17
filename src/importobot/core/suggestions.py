"""Implementation of suggestion engine components."""

import copy
from typing import Any, Dict, List, Tuple

from importobot import exceptions
from importobot.core.constants import (
    EXPECTED_RESULT_FIELD_NAMES,
    STEP_DESCRIPTION_FIELD_NAMES,
    TEST_DATA_FIELD_NAMES,
)
from importobot.core.interfaces import SuggestionEngine
from importobot.core.parsers import GenericTestFileParser
from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)


class GenericSuggestionEngine(SuggestionEngine):
    """Generic suggestion engine for test file improvements."""

    def get_suggestions(self, json_data: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving JSON test data for Robot conversion."""
        try:
            test_cases = self._extract_test_cases(json_data)
            if isinstance(test_cases, str):
                return [test_cases]  # Error message

            suggestions: List[str] = []
            parser = GenericTestFileParser()

            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case, dict):
                    continue

                self._check_test_case_fields(test_case, i + 1, suggestions)
                steps = parser.find_steps(test_case)
                self._check_steps(steps, i + 1, suggestions)

            return (
                suggestions
                if suggestions
                else ["No improvements needed - test data is well-structured"]
            )
        except Exception as e:
            logger.exception("Error generating suggestions")
            raise exceptions.SuggestionError(
                f"Failed to generate suggestions: {str(e)}"
            ) from e

    def _extract_test_cases(self, json_data: Any) -> Any:
        """Extract test cases from various JSON structures."""
        if isinstance(json_data, list):
            return json_data
        if isinstance(json_data, dict):
            if "tests" in json_data and isinstance(json_data["tests"], list):
                return json_data["tests"]
            return [json_data]
        return "Invalid JSON structure - expected dictionary or array"

    def _check_test_case_fields(
        self, test_case: Dict[str, Any], case_num: int, suggestions: List[str]
    ) -> None:
        """Check for missing fields in test case."""
        field_checks = [
            (["name", "title", "testname", "summary"], "Add a descriptive name field"),
            (["description", "objective", "documentation"], "Add documentation"),
            (["tags", "labels", "categories"], "Add tags for better test organization"),
        ]

        for fields, message in field_checks:
            if not any(field in test_case and test_case[field] for field in fields):
                suggestions.append(
                    f"Test case {case_num}: {message} ({', '.join(fields)})"
                )

    def _check_steps(
        self, steps: List[Dict[str, Any]], case_num: int, suggestions: List[str]
    ) -> None:
        """Check steps for missing fields and issues."""
        if not steps:
            suggestions.append(
                f"Test case {case_num}: Add execution steps "
                f"({', '.join(['steps', 'teststeps', 'actions'])})"
            )
            return

        for j, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            self._check_step_fields(step, case_num, j + 1, suggestions)
            self._check_brace_matching(step, case_num, j + 1, suggestions)

    def _check_step_fields(
        self, step: Dict[str, Any], case_num: int, step_num: int, suggestions: List[str]
    ) -> None:
        """Check for missing fields in a step."""
        field_checks = [
            (
                STEP_DESCRIPTION_FIELD_NAMES,
                "Add action description",
            ),
            (
                TEST_DATA_FIELD_NAMES,
                "Add test data if needed",
            ),
            (
                EXPECTED_RESULT_FIELD_NAMES,
                "Add expected result",
            ),
        ]

        for fields, message in field_checks:
            if not any(field in step and step[field] for field in fields):
                suggestions.append(
                    f"Test case {case_num}, step {step_num}: {message} "
                    f"({', '.join(fields)})"
                )

    def _check_brace_matching(
        self, step: Dict[str, Any], case_num: int, step_num: int, suggestions: List[str]
    ) -> None:
        """Check for unmatched braces in test data fields."""
        data_fields = ["testData", "testdata", "test_data", "data", "input"]

        for field in data_fields:
            if field in step and step[field]:
                test_data_value = str(step[field])
                # Optimized: count both braces in single pass
                open_braces = close_braces = 0
                for char in test_data_value:
                    if char == "{":
                        open_braces += 1
                    elif char == "}":
                        close_braces += 1
                if open_braces != close_braces:
                    suggestions.append(
                        f"Test case {case_num}, step {step_num}: "
                        f"Check unmatched braces in {field} "
                        f"({open_braces} open, {close_braces} close)"
                    )

    def apply_suggestions(
        self, json_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Apply automatic improvements to JSON test data for Robot conversion."""
        try:
            # Make a deep copy to avoid modifying the original
            improved_data = copy.deepcopy(json_data)
            changes_made: List[Dict[str, Any]] = []

            test_cases = self._extract_test_cases_for_improvement(improved_data)
            if test_cases is None:
                return improved_data, changes_made

            parser = GenericTestFileParser()

            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case, dict):
                    continue

                self._improve_test_case(test_case, i, changes_made)
                steps = parser.find_steps(test_case)
                self._improve_steps(test_case, steps, i, changes_made)

            return improved_data, changes_made
        except Exception as e:
            logger.exception("Error applying suggestions")
            raise exceptions.SuggestionError(
                f"Failed to apply suggestions: {str(e)}"
            ) from e

    def _extract_test_cases_for_improvement(self, data: Any) -> Any:
        """Extract test cases from various data structures for improvement."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "tests" in data and isinstance(data["tests"], list):
                return data["tests"]
            return [data]
        return None

    def _improve_test_case(
        self, test_case: Dict[str, Any], index: int, changes_made: List[Dict[str, Any]]
    ) -> None:
        """Apply improvements to a test case."""
        self._add_default_name(test_case, index, changes_made)
        self._add_default_description(test_case, index, changes_made)

    def _add_default_name(
        self, test_case: Dict[str, Any], index: int, changes_made: List[Dict[str, Any]]
    ) -> None:
        """Add default name if missing."""
        name_fields = ["name", "title", "testname", "summary"]
        has_name = any(field in test_case and test_case[field] for field in name_fields)
        if not has_name:
            test_case["name"] = "Unnamed Test Case"
            changes_made.append(
                {
                    "test_case_index": index,
                    "field": "name",
                    "original": "",
                    "improved": "Unnamed Test Case",
                    "reason": "Added default test case name",
                }
            )

    def _add_default_description(
        self, test_case: Dict[str, Any], index: int, changes_made: List[Dict[str, Any]]
    ) -> None:
        """Add default description if missing."""
        doc_fields = ["description", "objective", "documentation"]
        has_doc = any(field in test_case and test_case[field] for field in doc_fields)
        if not has_doc:
            default_desc = "Test case converted from JSON"
            test_case["description"] = default_desc
            changes_made.append(
                {
                    "test_case_index": index,
                    "field": "description",
                    "original": "",
                    "improved": default_desc,
                    "reason": "Added default test case description",
                }
            )

    def _improve_steps(
        self,
        test_case: Dict[str, Any],
        steps: List[Dict[str, Any]],
        index: int,
        changes_made: List[Dict[str, Any]],
    ) -> None:
        """Apply improvements to test steps."""
        if not steps:
            test_case["steps"] = []
            changes_made.append(
                {
                    "test_case_index": index,
                    "field": "steps",
                    "original": "",
                    "improved": "[]",
                    "reason": "Added empty steps array for test execution",
                }
            )
            return

        for j, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            self._improve_single_step(step, index, j, changes_made)

    def _improve_single_step(
        self,
        step: Dict[str, Any],
        test_index: int,
        step_index: int,
        changes_made: List[Dict[str, Any]],
    ) -> None:
        """Apply improvements to a single step."""
        self._add_default_action(step, test_index, step_index, changes_made)
        self._add_default_expected_result(step, test_index, step_index, changes_made)
        self._fix_unmatched_braces(step, test_index, step_index, changes_made)

    def _add_default_action(
        self,
        step: Dict[str, Any],
        test_index: int,
        step_index: int,
        changes_made: List[Dict[str, Any]],
    ) -> None:
        """Add default action if missing."""
        action_fields = ["step", "description", "action", "instruction"]
        has_action = any(field in step and step[field] for field in action_fields)
        if not has_action:
            default_action = "Perform test action"
            step["action"] = default_action
            changes_made.append(
                {
                    "test_case_index": test_index,
                    "step_index": step_index,
                    "field": "action",
                    "original": "",
                    "improved": default_action,
                    "reason": "Added default action description",
                }
            )

    def _add_default_expected_result(
        self,
        step: Dict[str, Any],
        test_index: int,
        step_index: int,
        changes_made: List[Dict[str, Any]],
    ) -> None:
        """Add default expected result if missing."""
        result_fields = EXPECTED_RESULT_FIELD_NAMES
        has_result = any(field in step and step[field] for field in result_fields)
        if not has_result:
            default_result = "Action completes successfully"
            step["expectedResult"] = default_result
            changes_made.append(
                {
                    "test_case_index": test_index,
                    "step_index": step_index,
                    "field": "expectedResult",
                    "original": "",
                    "improved": default_result,
                    "reason": "Added default expected result",
                }
            )

    def _fix_unmatched_braces(
        self,
        step: Dict[str, Any],
        test_index: int,
        step_index: int,
        changes_made: List[Dict[str, Any]],
    ) -> None:
        """Fix unmatched braces in test data fields."""
        test_data_fields = ["testData", "data", "command", "input"]

        for field in test_data_fields:
            if field not in step or not isinstance(step[field], str):
                continue

            original_value = step[field]
            open_braces = original_value.count("{")
            close_braces = original_value.count("}")

            if open_braces != close_braces:
                # Fix by adding missing closing braces
                if open_braces > close_braces:
                    missing_close = open_braces - close_braces
                    fixed_value = original_value + "}" * missing_close
                    step[field] = fixed_value
                    changes_made.append(
                        {
                            "test_case_index": test_index,
                            "step_index": step_index,
                            "field": field,
                            "original": original_value,
                            "improved": fixed_value,
                            "reason": f"Fixed unmatched braces (added "
                            f"{missing_close} closing brace(s))",
                        }
                    )
                # Fix by removing extra closing braces
                elif close_braces > open_braces:
                    extra_close = close_braces - open_braces
                    fixed_value = original_value
                    for _ in range(extra_close):
                        # Remove the last occurrence of }
                        last_brace_idx = fixed_value.rfind("}")
                        if last_brace_idx != -1:
                            last_brace_plus_one = last_brace_idx + 1
                            fixed_value = (
                                fixed_value[:last_brace_idx]
                                + fixed_value[last_brace_plus_one:]
                            )
                    step[field] = fixed_value
                    changes_made.append(
                        {
                            "test_case_index": test_index,
                            "step_index": step_index,
                            "field": field,
                            "original": original_value,
                            "improved": fixed_value,
                            "reason": f"Fixed unmatched braces (removed "
                            f"{extra_close} extra closing brace(s))",
                        }
                    )
