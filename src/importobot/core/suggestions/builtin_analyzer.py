"""Analyzer for BuiltIn keyword mapping ambiguities and suggestions."""

import re
from typing import Any

from importobot.core.constants import STEPS_FIELD_NAME
from importobot.core.field_definitions import (
    STEP_ACTION_FIELDS,
    STEP_DATA_FIELDS,
    STEP_EXPECTED_FIELDS,
    TEST_SCRIPT_FIELDS,
    get_field_value,
)
from importobot.utils.string_cache import data_to_lower_cached


class BuiltInKeywordAnalyzer:
    """Analyzer for Robot Framework BuiltIn keyword mapping ambiguities."""

    def __init__(self) -> None:
        """Initialize the analyzer with keyword patterns and ambiguity rules."""
        self._ambiguous_patterns = self._build_ambiguous_patterns()
        self._builtin_keywords = self._build_builtin_keywords_map()

    def check_builtin_keyword_ambiguities(
        self,
        *,
        steps: list[dict[str, Any]],
        test_case_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for BuiltIn keyword mapping ambiguities in test steps."""
        for i, step in enumerate(steps):
            # Handle different field name formats (camelCase vs snake_case)
            step_description = data_to_lower_cached(
                get_field_value(step, STEP_ACTION_FIELDS)
            )
            test_data = get_field_value(step, STEP_DATA_FIELDS)
            expected = get_field_value(step, STEP_EXPECTED_FIELDS)

            # Check for missing parameter issues first
            self._check_missing_parameters(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )

            # Check for specific ambiguity patterns
            self._check_log_vs_assertion_ambiguity(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )
            self._check_conversion_ambiguity(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )
            self._check_length_operation_ambiguity(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )
            self._check_string_operation_ambiguity(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )
            self._check_conditional_keyword_ambiguity(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )
            self._check_variable_operation_ambiguity(
                description=step_description,
                test_data=test_data,
                expected=expected,
                test_case_index=test_case_index,
                step_index=i + 1,
                suggestions=suggestions,
            )

    def suggest_builtin_keyword_improvements(
        self,
        test_case: dict[str, Any],
        test_case_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Suggest specific BuiltIn keyword improvements for test case."""
        script_field, script_data = TEST_SCRIPT_FIELDS.find_first(test_case)
        if not script_field or not isinstance(script_data, dict):
            return

        steps = script_data.get(STEPS_FIELD_NAME, [])
        if not isinstance(steps, list):
            return

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue

            self._improve_conversion_keywords(step, test_case_index, i, changes_made)
            self._improve_assertion_keywords(step, test_case_index, i, changes_made)
            self._improve_logging_keywords(step, test_case_index, i, changes_made)

    def _build_ambiguous_patterns(self) -> dict[str, list[str]]:
        """Build patterns that could map to multiple BuiltIn keywords."""
        return {
            "log_vs_assertion": [
                r"log.*(?:verify|check|assert)",
                r"(?:verify|check|assert).*log",
                r"log.*(?:and|then).*(?:verify|check)",
                r"(?:verify|check).*(?:and|then).*log",
            ],
            "conversion_vs_assertion": [
                r"convert.*(?:and|then).*(?:verify|check|assert)",
                r"(?:verify|check|assert).*(?:and|then).*convert",
                r"convert.*(?:to|as).*(?:integer|string|boolean|number)"
                r".*(?:verify|check)",
            ],
            "length_operations": [
                r"(?:get|check|verify).*length",
                r"length.*(?:should|must|equals?)",
                r"(?:count|size).*(?:should|must|equals?)",
            ],
            "string_operations": [
                r"(?:string|text).*(?:match|contains?|starts?|ends?)",
                r"(?:should|must).*(?:match|contain|start|end)",
                r"(?:check|verify).*(?:pattern|regex|regexp)",
            ],
            "conditional_operations": [
                r"(?:if|when|unless).*(?:run|execute).*keyword",
                r"(?:run|execute).*keyword.*(?:if|when|unless)",
                r"conditional.*(?:execution|keyword)",
            ],
            "variable_operations": [
                r"(?:set|create|define).*variable.*(?:and|then).*(?:verify|check)",
                r"(?:verify|check).*variable.*(?:exists?|defined)",
            ],
        }

    def _build_builtin_keywords_map(self) -> dict[str, list[str]]:
        """Build mapping of keyword categories to actual BuiltIn keywords."""
        return {
            "logging": ["Log", "Log Many", "Log To Console", "Log Variables"],
            "conversions": [
                "Convert To Binary",
                "Convert To Boolean",
                "Convert To Bytes",
                "Convert To Hex",
                "Convert To Integer",
                "Convert To Number",
                "Convert To Octal",
                "Convert To String",
            ],
            "assertions": [
                "Should Be Equal",
                "Should Not Be Equal",
                "Should Contain",
                "Should Not Contain",
                "Should Be Empty",
                "Should Not Be Empty",
                "Should Be True",
                "Should Be False",
                "Should Match",
                "Should Not Match",
                "Should Start With",
                "Should End With",
            ],
            "length_operations": ["Get Length", "Length Should Be"],
            "collections": ["Get Count", "Should Be Empty", "Should Not Be Empty"],
            "variables": [
                "Set Global Variable",
                "Set Suite Variable",
                "Set Test Variable",
                "Set Local Variable",
                "Get Variable Value",
                "Get Variables",
            ],
            "conditionals": [
                "Run Keyword If",
                "Run Keyword Unless",
                "Run Keywords",
                "Repeat Keyword",
                "Continue For Loop",
                "Exit For Loop",
            ],
            "evaluation": ["Evaluate"],
            "control_flow": ["Pass Execution", "Return From Keyword", "Fail"],
            "type_checking": [
                "Should Be X Type"  # Placeholder for type checking keywords
            ],
        }

    def _check_missing_parameters(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for BuiltIn keywords that require specific parameters."""
        # expected parameter is kept for interface consistency but
        # not used in this implementation
        _ = expected  # Mark as intentionally unused
        # Check for generic test_data_for_* patterns that indicate missing proper data
        if "test_data_for_" in test_data and "#" in test_data:
            operation_type = None
            required_format = None

            if "convert_to_" in description or "convert_to_" in test_data:
                if "integer" in test_data or "number" in test_data:
                    operation_type = "conversion to number"
                    required_format = "value: 123"
                elif "string" in test_data:
                    operation_type = "conversion to string"
                    required_format = "value: hello"
                elif "boolean" in test_data:
                    operation_type = "conversion to boolean"
                    required_format = "value: true"
            elif "run_keyword_if" in test_data or "conditionally" in description:
                operation_type = "conditional keyword execution"
                required_format = (
                    "condition: ${status} == 'pass', keyword: Log, args: Success"
                )
            elif "repeat_keyword" in test_data or "repeat" in description:
                operation_type = "keyword repetition"
                required_format = "times: 3, keyword: Log, args: Test message"

            if operation_type and required_format:
                suggestions.append(
                    f"Test case {test_case_index}, step {step_index}: "
                    f"BuiltIn keyword for {operation_type} requires "
                    f"structured test data. "
                    f"Replace generic test data with: {required_format}"
                )

    def _check_log_vs_assertion_ambiguity(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for ambiguity between logging and assertion operations."""
        # expected parameter is kept for interface consistency but
        # not used in this implementation
        _ = expected  # Mark as intentionally unused
        combined = data_to_lower_cached(f"{description} {test_data} {expected}")

        for pattern in self._ambiguous_patterns["log_vs_assertion"]:
            if re.search(pattern, combined):
                suggestions.append(
                    f"Test case {test_case_index}, "
                    f"step "
                    f"{step_index}: "
                    f"Ambiguous intention - could map to Log keyword "
                    f"or assertion keyword. "
                    f"Consider separating logging from verification "
                    f"into distinct steps. "
                    f"Use 'Log' for simple message output, "
                    f"or 'Should Contain/Should Be Equal' "
                    f"for verification operations."
                )
                break

    def _check_conversion_ambiguity(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for ambiguity in conversion operations."""
        # expected parameter is kept for interface consistency but
        # not used in this implementation
        _ = expected  # Mark as intentionally unused
        combined = data_to_lower_cached(f"{description} {test_data} {expected}")

        for pattern in self._ambiguous_patterns["conversion_vs_assertion"]:
            if re.search(pattern, combined):
                suggestions.append(
                    f"Test case {test_case_index}, step {step_index}: "
                    f"Conversion operation mixed with verification. "
                    f"Consider separating into: "
                    f"1) Convert To [Type] keyword for data conversion, "
                    f"2) Should Be Equal keyword for result verification. "
                    f"This improves clarity and follows Robot Framework best practices."
                )
                break

    def _check_length_operation_ambiguity(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for ambiguity in length operations."""
        # test_case_index and step_index parameters are kept for interface
        # consistency but not used in this implementation
        _ = test_case_index, step_index  # Mark as intentionally unused
        combined = data_to_lower_cached(f"{description} {test_data} {expected}")

        for pattern in self._ambiguous_patterns["length_operations"]:
            if re.search(pattern, combined):
                suggestions.append(
                    f"Test case {test_case_index}, step {step_index}: "
                    f"Length operation could map to 'Get Length' (returns length) "
                    f"or 'Length Should Be' (validates length). "
                    f"Use 'Get Length' to retrieve and store length, "
                    f"use 'Length Should Be' for direct validation."
                )
                break

    def _check_string_operation_ambiguity(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for ambiguity in string operations."""
        # test_case_index and step_index parameters are kept for interface
        # consistency but not used in this implementation
        _ = test_case_index, step_index  # Mark as intentionally unused
        combined = data_to_lower_cached(f"{description} {test_data} {expected}")

        for pattern in self._ambiguous_patterns["string_operations"]:
            if re.search(pattern, combined):
                string_keywords = [
                    "Should Start With",
                    "Should End With",
                    "Should Match",
                    "Should Contain",
                    "Get Substring",
                ]
                keywords_str = ", ".join(string_keywords)
                suggestions.append(
                    f"Test case {test_case_index}, "
                    f"step {step_index}: "
                    f"String operation could map to multiple "
                    f"keywords: {keywords_str}. "
                    f"Specify the exact string operation needed "
                    f"(contains, starts with, ends with, "
                    f"matches pattern, etc.) for precise keyword mapping."
                )
                break

    def _check_conditional_keyword_ambiguity(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for ambiguity in conditional keyword operations."""
        # test_case_index and step_index parameters are kept for interface
        # consistency but not used in this implementation
        _ = test_case_index, step_index  # Mark as intentionally unused
        combined = data_to_lower_cached(f"{description} {test_data} {expected}")

        for pattern in self._ambiguous_patterns["conditional_operations"]:
            if re.search(pattern, combined):
                suggestions.append(
                    f"Test case {test_case_index}, step {step_index}: "
                    f"Conditional keyword execution detected. Structure as: "
                    f"'Run Keyword If    condition    keyword    args' "
                    f"or 'Run Keyword Unless    condition    keyword    args'. "
                    f"Clearly separate condition, target keyword, and arguments."
                )
                break

    def _check_variable_operation_ambiguity(
        self,
        *,
        description: str,
        test_data: str,
        expected: str,
        test_case_index: int,
        step_index: int,
        suggestions: list[str],
    ) -> None:
        """Check for ambiguity in variable operations."""
        combined = data_to_lower_cached(f"{description} {test_data} {expected}")

        for pattern in self._ambiguous_patterns["variable_operations"]:
            if re.search(pattern, combined):
                suggestions.append(
                    f"Test case {test_case_index}, step {step_index}: "
                    f"Variable operation mixed with verification. Separate into: "
                    f"1) Set Variable/Create List/Create Dictionary for creation, "
                    f"2) Variable Should Exist/Should Be Equal for verification. "
                    f"Use appropriate scope (Global/Suite/Test/Local) for Set Variable."
                )
                break

    def _improve_conversion_keywords(
        self,
        step: dict[str, Any],
        test_case_index: int,
        step_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Improve conversion keyword usage in step."""
        description = data_to_lower_cached(
            step.get("step", step.get("description", ""))
        )
        test_data = str(step.get("test_data", step.get("testData", "")))

        # Pattern for conversion operations
        conversion_patterns = {
            r"convert.*to.*integer": "Convert To Integer",
            r"convert.*to.*string": "Convert To String",
            r"convert.*to.*boolean": "Convert To Boolean",
            r"convert.*to.*number": "Convert To Number",
            r"convert.*to.*binary": "Convert To Binary",
            r"convert.*to.*hex": "Convert To Hex",
        }

        for pattern, keyword in conversion_patterns.items():
            if re.search(pattern, description):
                # Extract value to convert
                value_match = re.search(r"value[:\s=]+([^,\s]+)", test_data)
                value = value_match.group(1) if value_match else "${value}"

                improved_step = {
                    "step": f"Convert value using {keyword}",
                    "test_data": f"value: {value}",
                    "robot_keyword": f"{keyword}    {value}",
                }

                step.update(improved_step)
                changes_made.append(
                    {
                        "type": "builtin_conversion_improvement",
                        "location": f"test_case_{test_case_index}_step_{step_index}",
                        "change": f"Improved conversion to use {keyword}",
                        "old_step": description,
                        "new_step": improved_step["step"],
                    }
                )
                break

    def _improve_assertion_keywords(
        self,
        step: dict[str, Any],
        test_case_index: int,
        step_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Improve assertion keyword usage in step."""
        description = data_to_lower_cached(
            step.get("step", step.get("description", ""))
        )
        test_data = str(step.get("test_data", step.get("testData", "")))
        expected = str(step.get("expected", step.get("expectedResult", "")))

        # Pattern for assertion improvements
        assertion_patterns = {
            r"(?:verify|check|assert).*equals?": "Should Be Equal",
            r"(?:verify|check|assert).*contains?": "Should Contain",
            r"(?:verify|check|assert).*empty": "Should Be Empty",
            r"(?:verify|check|assert).*true": "Should Be True",
            r"(?:verify|check|assert).*false": "Should Be False",
        }

        for pattern, keyword in assertion_patterns.items():
            if re.search(pattern, description):
                # Extract assertion parameters
                if keyword == "Should Be Equal":
                    arg1 = "${actual}"
                    arg2 = expected or "${expected}"
                elif keyword == "Should Contain":
                    arg1 = "${container}"
                    arg2 = expected or test_data or "${item}"
                else:
                    arg1 = expected or test_data or "${value}"
                    arg2 = ""

                robot_keyword = f"{keyword}    {arg1}"
                if arg2:
                    robot_keyword += f"    {arg2}"

                improved_step = {
                    "step": f"Assert using {keyword}",
                    "test_data": test_data,
                    "expected": expected,
                    "robot_keyword": (robot_keyword),
                }

                step.update(improved_step)
                changes_made.append(
                    {
                        "type": "builtin_assertion_improvement",
                        "location": f"test_case_{test_case_index}_step_{step_index}",
                        "change": f"Improved assertion to use {keyword}",
                        "old_step": description,
                        "new_step": improved_step["step"],
                    }
                )
                break

    def _improve_logging_keywords(
        self,
        step: dict[str, Any],
        test_case_index: int,
        step_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Improve logging keyword usage in step."""
        description = data_to_lower_cached(
            step.get("step", step.get("description", ""))
        )
        test_data = str(step.get("test_data", step.get("testData", "")))

        # Pattern for logging improvements
        if re.search(r"^log\b", description) and not re.search(
            r"(?:verify|check|assert)", description
        ):
            # Extract log message
            message_match = re.search(r"message[:\s=]+([^,]+)", test_data)
            message = (
                message_match.group(1).strip()
                if message_match
                else test_data or "Test message"
            )

            # Extract log level if specified
            level_match = re.search(r"level[:\s=]+([^,\s]+)", test_data)
            level = level_match.group(1).upper() if level_match else "INFO"

            if level in ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"]:
                robot_keyword = f"Log    {message}    {level}"
            else:
                robot_keyword = f"Log    {message}"

            improved_step = {
                "step": "Log message",
                "test_data": f"message: {message}",
                "robot_keyword": robot_keyword,
            }

            step.update(improved_step)
            changes_made.append(
                {
                    "type": "builtin_logging_improvement",
                    "location": (f"test_case_{test_case_index}_step_{step_index}"),
                    "change": "Improved logging to use Log keyword "
                    "with proper parameters",
                    "old_step": description,
                    "new_step": improved_step["step"],
                }
            )
