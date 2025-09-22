"""Importobot - A tool for converting test cases from JSON to Robot Framework format.

Importobot automates the conversion of test management frameworks (Atlassian Zephyr,
JIRA/Xray, TestLink, etc.) into Robot Framework format with bulk processing capabilities
and intelligent suggestions for ambiguous test cases.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

# Core public functionality - import without exposing modules
# API toolkit (following pandas.api pattern)
from importobot import api as _api
from importobot import config as _config
from importobot import exceptions as _exceptions
from importobot.core.converter import JsonToRobotConverter


# Dependency validation following pandas pattern
def _check_dependencies() -> None:
    """Validate critical dependencies at import time."""
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

# Type checking imports
if TYPE_CHECKING:
    pass  # Reserved for future type-only imports

# Expose through clean interface
config = _config
exceptions = _exceptions
api = _api

__all__ = [
    # Core business functionality
    "JsonToRobotConverter",
    # Configuration management
    "config",
    # Error handling
    "exceptions",
    # Public API toolkit
    "api",
]

__version__ = "1.0.0"

# Clean up namespace - remove internal imports from dir()
del _config, _exceptions, _api
del sys, TYPE_CHECKING
del annotations  # from __future__ import
