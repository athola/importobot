"""Main suggestion engine that orchestrates all suggestion components."""

import copy
from typing import Any

from importobot import exceptions
from importobot.core.constants import TEST_CONTAINER_FIELD_NAMES
from importobot.core.interfaces import SuggestionEngine
from importobot.core.parsers import GenericTestFileParser
from importobot.utils.logging import get_logger
from importobot.utils.validation import FieldValidator

from .builtin_analyzer import BuiltInKeywordAnalyzer
from .comparison_analyzer import ComparisonAnalyzer
from .parameter_analyzer import ParameterAnalyzer
from .step_analyzer import StepAnalyzer

logger = get_logger()


class GenericSuggestionEngine(SuggestionEngine):
    """Generic suggestion engine for test file improvements."""

    def __init__(self) -> None:
        """Initialize the suggestion engine with all analyzers."""
        self.field_validator = FieldValidator()
        self.step_analyzer = StepAnalyzer()
        self.parameter_analyzer = ParameterAnalyzer()
        self.comparison_analyzer = ComparisonAnalyzer()
        self.builtin_analyzer = BuiltInKeywordAnalyzer()

    def get_suggestions(self, json_data: dict[str, Any] | list[Any] | Any) -> list[str]:
        """Generate suggestions for improving JSON test data for Robot conversion."""
        try:
            test_cases = self._extract_test_cases(json_data)
            if isinstance(test_cases, str):
                return [test_cases]  # Error message

            suggestions: list[str] = []
            parser = GenericTestFileParser()

            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case, dict):
                    continue

                self.field_validator.check_test_case_fields(
                    test_case, i + 1, suggestions
                )
                steps = parser.find_steps(test_case)
                self.step_analyzer.check_steps(steps, i + 1, suggestions)
                self.parameter_analyzer.check_parameter_mapping(
                    test_case, steps, i + 1, suggestions
                )
                self.step_analyzer.check_step_ordering(steps, i + 1, suggestions)
                self.comparison_analyzer.check_result_comparison_opportunities(
                    steps, i + 1, suggestions
                )
                self.builtin_analyzer.check_builtin_keyword_ambiguities(
                    steps=steps, test_case_index=i + 1, suggestions=suggestions
                )

            return (
                suggestions
                if suggestions
                else ["No improvements needed - test data is well-structured"]
            )

        except Exception as e:
            logger.error("Error generating suggestions: %s", e)
            return [f"Error analyzing test data: {e!s}"]

    def suggest_improvements(self, test_data_list: list[Any]) -> list[str]:
        """Generate improvement suggestions for a list of test data.

        Args:
            test_data_list: List of test data to analyze

        Returns:
            list: List of improvement suggestions
        """
        all_suggestions = []
        for test_data in test_data_list:
            suggestions = self.get_suggestions(test_data)
            all_suggestions.extend(suggestions)
        return all_suggestions

    def apply_suggestions(
        self, json_data: dict[str, Any] | list[Any] | Any
    ) -> tuple[Any, list[dict[str, Any]]]:
        """Apply automatic improvements to test data."""
        try:
            # Create a deep copy to avoid modifying the original
            improved_data = copy.deepcopy(json_data)
            changes_made: list[dict[str, Any]] = []

            test_cases = self._extract_test_cases_for_improvement(improved_data)
            if isinstance(test_cases, str):
                raise exceptions.ImportobotError(test_cases)

            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case, dict):
                    continue

                # Apply field improvements
                self.field_validator.add_default_name(test_case, i, changes_made)
                self.field_validator.add_default_description(test_case, i, changes_made)

                # Apply step improvements
                self.step_analyzer.improve_steps(test_case, i, changes_made)

                # Apply parameter improvements
                self.parameter_analyzer.improve_parameters(test_case, i, changes_made)

                # Add comparison steps if beneficial
                parser = GenericTestFileParser()
                steps = parser.find_steps(test_case)
                self.comparison_analyzer.add_comparison_steps(
                    test_case, steps, i, changes_made
                )

                # Apply BuiltIn keyword improvements
                self.builtin_analyzer.suggest_builtin_keyword_improvements(
                    test_case, i, changes_made
                )

            return improved_data, changes_made

        except Exception as e:
            logger.error("Error applying suggestions: %s", e)
            raise exceptions.ImportobotError(
                f"Failed to apply suggestions: {e!s}"
            ) from e

    def _extract_test_cases(self, json_data: Any) -> Any:
        """Extract test cases from JSON data for analysis."""
        if isinstance(json_data, list):
            return json_data
        if isinstance(json_data, dict):
            for key, value in json_data.items():
                if (
                    isinstance(value, list)
                    and key.lower() in TEST_CONTAINER_FIELD_NAMES
                ):
                    return value
            for key, value in json_data.items():
                if key.lower() in TEST_CONTAINER_FIELD_NAMES:
                    return value
            return [json_data]  # Single test case
        return "Invalid JSON structure: expected object or array"

    def _extract_test_cases_for_improvement(self, data: Any) -> Any:
        """Extract test cases from data for improvement."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key, value in data.items():
                if (
                    isinstance(value, list)
                    and key.lower() in TEST_CONTAINER_FIELD_NAMES
                ):
                    return value
            for key, value in data.items():
                if key.lower() in TEST_CONTAINER_FIELD_NAMES:
                    return value
            return [data]  # Single test case
        return "Invalid JSON structure: expected object or array"
