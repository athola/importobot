"""Tests for CLI handlers module."""

import os
import tempfile
from unittest.mock import patch

from importobot.cli.handlers import (
    collect_suggestions,
    detect_input_type,
    filter_suggestions,
    print_suggestions,
    requires_output_directory,
)


class TestInputTypeDetection:
    """Test input type detection functions."""

    def test_detect_wildcard_pattern(self):
        """Test wildcard pattern detection."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["test1.json", "test2.json"]
            input_type, files = detect_input_type("*.json")
            assert input_type == "wildcard"
            assert files == ["test1.json", "test2.json"]

    def test_detect_wildcard_no_matches(self):
        """Test wildcard pattern with no matches."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = []
            input_type, files = detect_input_type("*.json")
            assert input_type == "error"
            assert files == []

    def test_detect_wildcard_non_json_files(self):
        """Test wildcard pattern filtering non-JSON files."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["test1.txt", "test2.xml"]
            input_type, files = detect_input_type("*.*")
            assert input_type == "error"
            assert files == []

    def test_detect_directory(self):
        """Test directory detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_type, files = detect_input_type(temp_dir)
            assert input_type == "directory"
            assert files == [temp_dir]

    def test_detect_file(self):
        """Test file detection."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            try:
                input_type, files = detect_input_type(temp_file.name)
                assert input_type == "file"
                assert files == [temp_file.name]
            finally:
                os.unlink(temp_file.name)

    def test_detect_nonexistent_path(self):
        """Test nonexistent path detection."""
        input_type, files = detect_input_type("/nonexistent/path")
        assert input_type == "error"
        assert files == []


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
        assert filtered == []

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

    def test_print_suggestions_no_improvements_only(self, capsys):
        """Test not printing 'No improvements needed' alone."""
        print_suggestions(["No improvements needed"])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_suggestions_real_suggestions(self, capsys):
        """Test printing real suggestions."""
        suggestions = ["Improve step description", "Add expected result"]
        print_suggestions(suggestions)
        captured = capsys.readouterr()
        assert "💡 Conversion Suggestions:" in captured.out
        assert "1. Improve step description" in captured.out
        assert "2. Add expected result" in captured.out
