"""Comprehensive tests for builtin keyword generator coverage."""

import pytest

from importobot.core.keywords.generators.builtin_keywords import BuiltInKeywordGenerator


@pytest.fixture
def generator():
    """Initialize builtin keyword generator."""
    return BuiltInKeywordGenerator()


class TestConversionKeywords:
    """Test coverage for type conversion keywords."""

    def test_convert_to_integer_keyword(self, generator):
        """Test convert to integer keyword generation."""
        test_data = "value: 123"
        result = generator.generate_convert_to_integer_keyword(test_data)
        assert "Convert To Integer    123" == result

    def test_convert_to_string_keyword(self, generator):
        """Test convert to string keyword generation."""
        test_data = "value: 123"
        result = generator.generate_convert_to_string_keyword(test_data)
        assert "Convert To String    123" == result

    def test_convert_to_boolean_keyword(self, generator):
        """Test convert to boolean keyword generation."""
        test_data = "value: True"
        result = generator.generate_convert_to_boolean_keyword(test_data)
        assert "Convert To Boolean    True" == result

    def test_convert_to_number_keyword(self, generator):
        """Test convert to number keyword generation."""
        test_data = "value: 123.45"
        result = generator.generate_convert_to_number_keyword(test_data)
        assert "Convert To Number    123.45" == result


class TestLoggingAndVariableKeywords:
    """Test coverage for logging and variable manipulation keywords."""

    def test_log_keyword(self, generator):
        """Test log keyword generation."""
        test_data = "message: Test message level: INFO"
        result = generator.generate_log_keyword(test_data)
        assert "Log    Test message level: INFO    INFO" == result

    def test_set_variable_keyword(self, generator):
        """Test set variable keyword generation."""
        test_data = "name: test_var value: test_value"
        result = generator.generate_set_variable_keyword(test_data)
        assert "Set Variable    test_var    test_value" == result

    def test_get_variable_keyword(self, generator):
        """Test get variable keyword generation."""
        test_data = "name: test_var"
        result = generator.generate_get_variable_keyword(test_data)
        assert "Get Variable Value    test_var" == result


class TestStringValidationKeywords:
    """Test coverage for string validation keywords."""

    def test_should_start_with_keyword(self, generator):
        """Test should start with keyword generation."""
        test_data = "text: hello world"
        expected = "hello"
        result = generator.generate_should_start_with_keyword(test_data, expected)
        assert "Should Start With    hello    hello" == result

    def test_should_end_with_keyword(self, generator):
        """Test should end with keyword generation."""
        test_data = "text: hello world"
        expected = "world"
        result = generator.generate_should_end_with_keyword(test_data, expected)
        assert "Should End With    hello    world" == result

    def test_should_match_keyword(self, generator):
        """Test should match keyword generation."""
        test_data = "text: hello123"
        expected = "hello*"
        result = generator.generate_should_match_keyword(test_data, expected)
        assert "Should Match    hello123    hello*" == result


class TestCollectionKeywords:
    """Test coverage for collection manipulation keywords."""

    def test_get_length_keyword(self, generator):
        """Test get length keyword generation."""
        test_data = "list: [1,2,3]"
        result = generator.generate_get_length_keyword(test_data)
        assert "Get Length" in result

    def test_get_count_keyword(self, generator):
        """Test get count keyword generation."""
        test_data = "list: [1,2,3,2,2] item: 2"
        expected = "2"
        result = generator.generate_get_count_keyword(test_data, expected)
        assert "Get Count" in result

    def test_assert_contains_keyword(self, generator):
        """Test assert contains keyword generation."""
        test_data = "text: hello world"
        expected = "world"
        result = generator.generate_assert_contains_keyword(test_data, expected)
        assert "Should Contain" in result


class TestControlFlowKeywords:
    """Test coverage for control flow keywords."""

    def test_evaluate_keyword(self, generator):
        """Test evaluate keyword generation."""
        test_data = "expression: 2 + 2"
        result = generator.generate_evaluate_keyword(test_data)
        assert "Evaluate    2 + 2" == result

    def test_run_keyword_if_keyword(self, generator):
        """Test run keyword if keyword generation."""
        test_data = "condition: '${var}' == 'expected' keyword: Log message"
        result = generator.generate_run_keyword_if_keyword(test_data)
        assert "Run Keyword If" in result

    def test_repeat_keyword_keyword(self, generator):
        """Test repeat keyword generation."""
        test_data = "times: 3 keyword: Log Hello"
        result = generator.generate_repeat_keyword_keyword(test_data)
        assert "Repeat Keyword" in result and "3" in result

    def test_fail_keyword(self, generator):
        """Test fail keyword generation."""
        test_data = "message: Test failed"
        result = generator.generate_fail_keyword(test_data)
        assert "Fail    Test failed" == result


class TestVerificationKeywords:
    """Test coverage for verification and comparison keywords."""

    def test_verification_keyword(self, generator):
        """Test verification keyword generation."""
        description = "verify values are equal"
        test_data = "actual: 5 expected: 5"
        expected = "5"
        result = generator.generate_verification_keyword(
            description, test_data, expected
        )
        assert "Should Be Equal" in result

    def test_verify_keyword(self, generator):
        """Test verify keyword generation."""
        expected = "test_value"
        result = generator.generate_verify_keyword(expected)
        assert "Should Be Equal    ${actual}    test_value" == result

    def test_comparison_keyword(self, generator):
        """Test comparison keyword generation."""
        description = "check if values are equal"
        test_data = "actual: 5 expected: 5"
        result = generator.generate_comparison_keyword(description, test_data)
        assert "Should Be Equal" in result


class TestIntegrationAndEdgeCases:
    """Test coverage for integration scenarios and edge cases."""

    def test_generate_step_keywords_integration(self, generator):
        """Test step keywords generation integration."""
        step = {
            "step": "Verify that value equals 5",
            "test_data": "actual: 5 expected: 5",
            "expected": "Values should be equal",
        }
        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_empty_input_handling(self, generator):
        """Test handling of empty inputs."""
        result = generator.generate_log_keyword("")
        assert "Log    Test message" == result

    def test_missing_value_handling(self, generator):
        """Test handling when values are missing."""
        result = generator.generate_convert_to_integer_keyword("")
        assert "Convert To Integer    ${value}" == result

    def test_special_characters_in_data(self, generator):
        """Test handling of special characters."""
        test_data = "message: Test with special chars: !@#$%^&*()"
        result = generator.generate_log_keyword(test_data)
        assert "Test with special chars: !@#$%^&*()" in result

    def test_complex_expression_evaluation(self, generator):
        """Test complex expression evaluation."""
        test_data = "expression: len('${text}') > 0 and '${text}' != ''"
        result = generator.generate_evaluate_keyword(test_data)
        assert "len('${text}') > 0 and '${text}' != ''" in result
