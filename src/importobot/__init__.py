"""Importobot - A tool for converting test cases from JSON to Robot Framework format.

Importobot automates the conversion of test management frameworks (Atlassian Zephyr,
JIRA/Xray, TestLink, etc.) into Robot Framework format with bulk processing capabilities
and provides suggestions for ambiguous test cases.

Public API:
    - JsonToRobotConverter
    - config
    - exceptions
    - api

Internal:
    - _check_dependencies
"""

from __future__ import annotations

from typing import Any

# Core public functionality - import without exposing modules
# API toolkit (following pandas.api pattern)
from importobot.core.converter import JsonToRobotConverter

from . import api, config, exceptions


# Dependency validation following pandas pattern
def _check_dependencies() -> None:
    """Validate essential runtime dependencies during package import."""
    missing_deps = []

    # Check json (standard library)
    try:
        __import__("json")
    except ImportError:
        missing_deps.append("json (standard library)")

    # Check robotframework
    try:
        __import__("robot")
    except ImportError:
        missing_deps.append("robotframework")

    if missing_deps:
        raise ImportError(
            f"Missing required dependencies: {', '.join(missing_deps)}. "
            "Please install with: pip install importobot"
        )


_check_dependencies()
config.validate_global_limits()

# Explicitly expose exception classes for convenient access
ImportobotError = exceptions.ImportobotError
ConfigurationError = exceptions.ConfigurationError
ValidationError = exceptions.ValidationError
ConversionError = exceptions.ConversionError
FileNotFound = exceptions.FileNotFound
FileAccessError = exceptions.FileAccessError
ParseError = exceptions.ParseError
SuggestionError = exceptions.SuggestionError
SecurityError = exceptions.SecurityError


def convert(payload: dict[str, Any] | str) -> str:
    """Convert a JSON payload (dictionary or string) to Robot Framework text."""
    converter = JsonToRobotConverter()
    return converter.convert(payload)


def convert_file(input_file: str, output_file: str) -> dict[str, Any]:
    """Convert a JSON file to Robot Framework output."""
    converter = JsonToRobotConverter()
    return converter.convert_file(input_file, output_file)


def convert_directory(input_dir: str, output_dir: str) -> dict[str, Any]:
    """Convert all JSON files within a directory to Robot Framework output."""
    converter = JsonToRobotConverter()
    return converter.convert_directory(input_dir, output_dir)


__all__ = [
    "JsonToRobotConverter",
    "api",
    "config",
    "convert",
    "convert_directory",
    "convert_file",
    "exceptions",
]

__version__ = "0.1.5"
