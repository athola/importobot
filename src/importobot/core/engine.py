"""Core conversion engine implementation."""

from typing import Any

from importobot import exceptions
from importobot.core.interfaces import ConversionEngine
from importobot.core.keyword_generator import GenericKeywordGenerator
from importobot.core.parsers import GenericTestFileParser
from importobot.core.pattern_matcher import LibraryDetector
from importobot.utils.logging import setup_logger
from importobot.utils.validation import (
    convert_parameters_to_robot_variables,
    sanitize_robot_string,
)

logger = setup_logger(__name__)


class GenericConversionEngine(ConversionEngine):
    """Conversion engine that transforms test data into Robot Framework format."""

    def __init__(self) -> None:
        """Initialize the parser and keyword generator components."""
        self.parser = GenericTestFileParser()
        self.keyword_generator = GenericKeywordGenerator()

    def convert(self, json_data: dict[str, Any], *, strict: bool = True) -> str:
        """Convert JSON test data to Robot Framework format.

        Args:
            json_data: The JSON data to convert
            strict: If True, raise errors for no tests found. If False,
                generate placeholder.
        """
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
            if strict:
                # Raise clear error when no tests found (new API behavior)
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
            # Create placeholder test case (backward compatibility)
            test_cases_content.extend(
                ["Empty Test Case", "    Log    No test cases found in input", ""]
            )

        if tests:
            for test in tests:
                test_case_lines = self.keyword_generator.generate_test_case(test)
                test_cases_content.extend(test_case_lines)

        # Detect libraries from both original steps and generated content
        detected_libraries = self.keyword_generator.detect_libraries(all_steps)

        # Also detect from generated Robot Framework content
        generated_content = "\n".join(test_cases_content)
        additional_libraries = LibraryDetector.detect_libraries_from_text(
            generated_content
        )

        # Combine all detected libraries
        all_libraries = detected_libraries.union(additional_libraries)

        # Libraries
        for lib in sorted(all_libraries):
            output_lines.append(f"Library    {lib}")

        output_lines.extend(["", "*** Test Cases ***", ""])
        output_lines.extend(test_cases_content)

        # Convert parameter placeholders to Robot Framework variables
        robot_content = "\n".join(output_lines)
        robot_content = convert_parameters_to_robot_variables(robot_content)

        return robot_content

    def _extract_documentation(self, data: dict[str, Any]) -> str:
        """Extract documentation from common fields."""
        doc_fields = ["description", "objective", "summary", "documentation"]

        for field in doc_fields:
            if field in data and data[field]:
                return f"Documentation    {sanitize_robot_string(data[field])}"

        # Default documentation when none found
        return "Documentation    Converted test case"

    def _extract_all_tags(self, data: dict[str, Any]) -> list[str]:
        """Extract tags from anywhere in the JSON structure."""
        tags = []

        def find_tags(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ["tags", "labels", "categories", "priority"]:
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
