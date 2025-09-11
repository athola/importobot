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
            with pytest.raises(ValueError, match="Path outside allowed directory"):
                validate_safe_path(outside_path, temp_dir)

    def test_validate_safe_path_directory_traversal(self):
        """Test validation fails for directory traversal attempts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            traversal_path = Path(temp_dir) / ".." / ".." / "etc" / "passwd"
            with pytest.raises(ValueError, match="Path outside allowed directory"):
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
            with pytest.raises(ValueError, match="Path contains unsafe components"):
                validate_safe_path(dangerous_path)

    def test_validate_safe_path_invalid_type(self):
        """Test validation fails for non-string input."""
        with pytest.raises(TypeError, match="File path must be a string"):
            validate_safe_path(123)

    def test_validate_safe_path_empty_string(self):
        """Test validation fails for empty string."""
        with pytest.raises(ValueError, match="File path cannot be empty"):
            validate_safe_path("")

    def test_validate_safe_path_whitespace_only(self):
        """Test validation fails for whitespace-only string."""
        with pytest.raises(ValueError, match="File path cannot be empty"):
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
        with pytest.raises(ValueError, match="JSON input too large"):
            validate_json_size(large_json)

    def test_validate_json_size_custom_limit(self):
        """Test validation with custom size limit."""
        medium_json = '{"data": "' + "x" * (2 * 1024 * 1024) + '"}'

        # Should pass with 5MB limit
        validate_json_size(medium_json, max_size_mb=5)

        # Should fail with 1MB limit
        with pytest.raises(ValueError, match="JSON input too large"):
            validate_json_size(medium_json, max_size_mb=1)

    def test_validate_json_size_non_string(self):
        """Test validation handles non-string input gracefully."""
        # Should not raise exception for non-string input
        validate_json_size(123)
        validate_json_size(None)
        validate_json_size([])


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
        result = sanitize_error_message(None)
        assert result == "An error occurred"
