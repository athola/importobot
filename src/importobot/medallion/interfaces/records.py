"""Record classes for Medallion architecture."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .data_models import DataLineage, FormatDetectionResult
from .enums import DataQuality, ProcessingStatus


@dataclass(frozen=True)
class RecordMetadata:
    """Enhanced metadata for medallion layer records with comprehensive tracking."""

    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    schema_version: str = "1.0"
    ingestion_timestamp: datetime = field(default_factory=datetime.now)

    # Data quality metrics
    data_quality: DataQuality = DataQuality.UNKNOWN
    quality_score: float = 0.0
    quality_checks: Dict[str, Any] = field(default_factory=dict)

    # Processing information
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_errors: List[str] = field(default_factory=list)
    processing_duration_ms: Optional[int] = None

    # Source information
    source_system: str = "importobot"
    source_file_size: Optional[int] = None
    source_checksum: Optional[str] = None

    # Custom attributes for extensibility
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate metadata constraints."""
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError(
                f"Quality score must be between 0.0 and 1.0, got {self.quality_score}"
            )

    @property
    def is_valid(self) -> bool:
        """Check if record metadata indicates valid processing."""
        return (
            self.processing_status == ProcessingStatus.COMPLETED
            and len(self.processing_errors) == 0
            and self.data_quality != DataQuality.POOR
        )


@dataclass(frozen=True)
class BronzeRecord:
    """Immutable Bronze layer record for raw data with comprehensive tracking.

    Bronze layer stores raw, unprocessed data with full metadata and lineage
    tracking as defined in Databricks Medallion Architecture patterns.
    """

    data: Dict[str, Any]
    metadata: RecordMetadata
    format_detection: FormatDetectionResult
    lineage: DataLineage

    # Storage information
    storage_location: Optional[str] = None
    storage_backend: str = "local"
    compression_type: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate Bronze record constraints."""
        if not isinstance(self.data, dict):
            raise ValueError("Bronze record data must be a dictionary")

        if (
            not self.data
            and self.metadata.processing_status == ProcessingStatus.COMPLETED
        ):
            raise ValueError("Bronze record data cannot be empty")

    @property
    def record_id(self) -> str:
        """Get unique record identifier."""
        return self.metadata.record_id

    @property
    def size_bytes(self) -> int:
        """Estimate record size in bytes."""
        return len(json.dumps(self.data, default=str).encode("utf-8"))

    @property
    def is_processed(self) -> bool:
        """Check if record has been successfully processed."""
        return self.metadata.processing_status == ProcessingStatus.COMPLETED

    def update_processing_status(
        self,
        status: ProcessingStatus,
        errors: Optional[List[str]] = None,
        duration_ms: Optional[int] = None,
    ) -> "BronzeRecord":
        """Create new record with updated processing status."""
        new_metadata = RecordMetadata(
            record_id=self.metadata.record_id,
            version=self.metadata.version,
            schema_version=self.metadata.schema_version,
            ingestion_timestamp=self.metadata.ingestion_timestamp,
            data_quality=self.metadata.data_quality,
            quality_score=self.metadata.quality_score,
            quality_checks=self.metadata.quality_checks,
            processing_status=status,
            processing_errors=errors or [],
            processing_duration_ms=duration_ms,
            source_system=self.metadata.source_system,
            source_file_size=self.metadata.source_file_size,
            source_checksum=self.metadata.source_checksum,
            custom_attributes=self.metadata.custom_attributes,
        )

        return BronzeRecord(
            data=self.data,
            metadata=new_metadata,
            format_detection=self.format_detection,
            lineage=self.lineage,
            storage_location=self.storage_location,
            storage_backend=self.storage_backend,
            compression_type=self.compression_type,
        )
