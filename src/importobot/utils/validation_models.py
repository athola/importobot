"""Unified validation models for the entire codebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ValidationSeverity(Enum):
    """Severity levels for validation results."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class QualitySeverity(Enum):
    """Quality severity levels (alias for ValidationSeverity)."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_counts(cls, error_count: int, warning_count: int) -> QualitySeverity:
        """Determine severity based on error and warning counts.

        Args:
            error_count: Number of errors
            warning_count: Number of warnings

        Returns:
            Appropriate QualitySeverity level
        """
        if error_count > 0:
            return cls.CRITICAL
        if warning_count > 5:
            return cls.HIGH
        if warning_count > 2:
            return cls.MEDIUM
        if warning_count > 0:
            return cls.LOW
        return cls.INFO


@dataclass
class ValidationResult:
    """Unified validation result for operational and data quality validation.

    Supports both use cases:
    - Operational validation (services): uses messages and context
    - Data quality validation (medallion): uses error_count, warning_count, issues
    """

    is_valid: bool
    severity: ValidationSeverity | QualitySeverity

    # Operational validation fields (services)
    messages: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    # Data quality validation fields (medallion)
    error_count: int = 0
    warning_count: int = 0
    issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    validation_timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Initialize fields and ensure consistency."""
        if self.context is None:
            self.context = {}
        if self.details is None:
            self.details = {}

        # Auto-populate counts from messages/issues if not set
        if self.error_count == 0 and self.warning_count == 0:
            all_msgs = self.messages + self.issues
            error_words = ["error", "invalid", "failed"]
            self.error_count = len(
                [
                    msg
                    for msg in all_msgs
                    if any(word in msg.lower() for word in error_words)
                ]
            )
            self.warning_count = len(
                [msg for msg in all_msgs if "warning" in msg.lower()]
            )


def create_validation_result(
    *,
    messages: list[str] | None = None,
    severity: ValidationSeverity | QualitySeverity | None = None,
    context: dict[str, Any] | None = None,
    error_count: int = 0,
    warning_count: int = 0,
    issues: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> ValidationResult:
    """Create a ValidationResult with consistent pattern.

    Supports both message-based and count-based validation patterns.

    Args:
        messages: List of validation messages (for services pattern)
        severity: Severity level for the validation
        context: Optional context dictionary (for services pattern)
        error_count: Number of errors found (for medallion pattern)
        warning_count: Number of warnings found (for medallion pattern)
        issues: List of issue descriptions (for medallion pattern)
        details: Optional details dictionary (for medallion pattern)

    Returns:
        ValidationResult with appropriate validity based on input pattern
    """
    messages = messages or []
    issues = issues or []

    # Determine validity based on pattern
    is_valid = len(messages) == 0 if messages else error_count == 0

    # Use provided severity or infer from errors
    if severity is None:
        if error_count > 0:
            severity = ValidationSeverity.CRITICAL
        elif messages:
            severity = ValidationSeverity.ERROR
        else:
            severity = ValidationSeverity.INFO

    return ValidationResult(
        is_valid=is_valid,
        severity=severity,
        messages=messages,
        context=context or {},
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
        details=details or {},
    )


def calculate_nesting_depth(
    obj: Any, current_depth: int = 0, max_depth: int = 20
) -> int:
    """Calculate the maximum nesting depth of a data structure.

    Args:
        obj: The object to analyze
        current_depth: Current depth in recursion
        max_depth: Safety limit to prevent infinite recursion

    Returns:
        Maximum nesting depth found
    """
    if current_depth > max_depth:
        return current_depth

    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(
            calculate_nesting_depth(value, current_depth + 1, max_depth)
            for value in obj.values()
        )
    if isinstance(obj, list):
        if not obj:
            return current_depth
        return max(
            calculate_nesting_depth(item, current_depth + 1, max_depth) for item in obj
        )

    return current_depth


def create_basic_validation_result(
    *,
    severity: Any,
    error_count: int = 0,
    warning_count: int = 0,
    issues: list[str] | None = None,
) -> ValidationResult:
    """Create a basic validation result with empty details.

    Args:
        severity: Validation severity level
        error_count: Number of errors
        warning_count: Number of warnings
        issues: List of issue descriptions

    Returns:
        ValidationResult with empty details
    """
    return create_validation_result(
        severity=severity,
        error_count=error_count,
        warning_count=warning_count,
        issues=issues or [],
        details={},
    )


# Internal utility - not part of public API
__all__: list[str] = []
