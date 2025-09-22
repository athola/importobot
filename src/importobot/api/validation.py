"""Public validation utilities for enterprise pipelines.

This module provides validation functions needed for robust
enterprise integration and CI/CD pipeline integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importobot.utils.validation import (
        ValidationError,
        validate_json_dict,
        validate_safe_path,
    )
else:
    # Import at runtime to avoid circular imports
    from importobot.utils.validation import (
        ValidationError,
        validate_json_dict,
        validate_safe_path,
    )

__all__ = ["validate_json_dict", "validate_safe_path", "ValidationError"]
