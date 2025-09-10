"""Unit tests for file conversion functionality."""

import json
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
            mock_file.assert_called_once_with("output.robot", "w", encoding="utf-8")

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
