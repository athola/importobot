"""Unit tests for JSON parsing functionality."""

import json
from pathlib import Path
from typing import Any

import pytest

from importobot import exceptions
from importobot.core.converter import JsonToRobotConverter


class TestParser:
    """Tests for the JSON parser."""

    def test_parser_handles_basic_case(self):
        """Verifies parsing of a standard test case."""
        sample_data = {
            "tests": [
                {
                    "name": "Sample Test Case",
                    "description": "A sample test case description",
                }
            ]
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(sample_data)
        assert "Sample Test Case" in result
        assert "A sample test case description" in result
        assert "*** Test Cases ***" in result

    def test_parser_handles_empty_input(self):
        """Verifies that empty JSON still produces a valid structure."""
        converter = JsonToRobotConverter()
        result = converter.convert_json_data({})
        assert "*** Test Cases ***" in result
        assert "Unnamed Test" not in result

    def test_parser_handles_steps(self):
        """Verifies that test steps are included in the output."""
        sample_data = {
            "tests": [
                {
                    "name": "Test with Steps",
                    "steps": [{"action": "Do something"}],
                }
            ]
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(sample_data)
        assert "Test with Steps" in result
        assert "# Step: Do something" in result

    def test_parser_handles_missing_fields(self):
        """Verifies default values are used for missing optional fields."""
        sample_data = {"tests": [{"steps": [{"action": "Do something"}]}]}
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(sample_data)
        assert "Unnamed Test" in result

    def test_parser_handles_zephyr_data(self):
        """Verifies parsing of Zephyr-like test data."""
        # Use pathlib for robust cross-platform path resolution
        test_data_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "json"
            / "browser_login.json"
        )
        with open(test_data_path, "r", encoding="utf-8") as f:
            zephyr_data = json.load(f)
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(zephyr_data)
        assert "Verify User Login Functionality" in result
        assert "Navigate to the application login page." in result
        assert "Enter valid username and password." in result
        assert "Click the 'Login' button." in result
        assert (
            "The login page is displayed with username and password fields." in result
        )
        assert "The username and password fields are populated." in result
        assert (
            "User is successfully logged in and redirected "
            "to the dashboard page." in result
        )

    def test_parser_handles_null_input(self):
        """Verifies parser handles None input gracefully."""
        converter = JsonToRobotConverter()
        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_data(None)  # type: ignore

    def test_parser_handles_non_dict_input(self):
        """Verifies parser handles non-dictionary input."""
        converter = JsonToRobotConverter()
        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_data("invalid string input")  # type: ignore

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_data([1, 2, 3])  # type: ignore

        with pytest.raises(exceptions.ValidationError):
            converter.convert_json_data(42)  # type: ignore

    def test_parser_handles_invalid_test_structure(self) -> None:
        """Verifies parser handles malformed test structures."""
        # Tests as non-list
        malformed_data: dict[str, Any] = {"tests": "not a list"}
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(malformed_data)
        assert "Empty Test Case" in result

        # Tests with invalid items
        malformed_data = {"tests": [None, "invalid", {}]}
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(malformed_data)
        assert "Unnamed Test" in result

    def test_parser_handles_invalid_steps_structure(self) -> None:
        """Verifies parser handles malformed step structures."""
        malformed_data: dict[str, Any] = {
            "tests": [{"name": "Test with Invalid Steps", "steps": "not a list"}]
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(malformed_data)
        assert "Test with Invalid Steps" in result
        assert "No Operation" in result

        # Steps with invalid items
        malformed_data = {
            "tests": [
                {
                    "name": "Test with Malformed Steps",
                    "steps": [None, "invalid", {"action": None}],
                }
            ]
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(malformed_data)
        assert "Test with Malformed Steps" in result

    def test_parser_handles_zephyr_malformed_structure(self) -> None:
        """Verifies parser handles malformed Zephyr-style data."""
        # Missing testScript
        malformed_data: dict[str, Any] = {
            "name": "Malformed Zephyr Test",
            "objective": "Test objective",
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(malformed_data)
        assert "Malformed Zephyr Test" in result

        # Invalid testScript structure
        malformed_data = {"name": "Invalid TestScript", "testScript": "not a dict"}

    def test_parser_handles_special_characters_in_strings(self):
        """Verifies parser handles special characters and encoding issues."""
        special_data = {
            "tests": [
                {
                    "name": "Test with Special Chars: áéíóú ñ 中文 🚀",
                    "description": (
                        "Description with quotes 'single' \"double\" and \\backslashes"
                    ),
                    "steps": [
                        {
                            "action": "Action with newlines\nand\ttabs",
                            "expectedResult": "Result with {braces} and [brackets]",
                        }
                    ],
                }
            ]
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(special_data)
        assert "Test with Special Chars" in result
        assert "# Step: Action with newlines\nand\ttabs" in result
        assert "# Expected Result: Result with {braces} and [brackets]" in result

    def test_parser_handles_deeply_nested_malformed_data(self):
        """Verifies parser handles deeply nested malformed structures."""
        deeply_nested = {
            "tests": [
                {
                    "name": "Deep Nesting Test",
                    "testScript": {
                        "steps": [
                            {
                                "description": "Valid step",
                                "testData": {"nested": {"data": {"very": "deep"}}},
                                "expectedResult": "Should work",
                            }
                        ]
                    },
                }
            ]
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(deeply_nested)
        assert "Deep Nesting Test" in result
        assert "Valid step" in result

    def test_parser_detects_ssh_library(self):
        """Verifies that SSHLibrary is detected and added when SSH-related
        keywords are present."""
        ssh_data = {
            "name": "SSH Test Case",
            "steps": [
                {"description": "Open SSH Connection"},
                {"description": "Execute Command ssh -l user host"},
                {"description": "Close SSH Connection"},
            ],
        }
        converter = JsonToRobotConverter()
        result = converter.convert_json_data(ssh_data)
        assert "Library    SSHLibrary" in result

    def test_load_and_parse_json_malformed_input(self):
        """Verifies that load_and_parse_json raises ValueError for malformed JSON."""
        malformed_jsons = [
            ('{"key": "value",}', exceptions.ParseError),  # Trailing comma
            ('{"key": "value"', exceptions.ParseError),  # Unclosed brace
            ("[1, 2, 3", exceptions.ParseError),  # Unclosed bracket
            ('"just a string"', exceptions.ValidationError),  # Not an object or array
            ("", exceptions.ValidationError),  # Empty string
            ("null", exceptions.ValidationError),  # Null
            ("true", exceptions.ValidationError),  # Boolean
            ("123", exceptions.ValidationError),  # Number
            (
                '{"key": "value" "another_key": "another_value"}',
                exceptions.ParseError,
            ),  # Missing comma between key-value pairs
            (
                '{"key": "value" "another_key": "another_value"}',
                exceptions.ParseError,
            ),  # Missing quotes around key
        ]

        for malformed_json, expected_exception in malformed_jsons:
            with pytest.raises(expected_exception):
                converter = JsonToRobotConverter()
                converter.convert_json_string(malformed_json)
