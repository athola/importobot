"""Tests for the command-line interface."""

from unittest.mock import patch

import pytest

# Import the main function directly
from importobot.__main__ import main


class TestCommandLineInterface:
    """Tests for the CLI."""

    @patch("sys.argv", ["importobot", "input.json", "output.robot"])
    @patch("importobot.__main__.convert_to_robot")
    def test_main_calls_converter(self, mock_convert):
        """Ensures the main CLI function calls the converter
        with correct args."""
        main()
        mock_convert.assert_called_once_with("input.json", "output.robot")

    @patch("sys.argv", ["importobot"])
    def test_cli_fails_with_insufficient_args(self):
        """Ensures the CLI exits with code 2 for missing arguments."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2

    @patch("sys.argv", ["importobot", "input.json", "output.robot", "extra"])
    def test_cli_fails_with_too_many_args(self):
        """Ensures the CLI exits with code 2 for extra arguments."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2
