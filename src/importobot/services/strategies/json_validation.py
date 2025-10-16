"""JSON validation strategy for the ValidationService."""

from __future__ import annotations

import json
from typing import Any

from importobot.utils.validation import (
    ValidationError,
    validate_json_dict,
    validate_json_size,
    validate_not_empty,
)
from importobot.utils.validation_models import ValidationResult, ValidationSeverity


class JsonValidationStrategy:
    """Validation strategy for JSON data."""

    def __init__(self, max_size_mb: int = 10):
        """Initialize JSON validation strategy.

        Args:
            max_size_mb: Maximum allowed JSON size in MB
        """
        self.max_size_mb = max_size_mb

    def validate(self, data: Any, context: dict[str, Any]) -> ValidationResult:
        """Validate JSON data structure and size."""
        messages = []
        severity = ValidationSeverity.INFO

        try:
            # Validate basic JSON structure
            if isinstance(data, str):
                parsed = json.loads(data)
                data = parsed

            validate_json_dict(data)

            # Size validation
            data_str = json.dumps(data)
            validate_json_size(data_str, max_size_mb=self.max_size_mb)

            # Content validation
            validate_not_empty(data, "JSON data")

        except ValidationError as e:
            messages.append(str(e))
            severity = ValidationSeverity.ERROR
        except Exception as e:
            messages.append(f"Unexpected validation error: {e}")
            severity = ValidationSeverity.CRITICAL

        return ValidationResult(
            is_valid=len(messages) == 0,
            severity=severity,
            messages=messages,
            context=context,
        )
