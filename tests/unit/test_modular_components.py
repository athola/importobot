"""Tests for modular components."""

from importobot.core.engine import GenericConversionEngine
from importobot.core.keyword_generator import GenericKeywordGenerator
from importobot.core.parsers import GenericTestFileParser
from importobot.core.suggestions import GenericSuggestionEngine


class TestModularComponents:
    """Tests for the modular components."""

    def test_parser_finds_tests(self) -> None:
        """Test that the parser can find tests in various formats."""
        test_parser = GenericTestFileParser()

        # Test with standard format
        test_data = {"tests": [{"name": "Test 1", "steps": []}]}
        found_tests = test_parser.find_tests(test_data)
        assert len(found_tests) == 1
        assert found_tests[0]["name"] == "Test 1"

        # Test with single test case format
        single_test_data = {
            "name": "Single Test",
            "description": "A single test case",
            "steps": [],
        }
        single_tests = test_parser.find_tests(single_test_data)
        assert len(single_tests) == 1
        assert single_tests[0]["name"] == "Single Test"

    def test_keyword_generator_creates_test_case(self) -> None:
        """Test that the keyword generator can create test cases."""
        generator = GenericKeywordGenerator()

        test_data = {
            "name": "Sample Test",
            "description": "A sample test case",
            "steps": [
                {"action": "Do something", "expectedResult": "Something happens"}
            ],
        }

        lines = generator.generate_test_case(test_data)
        assert "Sample Test" in lines[0]
        assert "A sample test case" in lines[1]
        assert "# Step: Do something" in lines[2]

    def test_conversion_engine_converts_data(self) -> None:
        """Test that the conversion engine can convert data."""
        engine = GenericConversionEngine()

        data = {
            "name": "Test Case",
            "description": "A test case description",
            "steps": [{"action": "Navigate to page", "expectedResult": "Page loads"}],
        }

        result = engine.convert(data)
        assert "*** Test Cases ***" in result
        assert "Test Case" in result
        assert "A test case description" in result

    def test_suggestion_engine_generates_suggestions(self) -> None:
        """Test that the suggestion engine generates suggestions."""
        engine = GenericSuggestionEngine()

        # Test with incomplete data that should generate suggestions
        data = {
            "steps": [
                {"expectedResult": "Something happens"}  # Missing action
            ]
        }

        suggestions = engine.get_suggestions(data)
        # Should have suggestions for missing fields
        assert len(suggestions) > 0

        # Verify suggestions for missing fields (updated for new format)
        suggestion_text = " ".join(suggestions).lower()
        assert "name" in suggestion_text
        assert "action" in suggestion_text
