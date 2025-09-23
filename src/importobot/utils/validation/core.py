"""Core validation functions and utilities."""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from importobot import exceptions

T = TypeVar("T")

# Re-export ValidationError for convenience
ValidationError = exceptions.ValidationError


def validate_type(value: Any, expected_type: type, param_name: str) -> None:
    """Validate that a value is of the expected type.

    Args:
        value: The value to validate
        expected_type: The expected type
        param_name: Name of the parameter for error messages

    Raises:
        ValidationError: If the value is not of the expected type
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{param_name} must be a {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )


def validate_not_empty(value: Any, param_name: str) -> None:
    """Validate that a value is not empty.

    Args:
        value: The value to validate
        param_name: Name of the parameter for error messages

    Raises:
        ValidationError: If the value is empty
    """
    if not value:
        raise ValidationError(f"{param_name} cannot be empty")

    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{param_name} cannot be empty or whitespace")


def validate_json_dict(data: Any) -> dict:
    """Validate that data is a dictionary suitable for JSON.

    Args:
        data: The data to validate

    Returns:
        The validated dictionary

    Raises:
        ValidationError: If data is not a dictionary
    """
    if not isinstance(data, dict):
        raise ValidationError(
            f"JSON data must be a dictionary, got {type(data).__name__}"
        )
    return data


def validate_string_content(content: Any) -> str:
    """Validate that content is a string.

    Args:
        content: The content to validate

    Returns:
        The validated string

    Raises:
        ValidationError: If content is not a string
    """
    if not isinstance(content, str):
        raise ValidationError(f"Content must be a string, got {type(content).__name__}")
    return content


def validate_json_size(json_string: Any, max_size_mb: int = 10) -> None:
    """Validate JSON string size to prevent memory exhaustion.

    Args:
        json_string: The JSON string to validate (any type accepted)
        max_size_mb: Maximum size in megabytes

    Raises:
        ValidationError: If JSON string is too large
    """
    if not isinstance(json_string, str):
        return

    size_mb = len(json_string.encode("utf-8")) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValidationError(
            f"JSON input too large: {size_mb:.1f}MB exceeds {max_size_mb}MB limit. "
            f"Consider reducing the input size or increasing the limit. "
            f"Large JSON files can cause memory exhaustion and system instability."
        )


def require_valid_input(*param_validations: Any) -> Callable:
    """Validate function parameters using the given validations.

    Args:
        param_validations: List of (param_index, validator_func) tuples

    Example:
        @require_valid_input(
            (0, lambda x: validate_type(x, str, "input_file")),
            (1, lambda x: validate_type(x, str, "output_file"))
        )
        def convert_file(input_file: str, output_file: str):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Validate positional arguments
            for param_index, validator in param_validations:
                if param_index < len(args):
                    validator(args[param_index])

            return func(*args, **kwargs)

        return wrapper

    return decorator


class ValidationContext:
    """Context manager for batch validation operations."""

    def __init__(self) -> None:
        """Initialize validation context."""
        self.errors: list[str] = []

    def validate(self, condition: bool, error_message: str) -> None:
        """Add a validation check.

        Args:
            condition: The condition to check
            error_message: Error message if condition is False
        """
        if not condition:
            self.errors.append(error_message)

    def validate_type(self, value: Any, expected_type: type, param_name: str) -> None:
        """Add a type validation check."""
        if not isinstance(value, expected_type):
            self.errors.append(
                f"{param_name} must be a {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    def validate_not_empty(self, value: Any, param_name: str) -> None:
        """Add a non-empty validation check."""
        if not value:
            self.errors.append(f"{param_name} cannot be empty")
        elif isinstance(value, str) and not value.strip():
            self.errors.append(f"{param_name} cannot be empty or whitespace")

    def __enter__(self) -> "ValidationContext":
        """Enter validation context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit validation context and raise if there were errors."""
        if self.errors:
            error_message = "Validation failed:\n" + "\n".join(
                f"  - {error}" for error in self.errors
            )
            raise ValidationError(error_message)
