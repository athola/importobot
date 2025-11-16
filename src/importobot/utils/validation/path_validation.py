"""Path validation utilities for security and reliability."""

import re
from pathlib import Path

from importobot import exceptions

from .core import validate_not_empty, validate_type


def validate_safe_path(file_path: str, base_dir: str | None = None) -> str:
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

    # Check for directory traversal in original path before resolving
    if ".." in file_path:
        raise exceptions.ValidationError("Directory traversal detected in path")

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
        r"^[\\/]etc[\\/]",  # System directories
        r"^[\\/]proc[\\/]",
        r"^[\\/]sys[\\/]",
        r"^[\\/]dev[\\/]",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, path_str, re.IGNORECASE):
            raise exceptions.ValidationError("Path contains unsafe components")

    return path_str


def validate_file_path(path: str, must_exist: bool = False) -> Path:
    """Validate a file path.

    Args:
        path: The file path to validate
        must_exist: Whether the file must exist

    Returns:
        Validated Path object

    Raises:
        ValidationError: If the path is invalid
        FileNotFound: If must_exist is True and file doesn't exist
    """
    validate_type(path, str, "File path")
    validate_not_empty(path, "File path")

    path_obj = Path(path).resolve()

    if must_exist and not path_obj.exists():
        raise exceptions.FileNotFound(f"File not found: {path}")

    return path_obj


def validate_directory_path(path: str, must_exist: bool = False) -> Path:
    """Validate a directory path.

    Args:
        path: The directory path to validate
        must_exist: Whether the directory must exist

    Returns:
        Validated Path object

    Raises:
        ValidationError: If the path is invalid
        FileNotFound: If must_exist is True and directory doesn't exist
    """
    validate_type(path, str, "Directory path")
    validate_not_empty(path, "Directory path")

    path_obj = Path(path).resolve()

    if must_exist:
        if not path_obj.exists():
            raise exceptions.FileNotFound(f"Directory not found: {path}")
        if not path_obj.is_dir():
            raise exceptions.ValidationError(f"Path is not a directory: {path}")

    return path_obj
