"""Contains internal core module implementations.

This module's contents are implementation details and should not be accessed
directly. Public API functionality is exposed through `importobot.api`.
"""

from typing import NoReturn

# No public exports - these are implementation details
# Access public functionality through importobot.api
__all__: list[str] = []


def __getattr__(name: str) -> NoReturn:
    """Prevents accidental access to internal core modules."""
    raise ModuleNotFoundError(
        "importobot.core is internal. Use importobot.api.* or documented helpers."
    )
