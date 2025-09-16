"""Implementation of conversion engine components."""

from typing import Any, Dict, List

from ..utils.logging import setup_logger
from ..utils.validation import sanitize_robot_string
from .interfaces import ConversionEngine
from .keywords import GenericKeywordGenerator
from .parsers import GenericTestFileParser

logger = setup_logger(__name__)


class GenericConversionEngine(ConversionEngine):
    """Generic conversion engine for converting test files to Robot Framework format."""

    def __init__(self) -> None:
        """Initialize the conversion engine with its components."""
        self.parser = GenericTestFileParser()
        self.keyword_generator = GenericKeywordGenerator()

    def convert(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON data to Robot Framework format."""
        # Extract tests from any JSON structure
        tests = self.parser.find_tests(json_data)

        # Extract all steps for library detection
        all_steps = []
        for test in tests:
            all_steps.extend(self.parser.find_steps(test))

        # Build Robot Framework output
        output_lines = []

        # Settings
        output_lines.append("*** Settings ***")
        output_lines.append(self._extract_documentation(json_data))

        # Tags - combine all tags into a single Force Tags line
        tags = self._extract_all_tags(json_data)
        if tags:
            sanitized_tags = [sanitize_robot_string(tag) for tag in tags]
            output_lines.append(f"Force Tags    {'    '.join(sanitized_tags)}")

        # Libraries
        for lib in sorted(self.keyword_generator.detect_libraries(all_steps)):
            output_lines.append(f"Library    {lib}")

        output_lines.extend(["", "*** Test Cases ***", ""])

        # Test cases - handle edge case where no tests found
        if not tests:
            # Better than failing silently
            output_lines.extend(
                ["Empty Test Case", "    Log    No test cases found in input", ""]
            )
        else:
            for test in tests:
                test_case_lines = self.keyword_generator.generate_test_case(test)
                output_lines.extend(test_case_lines)

        return "\n".join(output_lines)

    def _extract_documentation(self, data: Dict[str, Any]) -> str:
        """Extract documentation from common fields."""
        doc_fields = ["description", "objective", "summary", "documentation"]

        for field in doc_fields:
            if field in data and data[field]:
                return f"Documentation    {sanitize_robot_string(data[field])}"

        # Fallback - not ideal but works
        return "Documentation    Converted from legacy test format"

    def _extract_all_tags(self, data: Dict[str, Any]) -> List[str]:
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
