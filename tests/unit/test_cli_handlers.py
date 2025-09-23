"""Tests for CLI handlers module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from importobot.cli.handlers import (
    apply_suggestions_single_file,
    collect_suggestions,
    convert_directory_handler,
    convert_single_file,
    convert_wildcard_files,
    detect_input_type,
    display_suggestions,
    filter_suggestions,
    handle_bulk_conversion_with_suggestions,
    handle_directory_conversion,
    handle_files_conversion,
    handle_positional_args,
    print_suggestions,
    requires_output_directory,
    validate_input_and_output,
)


class TestInputTypeDetection:
    """Tests for figuring out what kind of input we're dealing with."""

    def test_detect_wildcard_pattern(self):
        """Should recognize wildcard patterns like *.json."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["test1.json", "test2.json"]
            input_type, files = detect_input_type("*.json")
            assert input_type == "wildcard"
            assert files == ["test1.json", "test2.json"]

    def test_detect_wildcard_no_matches(self):
        """What happens when wildcard finds nothing."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = []
            input_type, files = detect_input_type("*.json")
            assert input_type == "error"
            assert not files

    def test_detect_wildcard_non_json_files(self):
        """Wildcard should ignore non-JSON files."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["test1.txt", "test2.xml"]
            input_type, files = detect_input_type("*.*")
            assert input_type == "error"
            assert not files

    def test_detect_directory(self):
        """Should detect when input is a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_type, files = detect_input_type(temp_dir)
            assert input_type == "directory"
            assert files == [temp_dir]

    def test_detect_file(self):
        """Should detect when input is a single file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            try:
                input_type, files = detect_input_type(temp_file.name)
                assert input_type == "file"
                assert files == [temp_file.name]
            finally:
                os.unlink(temp_file.name)

    def test_detect_nonexistent_path(self):
        """Should handle paths that don't exist."""
        input_type, files = detect_input_type("/nonexistent/path")
        assert input_type == "error"
        assert not files


class TestOutputDirectoryRequirements:
    """Test output directory requirement logic."""

    def test_directory_requires_output_dir(self):
        """Test directory input requires output directory."""
        assert requires_output_directory("directory", 1) is True

    def test_multiple_wildcards_require_output_dir(self):
        """Test multiple wildcard files require output directory."""
        assert requires_output_directory("wildcard", 3) is True

    def test_single_wildcard_no_output_dir(self):
        """Test single wildcard file doesn't require output directory."""
        assert requires_output_directory("wildcard", 1) is False

    def test_file_no_output_dir(self):
        """Test file input doesn't require output directory."""
        assert requires_output_directory("file", 1) is False


class TestSuggestionHandling:
    """Test suggestion collection and filtering."""

    def test_collect_suggestions_single_test(self):
        """Test collecting suggestions from single test case."""
        test_data = {"name": "test", "steps": []}

        with patch("importobot.cli.handlers.get_conversion_suggestions") as mock_get:
            mock_get.return_value = ["suggestion1", "suggestion2"]
            suggestions = collect_suggestions(test_data)
            assert len(suggestions) == 2
            assert suggestions[0] == (0, 0, "suggestion1")
            assert suggestions[1] == (0, 1, "suggestion2")

    def test_collect_suggestions_multiple_tests(self):
        """Test collecting suggestions from multiple test cases."""
        test_data = [{"name": "test1"}, {"name": "test2"}]

        with patch("importobot.cli.handlers.get_conversion_suggestions") as mock_get:
            mock_get.return_value = ["suggestion"]
            suggestions = collect_suggestions(test_data)
            assert len(suggestions) == 2
            assert suggestions[0] == (0, 0, "suggestion")
            assert suggestions[1] == (1, 0, "suggestion")

    def test_filter_suggestions_empty(self) -> None:
        """Test filtering empty suggestions."""
        suggestions: list[tuple[int, int, str]] = []
        filtered = filter_suggestions(suggestions)
        assert not filtered

    def test_filter_suggestions_deduplication(self) -> None:
        """Test suggestion deduplication."""
        suggestions: list[tuple[int, int, str]] = [
            (0, 0, "duplicate"),
            (0, 1, "duplicate"),
            (1, 0, "unique"),
        ]
        filtered = filter_suggestions(suggestions)
        assert len(filtered) == 2
        assert "duplicate" in filtered
        assert "unique" in filtered

    def test_filter_suggestions_no_improvements_needed(self):
        """Test filtering 'No improvements needed' messages."""
        suggestions = [(0, 0, "Real suggestion"), (0, 1, "No improvements needed")]
        filtered = filter_suggestions(suggestions)
        assert len(filtered) == 1
        assert filtered[0] == "Real suggestion"

    def test_filter_suggestions_only_no_improvements(self):
        """Test keeping 'No improvements needed' if it's the only suggestion."""
        suggestions = [(0, 0, "No improvements needed")]
        filtered = filter_suggestions(suggestions)
        assert len(filtered) == 1
        assert filtered[0] == "No improvements needed"

    def test_print_suggestions_empty(self, capsys):
        """Test printing empty suggestions."""
        print_suggestions([])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_suggestions_gives_positive_feedback_when_no_improvements_needed(
        self, capsys
    ):
        """User gets positive confirmation when conversion is already optimal."""
        print_suggestions(["No improvements needed"])
        captured = capsys.readouterr()

        # User should feel good about their file quality
        assert (
            "well-structured" in captured.out
            or "Your conversion is already optimal" in captured.out
        )
        assert (
            "No suggestions for improvement" in captured.out
            or "optimal" in captured.out
        )

    def test_print_suggestions_real_suggestions(self, capsys):
        """Test printing real suggestions."""
        suggestions = ["Improve step description", "Add expected result"]
        print_suggestions(suggestions)
        captured = capsys.readouterr()
        assert "💡 Conversion Suggestions:" in captured.out
        assert "1. Improve step description" in captured.out
        assert "2. Add expected result" in captured.out


class TestInputValidation:
    """Test input validation functions."""

    def test_validate_input_and_output_directory_requires_output_dir(self):
        """Test validation when directory requires output directory."""
        parser = MagicMock()
        args = MagicMock()
        args.output_file = None

        validate_input_and_output("directory", ["/some/dir"], args, parser)

        parser.error.assert_called_once_with(
            "Output directory required for multiple files or directory input"
        )

    def test_validate_input_and_output_file_requires_output_file(self, tmp_path):
        """Test validation when file requires output file."""
        parser = MagicMock()
        args = MagicMock()
        args.output_file = None

        test_file = tmp_path / "some_file.json"
        validate_input_and_output("file", [str(test_file)], args, parser)

        parser.error.assert_called_once_with(
            "Output file required for single file input"
        )

    def test_validate_input_and_output_error_input_type(self):
        """Test validation with error input type."""
        parser = MagicMock()
        args = MagicMock()
        args.input = "nonexistent"

        with (
            patch("importobot.cli.handlers.logger") as mock_logger,
            patch("sys.exit") as mock_exit,
        ):
            validate_input_and_output("error", [], args, parser)

            mock_logger.error.assert_called_once_with(
                "No matching files found for '%s'", "nonexistent"
            )
            mock_exit.assert_called_once_with(1)


class TestDisplaySuggestions:
    """Test display_suggestions function."""

    def test_display_suggestions_disabled(self, capsys):
        """Test suggestions display when disabled."""
        display_suggestions("test.json", no_suggestions=True)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_display_suggestions_enabled_with_suggestions(self, capsys):
        """Test suggestions display with suggestions."""
        _ = capsys  # Mark as used to avoid linting warning
        with (
            patch("importobot.cli.handlers.load_json_file") as mock_load,
            patch("importobot.cli.handlers.collect_suggestions") as mock_collect,
            patch("importobot.cli.handlers.filter_suggestions") as mock_filter,
            patch("importobot.cli.handlers.print_suggestions") as mock_print,
        ):
            mock_load.return_value = {"test": "data"}
            mock_collect.return_value = [(0, 0, "suggestion")]
            mock_filter.return_value = ["filtered suggestion"]

            display_suggestions("test.json", no_suggestions=False)

            mock_load.assert_called_once_with("test.json")
            mock_collect.assert_called_once()
            mock_filter.assert_called_once()
            mock_print.assert_called_once_with(["filtered suggestion"])

    def test_display_suggestions_importobot_error(self):
        """Test suggestions display with ImportobotError."""
        with (
            patch(
                "importobot.cli.handlers.load_json_file",
                side_effect=Exception("Load error"),
            ),
            patch("importobot.cli.handlers.logger") as mock_logger,
        ):
            display_suggestions("test.json", no_suggestions=False)

            mock_logger.warning.assert_called_once()


class TestConvertSingleFile:
    """Test convert_single_file function with real file operations."""

    def test_convert_single_file_creates_robot_output(self, capsys):
        """User gets valid Robot Framework output from single file conversion."""

        # Create real test data that represents user scenario
        test_data = {
            "tests": [
                {
                    "name": "Login Validation Test",
                    "description": "Verify user can log into system",
                    "steps": [
                        {
                            "action": "Open login page",
                            "expectedResult": "Login form displays",
                        },
                        {
                            "action": "Enter credentials",
                            "expectedResult": "User successfully logs in",
                        },
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "test_login.json"
            output_file = temp_path / "test_login.robot"

            # Create real input file
            input_file.write_text(json.dumps(test_data, indent=2))

            # Create args object
            args = MagicMock()
            args.input = str(input_file)
            args.output_file = str(output_file)
            args.no_suggestions = True  # Skip suggestions for this test

            # Test the actual conversion
            convert_single_file(args)

            # Verify user gets actual Robot Framework output
            assert output_file.exists(), "Output file should be created"
            robot_content = output_file.read_text()
            assert "*** Test Cases ***" in robot_content
            assert "Login Validation Test" in robot_content
            assert "Open login page" in robot_content

            # Verify user gets feedback
            captured = capsys.readouterr()
            assert "Successfully converted" in captured.out
            assert str(input_file) in captured.out


class TestConvertDirectoryHandler:
    """Test convert_directory_handler function with real directory operations."""

    def test_convert_directory_handler_processes_multiple_files(self, capsys):
        """User can convert entire directory of JSON files to Robot Framework."""

        # Create realistic test scenario - user has directory with multiple test files
        test_data_1 = {
            "tests": [
                {
                    "name": "User Registration Test",
                    "steps": [
                        {"action": "Fill form", "expectedResult": "Form submitted"}
                    ],
                }
            ]
        }

        test_data_2 = {
            "tests": [
                {
                    "name": "Password Reset Test",
                    "steps": [
                        {"action": "Reset password", "expectedResult": "Email sent"}
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            output_dir = temp_path / "output"

            input_dir.mkdir()

            # Create multiple JSON files (real user scenario)
            (input_dir / "registration.json").write_text(
                json.dumps(test_data_1, indent=2)
            )
            (input_dir / "password_reset.json").write_text(
                json.dumps(test_data_2, indent=2)
            )

            args = MagicMock()
            args.input = str(input_dir)
            args.output_file = str(output_dir)

            # Test actual directory conversion
            convert_directory_handler(args)

            # Verify user gets all files converted
            assert output_dir.exists(), "Output directory should be created"

            registration_robot = output_dir / "registration.robot"
            password_robot = output_dir / "password_reset.robot"

            assert registration_robot.exists(), "Registration robot file should exist"
            assert password_robot.exists(), "Password reset robot file should exist"

            # Verify content is correct Robot Framework format
            reg_content = registration_robot.read_text()
            assert "*** Test Cases ***" in reg_content
            assert "User Registration Test" in reg_content

            pwd_content = password_robot.read_text()
            assert "*** Test Cases ***" in pwd_content
            assert "Password Reset Test" in pwd_content

            # Verify user gets feedback
            captured = capsys.readouterr()
            assert "Successfully converted directory" in captured.out


class TestConvertWildcardFiles:
    """Test convert_wildcard_files function."""

    def test_convert_wildcard_single_file(self, capsys):
        """Test wildcard conversion with single file."""
        args = MagicMock()
        args.output_file = "output.robot"
        args.no_suggestions = False
        detected_files = ["single.json"]

        with patch("importobot.cli.handlers.convert_file") as mock_convert:
            convert_wildcard_files(args, detected_files)

            mock_convert.assert_called_once_with("single.json", "output.robot")
            captured = capsys.readouterr()
            assert "Successfully converted single.json to output.robot" in captured.out

    def test_convert_wildcard_multiple_files(self, capsys):
        """Test wildcard conversion with multiple files."""
        args = MagicMock()
        args.output_file = "/output/dir"
        detected_files = ["file1.json", "file2.json", "file3.json"]

        with patch("importobot.cli.handlers.convert_multiple_files") as mock_convert:
            convert_wildcard_files(args, detected_files)

            mock_convert.assert_called_once_with(detected_files, "/output/dir")
            captured = capsys.readouterr()
            assert "Successfully converted 3 files to /output/dir" in captured.out


class TestApplySuggestionsSingleFile:
    """Test apply_suggestions_single_file function."""

    def test_apply_suggestions_single_file(self):
        """Test applying suggestions to single file."""
        args = MagicMock()
        args.input = "input.json"
        args.no_suggestions = False

        with (
            patch(
                "importobot.cli.handlers.process_single_file_with_suggestions"
            ) as mock_process,
            patch("importobot.cli.handlers.display_suggestions") as mock_display,
        ):
            apply_suggestions_single_file(args)

            mock_process.assert_called_once_with(
                args,
                display_changes_func=mock_process.call_args[1]["display_changes_func"],
                use_stem_for_basename=False,
            )
            mock_display.assert_called_once_with("input.json", False)


class TestHandleBulkConversionWithSuggestions:
    """Test handle_bulk_conversion_with_suggestions function."""

    def test_handle_bulk_directory(self, capsys):
        """Test bulk conversion with suggestions for directory."""
        args = MagicMock()
        args.input = "/input/dir"
        args.output_file = "/output/dir"
        args.no_suggestions = False

        with patch("importobot.cli.handlers.convert_directory") as mock_convert:
            handle_bulk_conversion_with_suggestions(args, "directory", ["/input/dir"])

            captured = capsys.readouterr()
            assert (
                "Warning: --apply-suggestions is only supported for "
                "single file conversion" in captured.out
            )
            assert "Performing normal conversion instead..." in captured.out
            mock_convert.assert_called_once_with("/input/dir", "/output/dir")

    def test_handle_bulk_multiple_files(self, capsys):
        """Test bulk conversion with suggestions for multiple files."""
        args = MagicMock()
        args.output_file = "/output/dir"
        detected_files = ["file1.json", "file2.json"]

        with patch("importobot.cli.handlers.convert_multiple_files") as mock_convert:
            handle_bulk_conversion_with_suggestions(args, "wildcard", detected_files)

            mock_convert.assert_called_once_with(detected_files, "/output/dir")
            captured = capsys.readouterr()
            assert "Successfully converted 2 files to /output/dir" in captured.out


class TestHandlePositionalArgs:
    """Test handle_positional_args function."""

    def test_handle_positional_args_single_file(self):
        """Test positional args handling for single file."""
        args = MagicMock()
        args.input = "test.json"
        args.output_file = "output.robot"
        args.apply_suggestions = False
        parser = MagicMock()

        with (
            patch(
                "importobot.cli.handlers.detect_input_type",
                return_value=("file", ["test.json"]),
            ),
            patch("importobot.cli.handlers.validate_input_and_output"),
            patch("importobot.cli.handlers.convert_single_file") as mock_convert,
        ):
            handle_positional_args(args, parser)

            mock_convert.assert_called_once_with(args)

    def test_handle_positional_args_directory(self):
        """Test positional args handling for directory."""
        args = MagicMock()
        args.input = "/input/dir"
        args.output_file = "/output/dir"
        args.apply_suggestions = False
        parser = MagicMock()

        with (
            patch(
                "importobot.cli.handlers.detect_input_type",
                return_value=("directory", ["/input/dir"]),
            ),
            patch("importobot.cli.handlers.validate_input_and_output"),
            patch("importobot.cli.handlers.convert_directory_handler") as mock_convert,
        ):
            handle_positional_args(args, parser)

            mock_convert.assert_called_once_with(args)

    def test_handle_positional_args_with_suggestions(self):
        """Test positional args handling with suggestions."""
        args = MagicMock()
        args.input = "test.json"
        args.output_file = "output.robot"
        args.apply_suggestions = True
        parser = MagicMock()

        with (
            patch(
                "importobot.cli.handlers.detect_input_type",
                return_value=("file", ["test.json"]),
            ),
            patch("importobot.cli.handlers.validate_input_and_output"),
            patch(
                "importobot.cli.handlers.apply_suggestions_single_file"
            ) as mock_apply,
        ):
            handle_positional_args(args, parser)

            mock_apply.assert_called_once_with(args)


class TestHandleFilesConversion:
    """Test handle_files_conversion function."""

    def test_handle_files_conversion_missing_output(self):
        """Test files conversion with missing output."""
        args = MagicMock()
        args.output = None
        parser = MagicMock()
        parser.error.side_effect = SystemExit(2)

        with pytest.raises(SystemExit):
            handle_files_conversion(args, parser)

        parser.error.assert_called_once_with("--output is required when using --files")

    def test_handle_files_conversion_single_file_with_suggestions(self):
        """Test files conversion single file with suggestions."""
        args = MagicMock()
        args.files = ["test.json"]
        args.output = "output.robot"
        args.apply_suggestions = True
        args.no_suggestions = False
        parser = MagicMock()

        with (
            patch(
                "importobot.cli.handlers.process_single_file_with_suggestions"
            ) as mock_process,
            patch("importobot.cli.handlers.display_suggestions") as mock_display,
        ):
            handle_files_conversion(args, parser)

            mock_process.assert_called_once()
            mock_display.assert_called_once_with("test.json", False)

    def test_handle_files_conversion_multiple_files(self, capsys):
        """Test files conversion multiple files."""
        args = MagicMock()
        args.files = ["file1.json", "file2.json"]
        args.output = "/output/dir"
        args.apply_suggestions = False
        parser = MagicMock()

        with patch("importobot.cli.handlers.convert_multiple_files") as mock_convert:
            handle_files_conversion(args, parser)

            mock_convert.assert_called_once_with(
                ["file1.json", "file2.json"], "/output/dir"
            )
            captured = capsys.readouterr()
            assert "Successfully converted 2 files to /output/dir" in captured.out


class TestHandleDirectoryConversion:
    """Test handle_directory_conversion function."""

    def test_handle_directory_conversion_missing_output(self):
        """Test directory conversion with missing output."""
        args = MagicMock()
        args.output = None
        parser = MagicMock()
        parser.error.side_effect = SystemExit(2)

        with pytest.raises(SystemExit):
            handle_directory_conversion(args, parser)

        parser.error.assert_called_once_with(
            "--output is required when using --directory"
        )

    def test_handle_directory_conversion_with_suggestions_warning(self, capsys):
        """Test directory conversion with suggestions warning."""
        args = MagicMock()
        args.directory = "/input/dir"
        args.output = "/output/dir"
        args.apply_suggestions = True
        parser = MagicMock()

        with patch("importobot.cli.handlers.convert_directory") as mock_convert:
            handle_directory_conversion(args, parser)

            captured = capsys.readouterr()
            assert (
                "Warning: --apply-suggestions is only supported for "
                "single file conversion" in captured.out
            )
            assert "Performing normal directory conversion instead..." in captured.out
            mock_convert.assert_called_once_with("/input/dir", "/output/dir")
