"""Public suggestion engine for incorrect/ambiguous test cases.

This module provides access to the suggestion engine for handling
problematic test cases that require intelligent fixes or improvements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importobot.core.suggestions import GenericSuggestionEngine
else:
    # Import at runtime to avoid circular imports
    from importobot.core.suggestions import GenericSuggestionEngine

__all__ = ["GenericSuggestionEngine"]
