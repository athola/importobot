"""Tests for validation utilities."""

import tempfile
from pathlib import Path

import pytest

from importobot.utils.validation import (
    sanitize_error_message,
    sanitize_robot_string,
    validate_json_size,
    validate_safe_path,
)


class TestPathValidation:
    """Test path validation functionality."""

    def test_validate_safe_path_valid_relative(self):
        """Test validation of valid relative path."""
        result = validate_safe_path("test.txt")
        assert result.endswith("test.txt")
        assert Path(result).is_absolute()

    def test_validate_safe_path_valid_absolute(self):
        """Test validation of valid absolute path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test.txt"
            result = validate_safe_path(str(test_path))
            assert result == str(test_path.resolve())

    def test_validate_safe_path_with_base_dir(self):
        """Test validation with base directory restriction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "subdir" / "test.txt"
            result = validate_safe_path(str(test_path), temp_dir)
            assert result == str(test_path.resolve())

    def test_validate_safe_path_outside_base_dir(self):
        """Test validation fails when path is outside base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            outside_path = "/tmp/outside.txt"
            with pytest.raises(Exception, match="Path outside allowed directory"):
                validate_safe_path(outside_path, temp_dir)

    def test_validate_safe_path_directory_traversal(self):
        """Test validation fails for directory traversal attempts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            traversal_path = Path(temp_dir) / ".." / ".." / "etc" / "passwd"
            with pytest.raises(Exception, match="Path outside allowed directory"):
                validate_safe_path(str(traversal_path), temp_dir)

    def test_validate_safe_path_dangerous_paths(self):
        """Test validation fails for dangerous system paths."""
        dangerous_paths = [
            "/etc/passwd",
            "/proc/version",
            "/sys/kernel",
            "/dev/null",
        ]

        for dangerous_path in dangerous_paths:
            with pytest.raises(Exception, match="Path contains unsafe components"):
                validate_safe_path(dangerous_path)

    def test_validate_safe_path_invalid_type(self):
        """Test validation fails for non-string input."""
        with pytest.raises(Exception, match="File path must be a string"):
            validate_safe_path(123)  # type: ignore

    def test_validate_safe_path_empty_string(self):
        """Test validation fails for empty string."""
        with pytest.raises(Exception, match="File path cannot be empty"):
            validate_safe_path("")

    def test_validate_safe_path_whitespace_only(self):
        """Test validation fails for whitespace-only string."""
        with pytest.raises(Exception, match="File path cannot be empty"):
            validate_safe_path("   ")


class TestStringSanitization:
    """Test string sanitization functionality."""

    def test_sanitize_robot_string_basic(self):
        """Test basic string sanitization."""
        result = sanitize_robot_string("Hello World")
        assert result == "Hello World"

    def test_sanitize_robot_string_newlines(self):
        """Test sanitization removes newlines."""
        result = sanitize_robot_string("Hello\nWorld\r\nTest")
        assert result == "Hello World Test"

    def test_sanitize_robot_string_whitespace(self):
        """Test sanitization trims whitespace."""
        result = sanitize_robot_string("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_robot_string_none(self):
        """Test sanitization handles None input."""
        result = sanitize_robot_string(None)
        assert result == ""

    def test_sanitize_robot_string_non_string(self):
        """Test sanitization converts non-string types."""
        result = sanitize_robot_string(123)
        assert result == "123"

        result = sanitize_robot_string(["test", "list"])
        assert result == "['test', 'list']"

    def test_sanitize_robot_string_complex_whitespace(self):
        """Test sanitization handles complex whitespace scenarios."""
        # Test multiple newlines and carriage returns
        result = sanitize_robot_string("Line1\n\nLine2\r\nLine3\r\rLine4")
        assert result == "Line1  Line2 Line3  Line4"

    def test_sanitize_robot_string_mixed_line_endings(self):
        """Test sanitization handles mixed line endings efficiently."""
        test_input = "Start\nMiddle\r\nEnd\rFinal"
        result = sanitize_robot_string(test_input)
        assert result == "Start Middle End Final"
        # Verify no carriage returns or newlines remain
        assert "\n" not in result
        assert "\r" not in result

    def test_sanitize_robot_string_performance_optimization(self):
        """Test that optimized translate method works correctly."""
        # Test the specific optimization: translate vs multiple replace calls
        test_string = "Hello\nWorld\rTest\n\rLine"
        result = sanitize_robot_string(test_string)

        # Expected result with newlines converted to spaces and carriage returns removed
        expected = "Hello World Test  Line"
        assert result == expected

    def test_sanitize_robot_string_unicode_handling(self):
        """Test sanitization handles unicode characters properly."""
        unicode_string = "Hello\nWorld\r测试\n文本\r"
        result = sanitize_robot_string(unicode_string)
        assert result == "Hello World 测试 文本"

    def test_sanitize_robot_string_edge_cases(self):
        """Test edge cases for string sanitization."""
        # Empty string
        assert sanitize_robot_string("") == ""

        # Only whitespace
        assert sanitize_robot_string("\n\r  \n\r") == ""

        # Only newlines and carriage returns
        assert sanitize_robot_string("\n\r\n\r") == ""


class TestJsonSizeValidation:
    """Test JSON size validation functionality."""

    def test_validate_json_size_small(self):
        """Test validation passes for small JSON."""
        small_json = '{"key": "value"}'
        # Should not raise any exception
        validate_json_size(small_json)

    def test_validate_json_size_large(self):
        """Test validation fails for large JSON."""
        # Create a JSON string larger than 10MB
        large_json = '{"data": "' + "x" * (11 * 1024 * 1024) + '"}'
        with pytest.raises(Exception, match="JSON input too large"):
            validate_json_size(large_json)

    def test_validate_json_size_enhanced_error_message(self):
        """Test that large JSON validation includes enhanced error message."""
        # Create a JSON string larger than 5MB (using smaller limit for testing)
        large_json = '{"data": "' + "x" * (6 * 1024 * 1024) + '"}'

        with pytest.raises(Exception) as exc_info:
            validate_json_size(large_json, max_size_mb=5)

        error_message = str(exc_info.value)
        # Verify enhanced error message components
        assert "exceeds" in error_message
        assert "limit" in error_message
        assert "Consider reducing the input size" in error_message
        assert "memory exhaustion" in error_message
        assert "system instability" in error_message

    def test_validate_json_size_exact_limit(self):
        """Test validation at exact size limit."""
        # Create JSON exactly at limit (should pass)
        limit_mb = 1
        # Account for JSON structure overhead
        data_size = (limit_mb * 1024 * 1024) - 100  # Leave room for JSON structure
        json_string = '{"data": "' + "x" * data_size + '"}'

        # Should not raise exception
        validate_json_size(json_string, max_size_mb=limit_mb)

    def test_validate_json_size_non_string_input(self):
        """Test validation handles non-string input gracefully."""
        # Should not raise exception for non-string input
        validate_json_size(None)
        validate_json_size(123)
        validate_json_size([1, 2, 3])

    def test_validate_json_size_empty_string(self):
        """Test validation handles empty string."""
        validate_json_size("")
        validate_json_size("   ")

    def test_validate_json_size_unicode_content(self):
        """Test validation handles unicode content correctly."""
        unicode_json = '{"message": "Hello 世界 🌍"}'
        validate_json_size(unicode_json)

        # Test with large unicode content
        large_unicode = '{"data": "' + "测试" * (2 * 1024 * 1024) + '"}'
        with pytest.raises(Exception, match="JSON input too large"):
            validate_json_size(large_unicode, max_size_mb=5)

    def test_validate_json_size_custom_limit(self):
        """Test validation with custom size limit."""
        medium_json = '{"data": "' + "x" * (2 * 1024 * 1024) + '"}'

        # Should pass with 5MB limit
        validate_json_size(medium_json, max_size_mb=5)

        # Should fail with 1MB limit
        with pytest.raises(Exception, match="JSON input too large"):
            validate_json_size(medium_json, max_size_mb=1)

    def test_validate_json_size_non_string(self):
        """Test validation handles non-string input gracefully."""
        # Should not raise exception for non-string input
        validate_json_size(123)  # type: ignore
        validate_json_size(None)  # type: ignore
        validate_json_size([])  # type: ignore


class TestErrorMessageSanitization:
    """Test error message sanitization functionality."""

    def test_sanitize_error_message_basic(self):
        """Test basic error message sanitization."""
        result = sanitize_error_message("Basic error message")
        assert result == "Basic error message"

    def test_sanitize_error_message_with_file_path(self):
        """Test sanitization removes full file paths."""
        message = "Could not find file /home/user/documents/secret.txt"
        result = sanitize_error_message(message, "/home/user/documents/secret.txt")
        assert result == "Could not find file 'secret.txt'"

    def test_sanitize_error_message_system_paths(self):
        """Test sanitization removes system paths."""
        message = "Error accessing /home/user/private/file.txt and /usr/local/bin/app"
        result = sanitize_error_message(message)
        assert "/home/user" not in result
        assert "/usr/local" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_message_windows_paths(self):
        """Test sanitization removes Windows paths."""
        message = "Error accessing C:\\Users\\user\\Documents\\file.txt"
        result = sanitize_error_message(message)
        assert "C:\\\\" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_message_empty(self):
        """Test sanitization handles empty message."""
        result = sanitize_error_message("")
        assert result == "An error occurred"

    def test_sanitize_error_message_none(self):
        """Test sanitization handles None message."""
        result = sanitize_error_message(None)  # type: ignore
        assert result == "An error occurred"
