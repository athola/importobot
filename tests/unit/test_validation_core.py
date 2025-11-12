"""Unit tests for validation core module.

Tests the core validation functions and utilities.
Following TDD principles with thorough validation testing.
"""

from typing import Any

import pytest

from importobot import exceptions
from importobot.utils.validation import (
    FieldValidator,
    ValidationContext,
    ValidationError,
    format_robot_framework_arguments,
    require_valid_input,
    sanitize_error_message,
    sanitize_robot_string,
    validate_json_dict,
    validate_json_size,
    validate_not_empty,
    validate_safe_path,
    validate_string_content,
    validate_type,
)


class TestValidationType:
    """Test validate_type function."""

    def test_validate_type_with_correct_type(self) -> None:
        """Test validate_type with correct type passes."""
        validate_type("hello", str, "test_param")
        validate_type(42, int, "test_param")
        validate_type([], list, "test_param")
        validate_type({}, dict, "test_param")

    def test_validate_type_with_incorrect_type_raises_error(self) -> None:
        """Test validate_type with incorrect type raises ValidationError."""
        with pytest.raises(ValidationError, match="test_param must be a str, got int"):
            validate_type(42, str, "test_param")

        with pytest.raises(ValidationError, match="number must be a int, got str"):
            validate_type("42", int, "number")

    def test_validate_type_with_none_value(self) -> None:
        """Test validate_type with None value."""
        with pytest.raises(ValidationError, match="param must be a str, got NoneType"):
            validate_type(None, str, "param")

    def test_validate_type_error_message_format(self) -> None:
        """Test that validate_type error messages are properly formatted."""
        with pytest.raises(ValidationError, match="test_list must be a str, got list"):
            validate_type([], str, "test_list")


class TestValidateNotEmpty:
    """Test validate_not_empty function."""

    def test_validate_not_empty_with_valid_values(self) -> None:
        """Test validate_not_empty with valid non-empty values."""
        validate_not_empty("hello", "text")
        validate_not_empty([1, 2, 3], "list")
        validate_not_empty({"key": "value"}, "dict")
        validate_not_empty(42, "number")

    def test_validate_not_empty_with_empty_values_raises_error(self) -> None:
        """Test validate_not_empty with empty values raises ValidationError."""
        with pytest.raises(ValidationError, match="text cannot be empty"):
            validate_not_empty("", "text")

        with pytest.raises(ValidationError, match="list cannot be empty"):
            validate_not_empty([], "list")

        with pytest.raises(ValidationError, match="dict cannot be empty"):
            validate_not_empty({}, "dict")

    def test_validate_not_empty_with_whitespace_string(self) -> None:
        """Test validate_not_empty with whitespace-only string."""
        with pytest.raises(ValidationError, match="text cannot be empty or whitespace"):
            validate_not_empty("   ", "text")

        with pytest.raises(ValidationError, match="text cannot be empty or whitespace"):
            validate_not_empty("\t\n  ", "text")

    def test_validate_not_empty_with_zero_and_false(self) -> None:
        """Test validate_not_empty with zero and False (should raise errors)."""
        with pytest.raises(ValidationError, match="number cannot be empty"):
            validate_not_empty(0, "number")

        with pytest.raises(ValidationError, match="flag cannot be empty"):
            validate_not_empty(False, "flag")

    def test_validate_not_empty_with_none(self) -> None:
        """Test validate_not_empty with None value."""
        with pytest.raises(ValidationError, match="value cannot be empty"):
            validate_not_empty(None, "value")


class TestValidateJsonDict:
    """Test validate_json_dict function."""

    def test_validate_json_dict_with_valid_dict(self) -> None:
        """Test validate_json_dict with valid dictionary."""
        test_dict = {"key": "value", "number": 42}
        result = validate_json_dict(test_dict)
        assert result is test_dict

    def test_validate_json_dict_with_empty_dict(self) -> None:
        """Test validate_json_dict with empty dictionary."""
        test_dict: dict[str, Any] = {}
        result = validate_json_dict(test_dict)
        assert result is test_dict

    def test_validate_json_dict_with_non_dict_raises_error(self) -> None:
        """Test validate_json_dict with non-dictionary raises ValidationError."""
        with pytest.raises(
            ValidationError, match="JSON data must be a dictionary, got list"
        ):
            validate_json_dict([])

        with pytest.raises(
            ValidationError, match="JSON data must be a dictionary, got str"
        ):
            validate_json_dict("not a dict")

        with pytest.raises(
            ValidationError, match="JSON data must be a dictionary, got int"
        ):
            validate_json_dict(42)

    def test_validate_json_dict_with_none(self) -> None:
        """Test validate_json_dict with None value."""
        with pytest.raises(
            ValidationError, match="JSON data must be a dictionary, got NoneType"
        ):
            validate_json_dict(None)


class TestValidateStringContent:
    """Test validate_string_content function."""

    def test_validate_string_content_with_valid_string(self) -> None:
        """Test validate_string_content with valid string."""
        result = validate_string_content("hello world")
        assert result == "hello world"

    def test_validate_string_content_with_empty_string(self) -> None:
        """Test validate_string_content with empty string."""
        result = validate_string_content("")
        assert result == ""

    def test_validate_string_content_with_non_string_raises_error(self) -> None:
        """Test validate_string_content with non-string raises ValidationError."""
        with pytest.raises(ValidationError, match="Content must be a string, got int"):
            validate_string_content(42)

        with pytest.raises(ValidationError, match="Content must be a string, got list"):
            validate_string_content([])

        with pytest.raises(
            ValidationError, match="Content must be a string, got NoneType"
        ):
            validate_string_content(None)

    def test_validate_string_content_with_unicode(self) -> None:
        """Test validate_string_content with unicode strings."""
        unicode_string = "Hello 世界"
        result = validate_string_content(unicode_string)
        assert result == unicode_string


class TestValidateJsonSize:
    """Test validate_json_size function."""

    def test_validate_json_size_with_small_string(self) -> None:
        """Test validate_json_size with small JSON string."""
        small_json = '{"key": "value"}'
        validate_json_size(small_json, 10)  # Should not raise

    def test_validate_json_size_with_large_string_raises_error(self) -> None:
        """Test validate_json_size with large JSON string raises ValidationError."""
        # Create a string larger than 1MB
        large_json = "x" * (1024 * 1024 + 1)  # 1MB + 1 byte

        with pytest.raises(ValidationError, match="JSON input too large"):
            validate_json_size(large_json, 1)

    def test_validate_json_size_with_non_string_ignores(self) -> None:
        """Test validate_json_size with non-string input is ignored."""
        # Should not raise error for non-string input
        validate_json_size(None, 1)
        validate_json_size(42, 1)
        validate_json_size([], 1)

    def test_validate_json_size_custom_limit(self) -> None:
        """Test validate_json_size with custom size limit."""
        # Create string just under limit
        test_string = "x" * (512 * 1024)  # 0.5MB

        validate_json_size(test_string, 1)  # Should pass with 1MB limit

        with pytest.raises(ValidationError):
            validate_json_size(test_string, 0)  # Should fail with 0MB limit

    def test_validate_json_size_error_message_content(self) -> None:
        """Test that validate_json_size error message contains helpful information."""
        large_json = "x" * (2 * 1024 * 1024)  # 2MB

        try:
            validate_json_size(large_json, 1)
        except ValidationError as e:
            error_msg = str(e)
            assert "JSON input too large" in error_msg
            assert "exceeds 1MB limit" in error_msg
            assert "memory exhaustion" in error_msg


class TestRequireValidInputDecorator:
    """Test require_valid_input decorator."""

    def test_require_valid_input_with_valid_parameters(self) -> None:
        """Test require_valid_input decorator with valid parameters."""

        @require_valid_input(
            (0, lambda x: validate_type(x, str, "param1")),
            (1, lambda x: validate_type(x, int, "param2")),
        )
        def test_function(param1: str, param2: int) -> str:
            return f"{param1}:{param2}"

        result = test_function("hello", 42)
        assert result == "hello:42"

    def test_require_valid_input_with_invalid_parameters(self) -> None:
        """Test require_valid_input decorator with invalid parameters."""

        @require_valid_input(
            (0, lambda x: validate_type(x, str, "param1")),
            (1, lambda x: validate_type(x, int, "param2")),
        )
        def test_function(param1: str, param2: int) -> str:
            return f"{param1}:{param2}"

        with pytest.raises(ValidationError, match="param1 must be a str"):
            test_function(42, 100)  # pyright: ignore[reportArgumentType]

    def test_require_valid_input_with_fewer_args_than_validations(self) -> None:
        """Test require_valid_input when fewer args provided than validations."""

        @require_valid_input(
            (0, lambda x: validate_type(x, str, "param1")),
            (2, lambda x: validate_type(x, int, "param3")),  # Index 2 won't exist
        )
        def test_function(param1: str, param2: str = "default") -> str:
            return f"{param1}:{param2}"

        # Should only validate param1, skip validation for index 2
        result = test_function("hello")
        assert result == "hello:default"

    def test_require_valid_input_preserves_function_metadata(self) -> None:
        """Test that require_valid_input preserves function metadata."""

        @require_valid_input((0, lambda x: validate_type(x, str, "param")))
        def documented_function(param: str) -> str:
            """This is a test function."""
            return param

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a test function."


class TestValidationContext:
    """Test ValidationContext class."""

    def test_validation_context_with_no_errors(self) -> None:
        """Test ValidationContext when no validation errors occur."""
        with ValidationContext() as ctx:
            ctx.validate(True, "This should not trigger")
            ctx.validate_type("hello", str, "text")
            ctx.validate_not_empty("hello", "text")

        # Should exit without raising

    def test_validation_context_with_single_error(self) -> None:
        """Test ValidationContext with single validation error."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                ctx.validate(False, "This validation failed")

        with pytest.raises(ValidationError, match="Validation failed"):
            run_validation()

    def test_validation_context_with_multiple_errors(self) -> None:
        """Test ValidationContext accumulates multiple errors."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                ctx.validate(False, "First error")
                ctx.validate(False, "Second error")
                ctx.validate_type(42, str, "param")

        with pytest.raises(ValidationError) as exc_info:
            run_validation()

        error_msg = str(exc_info.value)
        assert "First error" in error_msg
        assert "Second error" in error_msg
        assert "param must be a str" in error_msg

    def test_validation_context_type_validation(self) -> None:
        """Test ValidationContext type validation method."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                ctx.validate_type(42, str, "number_param")

        with pytest.raises(ValidationError) as exc_info:
            run_validation()

        assert "number_param must be a str, got int" in str(exc_info.value)

    def test_validation_context_not_empty_validation(self) -> None:
        """Test ValidationContext not empty validation method."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                ctx.validate_not_empty("", "empty_param")

        with pytest.raises(ValidationError) as exc_info:
            run_validation()

        assert "empty_param cannot be empty" in str(exc_info.value)

    def test_validation_context_not_empty_with_whitespace(self) -> None:
        """Test ValidationContext not empty validation with whitespace."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                ctx.validate_not_empty("   ", "whitespace_param")

        with pytest.raises(ValidationError) as exc_info:
            run_validation()

        assert "whitespace_param cannot be empty or whitespace" in str(exc_info.value)

    def test_validation_context_mixed_validation_methods(self) -> None:
        """Test ValidationContext with mixed validation methods."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                ctx.validate(False, "Custom validation failed")
                ctx.validate_type([], str, "list_param")
                ctx.validate_not_empty({}, "dict_param")

        with pytest.raises(ValidationError) as exc_info:
            run_validation()

        error_msg = str(exc_info.value)
        assert "Custom validation failed" in error_msg
        assert "list_param must be a str, got list" in error_msg
        assert "dict_param cannot be empty" in error_msg

    def test_validation_context_error_accumulation(self) -> None:
        """Test that ValidationContext properly accumulates errors."""
        ctx = ValidationContext()

        ctx.validate(False, "Error 1")
        assert len(ctx.errors) == 1

        ctx.validate_type(42, str, "param")
        assert len(ctx.errors) == 2

        ctx.validate_not_empty("", "empty")
        assert len(ctx.errors) == 3

        # All errors should be present
        assert "Error 1" in ctx.errors
        assert any("param must be a str" in error for error in ctx.errors)
        assert any("empty cannot be empty" in error for error in ctx.errors)


class TestValidationErrorReexport:
    """Test ValidationError re-export."""

    def test_validation_error_is_importobot_validation_error(self) -> None:
        """Test that ValidationError is the correct exception type."""
        assert ValidationError is exceptions.ValidationError

    def test_validation_error_can_be_raised_and_caught(self) -> None:
        """Test that ValidationError can be raised and caught."""
        with pytest.raises(ValidationError, match="Test error"):
            raise ValidationError("Test error")


class TestPathValidationUtilities:
    """Test path validation utilities."""

    def test_validate_safe_path_basic_functionality(self) -> None:
        """Test basic safe path validation."""
        # Test relative path resolution
        result = validate_safe_path("test.txt")
        assert result.endswith("test.txt")
        assert result.startswith("/")  # Should be absolute

    def test_sanitize_robot_string_thorough(self) -> None:
        """Test Robot Framework string sanitization."""
        # Test newline handling
        result = sanitize_robot_string("line1\nline2")
        assert "\n" not in result

        # Test whitespace normalization (function preserves internal spaces)
        result = sanitize_robot_string("  multiple   spaces  ")
        assert result == "multiple   spaces"

        # Test None handling
        result = sanitize_robot_string(None)
        assert result == ""

    def test_sanitize_error_message_functionality(self) -> None:
        """Test error message sanitization."""
        # Test path sanitization
        result = sanitize_error_message("Error in /home/user/file.txt")
        assert "/home/user" not in result

        # Test basic message passthrough
        result = sanitize_error_message("Simple error message")
        assert result == "Simple error message"


class TestUnifiedValidationComponents:
    """Test unified validation components."""

    def test_field_validator_functionality(self) -> None:
        """Test FieldValidator class basic functionality."""
        validator = FieldValidator()

        # Test that it can be instantiated
        assert validator is not None

    def test_format_robot_framework_arguments(self) -> None:
        """Test Robot Framework argument formatting."""
        result = format_robot_framework_arguments(["arg1", "arg2"])
        assert "arg1" in result
        assert "arg2" in result


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple validation functions."""

    def test_complete_json_validation_pipeline(self) -> None:
        """Test complete JSON validation pipeline."""
        json_data = {"test": "data"}
        json_string = '{"test": "data"}'

        # Should all pass
        validated_dict = validate_json_dict(json_data)
        validated_string = validate_string_content(json_string)
        validate_json_size(json_string, 1)
        validate_not_empty(json_string, "json_content")

        assert validated_dict == json_data
        assert validated_string == json_string

    def test_validation_context_full_scenario(self) -> None:
        """Test ValidationContext in a full scenario."""

        def run_validation() -> None:
            with ValidationContext() as ctx:
                # Mix of different validation types
                ctx.validate(len("short") > 10, "String too short")
                ctx.validate_type("not_a_number", int, "numeric_param")
                ctx.validate_not_empty("", "required_field")

                # Also test some passing validations
                ctx.validate(len("hello") == 5, "String length should be 5")
                ctx.validate_type([1, 2, 3], list, "list_param")

        with pytest.raises(ValidationError) as exc_info:
            run_validation()

        error_msg = str(exc_info.value)
        # Should contain failing validations but not passing ones
        assert "String too short" in error_msg
        assert "numeric_param must be a int" in error_msg
        assert "required_field cannot be empty" in error_msg
        # Should not contain passing validation messages
        assert "String length should be 5" not in error_msg

    def test_cross_module_validation_compatibility(self) -> None:
        """Test that validation works across different modules."""
        # Test that core validation functions work correctly
        # Should not raise errors
        path_result = validate_safe_path("test.txt")
        string_result = sanitize_robot_string("test string")

        assert isinstance(path_result, str)
        assert isinstance(string_result, str)
