"""
Unified JSON to Robot Framework converter.

Handles any Zephyr test format variation with generic parsing.
Single source of truth for all conversion logic - no legacy support.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from .. import config
from ..utils.validation import (
    sanitize_error_message,
    sanitize_robot_string,
    validate_safe_path,
)


class JsonToRobotConverter:
    """Generic converter that handles any JSON test format programmatically."""

    def __init__(self):
        """Initialize the converter with intent patterns."""
        self._intent_patterns = self._build_intent_patterns()

    def convert_json_string(self, json_string: str) -> str:
        """Convert JSON string directly to Robot Framework format."""
        if not json_string or not json_string.strip():
            raise ValueError("Empty JSON string provided")

        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON at line {e.lineno}: {e.msg}") from e

        if not isinstance(json_data, dict):
            raise TypeError("JSON data must be a dictionary")

        return self._convert_data_to_robot(json_data)

    def convert_json_data(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON data dict to Robot Framework format."""
        if not isinstance(json_data, dict):
            raise TypeError("JSON data must be a dictionary")

        return self._convert_data_to_robot(json_data)

    def _convert_data_to_robot(self, json_data: Dict[str, Any]) -> str:
        """Core conversion logic."""
        # Extract tests from any JSON structure
        tests = self._find_tests_anywhere(json_data)

        # Extract all steps for library detection
        all_steps = []
        for test in tests:
            all_steps.extend(self._find_steps_anywhere(test))

        # Build Robot Framework output
        output_lines = []

        # Settings
        output_lines.append("*** Settings ***")
        output_lines.append(self._extract_documentation(json_data))

        # Tags
        for tag in self._extract_all_tags(json_data):
            output_lines.append(f"Force Tags    {sanitize_robot_string(tag)}")

        # Libraries
        for lib in sorted(self._detect_libraries_from_steps(all_steps)):
            output_lines.append(f"Library    {lib}")

        output_lines.extend(["", "*** Test Cases ***", ""])

        # Test cases
        if not tests:
            output_lines.extend(["Empty Test Case", "    No Operation", ""])
        else:
            for test in tests:
                output_lines.extend(self._generate_test_case(test))

        return "\n".join(output_lines)

    def _find_tests_anywhere(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find test structures anywhere in JSON, regardless of format."""
        if not isinstance(data, dict):
            return []

        tests = []

        # Strategy 1: Look for explicit test arrays
        for key, value in data.items():
            if isinstance(value, list) and key.lower() in [
                "tests",
                "testcases",
                "test_cases",
            ]:
                tests.extend([t for t in value if isinstance(t, dict)])

        # Strategy 2: Single test case (has name + steps or testScript)
        if not tests and self._is_single_test(data):
            tests.append(data)

        return tests

    def _find_steps_anywhere(self, test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find step structures anywhere in test data."""
        steps = []

        def search_for_steps(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, list) and key.lower() in [
                        "steps",
                        "teststeps",
                        "actions",
                    ]:
                        steps.extend([s for s in value if isinstance(s, dict)])
                    elif isinstance(value, dict):
                        search_for_steps(value)
            elif isinstance(obj, list):
                for item in obj:
                    search_for_steps(item)

        search_for_steps(test_data)
        return steps

    def _is_single_test(self, data: Dict[str, Any]) -> bool:
        """Check if data looks like a single test case."""
        indicators = [
            "name",
            "description",
            "steps",
            "testscript",
            "objective",
            "summary",
        ]
        return any(key.lower() in indicators for key in data.keys())

    def _extract_documentation(self, data: Dict[str, Any]) -> str:
        """Extract documentation from common fields."""
        doc_fields = ["description", "objective", "summary", "documentation"]

        for field in doc_fields:
            if field in data and data[field]:
                return f"Documentation    {sanitize_robot_string(data[field])}"

        return "Documentation    Tests converted from JSON"

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

    def _detect_libraries_from_steps(self, steps: List[Dict[str, Any]]) -> Set[str]:
        """Detect required Robot Framework libraries from step content."""
        libraries = set()

        # Get all text content from steps
        all_text = []
        for step in steps:
            for value in step.values():
                if isinstance(value, str):
                    all_text.append(value.lower())

        combined_text = " ".join(all_text)

        # Library detection patterns
        if re.search(
            r"\b(?:browser|navigate|click|input|page|web|url|login|button)\b",
            combined_text,
        ):
            libraries.add("SeleniumLibrary")

        if re.search(r"\b(?:ssh|remote|connection|host|server)\b", combined_text):
            libraries.add("SSHLibrary")

        if re.search(
            r"\b(?:command|execute|run|curl|wget|bash|process)\b", combined_text
        ):
            libraries.add("Process")

        if re.search(
            r"\b(?:file|directory|exists|remove|delete|filesystem)\b", combined_text
        ):
            libraries.add("OperatingSystem")

        return libraries

    def _generate_test_case(self, test_data: Dict[str, Any]) -> List[str]:
        """Generate Robot Framework test case."""
        lines = []

        # Test name
        name = self._extract_field(test_data, ["name", "title", "testname", "summary"])
        lines.append(sanitize_robot_string(name or "Unnamed Test"))

        # Documentation
        doc = self._extract_field(
            test_data, ["description", "objective", "documentation"]
        )
        if doc:
            lines.append(f"    [Documentation]    {sanitize_robot_string(doc)}")

        # Steps
        steps = self._find_steps_anywhere(test_data)
        if not steps:
            lines.append("    No Operation  # Placeholder for missing steps")
        else:
            for step in steps:
                lines.extend(self._generate_step_keywords(step))

        lines.append("")
        return lines

    def _extract_field(self, data: Dict[str, Any], field_names: List[str]) -> str:
        """Extract value from first matching field name."""
        for field in field_names:
            if field in data and data[field]:
                return str(data[field])
        return ""

    def _generate_step_keywords(self, step: Dict[str, Any]) -> List[str]:
        """Generate Robot Framework keywords for a step."""
        lines = []

        # Extract step information
        description = self._extract_field(
            step, ["step", "description", "action", "instruction"]
        )
        test_data = self._extract_field(
            step, ["testData", "testdata", "test_data", "data", "input"]
        )
        expected = self._extract_field(
            step,
            [
                "expectedResult",
                "expectedresult",
                "expected_result",
                "expected",
                "result",
            ],
        )

        # Add traceability comments
        if description:
            lines.append(f"    # Step: {description}")
        if test_data:
            lines.extend(self._format_test_data_comment(test_data))
        if expected:
            lines.append(f"    # Expected Result: {expected}")

        # Generate Robot keyword
        keyword_line = self._determine_robot_keyword(description, test_data, expected)
        lines.append(f"    {keyword_line}")

        return lines

    def _format_test_data_comment(self, test_data: str) -> List[str]:
        """Format test data comment, splitting long lines as needed."""
        comment = f"    # Test Data: {test_data}"
        if len(comment) <= 88:
            return [comment]

        # Split long test data comments across multiple lines
        split_points = [", ", "; ", " "]
        best_split = None

        for split_char in split_points:
            # Look for split point that keeps first line under 88 chars
            for i in range(len(test_data)):
                if test_data[i : i + len(split_char)] == split_char:
                    first_part = (
                        f"    # Test Data: {test_data[: i + len(split_char) - 1]}"
                    )
                    if len(first_part) <= 88:
                        best_split = i + len(split_char) - 1
                    else:
                        break
            if best_split:
                break

        if best_split:
            first_part = test_data[:best_split].rstrip()
            second_part = test_data[best_split:].lstrip()
            return [
                f"    # Test Data: {first_part}",
                f"    # Test Data (cont.): {second_part}",
            ]

        # Fallback: split at 75 chars to leave room for prefix
        split_point = 75 - len("    # Test Data: ")
        first_part = test_data[:split_point].rstrip()
        second_part = test_data[split_point:].lstrip()
        return [
            f"    # Test Data: {first_part}",
            f"    # Test Data (cont.): {second_part}",
        ]

    def _determine_robot_keyword(
        self, description: str, test_data: str, expected: str
    ) -> str:
        """Determine Robot Framework keyword based on step content."""
        combined = f"{description} {test_data}".lower()

        # Match against intent patterns
        for pattern, keyword_func in self._intent_patterns.items():
            if re.search(pattern, combined):
                return keyword_func(description, test_data, expected)

        return "No Operation"

    def _build_intent_patterns(self) -> Dict[str, Any]:
        """Build intent pattern to keyword function mapping."""
        return {
            # Command execution (check first for curl/wget)
            r"\b(?:initiate.*download|execute.*curl|run.*wget|curl|wget)\b": lambda d,
            td,
            e: self._command_keyword(td),
            # File operations (most specific patterns first)
            r"\b(?:verify|check|ensure).*file.*exists?\b": lambda d,
            td,
            e: self._file_exists_keyword(td),
            r"\b(?:remove|delete|clean).*file\b": lambda d,
            td,
            e: self._remove_file_keyword(td),
            r"\b(?:get|retrieve).*file\b": lambda d, td, e: self._file_transfer_keyword(
                td
            ),
            r"\btransfer.*file\b": lambda d, td, e: self._file_transfer_keyword(td),
            # SSH operations
            r"\b(?:open|establish|create).*(?:ssh|connection|remote)\b": lambda d,
            td,
            e: self._ssh_connect_keyword(td),
            r"\b(?:close|disconnect|terminate).*(?:connection|ssh)\b": lambda d,
            td,
            e: "Close Connection",
            # Browser operations
            r"\b(?:open|navigate|visit).*(?:browser|page|url|application)\b": lambda d,
            td,
            e: self._browser_keyword(td),
            r"\b(?:go to|navigate to)\b.*\b(?:url|page|site)\b": lambda d,
            td,
            e: self._url_keyword(td),
            r"\b(?:enter|input|type|fill).*username\b": lambda d,
            td,
            e: self._input_keyword("username", td),
            r"\b(?:enter|input|type|fill).*password\b": lambda d,
            td,
            e: self._password_keyword(td),
            r"\b(?:click|press|tap).*(?:button|element)\b": lambda d,
            td,
            e: self._click_keyword(d),
            # Content verification
            r"\b(?:verify|check|ensure|assert).*(?:content|contains|displays)\b": (
                lambda d, td, e: self._verify_keyword(e or td)
            ),
        }

    def _browser_keyword(self, test_data: str) -> str:
        """Generate browser opening keyword with Chrome options for CI/headless."""
        url_match = re.search(r"https?://[^\s,]+", test_data)
        url = url_match.group(0) if url_match else config.TEST_LOGIN_URL
        # Add Chrome options to prevent session conflicts in CI/testing environments
        # Using the correct format for SeleniumLibrary Chrome options
        chrome_options = (
            "add_argument('--no-sandbox'); "
            "add_argument('--disable-dev-shm-usage'); "
            "add_argument('--disable-gpu'); "
            "add_argument('--headless'); "
            "add_argument('--disable-web-security'); "
            "add_argument('--allow-running-insecure-content')"
        )
        return f"Open Browser    {url}    chrome    options={chrome_options}"

    def _url_keyword(self, test_data: str) -> str:
        """Generate URL navigation keyword."""
        url_match = re.search(r"https?://[^\s,]+", test_data)
        if url_match:
            return f"Go To    {url_match.group(0)}"
        return "Go To"

    def _input_keyword(self, field_type: str, test_data: str) -> str:
        """Generate input keyword."""
        value = self._extract_value_from_data(test_data)
        return (
            f"Input Text    id={field_type}    {value}"
            if value
            else f"Input Text    id={field_type}"
        )

    def _password_keyword(self, test_data: str) -> str:
        """Generate password input keyword."""
        value = self._extract_value_from_data(test_data)
        return (
            f"Input Password    id=password    {value}"
            if value
            else "Input Password    id=password"
        )

    def _click_keyword(self, description: str) -> str:
        """Generate click keyword."""
        desc_lower = description.lower()
        if "login" in desc_lower and "button" in desc_lower:
            return "Click Button    id=login_button"
        if "button" in desc_lower:
            return "Click Button    id=submit_button"
        return "Click Element    id=clickable_element"

    def _ssh_connect_keyword(self, test_data: str) -> str:
        """Generate SSH connection keyword."""
        host = self._extract_pattern(test_data, r"(?:host|server):\s*([^,\s]+)")
        username = self._extract_pattern(test_data, r"username:\s*([^,\s]+)")
        password = self._extract_pattern(test_data, r"password:\s*([^,\s]+)")

        args = [host] if host else []
        if username and password:
            args.extend([username, password])

        return f"Open Connection    {'    '.join(args)}" if args else "Open Connection"

    def _file_transfer_keyword(self, test_data: str) -> str:
        """Generate file transfer keyword."""
        remote = self._extract_pattern(test_data, r"Remote File Path:\s*([^,\s]+)")
        local = self._extract_pattern(test_data, r"Local Destination Path:\s*([^,\s]+)")

        args = []
        if remote:
            args.append(remote)
        if local:
            args.append(local)

        return f"Get File    {'    '.join(args)}" if args else "Get File"

    def _file_exists_keyword(self, test_data: str) -> str:
        """Generate file exists verification keyword."""
        # Look for explicit file paths
        path = self._extract_pattern(test_data, r"/[^\s,]+|[a-zA-Z]:\\[^\s,]+")
        if not path:
            # Try alternative patterns for file paths in test data
            path = self._extract_pattern(test_data, r"at\s+([^\s,]+)")
        if not path:
            # Look for file names with extensions
            path_match = re.search(
                r"([a-zA-Z0-9_.-]+\.txt|[a-zA-Z0-9_.-]+\.json|"
                r"[a-zA-Z0-9_.-]+\.[a-zA-Z]+)",
                test_data,
            )
            if path_match:
                path = path_match.group(1)
        return f"File Should Exist    {path}" if path else "File Should Exist"

    def _remove_file_keyword(self, test_data: str) -> str:
        """Generate file removal keyword."""
        # First try to extract from "rm path" or "Command: rm path" patterns
        path = self._extract_pattern(test_data, r"rm\s+([^\s]+)")
        if not path:
            # Try generic file path extraction
            path = self._extract_pattern(test_data, r"/[^\s,]+|[a-zA-Z]:\\[^\s,]+")
        return f"Remove File    {path}" if path else "Remove File"

    def _command_keyword(self, test_data: str) -> str:
        """Generate command execution keyword."""
        command = self._extract_pattern(test_data, r"command:\s*(.+)")
        if command:
            cmd_parts = command.strip().split()
            return f"Run Process    {'    '.join(cmd_parts)}"
        return "Run Process"

    def _verify_keyword(self, content: str) -> str:
        """Generate content verification keyword."""
        if content and content not in ["N/A", "n/a"]:
            return f"Page Should Contain    {content}"
        return "Page Should Contain"

    def _extract_value_from_data(self, test_data: str) -> str:
        """Extract value from test data."""
        if ":" in test_data:
            return test_data.split(":", 1)[1].strip()
        return test_data.strip() if test_data else ""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract first match from regex pattern."""
        if not text:
            return ""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match and match.lastindex else ""


# File I/O functions
def load_json(file_path: str) -> Dict[str, Any]:
    """Load and validate JSON file."""
    validated_path = validate_safe_path(file_path)

    try:
        with open(validated_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("JSON content must be a dictionary.")
            return data
    except FileNotFoundError as e:
        raise FileNotFoundError(sanitize_error_message(str(e), file_path)) from e
    except json.JSONDecodeError as e:
        raise ValueError(
            sanitize_error_message(f"Could not parse JSON: {e.msg}", file_path)
        ) from e


def save_robot_file(content: str, file_path: str) -> None:
    """Save Robot Framework content to file."""
    if not isinstance(content, str):
        raise TypeError(f"Content must be a string, got {type(content).__name__}")

    validated_path = validate_safe_path(file_path)

    try:
        with open(validated_path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        raise IOError(sanitize_error_message(str(e), file_path)) from e


def convert_file(input_file: str, output_file: str) -> None:
    """Convert single JSON file to Robot Framework."""
    if not isinstance(input_file, str):
        raise TypeError(
            f"Input file path must be a string, got {type(input_file).__name__}"
        )

    if not isinstance(output_file, str):
        raise TypeError(
            f"Output file path must be a string, got {type(output_file).__name__}"
        )

    if not input_file.strip():
        raise ValueError("Input file path cannot be empty or whitespace")

    if not output_file.strip():
        raise ValueError("Output file path cannot be empty or whitespace")

    json_data = load_json(input_file)
    converter = JsonToRobotConverter()
    robot_content = converter.convert_json_data(json_data)
    save_robot_file(robot_content, output_file)


def convert_multiple_files(input_files: List[str], output_dir: str) -> None:
    """Convert multiple JSON files to Robot Framework files."""
    if not isinstance(input_files, list):
        raise TypeError(f"Input files must be a list, got {type(input_files).__name__}")

    if not isinstance(output_dir, str):
        raise TypeError(
            f"Output directory must be a string, got {type(output_dir).__name__}"
        )

    if not input_files:
        raise ValueError("Input files list cannot be empty")

    os.makedirs(output_dir, exist_ok=True)

    for input_file in input_files:
        output_filename = Path(input_file).stem + ".robot"
        output_path = Path(output_dir) / output_filename
        convert_file(input_file, str(output_path))


def convert_directory(input_dir: str, output_dir: str) -> None:
    """Convert all JSON files in directory to Robot Framework files."""
    if not isinstance(input_dir, str):
        raise TypeError(
            f"Input directory must be a string, got {type(input_dir).__name__}"
        )

    if not isinstance(output_dir, str):
        raise TypeError(
            f"Output directory must be a string, got {type(output_dir).__name__}"
        )
    try:
        all_files = Path(input_dir).rglob("*")
        json_files = [
            str(f) for f in all_files if f.is_file() and f.suffix.lower() == ".json"
        ]
    except Exception as e:
        raise ValueError(f"Error accessing directory {input_dir}: {e}") from e

    if not json_files:
        raise ValueError(f"No JSON files found in directory: {input_dir}")

    convert_multiple_files(json_files, output_dir)
