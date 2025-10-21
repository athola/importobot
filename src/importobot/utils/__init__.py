"""Internal utility modules - not part of public API.

This module contains implementation utilities and should not be accessed
directly. Use public validation functions through importobot.api.validation instead.
"""

from typing import NoReturn

# No public exports - these are implementation details
# Access public validation utilities through importobot.api.validation
__all__: list[str] = []


def __getattr__(name: str) -> NoReturn:
    """Guard against accidental use of internal utility modules."""
    raise ModuleNotFoundError(
        "importobot.utils is internal. "
        "Use importobot.api.validation for supported utilities."
    )
