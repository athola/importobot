"""Tests for the command-line interface."""

from unittest.mock import patch

import pytest

# Import the main function directly
from importobot.__main__ import main


class TestCommandLineInterface:
    """Tests for the CLI."""

    @patch("sys.argv", ["importobot", "input.json", "output.robot"])
    @patch("os.path.isfile")
    @patch("importobot.__main__.convert_file")
    def test_main_calls_converter(self, mock_convert, mock_isfile):
        """Ensures the main CLI function calls the converter
        with correct args."""
        mock_isfile.return_value = True
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


class TestBulkConversionCLI:
    """Tests for bulk conversion CLI functionality."""

    @patch(
        "sys.argv",
        ["importobot", "--files", "file1.json", "file2.json", "--output", "/output"],
    )
    @patch("importobot.__main__.convert_multiple_files")
    def test_multiple_files_conversion(self, mock_convert_multiple):
        """Tests CLI conversion of multiple files."""
        main()
        mock_convert_multiple.assert_called_once_with(
            ["file1.json", "file2.json"], "/output"
        )

    @patch(
        "sys.argv", ["importobot", "--files", "file1.json", "--output", "output.robot"]
    )
    @patch("importobot.__main__.convert_file")
    def test_single_file_conversion_with_files_flag(self, mock_convert):
        """Tests CLI conversion of single file using --files flag."""
        main()
        mock_convert.assert_called_once_with("file1.json", "output.robot")

    @patch("sys.argv", ["importobot", "--directory", "/input", "--output", "/output"])
    @patch("importobot.__main__.convert_directory")
    def test_directory_conversion(self, mock_convert_directory):
        """Tests CLI conversion of entire directory."""
        main()
        mock_convert_directory.assert_called_once_with("/input", "/output")

    @patch("sys.argv", ["importobot", "--files", "file1.json"])
    def test_files_missing_output(self):
        """Tests that files conversion requires output."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2

    @patch("sys.argv", ["importobot", "--directory", "/input"])
    def test_directory_missing_output(self):
        """Tests that directory conversion requires output."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2

    @patch(
        "sys.argv",
        [
            "importobot",
            "--files",
            "file1.json",
            "--directory",
            "/input",
            "--output",
            "/output",
        ],
    )
    def test_mutually_exclusive_options(self):
        """Tests that files and directory options are mutually exclusive."""
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2


class TestPositionalArgumentsCLI:
    """Tests for enhanced positional arguments functionality."""

    @patch("sys.argv", ["importobot", "/path/to/directory", "/output"])
    @patch("os.path.isdir")
    @patch("importobot.__main__.convert_directory")
    def test_directory_positional_argument(self, mock_convert_dir, mock_isdir):
        """Tests directory conversion using positional arguments."""
        mock_isdir.return_value = True
        main()
        mock_convert_dir.assert_called_once_with("/path/to/directory", "/output")

    @patch("sys.argv", ["importobot", "*.json", "/output"])
    @patch("glob.glob")
    @patch("importobot.__main__.convert_multiple_files")
    def test_wildcard_positional_argument(self, mock_convert_multiple, mock_glob):
        """Tests wildcard conversion using positional arguments."""
        mock_glob.return_value = ["file1.json", "file2.json", "file3.json"]
        main()
        mock_convert_multiple.assert_called_once_with(
            ["file1.json", "file2.json", "file3.json"], "/output"
        )

    @patch("sys.argv", ["importobot", "test*.json", "/output"])
    @patch("glob.glob")
    @patch("importobot.__main__.convert_multiple_files")
    def test_complex_wildcard_positional_argument(
        self, mock_convert_multiple, mock_glob
    ):
        """Tests complex wildcard patterns using positional arguments."""
        mock_glob.return_value = ["test1.json", "test2.json", "testdata.json"]
        main()
        mock_convert_multiple.assert_called_once_with(
            ["test1.json", "test2.json", "testdata.json"], "/output"
        )

    @patch("sys.argv", ["importobot", "*.json"])
    @patch("glob.glob")
    def test_wildcard_missing_output(self, mock_glob):
        """Tests that wildcard conversion requires output directory."""
        mock_glob.return_value = ["file1.json", "file2.json"]
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2

    @patch("sys.argv", ["importobot", "/path/to/directory"])
    @patch("os.path.isdir")
    def test_directory_missing_output(self, mock_isdir):
        """Tests that directory conversion requires output directory."""
        mock_isdir.return_value = True
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2

    @patch("sys.argv", ["importobot", "*.json", "/output"])
    @patch("glob.glob")
    def test_wildcard_no_matches(self, mock_glob):
        """Tests wildcard with no matching files."""
        mock_glob.return_value = []
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1

    @patch("sys.argv", ["importobot", "**/*.json", "/output"])
    @patch("glob.glob")
    @patch("importobot.__main__.convert_multiple_files")
    def test_recursive_wildcard_positional_argument(
        self, mock_convert_multiple, mock_glob
    ):
        """Tests recursive wildcard patterns using positional arguments."""
        mock_glob.return_value = [
            "dir1/file1.json",
            "dir2/file2.json",
            "subdir/file3.json",
        ]
        main()
        mock_convert_multiple.assert_called_once_with(
            ["dir1/file1.json", "dir2/file2.json", "subdir/file3.json"], "/output"
        )

    @patch("sys.argv", ["importobot", "/nonexistent/directory", "/output"])
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_nonexistent_path_error(self, mock_isfile, mock_isdir):
        """Tests error handling for nonexistent paths."""
        mock_isdir.return_value = False
        mock_isfile.return_value = False
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
