"""Data models for Medallion architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .enums import ProcessingStatus, SupportedFormat


@dataclass(frozen=True)
class FormatDetectionResult:
    """Result of format detection analysis for raw data integration."""

    detected_format: SupportedFormat
    confidence_score: float
    evidence_details: dict[str, Any]
    detection_timestamp: datetime = field(default_factory=datetime.now)
    detection_version: str = "1.0"

    def __post_init__(self) -> None:
        """Validate format detection result constraints."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got "
                f"{self.confidence_score}"
            )


@dataclass(frozen=True)
class DataLineage:
    """Comprehensive data lineage tracking for medallion architecture."""

    source_id: str
    source_type: str  # "file", "api", "stream", etc.
    source_location: str
    transformation_history: list[dict[str, Any]] = field(default_factory=list)
    parent_records: list[str] = field(default_factory=list)
    child_records: list[str] = field(default_factory=list)
    created_timestamp: datetime = field(default_factory=datetime.now)

    @property
    def depth(self) -> int:
        """Calculate lineage depth.

        Returns:
            Number of transformation steps in the lineage history.
        """
        return len(self.transformation_history)

    def add_transformation(self, transformation: dict[str, Any]) -> DataLineage:
        """Add transformation step to lineage history."""
        new_history = [*self.transformation_history, transformation]
        return DataLineage(
            source_id=self.source_id,
            source_type=self.source_type,
            source_location=self.source_location,
            transformation_history=new_history,
            parent_records=self.parent_records,
            child_records=self.child_records,
            created_timestamp=self.created_timestamp,
        )


@dataclass
class LayerMetadata:
    """Metadata for tracking data lineage and processing information."""

    source_path: Path
    layer_name: str
    ingestion_timestamp: datetime
    processing_timestamp: datetime | None = None
    data_hash: str = ""
    version: str = "1.0"
    format_type: SupportedFormat = SupportedFormat.UNKNOWN
    record_count: int = 0
    file_size_bytes: int = 0
    processing_duration_ms: float = 0.0
    user_id: str = "system"
    session_id: str = ""
    custom_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataQualityMetrics:
    """Quality metrics for validation scoring across layers."""

    completeness_score: float = 0.0  # Percentage of required fields populated
    consistency_score: float = 0.0  # Adherence to formatting standards
    validity_score: float = 0.0  # Data type and constraint validation
    accuracy_score: float = 0.0  # Business rule compliance
    uniqueness_score: float = 0.0  # Duplicate detection results
    overall_score: float = 0.0  # Weighted average of all scores

    quality_issues: list[str] = field(default_factory=list)
    validation_errors: int = 0
    validation_warnings: int = 0
    data_anomalies: int = 0

    calculated_at: datetime = field(default_factory=datetime.now)
    calculation_duration_ms: float = 0.0


@dataclass
class LineageInfo:
    """Data lineage tracking information."""

    data_id: str
    source_layer: str
    target_layer: str
    transformation_type: str
    transformation_timestamp: datetime
    parent_ids: list[str] = field(default_factory=list)
    child_ids: list[str] = field(default_factory=list)
    transformation_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of layer processing operations."""

    status: ProcessingStatus
    processed_count: int
    success_count: int
    error_count: int
    warning_count: int
    skipped_count: int
    processing_time_ms: float
    start_timestamp: datetime
    metadata: LayerMetadata
    quality_metrics: DataQualityMetrics
    end_timestamp: datetime | None = None
    lineage: list[LineageInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerQuery:
    """Query specification for retrieving data from layers."""

    layer_name: str
    data_ids: list[str] = field(default_factory=list)
    date_range: tuple[datetime, datetime] | None = None
    format_types: list[SupportedFormat] = field(default_factory=list)
    quality_threshold: float = 0.0
    limit: int | None = None
    offset: int = 0
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerData:
    """Data retrieved from a layer."""

    records: list[dict[str, Any]]
    metadata: list[LayerMetadata]
    total_count: int
    retrieved_count: int
    query: LayerQuery
    retrieved_at: datetime = field(default_factory=datetime.now)
