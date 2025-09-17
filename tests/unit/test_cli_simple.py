"""Simplified tests for the command-line interface after refactoring."""

from unittest.mock import patch

import pytest

from importobot.__main__ import main
from importobot.cli.handlers import detect_input_type, requires_output_directory
from importobot.cli.parser import create_parser
from importobot.exceptions import ImportobotError


class TestCLIBasics:
    """Basic CLI functionality tests."""

    def test_create_parser(self):
        """Test that parser creates correctly."""
        parser = create_parser()
        assert parser is not None
        assert (
            parser.description
            == "Convert test cases from JSON to Robot Framework format"
        )

    def test_parser_help(self):
        """Test parser help doesn't crash."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    @patch("sys.argv", ["importobot"])
    def test_insufficient_args(self):
        """Test CLI fails with insufficient arguments."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2  # type: ignore[attr-defined]

    @patch("sys.argv", ["importobot", "too", "many", "args", "here"])
    def test_too_many_args(self):
        """Test CLI fails with too many arguments."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2  # type: ignore[attr-defined]


class TestInputDetection:
    """Test input type detection logic."""

    def test_detect_input_type_error(self):
        """Test detection of non-existent files."""
        input_type, files = detect_input_type("/nonexistent/file.json")
        assert input_type == "error"
        assert files == []

    def test_requires_output_directory(self):
        """Test output directory requirement logic."""
        assert requires_output_directory("directory", 1) is True
        assert requires_output_directory("wildcard", 2) is True
        assert requires_output_directory("file", 1) is False


class TestCLIIntegration:
    """Integration tests with mocked handlers."""

    @patch("sys.argv", ["importobot", "input.json", "output.robot"])
    @patch("importobot.__main__.handle_positional_args")
    def test_positional_args_called(self, mock_handler):
        """Test that positional argument handler is called."""
        main()
        mock_handler.assert_called_once()

    @patch("sys.argv", ["importobot", "--files", "test.json", "--output", "out.robot"])
    @patch("importobot.__main__.handle_files_conversion")
    def test_files_handler_called(self, mock_handler):
        """Test that files handler is called."""
        main()
        mock_handler.assert_called_once()

    @patch("sys.argv", ["importobot", "--directory", "/input", "--output", "/output"])
    @patch("importobot.__main__.handle_directory_conversion")
    def test_directory_handler_called(self, mock_handler):
        """Test that directory handler is called."""
        main()
        mock_handler.assert_called_once()


class TestErrorHandling:
    """Test error handling in CLI."""

    @patch("sys.argv", ["importobot", "input.json", "output.robot"])
    @patch("importobot.cli.handlers.handle_positional_args")
    def test_importobot_error_handling(self, mock_handler):
        """Test ImportobotError handling."""
        mock_handler.side_effect = ImportobotError("Test error")
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1  # type: ignore[attr-defined]

    @patch("sys.argv", ["importobot", "input.json", "output.robot"])
    @patch("importobot.cli.handlers.handle_positional_args")
    def test_file_error_handling(self, mock_handler):
        """Test file error handling."""
        mock_handler.side_effect = FileNotFoundError("File not found")
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1  # type: ignore[attr-defined]

    @patch("sys.argv", ["importobot", "input.json", "output.robot"])
    @patch("importobot.cli.handlers.handle_positional_args")
    def test_generic_error_handling(self, mock_handler):
        """Test generic error handling."""
        mock_handler.side_effect = Exception("Unexpected error")
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1  # type: ignore[attr-defined]
