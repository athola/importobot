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

from . import api as _api
from . import config as _config
from . import exceptions as _exceptions


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
_config.validate_global_limits()

# TYPE_CHECKING block removed - no future type exports currently needed

# Expose through clean interface
config = _config
exceptions = _exceptions
api = _api

# Explicitly expose exception classes to ensure type checkers can access them
ImportobotError = _exceptions.ImportobotError
ConfigurationError = _exceptions.ConfigurationError
ValidationError = _exceptions.ValidationError
ConversionError = _exceptions.ConversionError
FileNotFound = _exceptions.FileNotFound
FileAccessError = _exceptions.FileAccessError
ParseError = _exceptions.ParseError
SuggestionError = _exceptions.SuggestionError
SecurityError = _exceptions.SecurityError


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

# Clean up namespace - remove internal imports from dir()
del _config, _exceptions, _api
