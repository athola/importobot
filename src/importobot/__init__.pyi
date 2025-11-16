from __future__ import annotations

from types import ModuleType
from typing import Any

from importobot.core.converter import JsonToRobotConverter as _JsonToRobotConverter

config: ModuleType
JsonToRobotConverter: type[_JsonToRobotConverter]
api: ModuleType
exceptions: ModuleType
__version__: str
__all__: list[str]


def convert(payload: dict[str, Any] | str) -> str: ...


def convert_file(input_file: str, output_file: str) -> dict[str, Any]: ...


def convert_directory(input_dir: str, output_dir: str) -> dict[str, Any]: ...
