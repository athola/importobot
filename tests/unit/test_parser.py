"""Unit tests for JSON parsing functionality."""

from importobot.core.parser import parse_json


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
