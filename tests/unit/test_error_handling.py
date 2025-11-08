"""Tests for error handling utilities."""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from importobot.utils.error_handling import (
    EnhancedErrorLogger,
    create_enhanced_io_error_message,
    create_enhanced_json_error_message,
    create_missing_resource_error_message,
    create_validation_error_message,
    safe_file_operation,
    safe_json_load,
)


class TestCreateEnhancedJsonErrorMessage:
    """Test create_enhanced_json_error_message function."""

    def test_basic_json_error_message(self) -> None:
        """Test basic JSON error message creation."""
        error = json.JSONDecodeError("Invalid JSON", "test.json", 5)
        error.lineno = 5
        error.colno = 10
        error.msg = "Expecting ',' delimiter"

        message = create_enhanced_json_error_message(error)

        assert "Failed to parse JSON during JSON parsing" in message
        assert "Line 5, Column 10: Expecting ',' delimiter." in message
        assert "Please check the JSON syntax" in message

    def test_json_error_with_file_path(self) -> None:
        """Test JSON error message with file path."""
        error = json.JSONDecodeError("Invalid JSON", "test.json", 5)
        error.lineno = 5
        error.colno = 10
        error.msg = "Expecting ',' delimiter"

        message = create_enhanced_json_error_message(error, file_path="config.json")

        assert "Failed to parse JSON during JSON parsing from config.json" in message
        assert "Line 5, Column 10" in message

    def test_json_error_with_custom_context(self) -> None:
        """Test JSON error message with custom context."""
        error = json.JSONDecodeError("Invalid JSON", "test.json", 5)
        error.lineno = 5
        error.colno = 10
        error.msg = "Expecting ',' delimiter"

        message = create_enhanced_json_error_message(
            error, context="configuration loading"
        )

        assert "Failed to parse JSON during configuration loading" in message


class TestCreateEnhancedIOErrorMessage:
    """Test create_enhanced_io_error_message function."""

    def test_basic_io_error_message(self) -> None:
        """Test basic IO error message creation."""
        error = OSError("Permission denied")

        message = create_enhanced_io_error_message(error)

        assert "Failed to perform file operation" in message
        assert "Permission denied." in message
        assert "Check file permissions" in message

    def test_io_error_with_file_path(self) -> None:
        """Test IO error message with file path."""
        error = OSError("File not found")

        message = create_enhanced_io_error_message(error, file_path="missing.txt")

        assert "Failed to perform file operation on missing.txt" in message
        assert "File not found." in message

    def test_io_error_with_custom_context(self) -> None:
        """Test IO error message with custom context."""
        error = OSError("Access denied")

        message = create_enhanced_io_error_message(error, context="file reading")

        assert "Failed to perform file reading" in message


class TestCreateMissingResourceErrorMessage:
    """Test create_missing_resource_error_message function."""

    def test_basic_missing_resource_message(self) -> None:
        """Test basic missing resource error message."""
        message = create_missing_resource_error_message("test_lib", "library")

        assert "No library found for 'test_lib'." in message

    def test_missing_resource_with_suggestions(self) -> None:
        """Test missing resource message with available resources and suggestion."""
        message = create_missing_resource_error_message(
            "test_lib",
            "library",
            available_resources=["lib1", "lib2", "lib3"],
            suggestion="Install test_lib using pip install test_lib",
        )

        assert "No library found for 'test_lib'." in message
        assert "Available libraries: lib1, lib2, lib3" in message
        assert "Install test_lib using pip install test_lib" in message

    def test_missing_resource_only_suggestion(self) -> None:
        """Test missing resource message with only suggestion."""
        message = create_missing_resource_error_message(
            "test_lib", "library", suggestion="Try installing the library"
        )

        assert "No library found for 'test_lib'." in message
        assert "Try installing the library" in message

    def test_missing_resource_only_available(self) -> None:
        """Test missing resource message with only available resources."""
        message = create_missing_resource_error_message(
            "test_lib", "library", available_resources=["lib1", "lib2"]
        )

        assert "No library found for 'test_lib'." in message
        assert "Available libraries: lib1, lib2" in message


class TestCreateValidationErrorMessage:
    """Test create_validation_error_message function."""

    def test_basic_validation_error_message(self) -> None:
        """Test basic validation error message creation."""
        errors = ["Field 'name' is required", "Field 'type' must be string"]

        message = create_validation_error_message(errors)

        assert (
            "Validation failed: Field 'name' is required; Field 'type' must be string"
            in message
        )

    def test_validation_error_with_custom_context(self) -> None:
        """Test validation error message with custom context."""
        errors = ["Invalid format"]

        message = create_validation_error_message(
            errors, context="configuration validation"
        )

        assert "Configuration validation failed: Invalid format" in message

    def test_validation_error_with_suggestions(self) -> None:
        """Test validation error message with suggestions."""
        errors = ["Invalid format"]
        suggestions = ["Use JSON format", "Check documentation"]

        message = create_validation_error_message(errors, suggestions=suggestions)

        assert "Validation failed: Invalid format" in message
        assert "Suggestions: Use JSON format; Check documentation" in message


class TestEnhancedErrorLogger:
    """Test EnhancedErrorLogger class."""

    def test_initialization_with_default_logger(self) -> None:
        """Test initialization with default logger."""
        logger = EnhancedErrorLogger()

        assert logger.component_name == "component"
        assert logger.logger is not None

    def test_initialization_with_custom_logger(self) -> None:
        """Test initialization with custom logger."""
        custom_logger = logging.getLogger("test")
        logger = EnhancedErrorLogger(custom_logger, "test_component")

        assert logger.component_name == "test_component"
        assert logger.logger == custom_logger

    def test_log_json_error(self) -> None:
        """Test logging JSON error."""
        error_logger = EnhancedErrorLogger()
        error = json.JSONDecodeError("Invalid", "test.json", 1)
        error.lineno = 1
        error.colno = 5
        error.msg = "Invalid syntax"

        with patch.object(error_logger.logger, "log") as mock_log:
            error_logger.log_json_error(error, file_path="test.json")

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR  # level
            assert (
                "Failed to parse JSON during component JSON parsing from test.json"
                in call_args[0][1]
            )

    def test_log_io_error(self) -> None:
        """Test logging IO error."""
        error_logger = EnhancedErrorLogger()
        error = OSError("Permission denied")

        with patch.object(error_logger.logger, "log") as mock_log:
            error_logger.log_io_error(error, file_path="test.txt")

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR
            assert (
                "Failed to perform component file operation on test.txt"
                in call_args[0][1]
            )

    def test_log_error(self) -> None:
        """Test logging general error."""
        error_logger = EnhancedErrorLogger()
        error = ValueError("Test error")

        with patch.object(error_logger.logger, "log") as mock_log:
            error_logger.log_error(error, context="test operation")

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR
            assert "component test operation: Test error" in call_args[0][1]

    def test_log_missing_resource(self) -> None:
        """Test logging missing resource error."""
        error_logger = EnhancedErrorLogger()
        available = ["res1", "res2"]

        with patch.object(error_logger.logger, "log") as mock_log:
            error_logger.log_missing_resource(
                "missing_res", "resource", available_resources=available
            )

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.WARNING
            assert "component: No resource found for 'missing_res'." in call_args[0][1]
            assert "Available resources: res1, res2" in call_args[0][1]

    def test_log_validation_error(self) -> None:
        """Test logging validation error."""
        error_logger = EnhancedErrorLogger()
        errors = ["Error 1", "Error 2"]
        suggestions = ["Fix 1", "Fix 2"]

        with patch.object(error_logger.logger, "log") as mock_log:
            error_logger.log_validation_error(errors, suggestions=suggestions)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR
            assert "component Validation failed: Error 1; Error 2" in call_args[0][1]
            assert "Suggestions: Fix 1; Fix 2" in call_args[0][1]


class TestSafeJsonLoad:
    """Test safe_json_load function."""

    def test_successful_json_load(self) -> None:
        """Test successful JSON loading."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value", "number": 42}')
            temp_path = f.name

        try:
            result = safe_json_load(temp_path)

            assert result == {"key": "value", "number": 42}
        finally:
            Path(temp_path).unlink()

    def test_json_load_invalid_json(self) -> None:
        """Test loading invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json}')
            temp_path = f.name

        try:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = safe_json_load(temp_path)

                assert result is None
                # Should have called log_json_error which logs to the logger
        finally:
            Path(temp_path).unlink()

    def test_json_load_non_dict_result(self) -> None:
        """Test loading JSON that doesn't result in a dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("[1, 2, 3]")  # Array instead of object
            temp_path = f.name

        try:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = safe_json_load(temp_path)

                assert result is None
                # Should have called log_error which logs to the logger
        finally:
            Path(temp_path).unlink()

    def test_json_load_io_error(self) -> None:
        """Test loading JSON with IO error."""
        result = safe_json_load("/nonexistent/path.json")

        assert result is None

    def test_json_load_with_custom_logger(self) -> None:
        """Test loading JSON with custom logger."""
        custom_logger = logging.getLogger("test")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"test": "data"}')
            temp_path = f.name

        try:
            result = safe_json_load(
                temp_path, logger=custom_logger, component_name="test"
            )

            assert result == {"test": "data"}
        finally:
            Path(temp_path).unlink()


class TestSafeFileOperation:
    """Test safe_file_operation function."""

    def test_successful_file_operation(self) -> None:
        """Test successful file operation."""

        def test_operation() -> str:
            return "success"

        result = safe_file_operation(test_operation, "test.txt")

        assert result == "success"

    def test_file_operation_io_error(self) -> None:
        """Test file operation that raises IO error."""

        def failing_operation() -> None:
            raise OSError("Operation failed")

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = safe_file_operation(failing_operation, "test.txt")

            assert result is None

    def test_file_operation_generic_error(self) -> None:
        """Test file operation that raises generic error."""

        def failing_operation() -> None:
            raise ValueError("Generic error")

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = safe_file_operation(failing_operation, "test.txt")

            assert result is None

    def test_file_operation_with_custom_logger(self) -> None:
        """Test file operation with custom logger."""

        def test_operation() -> str:
            return "success"

        custom_logger = logging.getLogger("test")

        result = safe_file_operation(
            test_operation,
            "test.txt",
            logger=custom_logger,
            component_name="test",
            operation_name="test operation",
        )

        assert result == "success"
