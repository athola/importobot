"""Simplified tests for the command-line interface after refactoring."""

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from importobot.__main__ import main
from importobot.cli.handlers import (
    InputType,
    detect_input_type,
    requires_output_directory,
)
from importobot.cli.parser import create_parser
from tests.test_constants import (
    CLI_TEST_BATCH_FILES_COUNT,
    CLI_TEST_DIRECTORY_FILES_COUNT,
    CLI_TEST_MULTIPLE_FILES_COUNT,
    EXIT_CODE_INVALID_ARGS,
    EXIT_CODE_SUCCESS,
)


class TestCLIBasics:
    """Basic CLI functionality tests."""

    def test_create_parser(self) -> None:
        """Test that parser creates correctly."""
        parser = create_parser()
        assert parser is not None
        assert (
            parser.description
            == "Convert test cases from JSON to Robot Framework format"
        )

    def test_parser_help(self) -> None:
        """Test parser help doesn't crash."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    @patch("sys.argv", ["importobot"])
    def test_insufficient_args(self) -> None:
        """Test CLI fails with insufficient arguments."""
        with pytest.raises(SystemExit) as e:
            main()
        assert isinstance(e.value, SystemExit)
        assert e.value.code == EXIT_CODE_INVALID_ARGS

    @patch("sys.argv", ["importobot", "too", "many", "args", "here"])
    def test_too_many_args(self) -> None:
        """Test CLI fails with too many arguments."""
        with pytest.raises(SystemExit) as e:
            main()
        assert isinstance(e.value, SystemExit)
        assert e.value.code == EXIT_CODE_INVALID_ARGS


class TestInputDetection:
    """Test input type detection logic."""

    def test_detect_input_type_error(self) -> None:
        """Test detection of non-existent files."""
        input_type, files = detect_input_type("/nonexistent/file.json")
        assert input_type == InputType.ERROR
        assert not files

    def test_requires_output_directory(self) -> None:
        """Test output directory requirement logic."""
        assert requires_output_directory(InputType.DIRECTORY, 1) is True
        assert requires_output_directory(InputType.WILDCARD, 2) is True
        assert requires_output_directory(InputType.FILE, 1) is False


class TestCLIUserWorkflows:
    """Test actual user workflows through the CLI."""

    def test_user_can_convert_simple_json_file_via_cli(self, tmp_path: Path) -> None:
        """User can successfully convert a JSON file to Robot Framework using CLI."""
        # Arrange: Create test data that represents a real user scenario
        test_data = {
            "tests": [
                {
                    "name": "User Login Test",
                    "description": "Test user can log into the system",
                    "steps": [
                        {
                            "action": "Navigate to login page",
                            "expectedResult": "Login page displays correctly",
                        },
                        {
                            "action": "Enter valid credentials",
                            "expectedResult": "User is successfully logged in",
                        },
                    ],
                }
            ]
        }

        input_file = tmp_path / "login_test.json"
        output_file = tmp_path / "login_test.robot"
        input_file.write_text(json.dumps(test_data, indent=2))

        # Act: Run CLI command
        result = subprocess.run(
            [sys.executable, "-m", "importobot", str(input_file), str(output_file)],
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert: User should get successful conversion
        assert result.returncode == EXIT_CODE_SUCCESS, (
            f"CLI failed with error: {result.stderr}"
        )
        assert output_file.exists(), "Output Robot file was not created"

        # Verify the output contains expected Robot Framework structure
        robot_content = output_file.read_text()
        assert "*** Test Cases ***" in robot_content
        assert "User Login Test" in robot_content
        assert "Navigate to login page" in robot_content

    def test_user_can_convert_multiple_files_via_cli(self, tmp_path: Path) -> None:
        """User can convert multiple files using --files flag."""
        # Arrange: Create test data and multiple input files
        test_data = {
            "tests": [
                {
                    "name": "Sample Test",
                    "steps": [
                        {"action": "Test step", "expectedResult": "Expected result"}
                    ],
                }
            ]
        }

        input_files = []
        for i in range(CLI_TEST_MULTIPLE_FILES_COUNT):
            input_file = tmp_path / f"test_{i}.json"
            input_file.write_text(json.dumps(test_data, indent=2))
            input_files.append(str(input_file))

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Act: Run CLI command with --files flag
        cmd = [
            sys.executable,
            "-m",
            "importobot",
            "--files",
            *input_files,
            "--output",
            str(output_dir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # Assert: Verify successful conversion and output files created
        assert result.returncode == EXIT_CODE_SUCCESS, (
            f"CLI failed with error: {result.stderr}"
        )

        for i in range(CLI_TEST_MULTIPLE_FILES_COUNT):
            output_file = output_dir / f"test_{i}.robot"
            assert output_file.exists(), f"Output file {output_file} was not created"

    def test_user_can_convert_directory_via_cli(self, tmp_path: Path) -> None:
        """User can convert an entire directory using --directory flag."""
        # Arrange: Create input directory with JSON files
        test_data = {
            "tests": [
                {
                    "name": "Directory Test",
                    "steps": [
                        {"action": "Test action", "expectedResult": "Test result"}
                    ],
                }
            ]
        }

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        for i in range(CLI_TEST_DIRECTORY_FILES_COUNT):
            input_file = input_dir / f"test_{i}.json"
            input_file.write_text(json.dumps(test_data, indent=2))

        output_dir = tmp_path / "output"

        # Act: Run CLI command with --directory flag
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "importobot",
                "--directory",
                str(input_dir),
                "--output",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert: Verify successful conversion and all files converted
        assert result.returncode == EXIT_CODE_SUCCESS, (
            f"CLI failed with error: {result.stderr}"
        )
        assert output_dir.exists(), "Output directory was not created"

        for i in range(CLI_TEST_DIRECTORY_FILES_COUNT):
            output_file = output_dir / f"test_{i}.robot"
            assert output_file.exists(), f"Output file {output_file} was not created"


class TestCLIUserErrorScenarios:
    """Test how CLI handles real user error scenarios."""

    def test_user_gets_helpful_error_for_corrupted_json(self, tmp_path: Path) -> None:
        """User gets clear guidance when JSON file is corrupted."""

        corrupted_file = tmp_path / "corrupted.json"
        output_file = tmp_path / "output.robot"

        # Create a corrupted JSON file (real user scenario)
        corrupted_file.write_text('{ "name": "Test", "incomplete": ')

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "importobot",
                str(corrupted_file),
                str(output_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # User should get helpful error message
        assert result.returncode != 0

        # User should see the location of the error
        assert "line" in result.stderr
        assert "column" in result.stderr

        # User should get helpful guidance about what to do
        assert (
            "corrupted" in result.stderr.lower()
            or "appears to be" in result.stderr.lower()
        )
        assert (
            "check the file format" in result.stderr.lower()
            or "fix" in result.stderr.lower()
        )

    def test_user_gets_clear_error_when_file_not_found(self, tmp_path: Path) -> None:
        """User gets clear error when input file doesn't exist."""

        missing_file = tmp_path / "nonexistent.json"
        output_file = tmp_path / "output.robot"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "importobot",
                str(missing_file),
                str(output_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # User should understand what went wrong
        assert result.returncode != 0
        assert (
            "No matching files found" in result.stderr
            or "Could not find" in result.stderr
        )
        assert "nonexistent.json" in result.stderr

    def test_user_gets_guidance_when_output_directory_missing(
        self, tmp_path: Path
    ) -> None:
        """User gets helpful error when output directory doesn't exist."""

        test_data = {"tests": [{"name": "Test", "steps": []}]}

        input_file = tmp_path / "test.json"
        input_file.write_text(json.dumps(test_data))

        # Try to write to non-existent directory
        missing_dir = tmp_path / "missing" / "output.robot"

        result = subprocess.run(
            [sys.executable, "-m", "importobot", str(input_file), str(missing_dir)],
            capture_output=True,
            text=True,
            check=False,
        )

        # User should get helpful guidance
        assert result.returncode != 0
        # Should help user understand what to do
        assert "directory" in result.stderr.lower() or "path" in result.stderr.lower()

    def test_user_can_get_help_information(self) -> None:
        """User can easily get help on how to use the tool."""
        result = subprocess.run(
            [sys.executable, "-m", "importobot", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # User should get detailed help
        assert result.returncode == EXIT_CODE_SUCCESS
        assert "usage:" in result.stdout.lower()
        assert "convert" in result.stdout.lower()
        assert "json" in result.stdout.lower()
        assert "robot" in result.stdout.lower()

    def test_user_gets_feedback_during_batch_processing(self, tmp_path: Path) -> None:
        """User gets feedback when processing multiple files."""

        test_data = {"tests": [{"name": "Test", "steps": []}]}

        # Create multiple files (simulate user batch processing)
        input_files = []
        for i in range(CLI_TEST_BATCH_FILES_COUNT):
            input_file = tmp_path / f"batch_test_{i}.json"
            input_file.write_text(json.dumps(test_data))
            input_files.append(str(input_file))

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        cmd = [
            sys.executable,
            "-m",
            "importobot",
            "--files",
            *input_files,
            "--output",
            str(output_dir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # User should get feedback about batch processing
        assert result.returncode == EXIT_CODE_SUCCESS
        assert "converted" in result.stdout.lower()
        assert (
            str(CLI_TEST_BATCH_FILES_COUNT) in result.stdout or "files" in result.stdout
        )

    def test_user_understands_when_no_valid_files_in_directory(
        self, tmp_path: Path
    ) -> None:
        """User gets clear message when directory has no JSON files."""

        # Create directory with non-JSON files
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Add non-JSON files
        (input_dir / "readme.txt").write_text("Not a JSON file")
        (input_dir / "config.xml").write_text("<config></config>")

        output_dir = tmp_path / "output"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "importobot",
                "--directory",
                str(input_dir),
                "--output",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # User should understand what happened
        assert result.returncode != 0
        assert "json" in result.stderr.lower() or "no.*files" in result.stderr.lower()


class TestErrorHandling:
    """Test how CLI handles errors from user perspective."""

    def test_user_gets_clear_feedback_when_file_missing(self) -> None:
        """User understands what went wrong when file doesn't exist."""
        result = subprocess.run(
            [sys.executable, "-m", "importobot", "non_existent.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Focus on user value: clear error message, not specific exit code
        assert result.returncode != 0  # Should fail
        assert "non_existent.json" in result.stderr  # Should mention the file
        assert (
            "No matching files found" in result.stderr
            or "Could not find" in result.stderr
        )

    def test_user_understands_missing_file_vs_directory_issues(
        self, tmp_path: Path
    ) -> None:
        """User can distinguish between missing files and directory problems."""
        input_file = tmp_path / "missing.json"
        # Don't create the file to trigger the error

        result = subprocess.run(
            [sys.executable, "-m", "importobot", str(input_file)],
            capture_output=True,
            text=True,
            check=False,
        )
        # User should understand this is about the file, not the directory
        assert result.returncode != 0
        assert "missing.json" in result.stderr
        assert (
            "No matching files found" in result.stderr
            or "Could not find" in result.stderr
        )

    def test_generic_error_handling(self) -> None:
        """Test generic error handling."""
        # Test generic exception handling in main() directly rather than subprocess

        # Mock stderr to capture the output
        captured_stderr = StringIO()

        with (
            patch("sys.argv", ["importobot", "input.json", "output.robot"]),
            patch(
                "importobot.__main__.handle_positional_args",
                side_effect=Exception("Unexpected error"),
            ),
            patch("sys.stderr", captured_stderr),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert isinstance(exc_info.value, SystemExit)
        assert exc_info.value.code == 1
        stderr_output = captured_stderr.getvalue()
        assert "An unexpected error occurred: Unexpected error" in stderr_output

    def test_no_input(self) -> None:
        """Test that the script exits with an error if no input is provided."""
        result = subprocess.run(
            [sys.executable, "-m", "importobot"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        assert "Please specify input and output files" in result.stderr
