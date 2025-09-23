"""Public toolkit API for Importobot extensions and integrations.

This module provides the stable public interface for enterprise integration,
following pandas-style API organization patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importobot.api import converters, suggestions, validation
else:
    # Import at runtime to avoid circular imports
    from importobot.api import converters, suggestions, validation

__all__ = ["converters", "suggestions", "validation"]
