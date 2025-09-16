"""Importobot - A tool for converting test cases from JSON to Robot Framework format."""

from . import config, exceptions
from .core.converter import JsonToRobotConverter

__all__ = ["JsonToRobotConverter", "config", "exceptions"]
__version__ = "1.0.0"
