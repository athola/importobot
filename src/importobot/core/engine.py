"""Core conversion engine implementation."""

from typing import Any

from importobot import exceptions
from importobot.core.field_definitions import (
    TEST_DESCRIPTION_FIELDS,
    TEST_TAG_FIELDS,
)
from importobot.core.interfaces import ConversionEngine
from importobot.core.keyword_generator import GenericKeywordGenerator
from importobot.core.parsers import GenericTestFileParser
from importobot.core.pattern_matcher import LibraryDetector
from importobot.core.templates.blueprints import render_with_blueprints
from importobot.utils.logging import get_logger
from importobot.utils.validation import (
    convert_parameters_to_robot_variables,
    sanitize_robot_string,
)

logger = get_logger()


class GenericConversionEngine(ConversionEngine):
    """Conversion engine that transforms test data into Robot Framework format."""

    def __init__(self) -> None:
        """Initialize the parser and keyword generator components."""
        self.parser = GenericTestFileParser()
        self.keyword_generator = GenericKeywordGenerator()

    def convert(
        self,
        json_data: dict[str, Any],
    ) -> str:  # pylint: disable=unused-argument
        """Convert JSON test data to Robot Framework format.

        Args:
            json_data: The JSON data to convert
        """
        specialized = render_with_blueprints(json_data)
        if specialized is not None:
            return specialized

        # Extract test cases from the JSON structure
        tests = self.parser.find_tests(json_data)

        # Extract all steps for library detection
        all_steps = []
        for test in tests:
            all_steps.extend(self.parser.find_steps(test))

        # Build Robot Framework output
        output_lines = []

        # Settings section
        output_lines.append("*** Settings ***")
        output_lines.append(self._extract_documentation(json_data))

        # Tags section
        tags = self._extract_all_tags(json_data)
        if tags:
            sanitized_tags = [sanitize_robot_string(tag) for tag in tags]
            output_lines.append(f"Force Tags    {'    '.join(sanitized_tags)}")

        # Generate test cases
        test_cases_content = []
        if not tests:
            # Raise clear error when no tests found
            available_keys = (
                list(json_data.keys()) if isinstance(json_data, dict) else []
            )
            raise exceptions.ValidationError(
                f"No test cases found in input data. "
                f"Expected structures like {{'testCase': {{...}}}}, "
                f"{{'tests': [...]}}, "
                f"or test cases with 'name' and 'steps' fields. "
                f"Found top-level keys: {available_keys}"
            )

        # Detect libraries from original steps before generating content
        detected_libraries = self.keyword_generator.detect_libraries(
            all_steps, json_data
        )

        # Pass library context to keyword generator for library-aware verification
        self.keyword_generator.set_library_context(detected_libraries)

        if tests:
            for test in tests:
                test_case_lines = self.keyword_generator.generate_test_case(test)
                test_cases_content.extend(test_case_lines)

        # Also detect from generated Robot Framework content
        generated_content = "\n".join(test_cases_content)
        additional_libraries = LibraryDetector.detect_libraries_from_text(
            generated_content
        )

        # Combine all detected libraries
        all_libraries = detected_libraries.union(additional_libraries)

        # Libraries - convert enum values to strings for Robot Framework
        output_lines.extend(
            f"Library    {lib.value}"
            for lib in sorted(all_libraries, key=lambda x: x.value)
        )

        output_lines.extend(["", "*** Test Cases ***", ""])
        output_lines.extend(test_cases_content)

        # Convert parameter placeholders to Robot Framework variables
        robot_content = "\n".join(output_lines)
        robot_content = convert_parameters_to_robot_variables(robot_content)

        return robot_content

    def _extract_documentation(self, data: dict[str, Any]) -> str:
        """Extract documentation from common fields."""
        field_name, value = TEST_DESCRIPTION_FIELDS.find_first(data)
        if field_name and value:
            return f"Documentation    {sanitize_robot_string(value)}"

        # Check summary field as well
        if data.get("summary"):
            return f"Documentation    {sanitize_robot_string(data['summary'])}"

        # Default to first test case when working with synthetic wrappers
        test_cases = data.get("testCases")
        if isinstance(test_cases, list) and test_cases:
            first_case = test_cases[0]
            if isinstance(first_case, dict):
                field_name, value = TEST_DESCRIPTION_FIELDS.find_first(first_case)
                if field_name and value:
                    return f"Documentation    {sanitize_robot_string(value)}"
                if first_case.get("summary"):
                    summary = first_case["summary"]
                    return f"Documentation    {sanitize_robot_string(summary)}"

        # Default documentation when none found
        return "Documentation    Converted test case"

    def _extract_all_tags(self, data: dict[str, Any]) -> list[str]:
        """Extract tags from anywhere in the JSON structure."""
        tags = []

        def find_tags(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in TEST_TAG_FIELDS:
                        if isinstance(value, list):
                            tags.extend([str(t) for t in value])
                        elif value:
                            tags.append(str(value))
                    elif isinstance(value, (dict, list)):
                        find_tags(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_tags(item)

        find_tags(data)
        return tags


__all__ = [
    "GenericConversionEngine",
]
