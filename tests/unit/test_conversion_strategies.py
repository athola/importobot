"""Tests for the different conversion strategies we support."""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from importobot import exceptions
from importobot.core.conversion_strategies import (
    ConversionStrategy,
    ConversionStrategyFactory,
    DirectoryConversionStrategy,
    MultipleFilesConversionStrategy,
    SingleFileConversionStrategy,
)
from importobot.utils.file_operations import display_suggestion_changes


class TestConversionStrategy:
    """Tests for the base ConversionStrategy class."""

    def test_abstract_base_class_cannot_be_instantiated(self):
        """ConversionStrategy is abstract and can't be created directly."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            ConversionStrategy()  # type: ignore[abstract]

    def test_concrete_strategy_implements_convert_method(self):
        """Concrete strategies need to implement the required methods."""

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
        assert not result

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


class TestConversionStrategyUserScenarios:
    """Test conversion strategies from user perspective - what users accomplish."""

    def test_user_can_convert_complex_test_scenario_end_to_end(self):
        """User can convert complex, realistic test scenario using strategies."""

        # Real user scenario: Complex e-commerce test case
        complex_test_data = {
            "tests": [
                {
                    "name": "E-commerce Checkout Flow",
                    "description": "Test purchase workflow from cart to confirm",
                    "tags": ["smoke", "checkout", "critical"],
                    "steps": [
                        {
                            "action": "Add product to cart",
                            "data": "Product ID: 12345",
                            "expectedResult": "Product appears in cart with price",
                        },
                        {
                            "action": "Proceed to checkout",
                            "data": "Click checkout button",
                            "expectedResult": "Checkout form displays with shipping",
                        },
                        {
                            "action": "Enter shipping information",
                            "data": "Name: John Doe, Address: 123 Test St",
                            "expectedResult": "Shipping cost calculated correctly",
                        },
                        {
                            "action": "Complete payment",
                            "data": "Credit Card: 4111111111111111",
                            "expectedResult": "Payment processed, confirmation shown",
                        },
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "ecommerce_checkout.json"
            output_file = temp_path / "ecommerce_checkout.robot"

            input_file.write_text(json.dumps(complex_test_data, indent=2))

            # Test using the actual strategy (not mocked)
            strategy = SingleFileConversionStrategy()

            args = MagicMock()
            args.input = str(input_file)
            args.output_file = str(output_file)
            args.no_suggestions = True
            args.apply_suggestions = False

            # User performs conversion
            strategy.convert(args)

            # Verify user gets complete, executable Robot Framework output
            assert output_file.exists(), "User should get output file"

            robot_content = output_file.read_text()

            # User should get proper Robot Framework structure
            assert "*** Settings ***" in robot_content
            assert "*** Test Cases ***" in robot_content

            # User's test case should be preserved with all details
            assert "E-commerce Checkout Flow" in robot_content
            assert "Add product to cart" in robot_content
            assert "Product ID: 12345" in robot_content
            assert "Payment processed" in robot_content

            # User should get actionable test steps
            assert "Click checkout button" in robot_content

    def test_user_can_process_directory_with_mixed_test_types(self):
        """User can convert directory containing different types of test cases."""

        # Realistic scenario: User has mixed test types
        api_test = {
            "tests": [
                {
                    "name": "API Authentication Test",
                    "steps": [
                        {
                            "action": "Send POST request to /auth",
                            "expectedResult": "200 OK response",
                        },
                        {
                            "action": "Verify token in response",
                            "expectedResult": "Valid JWT token returned",
                        },
                    ],
                }
            ]
        }

        ui_test = {
            "tests": [
                {
                    "name": "UI Navigation Test",
                    "steps": [
                        {
                            "action": "Click navigation menu",
                            "expectedResult": "Menu expands",
                        },
                        {
                            "action": "Select dashboard option",
                            "expectedResult": "Dashboard loads",
                        },
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "tests"
            output_dir = temp_path / "robot_tests"

            input_dir.mkdir()

            (input_dir / "api_auth.json").write_text(json.dumps(api_test, indent=2))
            (input_dir / "ui_navigation.json").write_text(json.dumps(ui_test, indent=2))

            # User converts entire directory
            strategy = DirectoryConversionStrategy()

            args = MagicMock()
            args.input = str(input_dir)
            args.output_file = str(output_dir)

            strategy.convert(args)

            # User gets all files converted properly
            api_robot = output_dir / "api_auth.robot"
            ui_robot = output_dir / "ui_navigation.robot"

            assert api_robot.exists(), "API test should be converted"
            assert ui_robot.exists(), "UI test should be converted"

            # Each file should contain proper test structure
            api_content = api_robot.read_text()
            assert "API Authentication Test" in api_content
            assert "Send POST request" in api_content

            ui_content = ui_robot.read_text()
            assert "UI Navigation Test" in ui_content
            assert "Click navigation menu" in ui_content


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


class TestConversionStrategyFactory:
    """Tests for ConversionStrategyFactory."""

    def test_create_strategy_file(self):
        """Test creating strategy for file input."""
        strategy = ConversionStrategyFactory.create_strategy("file", ["test.json"])

        assert isinstance(strategy, SingleFileConversionStrategy)

    def test_create_strategy_directory(self):
        """Test creating strategy for directory input."""
        strategy = ConversionStrategyFactory.create_strategy("directory", ["/some/dir"])

        assert isinstance(strategy, DirectoryConversionStrategy)

    def test_create_strategy_wildcard(self):
        """Test creating strategy for wildcard input."""
        files = ["file1.json", "file2.json"]
        strategy = ConversionStrategyFactory.create_strategy("wildcard", files)

        assert isinstance(strategy, MultipleFilesConversionStrategy)
        assert strategy.files == files

    def test_create_strategy_unknown_type(self):
        """Test creating strategy with unknown input type."""
        with pytest.raises(ValueError, match="Unknown input type: unknown"):
            ConversionStrategyFactory.create_strategy("unknown", [])


class TestSingleFileConversionStrategyAdditional:
    """Additional tests for SingleFileConversionStrategy edge cases."""

    @patch("importobot.core.conversion_strategies.convert_with_temp_file")
    def test_convert_with_temp_file_method(self, mock_convert_with_temp_file):
        """Test the _convert_with_temp_file method."""
        strategy = SingleFileConversionStrategy()

        conversion_data = {"test": "data"}
        robot_filename = "output.robot"
        changes_made = [{"field": "name", "change": "added"}]
        args = Mock()

        # pylint: disable=protected-access
        strategy._convert_with_temp_file(
            conversion_data, robot_filename, changes_made, args
        )

        # Verify the function was called with expected parameters
        mock_convert_with_temp_file.assert_called_once()
        call_args = mock_convert_with_temp_file.call_args
        assert call_args.kwargs["conversion_data"] == conversion_data
        assert call_args.kwargs["robot_filename"] == robot_filename
        assert call_args.kwargs["changes_made"] == changes_made
        assert call_args.kwargs["display_changes_func"] is display_suggestion_changes
        assert call_args.kwargs["args"] == args

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_with_importobot_error(
        self, mock_load_json, mock_get_suggestions
    ):
        """Test _display_suggestions handles ImportobotError."""
        strategy = SingleFileConversionStrategy()

        mock_load_json.side_effect = exceptions.ImportobotError("Load failed")

        # Should not raise exception, just log warning
        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        mock_load_json.assert_called_once_with("test.json")
        mock_get_suggestions.assert_not_called()

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_with_generic_error(
        self, mock_load_json, mock_get_suggestions
    ):
        """Test _display_suggestions handles generic exceptions."""
        strategy = SingleFileConversionStrategy()

        mock_load_json.side_effect = ValueError("Generic error")

        # Should not raise exception, just log warning
        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        mock_load_json.assert_called_once_with("test.json")
        mock_get_suggestions.assert_not_called()

    def test_print_suggestions_empty_list(self, capsys):
        """Test _print_suggestions with empty list."""
        strategy = SingleFileConversionStrategy()

        # pylint: disable=protected-access
        strategy._print_suggestions([])

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_suggestions_only_no_improvements(self, capsys):
        """Test _print_suggestions with only 'No improvements needed'."""
        strategy = SingleFileConversionStrategy()
        suggestions = ["No improvements needed - test data is well-structured"]

        # pylint: disable=protected-access
        strategy._print_suggestions(suggestions)

        captured = capsys.readouterr()
        assert captured.out == ""  # Should not print anything

    def test_print_suggestions_filtered_no_improvements(self, capsys):
        """Test _print_suggestions filters 'No improvements needed' with others."""
        strategy = SingleFileConversionStrategy()
        suggestions = [
            "Add test case name",
            "No improvements needed - test data well-structured",
        ]

        # pylint: disable=protected-access
        strategy._print_suggestions(suggestions)

        captured = capsys.readouterr()
        assert "💡 Conversion Suggestions:" in captured.out
        assert "Add test case name" in captured.out
        assert "No improvements needed" not in captured.out


class TestMultipleFilesConversionStrategyAdditional:
    """Additional tests for MultipleFilesConversionStrategy."""

    @patch("importobot.core.conversion_strategies.convert_file")
    def test_convert_single_file_with_suggestions(self, mock_convert_file):
        """Test converting single file with suggestions enabled."""
        files = ["single.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.apply_suggestions = True
        mock_args.output_file = "output.robot"
        mock_args.input = None  # Will be set by strategy
        mock_args.no_suggestions = False

        with patch(
            "importobot.core.conversion_strategies.SingleFileConversionStrategy"
        ) as mock_single_strategy:
            mock_single_instance = Mock()
            mock_single_strategy.return_value = mock_single_instance

            strategy.convert(mock_args)

            # Should create SingleFileConversionStrategy and call convert
            mock_single_strategy.assert_called_once()
            assert mock_args.input == "single.json"
            mock_single_instance.convert.assert_called_once_with(mock_args)
            # Verify mock_convert_file was not called directly (strategy handles it)
            mock_convert_file.assert_not_called()

    @patch("importobot.core.conversion_strategies.convert_file")
    def test_convert_single_file_without_suggestions(self, mock_convert_file):
        """Test converting single file without suggestions."""
        files = ["single.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.apply_suggestions = False
        mock_args.output_file = "output.robot"
        mock_args.no_suggestions = False

        with patch.object(strategy, "_display_suggestions"):
            strategy.convert(mock_args)

            mock_convert_file.assert_called_once_with("single.json", "output.robot")

    @patch("importobot.core.conversion_strategies.convert_multiple_files")
    def test_convert_multiple_files_with_suggestions_warning(
        self, mock_convert_multiple, capsys
    ):
        """Test converting multiple files shows suggestions warning."""
        files = ["file1.json", "file2.json"]
        strategy = MultipleFilesConversionStrategy(files)

        mock_args = Mock()
        mock_args.apply_suggestions = True
        mock_args.output_file = "/output/dir"

        strategy.convert(mock_args)

        captured = capsys.readouterr()
        assert (
            "Warning: --apply-suggestions only supported for single files."
            in captured.out
        )
        assert "Performing normal conversion instead..." in captured.out
        mock_convert_multiple.assert_called_once_with(files, "/output/dir")

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_no_suggestions_flag(
        self, mock_load_json, mock_get_suggestions
    ):
        """Test _display_suggestions respects no_suggestions flag."""
        strategy = MultipleFilesConversionStrategy(["test.json"])

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=True)

        mock_load_json.assert_not_called()
        mock_get_suggestions.assert_not_called()

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_filters_no_improvements(
        self, mock_load_json, mock_get_suggestions, capsys
    ):
        """Test _display_suggestions filters out 'No improvements needed'."""
        strategy = MultipleFilesConversionStrategy(["test.json"])

        mock_load_json.return_value = {"test": "data"}
        mock_get_suggestions.return_value = [
            "No improvements needed - test data is well-structured"
        ]

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        captured = capsys.readouterr()
        assert (
            captured.out == ""
        )  # Should not print anything for only "No improvements needed"
