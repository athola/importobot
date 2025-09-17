"""Unit tests for conversion strategies module."""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from importobot import exceptions
from importobot.core.conversion_strategies import (
    ConversionStrategy,
    DirectoryConversionStrategy,
    MultipleFilesConversionStrategy,
    SingleFileConversionStrategy,
)
from importobot.utils.file_operations import display_suggestion_changes


class TestConversionStrategy:
    """Tests for abstract ConversionStrategy base class."""

    def test_abstract_base_class_cannot_be_instantiated(self):
        """Test that ConversionStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            ConversionStrategy()  # type: ignore[abstract]

    def test_concrete_strategy_implements_convert_method(self):
        """Test that concrete strategies must implement convert and validate methods."""

        class IncompleteStrategy(ConversionStrategy):
            """Test class missing required abstract methods."""

        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            IncompleteStrategy()  # type: ignore[abstract]


class TestSingleFileConversionStrategy:
    """Tests for SingleFileConversionStrategy."""

    def test_validates_required_output_file(self):
        """Test that output file is required for single file conversion."""
        strategy = SingleFileConversionStrategy()

        mock_args = Mock()
        mock_args.output_file = None

        with pytest.raises(
            exceptions.ValidationError,
            match="Output file required for single file input",
        ):
            strategy.validate_args(mock_args)

    @patch("importobot.core.conversion_strategies.process_single_file_with_suggestions")
    def test_converts_with_suggestions(self, mock_process_file):
        """Test conversion with suggestions processing."""
        strategy = SingleFileConversionStrategy()

        mock_args = Mock()
        mock_args.output_file = "output.robot"
        mock_args.input = "input.json"
        mock_args.no_suggestions = False
        mock_args.apply_suggestions = True

        # Mock the _display_suggestions method
        with patch.object(strategy, "_display_suggestions"):
            strategy.convert(mock_args)

        # Verify process_single_file_with_suggestions was called correctly
        mock_process_file.assert_called_once_with(
            mock_args,
            display_changes_func=display_suggestion_changes,
            use_stem_for_basename=True,
        )

    @patch("importobot.core.conversion_strategies.convert_file")
    def test_converts_without_suggestions(self, mock_convert_file):
        """Test conversion without suggestions processing."""
        strategy = SingleFileConversionStrategy()

        mock_args = Mock()
        mock_args.output_file = "output.robot"
        mock_args.input = "input.json"
        mock_args.no_suggestions = False
        mock_args.apply_suggestions = False

        # Mock the _display_suggestions method
        with patch.object(strategy, "_display_suggestions"):
            strategy.convert(mock_args)

        # Verify convert_file was called
        mock_convert_file.assert_called_once_with("input.json", "output.robot")

    @patch("importobot.core.conversion_strategies.process_single_file_with_suggestions")
    def test_displays_suggestions_after_conversion(
        self,
        mock_process_file,  # pylint: disable=unused-argument
    ):
        """Test that suggestions are displayed after conversion."""
        strategy = SingleFileConversionStrategy()

        mock_args = Mock()
        mock_args.output_file = "output.robot"
        mock_args.input = "input.json"
        mock_args.no_suggestions = False
        mock_args.apply_suggestions = True

        with patch.object(strategy, "_display_suggestions") as mock_display:
            strategy.convert(mock_args)

        mock_display.assert_called_once_with("input.json", False)

    def test_prepare_conversion_data_with_list(self):
        """Test preparing conversion data from a list."""
        strategy = SingleFileConversionStrategy()

        improved_data = [
            {"name": "Test 1", "steps": []},
            {"name": "Test 2", "steps": []},
        ]

        # pylint: disable=protected-access
        result = strategy._prepare_conversion_data(improved_data)

        # Should return the first item from the list
        assert result == {"name": "Test 1", "steps": []}

    def test_prepare_conversion_data_with_empty_list(self) -> None:
        """Test preparing conversion data from an empty list."""
        strategy = SingleFileConversionStrategy()

        improved_data: list[Any] = []

        # pylint: disable=protected-access
        result = strategy._prepare_conversion_data(improved_data)

        # Should return empty list for empty list
        assert result == []

    def test_prepare_conversion_data_with_dict(self):
        """Test preparing conversion data from a dictionary."""
        strategy = SingleFileConversionStrategy()

        improved_data = {"name": "Test", "steps": []}

        # pylint: disable=protected-access
        result = strategy._prepare_conversion_data(improved_data)

        # Should return the dict as-is
        assert result == {"name": "Test", "steps": []}

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions(self, mock_load_json, mock_get_suggestions, capsys):
        """Test displaying suggestions for the input file."""
        strategy = SingleFileConversionStrategy()

        mock_load_json.return_value = {"test": "data"}
        mock_suggestions = [
            "Suggestion 1: Improve test data format",
            "Suggestion 2: Add more descriptive step names",
        ]
        mock_get_suggestions.return_value = mock_suggestions

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        captured = capsys.readouterr()
        assert "💡 Conversion Suggestions:" in captured.out
        assert "1. Suggestion 1: Improve test data format" in captured.out
        assert "2. Suggestion 2: Add more descriptive step names" in captured.out

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_respects_no_suggestions_flag(
        self, mock_load_json, mock_get_suggestions
    ):
        """Test that suggestions are not displayed when no_suggestions is True."""
        strategy = SingleFileConversionStrategy()

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=True)

        # Should not call load_json_file or get_conversion_suggestions
        mock_load_json.assert_not_called()
        mock_get_suggestions.assert_not_called()

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_handles_empty_suggestions(
        self, mock_load_json, mock_get_suggestions, capsys
    ):
        """Test handling when there are no suggestions."""
        strategy = SingleFileConversionStrategy()

        mock_load_json.return_value = {"test": "data"}
        mock_get_suggestions.return_value = []

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        captured = capsys.readouterr()
        # Should not print anything for empty suggestions
        assert captured.out.strip() == ""


class TestMultipleFilesConversionStrategy:
    """Tests for MultipleFilesConversionStrategy."""

    @patch("importobot.core.conversion_strategies.convert_multiple_files")
    def test_converts_multiple_files(self, mock_convert_multiple):
        """Test conversion of multiple files."""
        files = ["file1.json", "file2.json", "file3.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.apply_suggestions = False
        mock_args.output_file = "output_directory"

        strategy.convert(mock_args)

        mock_convert_multiple.assert_called_once_with(files, "output_directory")

    @patch("importobot.core.conversion_strategies.convert_file")
    def test_conversion_with_single_file_in_list(self, mock_convert_file):
        """Test conversion when files list contains only one file."""
        files = ["single_file.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.apply_suggestions = False
        mock_args.output_file = "output.robot"
        mock_args.no_suggestions = True

        with patch.object(strategy, "_display_suggestions"):
            strategy.convert(mock_args)

        mock_convert_file.assert_called_once_with("single_file.json", "output.robot")

    def test_validates_required_output_file_single(self):
        """Test validation for single file requires output file."""
        files = ["single_file.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.output_file = None

        with pytest.raises(
            exceptions.ValidationError,
            match="Output file required for single file input",
        ):
            strategy.validate_args(mock_args)

    def test_validates_required_output_directory_multiple(self):
        """Test validation for multiple files requires output directory."""
        files = ["file1.json", "file2.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.output_file = None

        with pytest.raises(
            exceptions.ValidationError,
            match="Output directory required for multiple files",
        ):
            strategy.validate_args(mock_args)


class TestDirectoryConversionStrategy:
    """Tests for DirectoryConversionStrategy."""

    @patch("importobot.core.conversion_strategies.convert_directory")
    def test_converts_directory(self, mock_convert_directory):
        """Test conversion of entire directory."""
        strategy = DirectoryConversionStrategy()

        mock_args = Mock()
        mock_args.input = "/path/to/input/directory"
        mock_args.output_file = "/path/to/output/directory"
        mock_args.apply_suggestions = False

        strategy.convert(mock_args)

        mock_convert_directory.assert_called_once_with(
            "/path/to/input/directory", "/path/to/output/directory"
        )

    @patch("importobot.core.conversion_strategies.convert_directory")
    def test_converts_relative_directory_paths(self, mock_convert_directory):
        """Test conversion with relative directory paths."""
        strategy = DirectoryConversionStrategy()

        mock_args = Mock()
        mock_args.input = "input_dir"
        mock_args.output_file = "output_dir"
        mock_args.apply_suggestions = False

        strategy.convert(mock_args)

        mock_convert_directory.assert_called_once_with("input_dir", "output_dir")

    def test_validates_required_output_directory(self):
        """Test that output directory is required."""
        strategy = DirectoryConversionStrategy()

        mock_args = Mock()
        mock_args.output_file = None

        with pytest.raises(
            exceptions.ValidationError,
            match="Output directory required for directory input",
        ):
            strategy.validate_args(mock_args)

    @patch("importobot.core.conversion_strategies.convert_directory")
    def test_handles_suggestions_warning(self, mock_convert_directory, capsys):
        """Test warning when suggestions are requested for directory."""
        strategy = DirectoryConversionStrategy()

        mock_args = Mock()
        mock_args.input = "input_dir"
        mock_args.output_file = "output_dir"
        mock_args.apply_suggestions = True

        strategy.convert(mock_args)

        captured = capsys.readouterr()
        assert (
            "Warning: --apply-suggestions only supported for single files."
            in captured.out
        )
        mock_convert_directory.assert_called_once_with("input_dir", "output_dir")


class TestConversionStrategyIntegration:
    """Integration tests for conversion strategies."""

    def test_single_file_strategy_end_to_end(self):
        """Test single file strategy end-to-end with temporary files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test JSON file
            input_file = Path(temp_dir) / "test.json"
            output_file = Path(temp_dir) / "test.robot"

            test_data = {
                "testScript": {
                    "type": "STEP_BY_STEP",
                    "steps": [
                        {
                            "step": "Test step",
                            "testData": "Test data",
                            "expectedResult": "Expected result",
                        }
                    ],
                }
            }

            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            mock_args = Mock()
            mock_args.input = str(input_file)
            mock_args.output_file = str(output_file)
            mock_args.no_suggestions = True
            mock_args.apply_suggestions = False

            strategy = SingleFileConversionStrategy()

            # Mock the conversion process to avoid actual file operations
            with patch("importobot.core.conversion_strategies.convert_file"):
                with patch.object(strategy, "_display_suggestions"):
                    strategy.convert(mock_args)

            # Test passes if no exceptions are raised

    def test_strategy_handles_conversion_errors(self):
        """Test that strategies handle conversion errors gracefully."""
        strategy = SingleFileConversionStrategy()

        mock_args = Mock()
        mock_args.output_file = "output.robot"
        mock_args.input = "nonexistent.json"
        mock_args.no_suggestions = True
        mock_args.apply_suggestions = True

        # Mock process_single_file_with_suggestions to raise an exception
        patch_target = (
            "importobot.core.conversion_strategies.process_single_file_with_suggestions"
        )
        with patch(patch_target, side_effect=Exception("Conversion failed")):
            with patch.object(strategy, "_display_suggestions"):
                with pytest.raises(Exception, match="Conversion failed"):
                    strategy.convert(mock_args)
