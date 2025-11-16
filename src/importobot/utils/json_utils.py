"""JSON loading utilities shared across modules."""

import json
import os
from typing import Any

from importobot import exceptions
from importobot.services.performance_cache import get_performance_cache
from importobot.utils.validation import validate_safe_path

_MULTI_TEST_CONTAINER_KEY = "testCases"


def load_json_file(json_file_path: str | None) -> dict[str, Any]:
    """Load JSON data from file.

    Args:
        json_file_path: Path to the JSON file to load

    Returns:
        Dict containing the loaded JSON data

    Raises:
        ValidationError: For invalid file paths or non-dictionary data
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        FileAccessError: For file permission or access issues
    """
    # Validate input parameters
    validated_path = _validate_file_path_input(json_file_path)

    # Ensure file exists
    _check_file_exists(validated_path)

    # Load and process JSON data
    return _load_and_process_json_data(validated_path)


def _validate_file_path_input(json_file_path: str | None) -> str:
    """Validate and sanitize the input file path.

    Args:
        json_file_path: Path to validate

    Returns:
        Validated file path

    Raises:
        ValueError: If path is invalid
    """
    if json_file_path is None:
        raise ValueError("File path cannot be empty or None")

    if not isinstance(json_file_path, str):
        raise ValueError(
            f"File path must be a string, got {type(json_file_path).__name__}"
        )

    if not json_file_path.strip():
        raise ValueError("File path cannot be empty or None")

    # Validate path safety
    return validate_safe_path(json_file_path)


def _check_file_exists(file_path: str) -> None:
    """Check if the file exists.

    Args:
        file_path: Path to check

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find JSON file: {file_path}")


def _load_and_process_json_data(file_path: str) -> dict[str, Any]:
    """Load JSON data from file and process it.

    Args:
        file_path: Path to JSON file

    Returns:
        Processed JSON data as dictionary

    Raises:
        json.JSONDecodeError: If file contains invalid JSON
        FileAccessError: For file permission or access issues
        ValidationError: For invalid data structure
    """
    try:
        raw_data = _read_json_file(file_path)
        return _process_json_structure(raw_data)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"JSON file appears to be corrupted at line {e.lineno}, "
            f"column {e.colno}: {e.msg}. Please check the file format and "
            "fix any syntax errors.",
            e.doc,
            e.pos,
        ) from e
    except PermissionError as e:
        raise exceptions.FileAccessError(
            f"Permission denied accessing file: {file_path}"
        ) from e
    except OSError as e:
        raise exceptions.FileAccessError(f"Error reading file {file_path}: {e}") from e


def _read_json_file(file_path: str) -> Any:
    """Read raw JSON data from file.

    Args:
        file_path: Path to JSON file

    Returns:
        Raw JSON data
    """
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def _process_json_structure(data: dict[str, Any] | list[Any]) -> dict[str, Any]:
    """Process JSON data structure and validate format.

    Args:
        data: Raw JSON data

    Returns:
        Processed data as dictionary

    Raises:
        ValidationError: For invalid data structure
    """
    # Handle case where JSON is an array with one or more test cases
    if isinstance(data, list):
        if not data:
            raise exceptions.ValidationError("JSON array cannot be empty.")

        if not all(isinstance(item, dict) for item in data):
            raise exceptions.ValidationError(
                "JSON array must contain only test case dictionaries."
            )

        if len(data) == 1:
            single_item = data[0]
            if isinstance(single_item, dict):
                return single_item
            raise exceptions.ValidationError(
                "Single item in JSON array must be a dictionary."
            )

        return {_MULTI_TEST_CONTAINER_KEY: data}

    if not isinstance(data, dict):
        raise exceptions.ValidationError("JSON content must be a dictionary or array.")

    return data


def dumps_cached(data: Any) -> str:
    """Serialize data to JSON using the shared performance cache."""
    cache = get_performance_cache()
    return cache.get_cached_json_string(data)
