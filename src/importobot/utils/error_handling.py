"""Common error handling utilities for consistent error management."""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from importobot.utils.logging import get_logger


def create_enhanced_json_error_message(
    error: json.JSONDecodeError,
    file_path: str | Path | None = None,
    context: str = "JSON parsing",
) -> str:
    """Create an error message for JSON decode errors.

    Args:
        error: The JSONDecodeError that occurred
        file_path: Optional file path where error occurred
        context: Context description for the error

    Returns:
        Error message with line/column information and guidance
    """
    message_parts = [
        f"Failed to parse JSON during {context}",
    ]

    if file_path:
        message_parts.append(f"from {file_path}")

    message_parts.extend(
        [
            f": Line {error.lineno}, Column {error.colno}: {error.msg}.",
            "Please check the JSON syntax in the configuration file.",
        ]
    )

    return " ".join(message_parts)


def create_enhanced_io_error_message(
    error: IOError,
    file_path: str | Path | None = None,
    context: str = "file operation",
) -> str:
    """Create an error message for IO errors.

    Args:
        error: The IOError that occurred
        file_path: Optional file path where error occurred
        context: Context description for the error

    Returns:
        Error message with guidance
    """
    message_parts = [
        f"Failed to perform {context}",
    ]

    if file_path:
        message_parts.append(f"on {file_path}")

    message_parts.extend(
        [f": {error}.", "Check file permissions and ensure the file is accessible."]
    )

    return " ".join(message_parts)


def create_missing_resource_error_message(
    resource_name: str,
    resource_type: str = "resource",
    available_resources: list[str] | None = None,
    suggestion: str | None = None,
) -> str:
    """Create an error message for missing resources.

    Args:
        resource_name: Name of the missing resource
        resource_type: Type of resource (e.g., "library", "file", "configuration")
        available_resources: List of available resources
        suggestion: Optional suggestion for resolution

    Returns:
        Error message with available alternatives and guidance
    """
    message_parts = [f"No {resource_type} found for '{resource_name}'."]

    if available_resources:
        # Handle pluralization properly
        if resource_type.endswith("y"):
            plural_type = resource_type[:-1] + "ies"
        elif resource_type.endswith(("s", "sh", "ch", "x", "z")):
            plural_type = resource_type + "es"
        else:
            plural_type = resource_type + "s"
        message_parts.append(
            f"Available {plural_type}: {', '.join(available_resources)}"
        )

    if suggestion:
        message_parts.append(suggestion)

    return " ".join(message_parts)


def create_validation_error_message(
    validation_errors: list[str],
    context: str = "validation",
    suggestions: list[str] | None = None,
) -> str:
    """Create an error message for validation failures.

    Args:
        validation_errors: List of validation error messages
        context: Context description for the validation
        suggestions: Optional list of suggestions for fixing the issues

    Returns:
        Error message with validation issues and suggestions
    """
    message_parts = [f"{context.capitalize()} failed: {'; '.join(validation_errors)}"]

    if suggestions:
        message_parts.append(f"Suggestions: {'; '.join(suggestions)}")

    return " ".join(message_parts)


class EnhancedErrorLogger:
    """Utility class for consistent error logging."""

    def __init__(
        self, logger: logging.Logger | None = None, component_name: str = "component"
    ):
        """Initialize error logger.

        Args:
            logger: Logger instance to use. If None, creates default logger.
            component_name: Name of the component for context
        """
        self.logger = logger or get_logger()
        self.component_name = component_name

    def log_json_error(
        self,
        error: json.JSONDecodeError,
        file_path: str | Path | None = None,
        level: int = logging.ERROR,
    ) -> None:
        """Log JSON decode error."""
        message = create_enhanced_json_error_message(
            error, file_path, f"{self.component_name} JSON parsing"
        )
        self.logger.log(level, message)

    def log_io_error(
        self,
        error: IOError,
        file_path: str | Path | None = None,
        operation: str = "file operation",
        level: int = logging.ERROR,
    ) -> None:
        """Log IO error."""
        message = create_enhanced_io_error_message(
            error, file_path, f"{self.component_name} {operation}"
        )
        self.logger.log(level, message)

    def log_error(
        self,
        error: Exception,
        context: str = "operation",
        level: int = logging.ERROR,
    ) -> None:
        """Log general error."""
        message = f"{self.component_name} {context}: {error!s}"
        self.logger.log(level, message)

    def log_missing_resource(
        self,
        resource_name: str,
        resource_type: str = "resource",
        available_resources: list[str] | None = None,
        level: int = logging.WARNING,
    ) -> None:
        """Log missing resource error."""
        message = create_missing_resource_error_message(
            resource_name, resource_type, available_resources
        )
        self.logger.log(level, f"{self.component_name}: {message}")

    def log_validation_error(
        self,
        validation_errors: list[str],
        context: str = "validation",
        suggestions: list[str] | None = None,
        level: int = logging.ERROR,
    ) -> None:
        """Log validation error."""
        message = create_validation_error_message(
            validation_errors, context, suggestions
        )
        self.logger.log(level, f"{self.component_name} {message}")


def safe_json_load(
    file_path: str | Path,
    logger: logging.Logger | None = None,
    component_name: str = "component",
) -> dict[str, Any] | None:
    """Safely load JSON file.

    Args:
        file_path: Path to JSON file
        logger: Logger for error reporting
        component_name: Component name for error context

    Returns:
        Loaded JSON data or None if loading failed
    """
    error_logger = EnhancedErrorLogger(logger, component_name)

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        error_logger.log_error(
            ValueError(f"Expected JSON object, got {type(data).__name__}"),
            f"Invalid JSON structure in {file_path}",
        )
        return None
    except json.JSONDecodeError as e:
        error_logger.log_json_error(e, file_path)
        return None
    except OSError as e:
        error_logger.log_io_error(e, file_path, "JSON file loading")
        return None


def safe_file_operation(
    operation_func: Callable[..., Any],
    file_path: str | Path,
    logger: logging.Logger | None = None,
    component_name: str = "component",
    operation_name: str = "file operation",
) -> Any | None:
    """Safely perform file operation.

    Args:
        operation_func: Function to perform the file operation
        file_path: Path to file
        logger: Logger for error reporting
        component_name: Component name for error context
        operation_name: Name of the operation for error context

    Returns:
        Result of operation or None if operation failed
    """
    error_logger = EnhancedErrorLogger(logger, component_name)

    try:
        return operation_func()
    except OSError as e:
        error_logger.log_io_error(e, file_path, operation_name)
        return None
    except Exception as e:
        error_logger.logger.error(
            f"{component_name} unexpected error during {operation_name} on "
            f"{file_path}: {type(e).__name__}: {e}"
        )
        return None
