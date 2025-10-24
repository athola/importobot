"""Core module internals - not part of public API.

This module contains implementation details and should not be accessed
directly. Use the public API through importobot.api instead.
"""

from typing import NoReturn

# No public exports - these are implementation details
# Access public functionality through importobot.api
__all__: list[str] = []


def __getattr__(name: str) -> NoReturn:
    """Guard against accidental use of internal core modules."""
    raise ModuleNotFoundError(
        "importobot.core is internal. Use importobot.api.* or documented helpers."
    )
