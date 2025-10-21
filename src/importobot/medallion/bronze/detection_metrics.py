"""Performance monitoring and metrics collection for format detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import get_logger


@dataclass
class DetectionMetrics:
    """Metrics collected during format detection process."""

    format_detected: SupportedFormat
    confidence_score: float
    detection_time_ms: int
    pattern_matches: dict[str, bool] = field(default_factory=dict)
    field_counts: dict[str, int] = field(default_factory=dict)
    fast_path_used: bool = False
    complexity_assessment: dict[str, Any] | None = None

    def to_metrics(self) -> dict[str, Any]:
        """Export metrics for monitoring systems."""
        return {
            "format_detected": self.format_detected.value,
            "confidence_score": self.confidence_score,
            "detection_time_ms": self.detection_time_ms,
            "pattern_matches_count": len(self.pattern_matches),
            "patterns_matched": sum(self.pattern_matches.values()),
            "total_fields": sum(self.field_counts.values()),
            "fast_path_used": self.fast_path_used,
            "complexity_level": (
                self.complexity_assessment.get("level")
                if self.complexity_assessment
                else "unknown"
            ),
        }

    def log_performance_warning(self, threshold_ms: int = 1000) -> bool:
        """Check if detection took longer than threshold and should be logged."""
        return self.detection_time_ms > threshold_ms


class PerformanceMonitor:
    """Context manager for monitoring format detection performance."""

    def __init__(self, data_size_estimate: int | None = None):
        """Initialize performance monitor.

        Args:
            data_size_estimate: Rough estimate of data size for correlation analysis
        """
        self.data_size_estimate = data_size_estimate
        self.start_time = 0.0
        self.metrics: DetectionMetrics | None = None

    def __enter__(self) -> PerformanceMonitor:
        """Start performance monitoring."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Finish performance monitoring and log if needed."""
        if self.metrics and self.metrics.log_performance_warning():
            logger = get_logger()

            logger.info(
                "Format detection performance metrics",
                extra={
                    "metrics": self.metrics.to_metrics(),
                    "data_size_estimate": self.data_size_estimate,
                    "performance_context": "detection_monitoring",
                },
            )

    def record_detection(
        self,
        format_detected: SupportedFormat,
        confidence_score: float,
        *,
        pattern_matches: dict[str, bool] | None = None,
        field_counts: dict[str, int] | None = None,
        fast_path_used: bool = False,
        complexity_assessment: dict[str, Any] | None = None,
    ) -> DetectionMetrics:
        """Record detection results and create metrics."""
        detection_time_ms = int((time.perf_counter() - self.start_time) * 1000)

        self.metrics = DetectionMetrics(
            format_detected=format_detected,
            confidence_score=confidence_score,
            detection_time_ms=detection_time_ms,
            pattern_matches=pattern_matches or {},
            field_counts=field_counts or {},
            fast_path_used=fast_path_used,
            complexity_assessment=complexity_assessment,
        )

        return self.metrics


__all__ = ["DetectionMetrics", "PerformanceMonitor"]
