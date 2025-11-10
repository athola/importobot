"""Unit tests for file operations utilities."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from importobot.utils.file_operations import (
    ConversionContext,
    convert_with_temp_file,
    display_suggestion_changes,
    load_json_file,
    process_single_file_with_suggestions,
    save_improved_json_and_convert,
    temporary_json_file,
)


class TestTemporaryJsonFile:
    """Tests for temporary_json_file context manager."""

    def test_creates_temporary_json_file(self) -> None:
        """Test that temporary_json_file creates a valid JSON file."""
        test_data: dict[str, Any] = {"test": "data", "number": 123}

        with temporary_json_file(test_data) as temp_filename:
            assert os.path.exists(temp_filename)
            assert temp_filename.endswith(".json")

            # Verify the content is correct
            with open(temp_filename, encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

        # File should be cleaned up after context
        assert not os.path.exists(temp_filename)

    def test_handles_unicode_content(self) -> None:
        """Test that temporary_json_file handles unicode content."""
        test_data = {"unicode": "Test with ñ, é, 中文", "special": "Test with ♠"}

        with temporary_json_file(test_data) as temp_filename:
            with open(temp_filename, encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_cleanup_on_exception(self) -> None:
        """Test that temporary file is cleaned up even if exception occurs."""
        test_data = {"test": "data"}
        temp_filename = None

        try:
            with temporary_json_file(test_data) as filename:
                temp_filename = filename
                assert os.path.exists(temp_filename)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # File should still be cleaned up
        assert temp_filename is not None
        assert not os.path.exists(temp_filename)


class TestLoadJsonFile:
    """Tests for load_json_file function."""

    def test_loads_valid_json_file(self) -> None:
        """Test loading a valid JSON file."""
        test_data = {"key": "value", "number": 42}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(test_data, f)
            temp_filename = f.name

        try:
            result = load_json_file(temp_filename)
            assert result == test_data
        finally:
            os.unlink(temp_filename)

    def test_load_json_file_single_test_case_array_unwraps(self) -> None:
        """Arrays with a single test case are unwrapped to a dictionary."""
        test_data = [{"name": "Login flow", "steps": []}]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(test_data, f)
            temp_filename = f.name

        try:
            result = load_json_file(temp_filename)
            assert result == test_data[0]
        finally:
            os.unlink(temp_filename)

    def test_load_json_file_multiple_test_cases_array_wraps(self) -> None:
        """Arrays with multiple test cases are wrapped for downstream parsing."""
        test_data = [
            {"name": "Login flow", "steps": []},
            {"name": "Logout flow", "steps": []},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(test_data, f)
            temp_filename = f.name

        try:
            result = load_json_file(temp_filename)
            assert result == {"testCases": test_data}
        finally:
            os.unlink(temp_filename)

    def test_load_json_file_empty_path_raises_error(self) -> None:
        """User gets clear error message when no file path provided."""
        with pytest.raises(ValueError, match="File path cannot be empty or None"):
            load_json_file("")

        with pytest.raises(ValueError, match="File path cannot be empty or None"):
            load_json_file(None)

    def test_load_json_file_missing_file_gives_clear_error(
        self, tmp_path: Path
    ) -> None:
        """User gets clear error message when file doesn't exist."""
        non_existent_file = tmp_path / "non_existent_file.json"
        with pytest.raises(
            FileNotFoundError,
            match=rf"Could not find JSON file: {re.escape(str(non_existent_file))}",
        ):
            load_json_file(str(non_existent_file))

    def test_load_json_file_corrupted_json_gives_helpful_error(self) -> None:
        """User gets helpful error message when JSON file is corrupted."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{ invalid json content")
            temp_filename = f.name

        try:
            with pytest.raises(
                json.JSONDecodeError,
                match=r"JSON file appears to be corrupted at line \d+, column \d+",
            ):
                load_json_file(temp_filename)
        finally:
            os.unlink(temp_filename)


@patch("importobot.core.converter.convert_file")
class TestConvertWithTempFile:
    """Tests for convert_with_temp_file function."""

    def test_successful_conversion_with_temp_file(
        self, mock_convert_file: Mock
    ) -> None:
        """Test successful conversion with temporary file."""
        test_data: dict[str, Any] = {"testScript": {"steps": []}}
        robot_filename = "test.robot"

        convert_with_temp_file(test_data, robot_filename, mock_convert_file)

        # Verify convert_file was called with a temporary JSON file
        mock_convert_file.assert_called_once()
        call_args = mock_convert_file.call_args[0]
        assert len(call_args) == 2
        assert call_args[0].endswith(".json")
        assert call_args[1] == robot_filename

    def test_displays_changes_when_provided(self, mock_convert_file: Mock) -> None:
        """Test that changes are displayed when function and data provided."""
        test_data: dict[str, Any] = {"testScript": {"steps": []}}
        robot_filename = "test.robot"
        changes_made: list[dict[str, str]] = [
            {"field": "test", "original": "old", "improved": "new"}
        ]

        mock_display_func = Mock()
        mock_args = Mock()
        context = ConversionContext(
            changes_made=changes_made,
            display_changes_func=mock_display_func,
            args=mock_args,
        )
        convert_with_temp_file(test_data, robot_filename, mock_convert_file, context)

        mock_display_func.assert_called_once_with(changes_made, mock_args)
        mock_convert_file.assert_called_once()

    def test_display_skipped_when_no_changes_provided(
        self, mock_convert_file: Mock
    ) -> None:
        """Test that display is skipped when no changes provided."""
        test_data: dict[str, Any] = {"testScript": {"steps": []}}
        robot_filename = "test.robot"

        mock_display_func = Mock()
        mock_args = Mock()
        context = ConversionContext(
            changes_made=None, display_changes_func=mock_display_func, args=mock_args
        )
        convert_with_temp_file(test_data, robot_filename, mock_convert_file, context)

        mock_display_func.assert_not_called()
        mock_convert_file.assert_called_once()


class TestSaveImprovedJsonAndConvert:
    """Tests for save_improved_json_and_convert function."""

    @patch("importobot.utils.file_operations.convert_with_temp_file")
    def test_saves_json_and_converts(
        self, mock_convert_with_temp_file: Mock, tmp_path: Path
    ) -> None:
        """Test saving improved JSON and converting to Robot Framework."""
        improved_data = {"name": "Test", "steps": []}

        mock_args = Mock()
        mock_args.output_file = None
        mock_convert_file = Mock()

        base_path = str(tmp_path / "test")

        context = ConversionContext(args=mock_args)
        save_improved_json_and_convert(
            improved_data=improved_data,
            base_name=base_path,
            convert_file_func=mock_convert_file,
            context=context,
        )

        # Check that JSON file was created
        json_file = f"{base_path}_improved.json"
        assert os.path.exists(json_file)

        # Verify JSON content
        with open(json_file, encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data == improved_data

        # Verify convert_with_temp_file was called correctly
        mock_convert_with_temp_file.assert_called_once()
        call_args = mock_convert_with_temp_file.call_args
        assert call_args[1]["conversion_data"] == improved_data
        assert call_args[1]["robot_filename"] == f"{base_path}_improved.robot"

    @patch("importobot.utils.file_operations.convert_with_temp_file")
    def test_uses_custom_output_file(
        self, mock_convert_with_temp_file: Mock, tmp_path: Path
    ) -> None:
        """Test using custom output file name."""
        improved_data = {"name": "Test", "steps": []}
        custom_output = str(tmp_path / "custom.robot")

        mock_args = Mock()
        mock_args.output_file = custom_output
        mock_convert_file = Mock()

        base_path = str(tmp_path / "test")
        context = ConversionContext(args=mock_args)
        save_improved_json_and_convert(
            improved_data=improved_data,
            base_name=base_path,
            convert_file_func=mock_convert_file,
            context=context,
        )

        # Verify custom output file name was used
        call_args = mock_convert_with_temp_file.call_args
        assert call_args[1]["robot_filename"] == custom_output


class TestDisplaySuggestionChanges:
    """Tests for display_suggestion_changes function."""

    def test_displays_changes_sorted_by_indices(self, capsys: Any) -> None:
        """Test that changes are displayed sorted by test case and step index."""
        changes_made = [
            {
                "test_case_index": 1,
                "step_index": 2,
                "field": "testData",
                "original": "old value 2",
                "improved": "new value 2",
                "reason": "Improved formatting",
            },
            {
                "test_case_index": 0,
                "step_index": 1,
                "field": "description",
                "original": "old value 1",
                "improved": "new value 1",
                "reason": "Better clarity",
            },
        ]

        mock_args = Mock()
        mock_args.no_suggestions = False

        display_suggestion_changes(changes_made, mock_args)

        captured = capsys.readouterr()

        # Check that changes are displayed in sorted order
        assert "Applied Suggestions:" in captured.out
        # Both changes should be present in the output
        assert "Test Case 1, Step 2 - description" in captured.out  # (0,1) change
        assert "Test Case 2, Step 3 - testData" in captured.out  # (1,2) change
        # Check that the sorting worked by verifying first change appears before second
        output = captured.out
        pos1 = output.find("Test Case 1, Step 2")
        pos2 = output.find("Test Case 2, Step 3")
        assert pos1 < pos2, "Changes should be sorted by test case and step index"

    def test_displays_no_changes_message(self, capsys: Any) -> None:
        """Test display when no changes were made."""
        mock_args = Mock()
        mock_args.no_suggestions = False

        display_suggestion_changes([], mock_args)

        captured = capsys.readouterr()
        assert "INFO: No automatic improvements could be applied." in captured.out
        assert "The JSON data is already in good shape!" in captured.out

    def test_respects_no_suggestions_flag(self, capsys: Any) -> None:
        """Test that no output is shown when no_suggestions flag is True."""
        mock_args = Mock()
        mock_args.no_suggestions = True

        display_suggestion_changes([], mock_args)

        captured = capsys.readouterr()
        assert captured.out.strip() == ""


class TestProcessSingleFileWithSuggestions:
    """Tests for process_single_file_with_suggestions function."""

    @patch("importobot.utils.file_operations.save_improved_json_and_convert")
    @patch("importobot.core.converter.apply_conversion_suggestions")
    @patch("importobot.utils.file_operations.load_json_file")
    def test_processes_file_with_os_splitext(
        self,
        mock_load_json: Mock,
        mock_apply_suggestions: Mock,
        mock_save_convert: Mock,
    ) -> None:
        """Test processing with os.path.splitext for basename."""
        # Setup mocks
        json_data: dict[str, Any] = {"testScript": {"steps": []}}
        improved_data: dict[str, Any] = {"testScript": {"steps": [{"improved": True}]}}
        changes_made: list[dict[str, str]] = [
            {"field": "test", "original": "old", "improved": "new"}
        ]

        mock_load_json.return_value = json_data
        mock_apply_suggestions.return_value = (improved_data, changes_made)

        mock_args = Mock()
        mock_args.input = "/path/to/test.json"
        mock_args.no_suggestions = False

        mock_display_func = Mock()

        process_single_file_with_suggestions(
            args=mock_args,
            display_changes_func=mock_display_func,
            use_stem_for_basename=False,
        )

        # Verify function calls
        mock_load_json.assert_called_once_with("/path/to/test.json")
        mock_apply_suggestions.assert_called_once_with(json_data)

        # Check save_improved_json_and_convert was called with correct basename
        mock_save_convert.assert_called_once()
        kwargs = mock_save_convert.call_args.kwargs
        assert kwargs["improved_data"] == improved_data
        assert kwargs["base_name"] == "/path/to/test"  # os.path.splitext result
        context: ConversionContext = kwargs["context"]
        assert context.args is mock_args
        assert context.changes_made == changes_made
        assert context.display_changes_func is mock_display_func

    @patch("importobot.utils.file_operations.save_improved_json_and_convert")
    @patch("importobot.core.converter.apply_conversion_suggestions")
    @patch("importobot.utils.file_operations.load_json_file")
    def test_processes_file_with_path_stem(
        self,
        mock_load_json: Mock,
        mock_apply_suggestions: Mock,
        mock_save_convert: Mock,
    ) -> None:
        """Test processing with Path.stem for basename."""
        # Setup mocks
        json_data: dict[str, Any] = {"testScript": {"steps": []}}
        improved_data: dict[str, Any] = {"testScript": {"steps": [{"improved": True}]}}
        changes_made: list[dict[str, str]] = []

        mock_load_json.return_value = json_data
        mock_apply_suggestions.return_value = (improved_data, changes_made)

        mock_args = Mock()
        mock_args.input = "/path/to/test.json"
        mock_args.no_suggestions = False

        process_single_file_with_suggestions(args=mock_args, use_stem_for_basename=True)

        # Verify function calls
        mock_load_json.assert_called_once_with("/path/to/test.json")
        mock_apply_suggestions.assert_called_once_with(json_data)

        # Check save_improved_json_and_convert was called with correct basename
        mock_save_convert.assert_called_once()
        kwargs = mock_save_convert.call_args.kwargs
        assert kwargs["improved_data"] == improved_data
        assert kwargs["base_name"] == "test"  # Path.stem result
        context: ConversionContext = kwargs["context"]
        assert context.args is mock_args
        assert context.changes_made == changes_made
        assert context.display_changes_func is None

    @patch("importobot.utils.file_operations.save_improved_json_and_convert")
    @patch("importobot.core.converter.apply_conversion_suggestions")
    @patch("importobot.utils.file_operations.load_json_file")
    def test_handles_empty_json_data(
        self,
        mock_load_json: Mock,
        mock_apply_suggestions: Mock,
        mock_save_convert: Mock,
    ) -> None:
        """Test handling of empty JSON data."""
        mock_load_json.return_value = {}
        mock_apply_suggestions.return_value = ({}, [])

        mock_args = Mock()
        mock_args.input = "/path/to/empty.json"
        mock_args.no_suggestions = False

        process_single_file_with_suggestions(
            args=mock_args, use_stem_for_basename=False
        )

        # Verify all functions were still called
        mock_load_json.assert_called_once_with("/path/to/empty.json")
        mock_apply_suggestions.assert_called_once_with({})
        mock_save_convert.assert_called_once()
