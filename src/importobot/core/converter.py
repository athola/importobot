"""
JSON to Robot Framework converter.

Handles Zephyr and similar test formats. Main conversion logic.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .. import exceptions
from ..utils.logging import setup_logger
from ..utils.validation import (
    validate_safe_path,
)
from .engine import GenericConversionEngine
from .suggestions import GenericSuggestionEngine

logger = setup_logger(__name__)


class JsonToRobotConverter:
    """Generic converter that handles any JSON test format programmatically."""

    def __init__(self) -> None:
        """Initialize the converter with modular components."""
        self.conversion_engine = GenericConversionEngine()
        self.suggestion_engine = GenericSuggestionEngine()

    def convert_json_string(self, json_string: str) -> str:
        """Convert JSON string directly to Robot Framework format."""
        if not json_string or not json_string.strip():
            raise exceptions.ValidationError("Empty JSON string provided")

        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise exceptions.ParseError(
                f"Invalid JSON at line {e.lineno}: {e.msg}"
            ) from e

        if not isinstance(json_data, dict):
            raise exceptions.ValidationError("JSON data must be a dictionary")

        try:
            return self.conversion_engine.convert(json_data)
        except Exception as e:
            logger.exception("Error during conversion")
            raise exceptions.ConversionError(
                f"Failed to convert JSON to Robot Framework: {str(e)}"
            ) from e

    def convert_json_data(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON data dict to Robot Framework format."""
        if not isinstance(json_data, dict):
            raise exceptions.ValidationError("JSON data must be a dictionary")

        try:
            return self.conversion_engine.convert(json_data)
        except Exception as e:
            logger.exception("Error during conversion")
            raise exceptions.ConversionError(
                f"Failed to convert JSON to Robot Framework: {str(e)}"
            ) from e


# Standalone suggestion functions
def get_conversion_suggestions(json_data: Dict[str, Any]) -> List[str]:
    """Generate suggestions for improving JSON test data for Robot conversion."""
    suggestion_engine = GenericSuggestionEngine()
    return suggestion_engine.get_suggestions(json_data)


def apply_conversion_suggestions(
    json_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Apply automatic improvements to JSON test data for Robot Framework conversion."""
    suggestion_engine = GenericSuggestionEngine()
    return suggestion_engine.apply_suggestions(json_data)


def apply_conversion_suggestions_simple(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply improvements to JSON test data, returning only the improved data."""
    improved_data, _ = apply_conversion_suggestions(json_data)
    return improved_data


# File I/O functions
def load_json(file_path: str) -> Dict[str, Any]:
    """Load and validate JSON file."""
    validated_path = validate_safe_path(file_path)

    with open(validated_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Handle case where JSON is an array with a single test case
        if isinstance(data, list):
            if len(data) == 1 and isinstance(data[0], dict):
                # Extract the first test case from the array
                return data[0]
            raise exceptions.ValidationError(
                "JSON array must contain exactly one test case dictionary."
            )
        if not isinstance(data, dict):
            raise exceptions.ValidationError(
                "JSON content must be a dictionary or array."
            )
        return data


def save_robot_file(content: str, file_path: str) -> None:
    """Save Robot Framework content to file."""
    if not isinstance(content, str):
        raise exceptions.ValidationError(
            f"Content must be a string, got {type(content).__name__}"
        )

    validated_path = validate_safe_path(file_path)

    with open(validated_path, "w", encoding="utf-8") as f:
        f.write(content)


def convert_file(input_file: str, output_file: str) -> None:
    """Convert single JSON file to Robot Framework."""
    if not isinstance(input_file, str):
        raise exceptions.ValidationError(
            f"Input file path must be a string, got {type(input_file).__name__}"
        )

    if not isinstance(output_file, str):
        raise exceptions.ValidationError(
            f"Output file path must be a string, got {type(output_file).__name__}"
        )

    if not input_file.strip():
        raise exceptions.ValidationError(
            "Input file path cannot be empty or whitespace"
        )

    if not output_file.strip():
        raise exceptions.ValidationError(
            "Output file path cannot be empty or whitespace"
        )

    json_data = load_json(input_file)
    converter = JsonToRobotConverter()
    robot_content = converter.convert_json_data(json_data)
    save_robot_file(robot_content, output_file)


def convert_multiple_files(input_files: List[str], output_dir: str) -> None:
    """Convert multiple JSON files to Robot Framework files."""
    if not isinstance(input_files, list):
        raise exceptions.ValidationError(
            f"Input files must be a list, got {type(input_files).__name__}"
        )

    if not isinstance(output_dir, str):
        raise exceptions.ValidationError(
            f"Output directory must be a string, got {type(output_dir).__name__}"
        )

    if not input_files:
        raise exceptions.ValidationError("Input files list cannot be empty")

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logger.exception("Error creating output directory")
        raise exceptions.FileAccessError(
            f"Could not create output directory: {str(e)}"
        ) from e

    for input_file in input_files:
        try:
            output_filename = Path(input_file).stem + ".robot"
            output_path = Path(output_dir) / output_filename
            convert_file(input_file, str(output_path))
        except exceptions.ImportobotError:
            # Re-raise Importobot-specific exceptions
            raise
        except Exception as e:
            logger.exception("Error converting file %s", input_file)
            raise exceptions.ConversionError(
                f"Failed to convert file {input_file}: {str(e)}"
            ) from e


def convert_directory(input_dir: str, output_dir: str) -> None:
    """Convert all JSON files in directory to Robot Framework files."""
    try:
        _validate_directory_args(input_dir, output_dir)
        json_files = _find_json_files_in_directory(input_dir)
    except exceptions.ImportobotError:
        # Re-raise Importobot-specific exceptions
        raise
    except Exception as e:
        logger.exception("Error validating directory arguments")
        raise exceptions.ValidationError(
            f"Invalid directory arguments: {str(e)}"
        ) from e

    if not json_files:
        raise exceptions.ValidationError(
            f"No JSON files found in directory: {input_dir}"
        )

    try:
        convert_multiple_files(json_files, output_dir)
    except exceptions.ImportobotError:
        # Re-raise Importobot-specific exceptions
        raise
    except Exception as e:
        logger.exception("Error converting directory")
        raise exceptions.ConversionError(
            f"Failed to convert directory: {str(e)}"
        ) from e


def _validate_directory_args(input_dir: str, output_dir: str) -> None:
    """Validate directory conversion arguments."""
    if not isinstance(input_dir, str):
        raise exceptions.ValidationError(
            f"Input directory must be a string, got {type(input_dir).__name__}"
        )

    if not isinstance(output_dir, str):
        raise exceptions.ValidationError(
            f"Output directory must be a string, got {type(output_dir).__name__}"
        )


def _find_json_files_in_directory(input_dir: str) -> List[str]:
    """Find all JSON files in a directory recursively."""
    all_files = Path(input_dir).rglob("*")
    json_files = [
        str(f) for f in all_files if f.is_file() and f.suffix.lower() == ".json"
    ]
    return json_files


__all__ = [
    "JsonToRobotConverter",
    "load_json",
    "save_robot_file",
    "convert_file",
    "convert_multiple_files",
    "convert_directory",
    "get_conversion_suggestions",
    "apply_conversion_suggestions",
]
