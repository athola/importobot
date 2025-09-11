"""Unit tests for JSON parsing functionality."""

import pytest

from importobot.core.parser import load_and_parse_json, parse_json


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
        result = parse_json(sample_data)
        assert "Sample Test Case" in result
        assert "A sample test case description" in result
        assert "*** Test Cases ***" in result

    def test_parser_handles_empty_input(self):
        """Verifies that empty JSON still produces a valid structure."""
        result = parse_json({})
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
        result = parse_json(sample_data)
        assert "Test with Steps" in result
        assert "# TODO: Implement step" in result

    def test_parser_handles_missing_fields(self):
        """Verifies default values are used for missing optional fields."""
        sample_data = {"tests": [{"steps": [{"action": "Do something"}]}]}
        result = parse_json(sample_data)
        assert "Unnamed Test" in result

    def test_parser_handles_zephyr_data(self):
        """Verifies parsing of Zephyr-like test data."""
        import json
        from pathlib import Path

        # Use pathlib for robust cross-platform path resolution
        test_data_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "json"
            / "new_zephyr_test_data.json"
        )
        with open(test_data_path, "r") as f:
            zephyr_data = json.load(f)
        result = parse_json(zephyr_data)
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
        with pytest.raises(TypeError):
            parse_json(None)

    def test_parser_handles_non_dict_input(self):
        """Verifies parser handles non-dictionary input."""
        with pytest.raises(TypeError):
            parse_json("invalid string input")

        with pytest.raises(TypeError):
            parse_json([1, 2, 3])

        with pytest.raises(TypeError):
            parse_json(42)

    def test_parser_handles_invalid_test_structure(self):
        """Verifies parser handles malformed test structures."""
        # Tests as non-list
        malformed_data = {"tests": "not a list"}
        result = parse_json(malformed_data)
        assert "Empty Test Case" in result

        # Tests with invalid items
        malformed_data = {"tests": [None, "invalid", {}]}
        result = parse_json(malformed_data)
        assert "Unnamed Test" in result

    def test_parser_handles_invalid_steps_structure(self):
        """Verifies parser handles malformed step structures."""
        malformed_data = {
            "tests": [{"name": "Test with Invalid Steps", "steps": "not a list"}]
        }
        result = parse_json(malformed_data)
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
        result = parse_json(malformed_data)
        assert "Test with Malformed Steps" in result

    def test_parser_handles_zephyr_malformed_structure(self):
        """Verifies parser handles malformed Zephyr-style data."""
        # Missing testScript
        malformed_data = {
            "name": "Malformed Zephyr Test",
            "objective": "Test objective",
        }
        result = parse_json(malformed_data)
        assert "Malformed Zephyr Test" in result
        assert "No Operation" in result

        # Invalid testScript structure
        malformed_data = {"name": "Invalid TestScript", "testScript": "not a dict"}
        result = parse_json(malformed_data)
        assert "Invalid TestScript" in result

        # Malformed steps in testScript
        malformed_data = {
            "name": "Invalid Steps in TestScript",
            "testScript": {"type": "STEP_BY_STEP", "steps": "not a list"},
        }
        result = parse_json(malformed_data)
        assert "Invalid Steps in TestScript" in result

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
        result = parse_json(special_data)
        assert "Test with Special Chars" in result
        assert "Action with newlines" in result
        assert "Result with {braces}" in result

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
        result = parse_json(deeply_nested)
        assert "Deep Nesting Test" in result
        assert "Valid step" in result

    def test_load_and_parse_json_malformed_input(self):
        """Verifies that load_and_parse_json raises ValueError for malformed JSON."""
        malformed_jsons = [
            ('{"key": "value",}', ValueError),  # Trailing comma
            ('{"key": "value"', ValueError),  # Unclosed brace
            ("[1, 2, 3", ValueError),  # Unclosed bracket
            ('"just a string"', TypeError),  # Not an object or array
            ("", ValueError),  # Empty string
            ("null", TypeError),  # Null
            ("true", TypeError),  # Boolean
            ("123", TypeError),  # Number
            (
                '{"key": "value" "another_key": "another_value"}',
                ValueError,
            ),  # Missing comma between key-value pairs
            (
                '{"key": "value" "another_key": "another_value"}',
                ValueError,
            ),  # Missing quotes around key
        ]

        for malformed_json, expected_exception in malformed_jsons:
            with pytest.raises(
                expected_exception,
                match=(
                    "Malformed JSON input" if expected_exception is ValueError else None
                ),
            ):
                load_and_parse_json(malformed_json)
