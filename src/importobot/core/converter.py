"""File conversion functionality."""

import json
from typing import Any, Dict

from importobot.core.parser import parse_json
from importobot.utils.validation import sanitize_error_message, validate_safe_path


def load_json(file_path: str) -> Dict[str, Any]:
    """Load test data from a JSON file."""
    # Early fail: validate input parameters and path safety
    validated_path = validate_safe_path(file_path)

    try:
        with open(validated_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if not isinstance(json_data, dict):
                raise ValueError("JSON content must be a dictionary.")
            return json_data
    except FileNotFoundError as e:
        error_msg = sanitize_error_message(str(e), file_path)
        raise FileNotFoundError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = sanitize_error_message(f"Could not parse JSON: {e.msg}", file_path)
        raise ValueError(error_msg) from e


def save_robot_file(content: str, file_path: str) -> None:
    """Save content to a Robot Framework file."""
    # Early fail: validate input parameters and path safety
    if not isinstance(content, str):
        raise TypeError(f"Content must be a string, got {type(content).__name__}")

    validated_path = validate_safe_path(file_path)

    try:
        with open(validated_path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        error_msg = sanitize_error_message(str(e), file_path)
        raise IOError(error_msg) from e


def convert_to_robot(input_file: str, output_file: str) -> None:
    """Convert a JSON file to a Robot Framework file."""
    # Early fail: validate input parameters (paths validated in called functions)
    if not isinstance(input_file, str):
        raise TypeError(
            f"Input file path must be a string, got {type(input_file).__name__}"
        )

    if not isinstance(output_file, str):
        raise TypeError(
            f"Output file path must be a string, got {type(output_file).__name__}"
        )

    if not input_file.strip():
        raise ValueError("Input file path cannot be empty or whitespace")

    if not output_file.strip():
        raise ValueError("Output file path cannot be empty or whitespace")

    json_data = load_json(input_file)
    robot_content = parse_json(json_data)
    save_robot_file(robot_content, output_file)
