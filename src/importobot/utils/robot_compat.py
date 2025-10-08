"""Compatibility shims for Robot Framework utilities.

SeleniumLibrary still imports helper functions like ``robot.utils.is_string`` that
were deprecated in Robot Framework 8.x. Accessing them triggers a deprecation
warning via ``robot.utils.__getattr__``. Importobot patches the module eagerly so
downstream dependencies can keep working without noisy warnings.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Callable


def patch_robot_legacy_utils() -> None:
    """Provide legacy ``robot.utils`` helpers to avoid deprecation warnings."""
    try:
        robot_utils: ModuleType = import_module("robot.utils")
    except ImportError:  # pragma: no cover - depends on optional dependency
        return

    # ``robot.utils`` exposes deprecated helpers via ``__getattr__``. That
    # mechanism emits warnings when accessed, so set them eagerly.
    legacy_aliases: dict[str, Callable[[object], bool]] = {
        "is_string": lambda item: isinstance(item, str),
        "is_unicode": lambda item: isinstance(item, str),
    }

    utils_dict = robot_utils.__dict__
    for name, func in legacy_aliases.items():
        if name not in utils_dict:
            setattr(robot_utils, name, func)
