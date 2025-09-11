"""Input validation utilities for security and reliability."""

import re
from pathlib import Path
from typing import Any


def validate_safe_path(file_path: str, base_dir: str = None) -> str:
    """Validate path is safe and within allowed directory.

    Args:
        file_path: The file path to validate
        base_dir: Optional base directory to restrict access to

    Returns:
        Validated absolute path

    Raises:
        ValueError: If path is invalid or unsafe
        TypeError: If file_path is not a string
    """
    if not isinstance(file_path, str):
        raise TypeError(f"File path must be a string, got {type(file_path).__name__}")

    if not file_path.strip():
        raise ValueError("File path cannot be empty or whitespace")

    try:
        # Resolve the path to catch any directory traversal attempts
        path = Path(file_path).resolve()

        # Check if path is within allowed base directory
        if base_dir:
            base = Path(base_dir).resolve()
            if not str(path).startswith(str(base)):
                raise ValueError("Path outside allowed directory")

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
                raise ValueError("Path contains unsafe components")

        return path_str

    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid file path: {e}") from e


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

    return str(text).replace("\n", " ").replace("\r", "").strip()


def validate_json_size(json_string: str, max_size_mb: int = 10) -> None:
    """Validate JSON string size to prevent memory exhaustion.

    Args:
        json_string: The JSON string to validate
        max_size_mb: Maximum size in megabytes

    Raises:
        ValueError: If JSON string is too large
    """
    if not isinstance(json_string, str):
        return

    size_mb = len(json_string.encode("utf-8")) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(
            f"JSON input too large: {size_mb:.1f}MB > {max_size_mb}MB limit"
        )


def sanitize_error_message(message: str, file_path: str = None) -> str:
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
