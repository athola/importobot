"""Unit tests for suggestion engine module.

Tests the main suggestion engine that orchestrates all suggestion components.
Following TDD principles with comprehensive suggestion validation.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from importobot import exceptions
from importobot.core.interfaces import SuggestionEngine
from importobot.core.suggestions.suggestion_engine import GenericSuggestionEngine


class TestGenericSuggestionEngineInitialization:
    """Test GenericSuggestionEngine initialization."""

    def test_suggestion_engine_initializes_correctly(self):
        """Test that suggestion engine initializes with all required components."""
        engine = GenericSuggestionEngine()

        # Check that all analyzers are initialized
        assert hasattr(engine, "field_validator")
        assert hasattr(engine, "step_analyzer")
        assert hasattr(engine, "parameter_analyzer")
        assert hasattr(engine, "comparison_analyzer")
        assert hasattr(engine, "builtin_analyzer")

    def test_suggestion_engine_implements_interface(self):
        """Test that GenericSuggestionEngine implements SuggestionEngine interface."""

        engine = GenericSuggestionEngine()
        assert isinstance(engine, SuggestionEngine)

    def test_suggestion_engine_has_required_methods(self):
        """Test that suggestion engine has required methods."""
        engine = GenericSuggestionEngine()

        assert hasattr(engine, "get_suggestions")
        assert callable(engine.get_suggestions)
        assert hasattr(engine, "apply_suggestions")
        assert callable(engine.apply_suggestions)


class TestGetSuggestions:
    """Test get_suggestions method."""

    def test_get_suggestions_with_dict_input(self):
        """Test get_suggestions with dictionary input."""
        engine = GenericSuggestionEngine()
        test_data = {
            "name": "Test Case",
            "description": "Test description",
            "steps": [],
        }

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1

    def test_get_suggestions_with_list_input(self):
        """Test get_suggestions with list input."""
        engine = GenericSuggestionEngine()
        test_data = [
            {"name": "Test Case 1", "steps": []},
            {"name": "Test Case 2", "steps": []},
        ]

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)

    def test_get_suggestions_with_nested_tests(self):
        """Test get_suggestions with nested test structure."""
        engine = GenericSuggestionEngine()
        test_data = {"tests": [{"name": "Test Case", "steps": []}]}

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)

    def test_get_suggestions_with_test_cases_key(self):
        """Test get_suggestions with testCases key."""
        engine = GenericSuggestionEngine()
        test_data = {"testCases": [{"name": "Test Case", "steps": []}]}

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)

    def test_get_suggestions_with_invalid_input(self):
        """Test get_suggestions with invalid input."""
        engine = GenericSuggestionEngine()

        suggestions = engine.get_suggestions("invalid")
        assert isinstance(suggestions, list)
        assert len(suggestions) == 1
        assert "Invalid JSON structure" in suggestions[0]

    def test_get_suggestions_with_well_structured_data(self):
        """Test get_suggestions with well-structured data."""
        engine = GenericSuggestionEngine()
        test_data = {
            "name": "Well Structured Test",
            "description": "Complete test case",
            "steps": [
                {
                    "step": "Navigate to login page",
                    "expectedResult": "Page loads successfully",
                }
            ],
        }

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)
        # Should return suggestions or "No improvements needed" - either is valid
        assert len(suggestions) >= 1

    @patch("importobot.core.suggestions.suggestion_engine.GenericTestFileParser")
    def test_get_suggestions_handles_parser_errors(self, mock_parser_class):
        """Test that get_suggestions handles parser errors gracefully."""
        mock_parser = Mock()
        mock_parser.find_steps.side_effect = Exception("Parser error")
        mock_parser_class.return_value = mock_parser

        engine = GenericSuggestionEngine()
        test_data = {"name": "Test", "steps": []}

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        assert any("Error analyzing test data" in s for s in suggestions)


class TestApplySuggestions:
    """Test apply_suggestions method."""

    def test_apply_suggestions_with_dict_input(self):
        """Test apply_suggestions with dictionary input."""
        engine = GenericSuggestionEngine()
        test_data: dict[str, Any] = {"steps": []}

        improved_data, changes = engine.apply_suggestions(test_data)
        assert isinstance(improved_data, dict)
        assert isinstance(changes, list)
        # Original data should not be modified
        assert "name" not in test_data

    def test_apply_suggestions_with_list_input(self):
        """Test apply_suggestions with list input."""
        engine = GenericSuggestionEngine()
        test_data: list[dict[str, Any]] = [{"steps": []}, {"steps": []}]

        improved_data, changes = engine.apply_suggestions(test_data)
        assert isinstance(improved_data, list)
        assert isinstance(changes, list)
        assert len(improved_data) == 2

    def test_apply_suggestions_preserves_original_data(self):
        """Test that apply_suggestions doesn't modify original data."""
        engine = GenericSuggestionEngine()
        original_data: dict[str, Any] = {"steps": []}
        original_copy = original_data.copy()

        improved_data, _ = engine.apply_suggestions(original_data)

        # Original data should be unchanged
        assert original_data == original_copy
        # But improved data might have additions
        assert isinstance(improved_data, dict)

    def test_apply_suggestions_tracks_changes(self):
        """Test that apply_suggestions tracks changes made."""
        engine = GenericSuggestionEngine()
        test_data: dict[str, Any] = {"steps": []}

        improved_data, changes = engine.apply_suggestions(test_data)

        assert isinstance(changes, list)
        # Should have made some changes (like adding default name/description/steps)
        # Verify tracked changes by ensuring the improved data differs from original
        assert "name" in improved_data or "testScript" in improved_data
        # Changes list should contain the modifications made
        assert all(isinstance(change, dict) for change in changes)

    def test_apply_suggestions_with_nested_structure(self):
        """Test apply_suggestions with nested test structure."""
        engine = GenericSuggestionEngine()
        test_data: dict[str, Any] = {"tests": [{"steps": []}, {"steps": []}]}

        improved_data, _ = engine.apply_suggestions(test_data)
        assert isinstance(improved_data, dict)
        assert "tests" in improved_data
        assert len(improved_data["tests"]) == 2

    @patch("importobot.core.suggestions.suggestion_engine.GenericTestFileParser")
    def test_apply_suggestions_handles_errors(self, mock_parser_class):
        """Test that apply_suggestions handles errors appropriately."""
        mock_parser = Mock()
        mock_parser.find_steps.side_effect = Exception("Parser error")
        mock_parser_class.return_value = mock_parser

        engine = GenericSuggestionEngine()
        test_data: dict[str, Any] = {"steps": []}

        with pytest.raises(exceptions.ImportobotError):
            engine.apply_suggestions(test_data)


class TestPrivateMethods:
    """Test private helper methods."""

    def test_extract_test_cases_with_list(self):
        """Test _extract_test_cases with list input."""
        engine = GenericSuggestionEngine()
        test_data = [{"name": "Test1"}, {"name": "Test2"}]

        # pylint: disable=protected-access
        result = engine._extract_test_cases(test_data)
        assert result == test_data

    def test_extract_test_cases_with_dict_tests_key(self):
        """Test _extract_test_cases with dict containing tests key."""
        engine = GenericSuggestionEngine()
        test_data = {"tests": [{"name": "Test1"}]}

        # pylint: disable=protected-access
        result = engine._extract_test_cases(test_data)
        assert result == [{"name": "Test1"}]

    def test_extract_test_cases_with_dict_test_cases_key(self):
        """Test _extract_test_cases with dict containing testCases key."""
        engine = GenericSuggestionEngine()
        test_data = {"testCases": [{"name": "Test1"}]}

        # pylint: disable=protected-access
        result = engine._extract_test_cases(test_data)
        assert result == [{"name": "Test1"}]

    def test_extract_test_cases_with_single_test_dict(self):
        """Test _extract_test_cases with single test case dict."""
        engine = GenericSuggestionEngine()
        test_data = {"name": "Single Test"}

        # pylint: disable=protected-access
        result = engine._extract_test_cases(test_data)
        assert result == [{"name": "Single Test"}]

    def test_extract_test_cases_with_invalid_input(self):
        """Test _extract_test_cases with invalid input."""
        engine = GenericSuggestionEngine()

        # pylint: disable=protected-access
        result = engine._extract_test_cases("invalid")
        assert isinstance(result, str)
        assert "Invalid JSON structure" in result

    def test_extract_test_cases_for_improvement_matches_extract_test_cases(self):
        """Test that both extraction methods behave consistently."""
        engine = GenericSuggestionEngine()

        test_inputs = [
            [{"name": "Test1"}],
            {"tests": [{"name": "Test1"}]},
            {"testCases": [{"name": "Test1"}]},
            {"name": "Single Test"},
            "invalid",
        ]

        for test_input in test_inputs:
            # pylint: disable=protected-access
            result1 = engine._extract_test_cases(test_input)
            # pylint: disable=protected-access
            result2 = engine._extract_test_cases_for_improvement(test_input)
            assert result1 == result2


class TestSuggestionEngineIntegration:
    """Test suggestion engine integration scenarios."""

    def test_complete_suggestion_workflow(self):
        """Test complete workflow from suggestions to application."""
        engine = GenericSuggestionEngine()
        test_data = {"steps": [{"step": "Click login"}]}

        # Get suggestions
        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)

        # Apply suggestions
        improved_data, changes = engine.apply_suggestions(test_data)
        assert isinstance(improved_data, dict)
        assert isinstance(changes, list)

        # Verify improvements were made - assert separately
        # The improved data should have a name field added
        assert "name" in improved_data
        # Changes should have been tracked (non-negative length is always true)
        # So we verify it's actually a list that can contain changes
        assert isinstance(changes, list)

    def test_suggestion_engine_with_complex_test_data(self):
        """Test suggestion engine with complex test structure."""
        engine = GenericSuggestionEngine()
        test_data = {
            "testCases": [
                {
                    "name": "Login Test",
                    "description": "Test user login functionality",
                    "steps": [
                        {"step": "Enter username", "testData": "user@example.com"},
                        {"step": "Enter password", "testData": "password123"},
                        {
                            "step": "Click login button",
                            "expectedResult": "User is logged in",
                        },
                    ],
                },
                {
                    "name": "Logout Test",
                    "steps": [
                        {
                            "step": "Click logout button",
                            "expectedResult": "User is logged out",
                        }
                    ],
                },
            ]
        }

        suggestions = engine.get_suggestions(test_data)
        assert isinstance(suggestions, list)

        improved_data, _ = engine.apply_suggestions(test_data)
        assert isinstance(improved_data, dict)
        assert "testCases" in improved_data
        assert len(improved_data["testCases"]) == 2

    def test_suggestion_engine_error_recovery(self):
        """Test that suggestion engine recovers gracefully from errors."""
        engine = GenericSuggestionEngine()

        # Test with malformed data
        malformed_data = {
            "tests": [
                None,  # This should be handled gracefully
                {"name": "Valid Test", "steps": []},
                "string instead of dict",  # This should also be handled
            ]
        }

        suggestions = engine.get_suggestions(malformed_data)
        assert isinstance(suggestions, list)

        # Apply suggestions should still work (skipping invalid entries)
        improved_data, _ = engine.apply_suggestions(malformed_data)
        assert isinstance(improved_data, dict)
        assert "tests" in improved_data
