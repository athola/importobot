"""Quality assessment service extracted from RawDataProcessor.

Handles data quality metrics calculation and validation reporting.
"""

from __future__ import annotations

from typing import Any

from importobot.medallion.bronze.validation import BronzeValidator
from importobot.medallion.interfaces.data_models import DataQualityMetrics
from importobot.utils.data_analysis import count_data_elements, count_data_fields
from importobot.utils.logging import get_logger
from importobot.utils.validation_models import QualitySeverity, ValidationResult

logger = get_logger()


def stable_weighted_average(values: list[float], weights: list[float]) -> float:
    """Calculate weighted average with numerical stability.

    Uses Kahan summation algorithm to minimize floating-point errors
    and includes proper validation for edge cases.

    Args:
        values: List of values to average
        weights: List of weights corresponding to values

    Returns:
        Weighted average

    Raises:
        ValueError: If lengths don't match or total weight is near zero
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have the same length")

    if not values:
        return 0.0

    # Use Kahan summation for numerical stability
    total_weight = 0.0
    weighted_sum = 0.0
    compensation = 0.0  # Compensation term for lost low-order bits

    for val, weight in zip(values, weights, strict=False):
        # Add weight to total with Kahan summation
        y = weight - compensation
        t = total_weight + y
        compensation = (t - total_weight) - y
        total_weight = t

        # Add weighted value to sum with Kahan summation
        y = (val * weight) - compensation
        t = weighted_sum + y
        compensation = (t - weighted_sum) - y
        weighted_sum = t

    # Check for near-zero total weight to avoid division by very small numbers
    if abs(total_weight) < 1e-10:
        raise ValueError("Total weight is too close to zero")

    return weighted_sum / total_weight


class QualityAssessmentService:
    """Service for assessing data quality and calculating metrics."""

    def __init__(
        self,
        *,
        high_threshold: float = 0.9,
        medium_threshold: float = 0.7,
        min_quality_for_valid: float = 0.5,
    ) -> None:
        """Initialize quality assessment service.

        Args:
            high_threshold: Overall score at or above which severity is HIGH
            medium_threshold: Overall score at or above which severity is MEDIUM
            min_quality_for_valid: Minimum overall score to consider data valid
                before ingestion
        """
        self.validator = BronzeValidator()
        self._high_threshold = float(high_threshold)
        self._medium_threshold = float(medium_threshold)
        self._min_quality_for_valid = float(min_quality_for_valid)

    def configure_thresholds(
        self,
        *,
        high_threshold: float | None = None,
        medium_threshold: float | None = None,
        min_quality_for_valid: float | None = None,
    ) -> None:
        """Update quality thresholds at runtime."""
        if high_threshold is not None:
            self._high_threshold = float(high_threshold)
        if medium_threshold is not None:
            self._medium_threshold = float(medium_threshold)
        if min_quality_for_valid is not None:
            self._min_quality_for_valid = float(min_quality_for_valid)

    def calculate_quality_metrics(self, data: Any) -> DataQualityMetrics:
        """Calculate data quality metrics.

        Args:
            data: Data to assess quality for

        Returns:
            DataQualityMetrics with quality scores and assessments
        """
        # Basic quality metrics
        completeness_score = self._calculate_completeness(data)
        validity_score = self._calculate_validity(data)
        consistency_score = self._calculate_consistency(data)

        # Overall quality score (weighted average with numerical stability)
        overall_score = stable_weighted_average(
            [completeness_score, validity_score, consistency_score], [0.4, 0.4, 0.2]
        )

        # Determine severity based on overall score for issue categorization
        if overall_score >= self._high_threshold:
            severity = QualitySeverity.HIGH  # High quality data
        elif overall_score >= self._medium_threshold:
            severity = QualitySeverity.MEDIUM  # Medium quality data
        else:
            severity = QualitySeverity.LOW  # Low quality data, needs attention

        # Create quality issues with severity-based categorization
        quality_issues = []
        if completeness_score < 0.8:
            quality_issues.append(f"Low completeness: {completeness_score:.2f}")
        if validity_score < 0.8:
            quality_issues.append(f"Low validity: {validity_score:.2f}")
        if consistency_score < 0.8:
            quality_issues.append(f"Low consistency: {consistency_score:.2f}")

        # Add severity-based issue if overall quality is concerning
        if severity == QualitySeverity.LOW:
            quality_issues.append(
                f"Overall data quality is low (score: {overall_score:.2f})"
            )
        elif severity == QualitySeverity.MEDIUM:
            quality_issues.append(
                f"Data quality is moderate (score: {overall_score:.2f})"
            )

        # Determine validation error count based on severity
        validation_errors = len(
            [issue for issue in quality_issues if severity == QualitySeverity.LOW]
        )
        validation_warnings = len(
            [issue for issue in quality_issues if severity == QualitySeverity.MEDIUM]
        )

        return DataQualityMetrics(
            completeness_score=completeness_score,
            validity_score=validity_score,
            consistency_score=consistency_score,
            overall_score=overall_score,
            quality_issues=quality_issues,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
        )

    def validate_bronze_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate data using Bronze layer validation rules.

        Args:
            data: Data to validate

        Returns:
            Dictionary containing validation results and recommendations
        """
        validation_result = self.validator.validate_raw_data(data)

        return {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.issues,
            "warnings": [],  # ValidationResult doesn't have
            # separate warnings
            "quality_metrics": self.calculate_quality_metrics(data),
        }

    def validate_before_ingestion(self, data: dict[str, Any]) -> ValidationResult:
        """Perform validation before data ingestion.

        Args:
            data: Data to validate

        Returns:
            ValidationResult indicating if data is ready for ingestion
        """
        # Get basic validation result
        base_result = self.validator.validate_raw_data(data)

        # Calculate quality metrics to determine severity
        quality_metrics = self.calculate_quality_metrics(data)

        # Determine severity based on overall quality score
        if quality_metrics.overall_score >= self._high_threshold:
            severity = QualitySeverity.HIGH  # High quality
            # data
        elif quality_metrics.overall_score >= self._medium_threshold:
            severity = QualitySeverity.MEDIUM  # Medium quality
            # data
        else:
            severity = QualitySeverity.LOW  # Low quality data,
            # needs attention

        # Enhance validation result with quality-based severity and metrics
        enhanced_result = ValidationResult(
            is_valid=base_result.is_valid
            and quality_metrics.overall_score >= self._min_quality_for_valid,
            # Require minimum quality
            severity=severity,
            error_count=base_result.error_count + quality_metrics.validation_errors,
            details={
                **base_result.details,
                "quality_metrics": {
                    "overall_score": quality_metrics.overall_score,
                    "completeness": quality_metrics.completeness_score,
                    "validity": quality_metrics.validity_score,
                    "consistency": (quality_metrics.consistency_score),
                },
            },
        )

        return enhanced_result

    def _calculate_completeness(self, data: Any) -> float:
        """Calculate data completeness score (0.0 to 1.0)."""
        if not data:
            return 0.0

        if isinstance(data, dict):
            total_fields = len(data)
            non_empty_fields = sum(
                1 for v in data.values() if v is not None and v != ""
            )
            return non_empty_fields / total_fields if total_fields > 0 else 0.0

        return 1.0 if data else 0.0

    def _calculate_validity(self, data: Any) -> float:
        """Calculate data validity score based on type consistency."""
        if not isinstance(data, dict):
            return 1.0

        # Check for consistent data types within collections
        type_consistency = 0.0
        field_count = len(data)

        for value in data.values():
            if isinstance(value, list | tuple) and value:
                # Check type consistency in lists
                first_type = type(value[0])
                consistent = all(isinstance(item, first_type) for item in value)
                type_consistency += 1.0 if consistent else 0.5
            else:
                # Single values are always consistent
                type_consistency += 1.0

        return type_consistency / field_count if field_count > 0 else 1.0

    def _calculate_consistency(self, data: Any) -> float:
        """Calculate data consistency score."""
        if not isinstance(data, dict):
            return 1.0

        # Basic consistency check - no duplicate keys, consistent structure
        # This is simplified - could be expanded with more sophisticated rules
        return 1.0

    def _count_records(self, data: Any) -> int:
        """Count the number of records in the data."""
        return count_data_elements(data)

    def _count_fields(self, data: Any) -> int:
        """Count the number of fields/attributes in the data."""
        return count_data_fields(data)
