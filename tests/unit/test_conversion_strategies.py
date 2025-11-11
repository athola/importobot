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
    DirectoryStrategy,
    SingleFileStrategy,
)


class TestConversionStrategy:
    """Tests for the base ConversionStrategy class."""

    def test_abstract_base_class_cannot_be_instantiated(self) -> None:
        """ConversionStrategy is abstract and can't be created directly."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            ConversionStrategy()  # type: ignore[abstract]

    def test_concrete_strategy_implements_convert_method(self) -> None:
        """Concrete strategies need to implement the required methods."""

        class IncompleteStrategy(ConversionStrategy):
            """Test class missing required abstract methods."""

        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            IncompleteStrategy()  # type: ignore[abstract]


class TestSingleFileStrategy:
    """Tests for SingleFileStrategy."""

    def test_validates_required_output_file(self) -> None:
        """Test that output file is required for single file conversion."""
        strategy = SingleFileStrategy()

        mock_args = Mock()
        mock_args.output_file = None

        with pytest.raises(
            exceptions.ValidationError,
            match="Output file required for single file input",
        ):
            strategy.validate_args(mock_args)

    @patch("importobot.core.conversion_strategies.process_single_file_with_suggestions")
    def test_displays_suggestions_after_conversion(
        self,
        mock_process_file: MagicMock,  # pylint: disable=unused-argument
    ) -> None:
        """Test that suggestions are displayed after conversion."""
        strategy = SingleFileStrategy()

        mock_args = Mock()
        mock_args.output_file = "output.robot"
        mock_args.input = "input.json"
        mock_args.no_suggestions = False
        mock_args.apply_suggestions = True

        with patch.object(strategy, "_display_suggestions") as mock_display:
            strategy.convert(mock_args)

        mock_display.assert_called_once_with("input.json", False)

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions(
        self, mock_load_json: MagicMock, mock_get_suggestions: MagicMock, capsys: Any
    ) -> None:
        """Test displaying suggestions for the input file."""
        strategy = SingleFileStrategy()

        mock_load_json.return_value = {"test": "data"}
        mock_suggestions = [
            "Suggestion 1: Improve test data format",
            "Suggestion 2: Add more descriptive step names",
        ]
        mock_get_suggestions.return_value = mock_suggestions

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        captured = capsys.readouterr()
        assert "Conversion Suggestions:" in captured.out
        assert "1. Suggestion 1: Improve test data format" in captured.out
        assert "2. Suggestion 2: Add more descriptive step names" in captured.out

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_respects_no_suggestions_flag(
        self, mock_load_json: MagicMock, mock_get_suggestions: MagicMock
    ) -> None:
        """Test that suggestions are not displayed when no_suggestions is True."""
        strategy = SingleFileStrategy()

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=True)

        # Should not call load_json_file or get_conversion_suggestions
        mock_load_json.assert_not_called()
        mock_get_suggestions.assert_not_called()

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_handles_empty_suggestions(
        self, mock_load_json: MagicMock, mock_get_suggestions: MagicMock, capsys: Any
    ) -> None:
        """Test handling when there are no suggestions."""
        strategy = SingleFileStrategy()

        mock_load_json.return_value = {"test": "data"}
        mock_get_suggestions.return_value = []

        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        captured = capsys.readouterr()
        # Should not print anything for empty suggestions
        assert captured.out.strip() == ""


class TestMultipleFileStrategy:
    """Tests for MultipleFileStrategy."""


class TestDirectoryStrategy:
    """Tests for DirectoryStrategy."""

    def test_validates_required_output_directory(self) -> None:
        """Test that output directory is required."""
        strategy = DirectoryStrategy()

        mock_args = Mock()
        mock_args.output_file = None

        with pytest.raises(
            exceptions.ValidationError,
            match="Output directory required for directory input",
        ):
            strategy.validate_args(mock_args)

    @patch("importobot.core.conversion_strategies.convert_directory")
    def test_handles_suggestions_warning(
        self, mock_convert_directory: MagicMock, capsys: Any
    ) -> None:
        """Test warning when suggestions are requested for directory."""
        strategy = DirectoryStrategy()

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

    def test_user_can_convert_complex_test_scenario_end_to_end(self) -> None:
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
            strategy = SingleFileStrategy()

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

    def test_user_can_process_directory_with_mixed_test_types(self) -> None:
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
            strategy = DirectoryStrategy()

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

    def test_single_file_strategy_end_to_end(self) -> None:
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

            strategy = SingleFileStrategy()

            # Mock the conversion process to avoid actual file operations
            with (
                patch("importobot.core.conversion_strategies.convert_file"),
                patch.object(strategy, "_display_suggestions"),
            ):
                strategy.convert(mock_args)

            # Test passes if no exceptions are raised

    def test_strategy_handles_conversion_errors(self) -> None:
        """Test that strategies handle conversion errors gracefully."""
        strategy = SingleFileStrategy()

        mock_args = Mock()
        mock_args.output_file = "output.robot"
        mock_args.input = "nonexistent.json"
        mock_args.no_suggestions = True
        mock_args.apply_suggestions = True

        # Mock process_single_file_with_suggestions to raise an exception
        patch_target = (
            "importobot.core.conversion_strategies.process_single_file_with_suggestions"
        )
        with (
            patch(patch_target, side_effect=Exception("Conversion failed")),
            patch.object(strategy, "_display_suggestions"),
            pytest.raises(Exception, match="Conversion failed"),
        ):
            strategy.convert(mock_args)


class TestSingleFileStrategyAdditional:
    """Additional tests for SingleFileStrategy edge cases."""

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_with_importobot_error(
        self, mock_load_json: MagicMock, mock_get_suggestions: MagicMock
    ) -> None:
        """Test _display_suggestions handles ImportobotError."""
        strategy = SingleFileStrategy()

        mock_load_json.side_effect = exceptions.ImportobotError("Load failed")

        # Should not raise exception, just log warning
        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        mock_load_json.assert_called_once_with("test.json")
        mock_get_suggestions.assert_not_called()

    @patch("importobot.core.conversion_strategies.get_conversion_suggestions")
    @patch("importobot.core.conversion_strategies.load_json_file")
    def test_display_suggestions_with_generic_error(
        self, mock_load_json: MagicMock, mock_get_suggestions: MagicMock
    ) -> None:
        """Test _display_suggestions handles generic exceptions."""
        strategy = SingleFileStrategy()

        mock_load_json.side_effect = ValueError("Generic error")

        # Should not raise exception, just log warning
        # pylint: disable=protected-access
        strategy._display_suggestions("test.json", no_suggestions=False)

        mock_load_json.assert_called_once_with("test.json")
        mock_get_suggestions.assert_not_called()
