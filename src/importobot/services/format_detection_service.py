"""Format detection service extracted from RawDataProcessor.

Provides specialized format detection and confidence scoring capabilities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.interfaces.data_models import (
    FormatDetectionResult,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import get_logger

logger = get_logger()


class FormatDetectionService:
    """Service for detecting data formats and calculating confidence scores."""

    def __init__(self) -> None:
        """Initialize format detection service."""
        self.format_detector = FormatDetector()

    def detect_format(self, data: dict[str, Any]) -> SupportedFormat:
        """Detect the most likely format for the given data.

        Args:
            data: Data to analyze for format detection

        Returns:
            SupportedFormat enum for the detected format
        """
        return self.format_detector.detect_format(data)

    def get_format_confidence(
        self, data: dict[str, Any], target_format: SupportedFormat
    ) -> float:
        """Get confidence score for a specific format.

        Args:
            data: Data to analyze
            target_format: Format to get confidence score for

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Use Independent Bayesian confidence scoring from format detector
        return self.format_detector.get_format_confidence(data, target_format)

    def get_all_format_scores(
        self, data: dict[str, Any]
    ) -> dict[SupportedFormat, float]:
        """Get confidence scores for all supported formats.

        Args:
            data: Data to analyze

        Returns:
            Dictionary mapping formats to confidence scores
        """
        detected_format = self.format_detector.detect_format(data)
        # Return a dict with the detected format having score 1.0, others 0.0
        scores: dict[SupportedFormat, float] = cast(
            dict[SupportedFormat, float], dict.fromkeys(SupportedFormat, 0.0)
        )
        scores[detected_format] = 1.0
        return scores

    def get_detailed_detection_result(
        self, data: dict[str, Any]
    ) -> FormatDetectionResult:
        """Get full format detection result with all details.

        Args:
            data: Data to analyze

        Returns:
            Complete FormatDetectionResult with format, confidence, and evidence
        """
        detected_format = self.format_detector.detect_format(data)
        return FormatDetectionResult(
            detected_format=detected_format,
            confidence_score=1.0,  # FormatDetector provides binary detection
            evidence_details={"detection_method": "format_detector"},
            detection_timestamp=datetime.now(),
        )
