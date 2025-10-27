"""File validation strategy for the ValidationService."""

from __future__ import annotations

from typing import Any

from importobot.utils.security import SecurityValidator
from importobot.utils.validation import (
    ValidationError,
    validate_file_path,
    validate_safe_path,
)
from importobot.utils.validation_models import (
    ValidationResult,
    ValidationSeverity,
    create_validation_result,
)


class FileValidationStrategy:
    """Validation strategy for file operations."""

    def __init__(self, security_level: str = "standard"):
        """Initialize file validation strategy.

        Args:
            security_level: Security level for validation
        """
        self.security_validator = SecurityValidator(security_level=security_level)

    def validate(self, data: Any, context: dict[str, Any]) -> ValidationResult:
        """Validate file paths and operations."""
        messages = []
        severity = ValidationSeverity.INFO

        try:
            if isinstance(data, str | bytes):
                path_str = str(data)

                # Basic path validation
                validate_file_path(path_str)
                validate_safe_path(path_str)

                # Security validation - check for file operation warnings
                file_warnings = self.security_validator.validate_file_operations(
                    path_str, "access"
                )

                if file_warnings:
                    messages.extend(file_warnings)
                    severity = ValidationSeverity.ERROR

        except ValidationError as e:
            messages.append(str(e))
            severity = ValidationSeverity.ERROR
        except Exception as e:
            messages.append(f"File validation error: {e}")
            severity = ValidationSeverity.CRITICAL

        return create_validation_result(
            messages=messages, severity=severity, context=context
        )
