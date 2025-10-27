"""Format validation strategy for the ValidationService."""

from __future__ import annotations

from typing import Any

from importobot.utils.validation import (
    ValidationError,
    validate_not_empty,
    validate_type,
)
from importobot.utils.validation_models import (
    ValidationResult,
    ValidationSeverity,
    create_validation_result,
)


class FormatValidationStrategy:
    """Validation strategy for format detection data."""

    def validate(self, data: Any, context: dict[str, Any]) -> ValidationResult:
        """Validate format detection input."""
        messages = []
        severity = ValidationSeverity.INFO

        try:
            # Must be a dictionary
            validate_type(data, dict, "Format data")
            validate_not_empty(data, "Format data")

            # Check for minimum required structure
            if not any(isinstance(v, dict | list) for v in data.values()):
                messages.append("Format data lacks complex structure indicators")
                severity = ValidationSeverity.WARNING

        except ValidationError as e:
            messages.append(str(e))
            severity = ValidationSeverity.ERROR
        except Exception as e:
            messages.append(f"Format validation error: {e}")
            severity = ValidationSeverity.CRITICAL

        return create_validation_result(
            messages=messages, severity=severity, context=context
        )
