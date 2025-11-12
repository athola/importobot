"""Bronze layer validation for raw data quality checks."""

from __future__ import annotations

import json
from typing import Any

from importobot.utils.logging import get_logger
from importobot.utils.string_cache import data_to_lower_cached
from importobot.utils.validation_models import (
    QualitySeverity,
    ValidationResult,
    calculate_nesting_depth,
    create_validation_result,
)

logger = get_logger()


class ValidationThresholds:
    """Validation threshold constants with clear documentation and appropriate ranges.

    This class contains constants that define validation thresholds for the bronze
    layer validation system.
    """

    # Data Size Limits (in MB)
    MAX_DATA_SIZE_MB = 100  # Maximum total data size - range: 50-500MB typical
    LARGE_FIELD_SIZE_MB = 10  # Individual field size warning threshold - range: 5-50MB

    # JSON Structure Limits
    MAX_NESTING_DEPTH = 20  # Maximum JSON nesting depth - range: 10-50 levels

    # Data Quality Thresholds (percentages: 0-100)
    NULL_VALUE_WARNING_PERCENT = (
        20  # Warn when null/empty values exceed this % - range: 15-35%
    )
    HIGH_NULL_VALUE_PERCENT = 50  # Critical null value threshold - range: 40-70%

    # String Content Limits (in characters)
    MAX_STRING_LENGTH_CHARS = (
        10000  # Maximum string length before warning - range: 5000-50000
    )

    # Test Data Quality Indicators
    MIN_TEST_INDICATORS = 1  # Minimum test-related indicators expected - range: 1-3


class BronzeValidator:
    """Validate raw data for Bronze layer ingestion."""

    def __init__(self) -> None:
        """Initialize the Bronze validator with validation thresholds."""
        self.max_data_size_mb = ValidationThresholds.MAX_DATA_SIZE_MB
        self.max_nesting_depth = ValidationThresholds.MAX_NESTING_DEPTH

    def validate_raw_data(self, data: Any) -> ValidationResult:
        """Validate raw data for Bronze layer ingestion.

        Args:
            data: The raw data to validate

        Returns:
            ValidationResult with validation status and issues
        """
        issues = []
        error_count = 0
        warning_count = 0

        # Structure validation
        structure_result = self._validate_structure(data)
        issues.extend(structure_result.issues)
        error_count += structure_result.error_count
        warning_count += structure_result.warning_count

        # Size validation
        size_result = self._validate_size(data)
        issues.extend(size_result.issues)
        error_count += size_result.error_count
        warning_count += size_result.warning_count

        # Content validation
        content_result = self._validate_content(data)
        issues.extend(content_result.issues)
        error_count += content_result.error_count
        warning_count += content_result.warning_count

        # Determine overall validation result
        severity = QualitySeverity.from_counts(error_count, warning_count)

        return create_validation_result(
            severity=severity,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            details={
                "structure_validation": structure_result.details,
                "size_validation": size_result.details,
                "content_validation": content_result.details,
            },
        )

    def _validate_structure(self, data: Any) -> ValidationResult:
        """Validate the basic structure of the data."""
        issues = []
        error_count = 0
        warning_count = 0
        details: dict[str, Any] = {}

        # Check if data is a dictionary
        if not isinstance(data, dict):
            issues.append(f"Data must be a dictionary, got {type(data).__name__}")
            error_count += 1
            details["data_type"] = type(data).__name__
        else:
            # Check if dictionary is empty
            if not data:
                issues.append("Data dictionary is empty")
                warning_count += 1
                details["empty_data"] = True

            # Check nesting depth
            depth = calculate_nesting_depth(data, 0, self.max_nesting_depth + 5)
            details["nesting_depth"] = depth
            if depth > self.max_nesting_depth:
                issues.append(
                    f"Data nesting depth ({depth}) exceeds maximum "
                    f"({self.max_nesting_depth})"
                )
                warning_count += 1

            # Check for basic test indicators
            test_indicators = self._find_test_indicators(data)
            details["test_indicators"] = test_indicators
            if not test_indicators:
                issues.append("No test case indicators found in data")
                warning_count += 1

        severity = (
            QualitySeverity.CRITICAL if error_count > 0 else QualitySeverity.MEDIUM
        )

        return ValidationResult(
            is_valid=error_count == 0,
            severity=severity,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            details=details,
        )

    def _validate_size(self, data: Any) -> ValidationResult:
        """Validate the size of the data."""
        issues = []
        error_count = 0
        warning_count = 0
        details: dict[str, Any] = {}

        # Calculate data size
        try:
            data_str = json.dumps(data, default=str)
            size_bytes = len(data_str.encode("utf-8"))
            size_mb = size_bytes / (1024 * 1024)

            details["size_bytes"] = size_bytes
            details["size_mb"] = round(size_mb, 2)

            if size_mb > self.max_data_size_mb:
                issues.append(
                    f"Data size ({size_mb:.2f} MB) exceeds maximum "
                    f"({self.max_data_size_mb} MB)"
                )
                error_count += 1
        except (TypeError, ValueError) as e:
            issues.append(f"Unable to calculate data size: {e!s}")
            error_count += 1

        # Check for extremely large individual fields
        if isinstance(data, dict):
            large_fields = []
            problematic_fields = []
            for key, value in data.items():
                field_size_mb, error_message = self._calculate_field_size(value)
                if error_message is not None:
                    problematic_fields.append(key)
                    issues.append(
                        f"Unable to calculate size for field '{key}': {error_message}"
                    )
                    error_count += 1
                    continue

                if field_size_mb > ValidationThresholds.LARGE_FIELD_SIZE_MB:
                    large_fields.append((key, field_size_mb))

            if large_fields:
                details["large_fields"] = large_fields
                issues.append(
                    f"Found {len(large_fields)} large fields that may cause "
                    "processing issues"
                )
                warning_count += 1

            if problematic_fields:
                details["problematic_fields"] = problematic_fields

        severity = QualitySeverity.CRITICAL if error_count > 0 else QualitySeverity.LOW

        return ValidationResult(
            is_valid=error_count == 0,
            severity=severity,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            details=details,
        )

    def _validate_content(self, data: Any) -> ValidationResult:
        """Validate the content quality of the data."""
        issues = []
        error_count = 0
        warning_count = 0
        details: dict[str, Any] = {}

        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=True,
                severity=QualitySeverity.INFO,
                error_count=0,
                warning_count=0,
                issues=[],
                details={},
            )

        # Check for suspicious or potentially problematic content
        suspicious_patterns = []

        # Check for common encoding issues
        if self._contains_encoding_issues(data):
            suspicious_patterns.append("encoding_issues")
            issues.append("Data may contain encoding issues")
            warning_count += 1

        # Check for extremely long strings that might cause issues
        long_strings = self._find_long_strings(data)
        if long_strings:
            suspicious_patterns.append("long_strings")
            details["long_strings_count"] = len(long_strings)
            issues.append(f"Found {len(long_strings)} extremely long string values")
            warning_count += 1

        # Check for empty keys - indicates poor data quality
        empty_keys = [key for key in data if not key or not key.strip()]
        if empty_keys:
            suspicious_patterns.append("empty_keys")
            issues.append(f"Found {len(empty_keys)} empty or whitespace-only keys")
            warning_count += 1

        # Check for null/empty value patterns
        null_stats = self._analyze_null_values(data)
        details["null_analysis"] = null_stats
        null_percent = null_stats["null_percentage"]
        threshold = ValidationThresholds.NULL_VALUE_WARNING_PERCENT
        if null_percent >= threshold:
            suspicious_patterns.append("high_null_rate")
            issues.append(
                "High percentage of null/empty values "
                f"({null_stats['null_percentage']:.1f}%)"
            )
            warning_count += 1

        details["suspicious_patterns"] = suspicious_patterns

        severity = QualitySeverity.MEDIUM if warning_count > 0 else QualitySeverity.LOW

        return ValidationResult(
            is_valid=error_count == 0,
            severity=severity,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            details=details,
        )

    def _calculate_field_size(self, value: Any) -> tuple[float, str | None]:
        """Calculate serialized field size, capturing serialization failures."""
        try:
            field_str = json.dumps(value, default=str)
        except (TypeError, ValueError) as error:
            return 0.0, str(error)

        field_size_mb = len(field_str.encode("utf-8")) / (1024 * 1024)
        return field_size_mb, None

    def _find_test_indicators(self, data: dict[str, Any]) -> list[str]:
        """Find indicators that suggest this is test data."""
        data_str = data_to_lower_cached(data)

        test_keywords = [
            "test",
            "case",
            "step",
            "expected",
            "result",
            "verify",
            "assert",
            "check",
            "validate",
            "suite",
            "scenario",
        ]

        return [keyword for keyword in test_keywords if keyword in data_str]

    def _contains_encoding_issues(self, data: dict[str, Any]) -> bool:
        """Check for common encoding issues in string values."""
        try:
            data_str = json.dumps(data, default=str)
            # Look for common encoding issue patterns
            encoding_patterns = [
                b"\xef\xbf\xbd",  # UTF-8 replacement character
                "\\u",  # Unicode escape sequences
                "\\x",  # Hex escape sequences
            ]

            for pattern in encoding_patterns:
                if str(pattern) in data_str:
                    return True
        except (TypeError, ValueError):
            return True  # If we can't serialize, there might be encoding issues

        return False

    def _find_long_strings(
        self,
        data: dict[str, Any],
        max_length: int = ValidationThresholds.MAX_STRING_LENGTH_CHARS,
    ) -> list[str]:
        """Find extremely long string values that might cause issues."""
        long_strings = []

        def _check_value(value: Any, path: str = "") -> None:
            if isinstance(value, str) and len(value) > max_length:
                long_strings.append(f"{path}: {len(value)} characters")
            elif isinstance(value, dict):
                for key, val in value.items():
                    _check_value(val, f"{path}.{key}" if path else key)
            elif isinstance(value, list):
                for i, val in enumerate(value):
                    _check_value(val, f"{path}[{i}]" if path else f"[{i}]")

        _check_value(data)
        return long_strings

    def _analyze_null_values(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analyze null and empty values in the data."""
        total_values = 0
        null_values = 0

        def _count_values(obj: Any) -> None:
            nonlocal total_values, null_values
            total_values += 1

            if obj is None or obj in ("", []):
                null_values += 1
            elif isinstance(obj, dict):
                for value in obj.values():
                    _count_values(value)
            elif isinstance(obj, list):
                for item in obj:
                    _count_values(item)

        _count_values(data)

        null_percentage = (null_values / total_values * 100) if total_values > 0 else 0

        return {
            "total_values": total_values,
            "null_values": null_values,
            "null_percentage": null_percentage,
        }
