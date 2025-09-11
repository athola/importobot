"""Unit tests for file conversion functionality."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import mock_open, patch

import pytest

from importobot.core.converter import (
    convert_to_robot,
    load_json,
    save_robot_file,
)


class TestFileConverter:
    """Tests for the file conversion utilities."""

    def test_load_json_success(self):
        """Verifies successful loading of a valid JSON file."""
        sample_data = {"tests": []}
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_data))):
            result = load_json("test.json")
            assert result == sample_data

    def test_load_json_handles_file_not_found(self):
        """Verifies that a FileNotFoundError is raised for a missing file."""
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError()
            with pytest.raises(FileNotFoundError):
                load_json("nonexistent.json")

    def test_load_json_handles_invalid_json(self):
        """Verifies that a ValueError is raised for malformed JSON."""
        with patch("builtins.open", mock_open(read_data="{ invalid json }")):
            with pytest.raises(ValueError):
                load_json("invalid.json")

    def test_save_file_success(self):
        """Verifies that a file is written to correctly."""
        with patch("builtins.open", mock_open()) as mock_file:
            save_robot_file("content", "output.robot")
            # Path gets resolved to absolute path
            call_args = mock_file.call_args
            assert call_args[0][1] == "w"
            assert call_args[1]["encoding"] == "utf-8"
            assert call_args[0][0].endswith("output.robot")

    def test_save_file_handles_io_error(self):
        """Verifies that an IOError is raised on a write error."""
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("Permission denied")
            with pytest.raises(IOError):
                save_robot_file("content", "output.robot")

    @patch("importobot.core.converter.load_json")
    @patch("importobot.core.converter.save_robot_file")
    @patch("importobot.core.converter.parse_json")
    def test_full_conversion_success(self, mock_parse, mock_save, mock_load):
        """Tests the end-to-end conversion process with mocks."""
        mock_load.return_value = {"tests": []}
        mock_parse.return_value = "*** Test Cases ***"

        convert_to_robot("input.json", "output.robot")

        mock_load.assert_called_once_with("input.json")
        mock_parse.assert_called_once_with({"tests": []})
        mock_save.assert_called_once_with("*** Test Cases ***", "output.robot")

    @patch("importobot.core.converter.load_json")
    def test_full_conversion_handles_load_error(self, mock_load):
        """Ensures that a file loading error propagates correctly."""
        mock_load.side_effect = FileNotFoundError("File not found")

        with pytest.raises(FileNotFoundError):
            convert_to_robot("nonexistent.json", "output.robot")

    def test_load_json_handles_various_malformed_json(self):
        """Verifies ValueError is raised for various malformed JSON scenarios."""
        malformed_cases = [
            ("{ incomplete json", r"Could not parse JSON:"),
            ('{ "key": }', r"Could not parse JSON:"),
            ('{ "key": "value", }', r"Could not parse JSON:"),  # Trailing comma
            ('{ "key" "value" }', r"Could not parse JSON:"),  # Missing colon
            (
                "{ 'single_quotes': 'invalid' }",
                r"Could not parse JSON:",
            ),  # Single quotes
            ('{ key: "value" }', r"Could not parse JSON:"),  # Unquoted keys
            ("", r"Could not parse JSON:"),  # Empty string
            ("null", "JSON content must be a dictionary."),  # Just null
            ("undefined", r"Could not parse JSON:"),  # Invalid literal
            ("{{}", r"Could not parse JSON:"),  # Double opening brace
            ('{ "key": "unclosed string }', r"Could not parse JSON:"),
        ]

        for malformed_json, expected_match in malformed_cases:
            with patch("builtins.open", mock_open(read_data=malformed_json)):
                with pytest.raises(ValueError, match=expected_match):
                    load_json("invalid.json")

    def test_load_json_handles_encoding_issues(self):
        """Verifies handling of encoding-related issues."""
        # Test with binary data that's not valid UTF-8
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = UnicodeDecodeError(
                "utf-8", b"\x80\x81", 0, 1, "invalid start byte"
            )
            with pytest.raises(UnicodeDecodeError):
                load_json("encoding_issue.json")

    def test_load_json_handles_permission_denied(self):
        """Verifies handling of permission denied errors."""
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")
            with pytest.raises(PermissionError):
                load_json("no_permission.json")

    def test_save_file_handles_various_io_errors(self):
        """Verifies handling of various IO errors during file writing."""
        io_errors = [
            PermissionError("Permission denied"),
            OSError("Disk full"),
            IsADirectoryError("Is a directory"),
            FileExistsError("File exists"),
        ]

        for error in io_errors:
            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = error
                with pytest.raises(IOError):
                    save_robot_file("content", "output.robot")

    def test_save_file_handles_special_characters(self):
        """Verifies saving files with special characters and encoding."""
        special_content = "Content with special chars: áéíóú ñ 中文 🚀\nNewlines\tTabs"
        with patch("builtins.open", mock_open()) as mock_file:
            save_robot_file(special_content, "output.robot")
            # Path gets resolved to absolute path
            call_args = mock_file.call_args
            assert call_args[0][1] == "w"
            assert call_args[1]["encoding"] == "utf-8"
            assert call_args[0][0].endswith("output.robot")
            mock_file().write.assert_called_once_with(special_content)

    @patch("importobot.core.converter.parse_json")
    @patch("importobot.core.converter.save_robot_file")
    def test_convert_propagates_parse_errors(self, mock_save, mock_parse):
        """Ensures parser errors propagate through conversion process."""
        with patch("importobot.core.converter.load_json", return_value={}):
            mock_parse.side_effect = AttributeError("Invalid data structure")

            with pytest.raises(AttributeError):
                convert_to_robot("input.json", "output.robot")

    @patch("importobot.core.converter.load_json")
    @patch("importobot.core.converter.parse_json")
    def test_convert_propagates_save_errors(self, mock_parse, mock_load):
        """Ensures save errors propagate through conversion process."""
        mock_load.return_value = {"tests": []}
        mock_parse.return_value = "*** Test Cases ***"

        with patch("importobot.core.converter.save_robot_file") as mock_save:
            mock_save.side_effect = IOError("Write failed")

            with pytest.raises(IOError):
                convert_to_robot("input.json", "output.robot")

    def test_load_json_with_extremely_large_file(self):
        """Verifies handling of memory issues with large files."""
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = MemoryError("Not enough memory")
            with pytest.raises(MemoryError):
                load_json("huge_file.json")

    def test_path_resolution(self):
        """Verifies load_json and save_robot_file handle relative paths correctly."""
        sample_data = {"test": "data"}
        robot_content = "*** Test Cases ***\nTest Case 1\n    Log    Hello"

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test loading from a relative path
            input_file_path = tmp_path / "input.json"
            input_file_path.write_text(json.dumps(sample_data))
            loaded_data = load_json(str(input_file_path))
            assert loaded_data == sample_data

            # Test saving to a relative path
            output_file_path = tmp_path / "output.robot"
            save_robot_file(robot_content, str(output_file_path))
            assert output_file_path.read_text() == robot_content

            # Test loading from a nested relative path
            nested_dir = tmp_path / "nested"
            nested_dir.mkdir()
            nested_input_file_path = nested_dir / "nested_input.json"
            nested_input_file_path.write_text(json.dumps(sample_data))
            loaded_data_nested = load_json(str(nested_input_file_path))
            assert loaded_data_nested == sample_data

            # Test saving to a nested relative path
            nested_output_file_path = nested_dir / "nested_output.robot"
            save_robot_file(robot_content, str(nested_output_file_path))
            assert nested_output_file_path.read_text() == robot_content


class TestEarlyFailConditions:
    """Tests for early fail condition validation in converter functions."""

    def test_load_json_early_fail_invalid_type(self):
        """Test that load_json fails early for invalid input types."""
        invalid_inputs = [None, 123, [], {}, True, b'binary']

        for invalid_input in invalid_inputs:
            with pytest.raises(TypeError, match="File path must be a string"):
                load_json(invalid_input)

    def test_load_json_early_fail_empty_path(self):
        """Test that load_json fails early for empty paths."""
        empty_paths = ["", "   ", "\t", "\n"]

        for empty_path in empty_paths:
            with pytest.raises(ValueError, match="File path cannot be empty or whitespace"):
                load_json(empty_path)

    def test_save_robot_file_early_fail_invalid_content_type(self):
        """Test that save_robot_file fails early for invalid content types."""
        invalid_contents = [None, 123, [], {}, True, b'binary']

        for invalid_content in invalid_contents:
            with pytest.raises(TypeError, match="Content must be a string"):
                save_robot_file(invalid_content, "valid_path.robot")

    def test_save_robot_file_early_fail_invalid_path_type(self):
        """Test that save_robot_file fails early for invalid path types."""
        invalid_paths = [None, 123, [], {}, True, b'binary']

        for invalid_path in invalid_paths:
            with pytest.raises(TypeError, match="File path must be a string"):
                save_robot_file("valid content", invalid_path)

    def test_save_robot_file_early_fail_empty_path(self):
        """Test that save_robot_file fails early for empty paths."""
        empty_paths = ["", "   ", "\t", "\n"]

        for empty_path in empty_paths:
            with pytest.raises(ValueError, match="File path cannot be empty or whitespace"):
                save_robot_file("valid content", empty_path)

    def test_convert_to_robot_early_fail_invalid_input_type(self):
        """Test that convert_to_robot fails early for invalid input types."""
        invalid_inputs = [None, 123, [], {}, True, b'binary']

        for invalid_input in invalid_inputs:
            with pytest.raises(TypeError, match="Input file path must be a string"):
                convert_to_robot(invalid_input, "output.robot")

    def test_convert_to_robot_early_fail_invalid_output_type(self):
        """Test that convert_to_robot fails early for invalid output types."""
        invalid_outputs = [None, 123, [], {}, True, b'binary']

        for invalid_output in invalid_outputs:
            with pytest.raises(TypeError, match="Output file path must be a string"):
                convert_to_robot("input.json", invalid_output)

    def test_convert_to_robot_early_fail_empty_paths(self):
        """Test that convert_to_robot fails early for empty paths."""
        empty_paths = ["", "   ", "\t", "\n"]

        # Test empty input path
        for empty_path in empty_paths:
            with pytest.raises(ValueError, match="Input file path cannot be empty or whitespace"):
                convert_to_robot(empty_path, "output.robot")

        # Test empty output path
        for empty_path in empty_paths:
            with pytest.raises(ValueError, match="Output file path cannot be empty or whitespace"):
                convert_to_robot("input.json", empty_path)
