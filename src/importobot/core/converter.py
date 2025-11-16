"""Convert JSON test data into Robot Framework format.

Handles Zephyr, TestRail, and similar JSON exports containing test cases
with steps, expected results, and metadata.
"""

import json
import os
from pathlib import Path
from typing import Any

from importobot import exceptions
from importobot.core.engine import GenericConversionEngine
from importobot.core.suggestions import GenericSuggestionEngine
from importobot.services.performance_cache import cached_string_lower
from importobot.utils.json_utils import load_json_file
from importobot.utils.logging import get_logger
from importobot.utils.validation import (
    validate_json_dict,
    validate_not_empty,
    validate_safe_path,
    validate_string_content,
    validate_type,
)

logger = get_logger()


class JsonToRobotConverter:
    """Convert JSON test formats into Robot Framework code."""

    def __init__(self) -> None:
        """Initialize converter with default engines."""
        self.conversion_engine = GenericConversionEngine()
        self.suggestion_engine = GenericSuggestionEngine()

    def convert(self, json_input: dict[str, Any] | str) -> str:
        """Convert JSON strings or dictionaries to Robot Framework format."""
        if isinstance(json_input, str):
            return self.convert_json_string(json_input)
        if isinstance(json_input, dict):
            return self.convert_json_data(json_input)
        raise TypeError(
            "JsonToRobotConverter.convert accepts either a JSON string or a dict"
        )

    def convert_json_string(self, json_string: str) -> str:
        """Convert a JSON string directly to Robot Framework format."""
        validate_string_content(json_string)
        validate_not_empty(json_string, "JSON string")

        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise exceptions.ParseError(
                f"Invalid JSON at line {e.lineno}: {e.msg}"
            ) from e

        validate_json_dict(json_data)

        try:
            return self.conversion_engine.convert(json_data)
        except Exception as e:
            logger.exception("Error during conversion")
            raise exceptions.ConversionError(
                f"Failed to convert JSON to Robot Framework: {e!s}"
            ) from e

    def convert_json_data(self, json_data: dict[str, Any]) -> str:
        """Convert a JSON dictionary to Robot Framework format."""
        validate_json_dict(json_data)
        _prime_string_cache(json_data)

        try:
            return self.conversion_engine.convert(json_data)
        except Exception as e:
            logger.exception("Error during conversion")
            raise exceptions.ConversionError(
                f"Failed to convert JSON to Robot Framework: {e!s}"
            ) from e

    def convert_file(self, input_file: str, output_file: str) -> dict[str, Any]:
        """Convert a JSON file to Robot Framework format.

        Args:
            input_file: Path to the input JSON file
            output_file: Path to the output Robot Framework file

        Returns:
            Dict with conversion result and metadata.
        """
        convert_file(input_file, output_file)
        return {"success": True, "input_file": input_file, "output_file": output_file}

    def convert_directory(self, input_dir: str, output_dir: str) -> dict[str, Any]:
        """Convert all JSON files in a directory to Robot Framework format.

        Args:
            input_dir: Path to directory containing JSON files
            output_dir: Path to directory for Robot Framework files

        Returns:
            Dict with conversion result and file counts.
        """
        convert_directory(input_dir, output_dir)
        return {"success": True, "input_dir": input_dir, "output_dir": output_dir}


def get_conversion_suggestions(json_data: dict[str, Any]) -> list[str]:
    """Generate suggestions to improve JSON test data for Robot conversion."""
    suggestion_engine = GenericSuggestionEngine()
    return suggestion_engine.get_suggestions(json_data)


def apply_conversion_suggestions(
    json_data: dict[str, Any] | list[Any],
) -> tuple[dict[str, Any] | list[Any], list[dict[str, Any]]]:
    """Apply automatic improvements to JSON test data for Robot Framework."""
    suggestion_engine = GenericSuggestionEngine()
    try:
        return suggestion_engine.apply_suggestions(json_data)
    except exceptions.ImportobotError:
        # For invalid JSON structures, return the original data with no changes
        return json_data, []


def apply_conversion_suggestions_simple(
    json_data: dict[str, Any] | list[Any],
) -> dict[str, Any] | list[Any]:
    """Apply improvements to JSON test data, returning only the modified data."""
    improved_data, _ = apply_conversion_suggestions(json_data)
    return improved_data


def save_robot_file(content: str, file_path: str) -> None:
    """Save Robot Framework content to a specified file."""
    validate_string_content(content)

    validated_path = validate_safe_path(file_path)

    with open(validated_path, "w", encoding="utf-8") as f:
        f.write(content)


def convert_file(input_file: str, output_file: str) -> None:
    """Convert a single JSON file to Robot Framework format.

    Raises:
        `ValidationError`: If input parameters are invalid.
        `ConversionError`: If the conversion process fails.
        `FileNotFoundError`: If the input file does not exist.
    """
    validate_type(input_file, str, "Input file path")
    validate_type(output_file, str, "Output file path")
    validate_not_empty(input_file, "Input file path")
    validate_not_empty(output_file, "Output file path")

    json_data = load_json_file(input_file)
    converter = JsonToRobotConverter()
    robot_content = converter.convert_json_data(json_data)
    save_robot_file(robot_content, output_file)


def convert_multiple_files(input_files: list[str], output_dir: str) -> None:
    """Convert multiple JSON files to Robot Framework files."""
    validate_type(input_files, list, "Input files")
    validate_type(output_dir, str, "Output directory")
    validate_not_empty(input_files, "Input files list")

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logger.exception("Error creating output directory")
        raise exceptions.FileAccessError(
            f"Could not create output directory: {e!s}"
        ) from e

    for input_file in input_files:
        _convert_file_with_error_handling(input_file, output_dir)


def _prime_string_cache(payload: Any) -> None:
    """Recursively primes the string cache with all string values in the payload."""
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, str):
                cached_string_lower(value)
            else:
                _prime_string_cache(value)
    elif isinstance(payload, list):
        for item in payload:
            _prime_string_cache(item)


def convert_directory(input_dir: str, output_dir: str) -> None:
    """Convert all JSON files within a directory to Robot Framework files."""
    try:
        _validate_directory_args(input_dir, output_dir)
        json_files = _find_json_files_in_directory(input_dir)
    except exceptions.ImportobotError:
        # Re-raise Importobot-specific exceptions
        raise
    except Exception as e:
        logger.exception("Error validating directory arguments")
        raise exceptions.ValidationError(f"Invalid directory arguments: {e!s}") from e

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
        raise exceptions.ConversionError(f"Failed to convert directory: {e!s}") from e


def _convert_file_with_error_handling(input_file: str, output_dir: str) -> None:
    """Convert a single file, incorporating consistent error handling."""
    try:
        output_filename = Path(input_file).stem + ".robot"
        output_path = Path(output_dir) / output_filename
        convert_file(input_file, str(output_path))
    except exceptions.ImportobotError:
        raise
    except Exception as e:
        logger.exception("Error converting file %s", input_file)
        raise exceptions.ConversionError(
            f"Failed to convert file {input_file}: {e!s}"
        ) from e


def _validate_directory_args(input_dir: str, output_dir: str) -> None:
    """Validate directory conversion arguments."""
    validate_type(input_dir, str, "Input directory")
    validate_type(output_dir, str, "Output directory")


def _find_json_files_in_directory(input_dir: str) -> list[str]:
    """Recursively finds all JSON files within a specified directory."""
    all_files = Path(input_dir).rglob("*")
    json_files = [
        str(f) for f in all_files if f.is_file() and f.suffix.lower() == ".json"
    ]
    return json_files


__all__ = [
    "JsonToRobotConverter",
]
