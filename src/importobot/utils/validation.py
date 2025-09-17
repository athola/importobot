"""Input validation utilities for security and reliability."""

import re
from pathlib import Path
from typing import Any, Optional

from importobot import exceptions


def validate_safe_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """Validate path is safe and within allowed directory.

    Args:
        file_path: The file path to validate
        base_dir: Optional base directory to restrict access to

    Returns:
        Validated absolute path

    Raises:
        exceptions.ValidationError: If path is invalid or unsafe
        exceptions.ConfigurationError: If file_path is not a string
    """
    if not isinstance(file_path, str):
        raise exceptions.ConfigurationError(
            f"File path must be a string, got {type(file_path).__name__}"
        )

    if not file_path.strip():
        raise exceptions.ValidationError("File path cannot be empty or whitespace")

    # Resolve the path to catch any directory traversal attempts
    path = Path(file_path).resolve()

    # Check if path is within allowed base directory
    if base_dir:
        base = Path(base_dir).resolve()
        if not str(path).startswith(str(base)):
            raise exceptions.ValidationError("Path outside allowed directory")

    # Additional security checks
    path_str = str(path)

    # Check for suspicious path components
    dangerous_patterns = [
        r"\.\.[\\/]",  # Directory traversal
        r"^[\\/]etc[\\/]",  # System directories
        r"^[\\/]proc[\\/]",
        r"^[\\/]sys[\\/]",
        r"^[\\/]dev[\\/]",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, path_str, re.IGNORECASE):
            raise exceptions.ValidationError("Path contains unsafe components")

    return path_str


def sanitize_robot_string(text: Any) -> str:
    """Sanitize string for Robot Framework output.

    Removes newlines, carriage returns, and trims whitespace
    to prevent Robot Framework syntax errors.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized string safe for Robot Framework
    """
    if text is None:
        return ""

    # Handle line endings preserving consecutive ones as multiple spaces
    text_str = str(text)
    # Replace Windows line endings first to avoid double spaces
    text_str = text_str.replace("\r\n", " ")
    # Then replace remaining newlines and carriage returns
    text_str = text_str.translate({ord("\n"): " ", ord("\r"): " "})
    # Trim leading/trailing whitespace but preserve internal spacing
    return text_str.strip()


def validate_json_size(json_string: Any, max_size_mb: int = 10) -> None:
    """Validate JSON string size to prevent memory exhaustion.

    Args:
        json_string: The JSON string to validate (any type accepted)
        max_size_mb: Maximum size in megabytes

    Raises:
        exceptions.ValidationError: If JSON string is too large
    """
    if not isinstance(json_string, str):
        return

    size_mb = len(json_string.encode("utf-8")) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise exceptions.ValidationError(
            f"JSON input too large: {size_mb:.1f}MB exceeds {max_size_mb}MB limit. "
            f"Consider reducing the input size or increasing the limit. "
            f"Large JSON files can cause memory exhaustion and system instability."
        )


def sanitize_error_message(message: str, file_path: Optional[str] = None) -> str:
    """Sanitize error messages to prevent information disclosure.

    Args:
        message: Original error message
        file_path: Optional file path to sanitize from message

    Returns:
        Sanitized error message
    """
    if not message:
        return "An error occurred"

    sanitized = message

    # Remove full paths, keep only filename
    if file_path:
        filename = Path(file_path).name
        sanitized = sanitized.replace(file_path, f"'{filename}'")

    # Remove system information patterns
    patterns_to_remove = [
        r"[\\/]home[\\/][^\\s\\n]*",  # Home directories
        r"[\\/]usr[\\/][^\\s\\n]*",  # System directories
        r"[\\/]tmp[\\/][^\\s\\n]*",  # Temp directories
        r"C:\\[^\\s\\n]*",  # Windows paths
    ]

    for pattern in patterns_to_remove:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    return sanitized
