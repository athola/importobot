"""Comprehensive tests for builtin keyword generator coverage."""

import pytest

from importobot.core.keywords.generators.builtin_keywords import BuiltInKeywordGenerator


@pytest.fixture
def generator() -> BuiltInKeywordGenerator:
    """Initialize builtin keyword generator."""
    return BuiltInKeywordGenerator()


class TestConversionKeywords:
    """Test coverage for type conversion keywords."""

    def test_convert_to_integer_keyword(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test convert to integer keyword generation."""
        test_data = "value: 123"
        result = generator.generate_convert_to_integer_keyword(test_data)
        assert result == "Convert To Integer    123"

    def test_convert_to_string_keyword(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test convert to string keyword generation."""
        test_data = "value: 123"
        result = generator.generate_convert_to_string_keyword(test_data)
        assert result == "Convert To String    123"

    def test_convert_to_boolean_keyword(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test convert to boolean keyword generation."""
        test_data = "value: True"
        result = generator.generate_convert_to_boolean_keyword(test_data)
        assert result == "Convert To Boolean    True"

    def test_convert_to_number_keyword(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test convert to number keyword generation."""
        test_data = "value: 123.45"
        result = generator.generate_convert_to_number_keyword(test_data)
        assert result == "Convert To Number    123.45"


class TestLoggingAndVariableKeywords:
    """Test coverage for logging and variable manipulation keywords."""

    def test_log_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test log keyword generation."""
        test_data = "message: Test message level: INFO"
        result = generator.generate_log_keyword(test_data)
        assert result == "Log    Test message level: INFO    INFO"

    def test_set_variable_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test set variable keyword generation."""
        test_data = "name: test_var value: test_value"
        result = generator.generate_set_variable_keyword(test_data)
        assert result == "Set Variable    test_var    test_value"

    def test_get_variable_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test get variable keyword generation."""
        test_data = "name: test_var"
        result = generator.generate_get_variable_keyword(test_data)
        assert result == "Get Variable Value    test_var"


class TestStringValidationKeywords:
    """Test coverage for string validation keywords."""

    def test_should_start_with_keyword(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test should start with keyword generation."""
        test_data = "text: hello world"
        expected = "hello"
        result = generator.generate_should_start_with_keyword(test_data, expected)
        assert result == "Should Start With    hello    hello"

    def test_should_end_with_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test should end with keyword generation."""
        test_data = "text: hello world"
        expected = "world"
        result = generator.generate_should_end_with_keyword(test_data, expected)
        assert result == "Should End With    hello    world"

    def test_should_match_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test should match keyword generation."""
        test_data = "text: hello123"
        expected = "hello*"
        result = generator.generate_should_match_keyword(test_data, expected)
        assert result == "Should Match    hello123    hello*"


class TestCollectionKeywords:
    """Test coverage for collection manipulation keywords."""

    def test_get_length_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test get length keyword generation."""
        test_data = "list: [1,2,3]"
        result = generator.generate_get_length_keyword(test_data)
        assert "Get Length" in result

    def test_get_count_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test get count keyword generation."""
        test_data = "list: [1,2,3,2,2] item: 2"
        expected = "2"
        result = generator.generate_get_count_keyword(test_data, expected)
        assert "Get Count" in result

    def test_assert_contains_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test assert contains keyword generation."""
        test_data = "text: hello world"
        expected = "world"
        result = generator.generate_assert_contains_keyword(test_data, expected)
        assert "Should Contain" in result


class TestControlFlowKeywords:
    """Test coverage for control flow keywords."""

    def test_evaluate_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test evaluate keyword generation."""
        test_data = "expression: 2 + 2"
        result = generator.generate_evaluate_keyword(test_data)
        assert result == "Evaluate    2 + 2"

    def test_run_keyword_if_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test run keyword if keyword generation."""
        test_data = "condition: '${var}' == 'expected' keyword: Log message"
        result = generator.generate_run_keyword_if_keyword(test_data)
        assert "Run Keyword If" in result

    def test_repeat_keyword_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test repeat keyword generation."""
        test_data = "times: 3 keyword: Log Hello"
        result = generator.generate_repeat_keyword_keyword(test_data)
        assert "Repeat Keyword" in result
        assert "3" in result

    def test_fail_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test fail keyword generation."""
        test_data = "message: Test failed"
        result = generator.generate_fail_keyword(test_data)
        assert result == "Fail    Test failed"


class TestVerificationKeywords:
    """Test coverage for verification and comparison keywords."""

    def test_verification_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test verification keyword generation."""
        description = "verify values are equal"
        test_data = "actual: 5 expected: 5"
        expected = "5"
        result = generator.generate_verification_keyword(
            description, test_data, expected
        )
        assert "Should Be Equal" in result

    def test_verify_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test verify keyword generation."""
        expected = "test_value"
        result = generator.generate_verify_keyword(expected)
        assert result == "Should Be Equal    ${actual}    test_value"

    def test_comparison_keyword(self, generator: BuiltInKeywordGenerator) -> None:
        """Test comparison keyword generation."""
        description = "check if values are equal"
        test_data = "actual: 5 expected: 5"
        result = generator.generate_comparison_keyword(description, test_data)
        assert "Should Be Equal" in result


class TestIntegrationAndEdgeCases:
    """Test coverage for integration scenarios and edge cases."""

    def test_generate_step_keywords_integration(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test step keywords generation integration."""
        step = {
            "step": "Verify that value equals 5",
            "test_data": "actual: 5 expected: 5",
            "expected": "Values should be equal",
        }
        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_empty_input_handling(self, generator: BuiltInKeywordGenerator) -> None:
        """Test handling of empty inputs."""
        result = generator.generate_log_keyword("")
        assert result == "Log    Test message"

    def test_missing_value_handling(self, generator: BuiltInKeywordGenerator) -> None:
        """Test handling when values are missing."""
        result = generator.generate_convert_to_integer_keyword("")
        assert result == "Convert To Integer    ${value}"

    def test_special_characters_in_data(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test handling of special characters."""
        test_data = "message: Test with special chars: !@#$%^&*()"
        result = generator.generate_log_keyword(test_data)
        assert "Test with special chars: !@#$%^&*()" in result

    def test_complex_expression_evaluation(
        self, generator: BuiltInKeywordGenerator
    ) -> None:
        """Test complex expression evaluation."""
        test_data = "expression: len('${text}') > 0 and '${text}' != ''"
        result = generator.generate_evaluate_keyword(test_data)
        assert "len('${text}') > 0 and '${text}' != ''" in result
