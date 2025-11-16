"""Importobot: A tool for converting test cases from JSON to Robot Framework format.

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

import importlib
import importlib.util
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

import importobot.api as _api_module  # type: ignore[import-self]
import importobot.exceptions as _exceptions_module  # type: ignore[import-self]

# Core public functionality - import without exposing modules
# API toolkit (following pandas.api pattern)

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from importobot.core.converter import JsonToRobotConverter as _ConverterClass
else:  # pragma: no cover - runtime only
    _ConverterClass = Any  # type: ignore[assignment]


# Dependency validation following pandas pattern
def _check_dependencies() -> None:
    """Validate essential runtime dependencies during package import."""
    missing_deps = []

    # Check json (standard library)
    if importlib.util.find_spec("json") is None:
        missing_deps.append("json (standard library)")

    # Check robotframework without importing the heavy module
    if importlib.util.find_spec("robot") is None:
        missing_deps.append("robotframework")

    if missing_deps:
        raise ImportError(
            f"Missing required dependencies: {', '.join(missing_deps)}. "
            "Please install with: pip install importobot"
        )


_check_dependencies()
_config = importlib.import_module("importobot.config")
_config.validate_global_limits()

# TYPE_CHECKING block removed - no future type exports currently needed

# Expose through clean interface
config = _config
api = cast(Any, _api_module)
exceptions = cast(Any, _exceptions_module)


_MODULE = sys.modules[__name__]


def _cache_attr(name: str, value: Any) -> Any:
    setattr(_MODULE, name, value)
    return value


@lru_cache(maxsize=1)
def _load_converter_module() -> Any:
    return importlib.import_module("importobot.core.converter")


def _get_converter_class() -> type[_ConverterClass]:
    module = _load_converter_module()
    return cast(type[_ConverterClass], module.JsonToRobotConverter)


def convert(payload: dict[str, Any] | str) -> str:
    """Convert a JSON payload (dictionary or string) to Robot Framework text."""
    converter = _get_converter_class()()
    return converter.convert(payload)


def convert_file(input_file: str, output_file: str) -> dict[str, Any]:
    """Convert a JSON file to Robot Framework output."""
    converter = _get_converter_class()()
    return converter.convert_file(input_file, output_file)


def convert_directory(input_dir: str, output_dir: str) -> dict[str, Any]:
    """Convert all JSON files within a directory to Robot Framework output."""
    converter = _get_converter_class()()
    return converter.convert_directory(input_dir, output_dir)


@lru_cache(maxsize=1)
def _load_api_module() -> Any:
    return importlib.import_module("importobot.api")


@lru_cache(maxsize=1)
def _load_exceptions_module() -> Any:
    return importlib.import_module("importobot.exceptions")


def __getattr__(name: str) -> Any:
    if name == "JsonToRobotConverter":
        return _cache_attr(name, _get_converter_class())
    if name == "api":
        return _cache_attr(name, _load_api_module())
    if name == "exceptions":
        return _cache_attr(name, _load_exceptions_module())
    raise AttributeError(f"module 'importobot' has no attribute {name!r}")


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
del _config
del TYPE_CHECKING
