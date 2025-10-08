"""Bronze layer implementation for raw data ingestion with minimal processing."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from importobot.medallion.base_layers import BaseMedallionLayer
from importobot.medallion.interfaces.data_models import (
    DataLineage,
    DataQualityMetrics,
    FormatDetectionResult,
    LayerMetadata,
    ProcessingResult,
)
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.interfaces.records import BronzeRecord, RecordMetadata
from importobot.utils.logging import setup_logger
from importobot.utils.string_cache import data_to_lower_cached
from importobot.utils.validation_models import (
    QualitySeverity,
    ValidationResult,
    create_basic_validation_result,
)

logger = setup_logger(__name__)


class BronzeLayer(BaseMedallionLayer):
    """Bronze layer for raw data ingestion with minimal processing."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        """Initialize the Bronze layer."""
        super().__init__("bronze", storage_path)

    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Ingest raw data into the Bronze layer."""
        start_time = datetime.now()

        try:
            # Generate unique ID for this data
            data_id = self._generate_data_id(data, metadata)

            # Update metadata with processing information
            metadata.data_hash = self._calculate_data_hash(data)
            metadata.format_type = self._detect_format_type(data)
            metadata.processing_timestamp = start_time
            metadata.layer_name = self.layer_name

            # Validate data
            validation_result = self.validate(data)
            if not validation_result.is_valid:
                logger.warning(
                    "Data validation failed for %s: %s",
                    data_id,
                    validation_result.issues,
                )

            # Calculate quality metrics
            quality_metrics = self.calculate_quality_metrics(data)

            # Create lineage record
            lineage = self._create_lineage(
                data_id=data_id,
                source_layer="input",
                target_layer=self.layer_name,
                transformation_type="raw_ingestion",
            )

            # Store data and metadata
            self._data_store[data_id] = data
            self._metadata_store[data_id] = metadata
            self._lineage_store[data_id] = lineage

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds() * 1000

            return ProcessingResult(
                status=(
                    ProcessingStatus.COMPLETED
                    if validation_result.is_valid
                    else ProcessingStatus.FAILED
                ),
                processed_count=1,
                success_count=1 if validation_result.is_valid else 0,
                error_count=0 if validation_result.is_valid else 1,
                warning_count=validation_result.warning_count,
                skipped_count=0,
                processing_time_ms=processing_time,
                start_timestamp=start_time,
                end_timestamp=end_time,
                metadata=metadata,
                quality_metrics=quality_metrics,
                lineage=[lineage],
                errors=(
                    validation_result.issues if not validation_result.is_valid else []
                ),
            )

        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds() * 1000
            logger.error("Failed to ingest data into Bronze layer: %s", str(e))

            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                processed_count=1,
                success_count=0,
                error_count=1,
                warning_count=0,
                skipped_count=0,
                processing_time_ms=processing_time,
                start_timestamp=start_time,
                end_timestamp=end_time,
                metadata=metadata,
                quality_metrics=DataQualityMetrics(),
                errors=[str(e)],
            )

    def validate(self, data: Any) -> ValidationResult:
        """Validate raw data for Bronze layer ingestion."""
        issues = []
        error_count = 0
        warning_count = 0

        # Basic structure validation
        if not isinstance(data, dict):
            issues.append("Data must be a dictionary structure")
            error_count += 1

        if isinstance(data, dict):
            # Check for completely empty data
            if not data:
                issues.append("Data dictionary is empty")
                warning_count += 1

            # Check for basic test structure indicators
            test_indicators = ["test", "case", "step", "name", "description"]
            has_test_indicator = any(
                indicator in data_to_lower_cached(data) for indicator in test_indicators
            )
            if not has_test_indicator:
                issues.append("Data does not appear to contain test case information")
                warning_count += 1

        severity = (
            QualitySeverity.CRITICAL if error_count > 0 else QualitySeverity.MEDIUM
        )

        return create_basic_validation_result(
            severity=severity,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
        )

    def ingest_with_detection(
        self, data: dict[str, Any], source_info: dict[str, Any]
    ) -> BronzeRecord:
        """Ingest data with format detection and create BronzeRecord.

        Args:
            data: The data to ingest
            source_info: Source information for metadata

        Returns:
            BronzeRecord with complete metadata and format detection
        """
        # Simple implementation for Bronze layer
        # Create basic format detection result
        format_detection = FormatDetectionResult(
            detected_format=SupportedFormat.UNKNOWN,
            confidence_score=0.5,
            evidence_details={"source": "bronze_layer", "method": "basic_detection"},
        )

        # Create record metadata
        record_metadata = RecordMetadata(
            source_system="bronze_layer",
            source_file_size=source_info.get("file_size", 0),
        )

        # Create data lineage
        source_path = source_info.get("source_path", "bronze_layer")
        lineage = DataLineage(
            source_id=str(source_path),
            source_type="bronze_layer",
            source_location=str(source_path),
        )

        return BronzeRecord(
            data=data,
            metadata=record_metadata,
            format_detection=format_detection,
            lineage=lineage,
        )

    def get_record_metadata(self, record_id: str) -> Optional[RecordMetadata]:
        """Retrieve enhanced metadata for a specific record.

        Args:
            record_id: The unique identifier for the record

        Returns:
            Record metadata if found, None otherwise
        """
        # Bronze layer doesn't maintain persistent record metadata
        return None

    def get_record_lineage(self, record_id: str) -> Optional[DataLineage]:
        """Retrieve comprehensive lineage information for a specific record.

        Args:
            record_id: The unique identifier for the record

        Returns:
            Data lineage if found, None otherwise
        """
        # Bronze layer doesn't maintain persistent record lineage
        return None

    def validate_bronze_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate raw data quality and return quality metrics.

        Args:
            data: The data to validate

        Returns:
            Dictionary with validation results and quality metrics
        """
        validation_result = self.validate(data)
        quality_metrics = self.calculate_quality_metrics(data)

        return {
            "is_valid": validation_result.is_valid,
            "error_count": validation_result.error_count,
            "warning_count": validation_result.warning_count,
            "issues": validation_result.issues,
            "quality_score": quality_metrics.overall_score,
            "completeness_score": quality_metrics.completeness_score,
            "consistency_score": quality_metrics.consistency_score,
            "validity_score": quality_metrics.validity_score,
        }

    def get_bronze_records(
        self,
        filter_criteria: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> list[BronzeRecord]:
        """Retrieve Bronze records based on filter criteria.

        Args:
            filter_criteria: Optional filtering criteria
            limit: Optional limit on number of records

        Returns:
            List of Bronze records matching the criteria
        """
        # Bronze layer doesn't maintain persistent records in this simple implementation
        return []


__all__ = ["BronzeLayer"]
