"""Unit tests for JSON parsing functionality."""

import json
from pathlib import Path

import pytest

from importobot.core.parser import _needs_ssh_library, load_and_parse_json, parse_json


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
        # Use pathlib for robust cross-platform path resolution
        test_data_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "json"
            / "new_zephyr_test_data.json"
        )
        with open(test_data_path, "r", encoding="utf-8") as f:
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
            with pytest.raises(expected_exception):
                load_and_parse_json(malformed_json)


class TestSSHLibraryDetection:
    """Tests for SSH library detection functionality."""

    def test_needs_ssh_library_ssh_connect_patterns(self):
        """Test detection of SSH connection patterns."""
        test_cases = [
            {"test": "ssh connect to server"},
            {"test": "SSH LOGIN to remote host"},
            {"test": "ssh command execution"},
            {"test": "ssh execute on remote"},
            {"test": "connect to remote host"},
            {"test": "remote connect to server"},
            {"test": "remote login process"},
        ]

        for test_data in test_cases:
            assert _needs_ssh_library(test_data), (
                f"Should detect SSH need in: {test_data}"
            )

    def test_needs_ssh_library_file_transfer_patterns(self):
        """Test detection of file transfer patterns."""
        test_cases = [
            {"test": "scp file transfer"},
            {"test": "sftp upload file"},
            {"test": "transfer file to remote server"},
            {"test": "transfer file via ssh"},
        ]

        for test_data in test_cases:
            assert _needs_ssh_library(test_data), (
                f"Should detect SSH need in: {test_data}"
            )

    def test_needs_ssh_library_connection_management(self):
        """Test detection of connection management patterns."""
        test_cases = [
            {"test": "open ssh connection"},
            {"test": "open connection to remote"},
            {"test": "close ssh connection"},
            {"test": "close connection"},
            {"test": "execute remote command"},
            {"test": "execute ssh command"},
        ]

        for test_data in test_cases:
            assert _needs_ssh_library(test_data), (
                f"Should detect SSH need in: {test_data}"
            )

    def test_needs_ssh_library_standalone_ssh_mention(self):
        """Test detection of standalone SSH mentions."""
        test_cases = [
            {"test": "using ssh for testing"},
            {"test": "configure ssh settings"},
            {"test": "ssh is required"},
        ]

        for test_data in test_cases:
            assert _needs_ssh_library(test_data), (
                f"Should detect SSH need in: {test_data}"
            )

    def test_needs_ssh_library_exclude_retrieve_file(self):
        """Test exclusion of 'Retrieve File From Remote Host' pattern."""
        test_data = {"test": "Retrieve File From Remote Host operation"}
        assert not _needs_ssh_library(test_data), (
            "Should NOT detect SSH need for 'Retrieve File From Remote Host'"
        )

    def test_needs_ssh_library_false_positives(self):
        """Test avoidance of false positive SSH detections."""
        test_cases = [
            {"test": "washing dishes in kitchen"},  # 'ssh' as part of word
            {"test": "pushing code to repository"},  # 'ssh' as part of word
            {"test": "web browser testing"},  # No SSH-related content
            {"test": "database connection"},  # Non-SSH connection
            {"test": "http request testing"},  # Different protocol
        ]

        for test_data in test_cases:
            assert not _needs_ssh_library(test_data), (
                f"Should NOT detect SSH need in: {test_data}"
            )

    def test_needs_ssh_library_case_insensitive(self):
        """Test case-insensitive detection."""
        test_cases = [
            {"test": "SSH Connect To Server"},
            {"test": "ssh COMMAND execution"},
            {"test": "Remote LOGIN Process"},
            {"test": "SCP File Transfer"},
        ]

        for test_data in test_cases:
            assert _needs_ssh_library(test_data), (
                f"Should detect SSH need (case insensitive) in: {test_data}"
            )

    def test_needs_ssh_library_nested_data_structures(self):
        """Test detection in nested JSON structures."""
        nested_data = {
            "tests": [
                {
                    "name": "SSH Test",
                    "steps": [
                        {"action": "ssh connect to server"},
                        {"expectedResult": "connection established"},
                    ],
                }
            ]
        }
        assert _needs_ssh_library(nested_data), (
            "Should detect SSH need in nested structures"
        )

    def test_needs_ssh_library_complex_scenarios(self):
        """Test detection in complex realistic scenarios."""
        complex_scenarios = [
            {
                "tests": [
                    {
                        "name": "Server Deployment Test",
                        "steps": [
                            {"action": "Connect to remote server via SSH"},
                            {"action": "Execute deployment commands"},
                            {"expectedResult": "Deployment successful"},
                        ],
                    }
                ]
            },
            {
                "testScript": {
                    "steps": [
                        {"description": "Open SSH connection to test server"},
                        {"description": "Transfer configuration files using SCP"},
                    ]
                }
            },
        ]

        for scenario in complex_scenarios:
            assert _needs_ssh_library(scenario), (
                f"Should detect SSH need in complex scenario: {scenario}"
            )

    def test_needs_ssh_library_edge_cases(self):
        """Test edge cases for SSH detection."""
        edge_cases = [
            ({}, False),  # Empty data
            ({"test": ""}, False),  # Empty string
            ({"test": None}, False),  # None value (will be converted to string)
            ({"test": "ssh"}, True),  # Minimal SSH mention
            ({"test": "ssh "}, True),  # SSH with space
            ({"test": " ssh"}, True),  # SSH with leading space
        ]

        for test_data, expected in edge_cases:
            result = _needs_ssh_library(test_data)
            assert result == expected, (
                f"Expected {expected} for {test_data}, got {result}"
            )

    def test_needs_ssh_library_early_fail_conditions(self):
        """Test early fail conditions for _needs_ssh_library function."""
        # Test None input
        assert not _needs_ssh_library(None), "Should return False for None input"

        # Test non-dict inputs
        invalid_inputs = ["string", 123, [], True, 45.67]
        for invalid_input in invalid_inputs:
            assert not _needs_ssh_library(invalid_input), (
                f"Should return False for non-dict input: {invalid_input}"
            )
