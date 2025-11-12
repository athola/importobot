"""Raw Data Processor using service decomposition.

Provides composition-based approach using focused services for improved
maintainability and separation of concerns.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.base_interfaces import DataLayer
from importobot.medallion.interfaces.data_models import (
    DataLineage,
    DataQualityMetrics,
    FormatDetectionResult,
    LayerData,
    LayerMetadata,
    LayerQuery,
    LineageInfo,
    ProcessingResult,
)
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.interfaces.records import BronzeRecord, RecordMetadata
from importobot.services.data_ingestion_service import DataIngestionService
from importobot.services.format_detection_service import FormatDetectionService
from importobot.services.metadata_service import MetadataService
from importobot.services.quality_assessment_service import QualityAssessmentService
from importobot.services.security_types import SecurityLevel
from importobot.services.validation_service import ValidationService
from importobot.utils.logging import get_logger
from importobot.utils.validation_models import QualitySeverity, ValidationResult

logger = get_logger()


class BronzeRecordResponse(dict[str, Any], BronzeRecord):
    """Hybrid response that behaves like both a BronzeRecord and a mapping."""

    def __init__(
        self,
        *,
        data: dict[str, Any],
        metadata: RecordMetadata,
        format_detection: FormatDetectionResult,
        lineage: DataLineage,
        payload: dict[str, Any],
        storage_location: str | None = None,
        storage_backend: str = "local",
        compression_type: str | None = None,
    ) -> None:
        """Initialize RawDataRecord with data and metadata."""
        BronzeRecord.__init__(
            self,
            data=data,
            metadata=metadata,
            format_detection=format_detection,
            lineage=lineage,
            storage_location=storage_location,
            storage_backend=storage_backend,
            compression_type=compression_type,
        )
        dict.__init__(self, payload)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        """Return string representation of RawDataRecord."""
        return (
            f"BronzeRecordResponse(record_id={self.record_id}, "
            f"keys={list(self.keys())})"
        )


class IngestionFacade:
    """Facade for data ingestion operations."""

    def __init__(self, ingestion_service: DataIngestionService):
        """Initialize ingestion facade."""
        self.ingestion_service = ingestion_service

    def ingest_file(self, file_path: str | Path) -> ProcessingResult:
        """Delegate to ingestion service."""
        return self.ingestion_service.ingest_file(file_path)

    def ingest_json_string(
        self, json_string: str, source_name: str = "string_input"
    ) -> ProcessingResult:
        """Delegate to ingestion service."""
        return self.ingestion_service.ingest_json_string(json_string, source_name)

    def ingest_data_dict(
        self, data: dict[str, Any], source_name: str = "dict_input"
    ) -> ProcessingResult:
        """Delegate to ingestion service."""
        return self.ingestion_service.ingest_data_dict(data, source_name)


class FormatDetectionFacade:
    """Facade for format detection operations."""

    def __init__(self, format_service: FormatDetectionService):
        """Initialize format detection facade."""
        self.format_service = format_service

    def detect_format(self, data: dict[str, Any]) -> SupportedFormat:
        """Delegate to format service."""
        return self.format_service.detect_format(data)

    def get_format_confidence(
        self, data: dict[str, Any], target_format: SupportedFormat
    ) -> float:
        """Delegate to format service."""
        return self.format_service.get_format_confidence(data, target_format)


class QualityAssessmentFacade:
    """Facade for quality assessment operations."""

    def __init__(self, quality_service: QualityAssessmentService):
        """Initialize quality assessment facade."""
        self.quality_service = quality_service

    def validate_before_ingestion(self, data: dict[str, Any]) -> ValidationResult:
        """Delegate to quality service."""
        return self.quality_service.validate_before_ingestion(data)

    def calculate_quality_metrics(self, data: Any) -> DataQualityMetrics:
        """Delegate to quality service."""
        return self.quality_service.calculate_quality_metrics(data)

    def validate_bronze_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to quality service."""
        return self.quality_service.validate_bronze_data(data)

    def configure_thresholds(
        self,
        *,
        high: float | None = None,
        medium: float | None = None,
        min_valid: float | None = None,
    ) -> None:
        """Configure quality thresholds."""
        self.quality_service.configure_thresholds(
            high_threshold=high,
            medium_threshold=medium,
            min_quality_for_valid=min_valid,
        )


class MetadataFacade:
    """Facade for metadata operations."""

    def __init__(self, metadata_service: MetadataService):
        """Initialize metadata facade."""
        self.metadata_service = metadata_service

    def get_record_metadata(self, record_id: str) -> RecordMetadata | None:
        """Delegate to metadata service."""
        return self.metadata_service.get_record_metadata(record_id)

    def get_record_lineage(self, record_id: str) -> DataLineage | None:
        """Delegate to metadata service."""
        return self.metadata_service.get_record_lineage(record_id)

    def get_lineage(self, data_id: str) -> LineageInfo:
        """Delegate to metadata service."""
        return self.metadata_service.create_lineage_info(data_id)


class PreviewOperations:
    """Handle preview operations combining format detection and quality metrics."""

    def __init__(
        self,
        format_service: FormatDetectionService,
        quality_service: QualityAssessmentService,
        metadata_service: MetadataService,
    ):
        """Initialize preview operations."""
        self.format_service = format_service
        self.quality_service = quality_service
        self.metadata_service = metadata_service

    def preview_ingestion(self, file_path: str | Path) -> dict[str, Any]:
        """Preview data ingestion without actually ingesting."""
        file_path = Path(file_path)

        try:
            # Read file data
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            return self.preview_ingestion_dict(data)

        except Exception as e:
            logger.error("Failed to preview file %s: %s", file_path, e)
            return {
                "error": str(e),
                "file_path": str(file_path),
                "preview_available": False,
            }

    def preview_ingestion_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Preview dictionary ingestion with quality and format analysis."""
        # Get format detection results
        format_result = self.format_service.get_detailed_detection_result(data)

        # Get quality metrics
        quality_metrics = self.quality_service.calculate_quality_metrics(data)

        # Get preview statistics
        preview_stats = self.metadata_service.calculate_preview_stats(data)

        return {
            "preview_available": True,
            "detected_format": format_result.detected_format.value,
            "format_confidence": {
                format_result.detected_format: format_result.confidence_score
            },
            "quality_score": quality_metrics.overall_score,
            "quality_issues": quality_metrics.quality_issues,
            "stats": preview_stats,
            "validation_ready": quality_metrics.overall_score >= 0.7,
        }


class DataLayerOperations:
    """Handle DataLayer interface operations."""

    def __init__(
        self,
        bronze_layer: BronzeLayer,
        validation_service: ValidationService,
    ):
        """Initialize data layer operations."""
        self.bronze_layer = bronze_layer
        self.validation_service = validation_service

    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Implement DataLayer abstract method for ingestion."""
        return self.bronze_layer.ingest(data, metadata)

    def retrieve(self, query: LayerQuery) -> LayerData:
        """Implement DataLayer abstract method for retrieval."""
        return self.bronze_layer.retrieve(query)

    def validate(self, data: Any) -> ValidationResult:
        """Implement DataLayer abstract method for validation."""
        service_result = self.validation_service.validate(data, strategy_name="json")

        # Convert service ValidationResult to interface ValidationResult
        return ValidationResult(
            is_valid=service_result.is_valid,
            severity=(
                QualitySeverity.HIGH
                if not service_result.is_valid
                else QualitySeverity.LOW
            ),
            error_count=len(
                [msg for msg in service_result.messages if "error" in msg.lower()]
            ),
            warning_count=len(
                [msg for msg in service_result.messages if "warning" in msg.lower()]
            ),
            issues=service_result.messages,
        )

    def ingest_to_layer(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Implement DataLayer interface for direct layer ingestion."""
        return self.bronze_layer.ingest(data, metadata)

    def retrieve_from_layer(self, query: LayerQuery) -> LayerData:
        """Implement DataLayer interface for layer data retrieval."""
        return self.bronze_layer.retrieve(query)

    def validate_layer_data(self, data: Any) -> ValidationResult:
        """Implement DataLayer interface validation using validation service."""
        service_result = self.validation_service.validate(data, strategy_name="json")

        # Convert service ValidationResult to interface ValidationResult
        return ValidationResult(
            is_valid=service_result.is_valid,
            severity=(
                QualitySeverity.HIGH
                if not service_result.is_valid
                else QualitySeverity.LOW
            ),
            error_count=len(
                [msg for msg in service_result.messages if "error" in msg.lower()]
            ),
            warning_count=len(
                [msg for msg in service_result.messages if "warning" in msg.lower()]
            ),
            issues=service_result.messages,
        )


class IntegrationOperations:
    """Handle integrated operations requiring multiple services."""

    def __init__(
        self,
        format_service: FormatDetectionService,
        quality_service: QualityAssessmentService,
        metadata_service: MetadataService,
        layer_name: str,
    ):
        """Initialize integration operations."""
        self.format_service = format_service
        self.quality_service = quality_service
        self.metadata_service = metadata_service
        self.layer_name = layer_name

    def ingest_with_detection(
        self,
        data: dict[str, Any],
        source_info: dict[str, Any],
    ) -> BronzeRecord:
        """Ingest data with automatic format detection and quality assessment."""
        processing_started_at = datetime.now()

        # Run detection and validation pipelines
        format_result = self.format_service.get_detailed_detection_result(data)
        quality_metrics = self.quality_service.calculate_quality_metrics(data)
        validation_result = self.quality_service.validate_before_ingestion(data)

        # Determine processing status based on validation and data presence
        if not data:
            processing_status = ProcessingStatus.SKIPPED
        elif validation_result.is_valid:
            processing_status = ProcessingStatus.COMPLETED
        else:
            processing_status = ProcessingStatus.FAILED

        # Create record metadata with lineage context
        record_id = hashlib.blake2b(str(data).encode()).hexdigest()
        metadata = RecordMetadata(
            record_id=record_id,
            ingestion_timestamp=processing_started_at,
            quality_score=quality_metrics.overall_score,
            processing_status=processing_status,
            custom_attributes=source_info,
        )

        lineage = DataLineage(
            source_id=record_id,
            source_type="raw_data",
            source_location=source_info.get("source_location", "unknown"),
            transformation_history=[
                {
                    "transformation_type": "format_detection",
                    "timestamp": datetime.now().isoformat(),
                    "detected_format": format_result.detected_format.value,
                    "confidence_score": format_result.confidence_score,
                    "quality_metrics": quality_metrics.overall_score,
                    "validation_severity": str(validation_result.severity),
                }
            ],
        )

        # Persist metadata and lineage for downstream queries
        self.metadata_service.store_record_metadata(record_id, metadata)
        self.metadata_service.store_record_lineage(record_id, lineage)

        # Build layer metadata for processing result
        source_path_hint = (
            source_info.get("source_path")
            or source_info.get("source")
            or f"bronze_record_{record_id}"
        )
        layer_metadata = self.metadata_service.create_metadata(
            Path(str(source_path_hint)),
            data,
        )
        layer_metadata.format_type = format_result.detected_format
        layer_metadata.data_hash = record_id
        layer_metadata.record_count = len(data) if isinstance(data, dict) else 0

        processing_finished_at = datetime.now()
        processing_duration_ms = (
            processing_finished_at - processing_started_at
        ).total_seconds() * 1000
        layer_metadata.processing_timestamp = processing_finished_at
        layer_metadata.processing_duration_ms = processing_duration_ms

        lineage_info = LineageInfo(
            data_id=record_id,
            source_layer="raw",
            target_layer=self.layer_name,
            transformation_type="ingest_with_detection",
            transformation_timestamp=processing_finished_at,
            transformation_details={
                "detected_format": format_result.detected_format.value,
                "confidence": format_result.confidence_score,
                "status": processing_status.value,
            },
        )

        processing_result = ProcessingResult(
            status=processing_status,
            processed_count=1 if data else 0,
            success_count=1 if processing_status == ProcessingStatus.COMPLETED else 0,
            error_count=validation_result.error_count,
            warning_count=validation_result.warning_count
            or len(quality_metrics.quality_issues),
            skipped_count=1 if processing_status == ProcessingStatus.SKIPPED else 0,
            processing_time_ms=processing_duration_ms,
            start_timestamp=processing_started_at,
            metadata=layer_metadata,
            quality_metrics=quality_metrics,
            end_timestamp=processing_finished_at,
            lineage=[lineage_info],
            errors=validation_result.issues,
            warnings=quality_metrics.quality_issues,
            details={
                "detected_format": format_result.detected_format.value,
                "confidence": format_result.confidence_score,
            },
        )

        response_payload = {
            "processing_result": processing_result,
            "quality_metrics": quality_metrics,
            "detected_format": format_result.detected_format.value,
            "format_confidence": format_result.confidence_score,
            "validation": validation_result,
            "original_data": data,
            "record_metadata": metadata,
            "lineage": lineage,
        }

        response = BronzeRecordResponse(
            data=data,
            metadata=metadata,
            format_detection=format_result,
            lineage=lineage,
            payload=response_payload,
        )
        response["status"] = processing_status

        return response

    def get_bronze_records(
        self,
        filter_criteria: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[BronzeRecord]:
        """Retrieve Bronze records with optional filtering."""
        # This would typically query the bronze layer's storage
        # For now, return empty list as storage implementation depends on backend
        logger.info(
            "Retrieving Bronze records: filter_criteria=%s, limit=%s",
            filter_criteria,
            limit,
        )
        return []


class SecurityOperations:
    """Handle security-related operations."""

    def __init__(self, ingestion_service: DataIngestionService):
        """Initialize security operations."""
        self.ingestion_service = ingestion_service

    def enable_security(
        self, security_level: SecurityLevel | str = SecurityLevel.STANDARD
    ) -> None:
        """Enable security gateway for data processing."""
        self.ingestion_service.enable_security(security_level)
        logger.info("Security gateway enabled for RawDataProcessor")

    def disable_security(self) -> None:
        """Disable security gateway for performance-critical scenarios."""
        self.ingestion_service.disable_security()
        logger.info("Security gateway disabled for RawDataProcessor")

    def get_security_configuration(self) -> dict[str, Any]:
        """Get current security configuration."""
        return self.ingestion_service.get_security_configuration()


class RawDataProcessor(DataLayer):
    """Bronze layer processor using service composition.

    Provides focused services for data processing with reduced complexity.

    Services:
    - DataIngestionService: Handles data intake with optional security hardening
    - FormatDetectionService: Provides format detection and confidence scoring
    - QualityAssessmentService: Manages data quality metrics and validation
    - MetadataService: Handles metadata creation and lineage tracking
    - ValidationService: Centralized validation logic

    The processor acts as a facade, delegating to specialized helper classes
    that organize related operations.
    """

    def __init__(
        self,
        *,
        bronze_layer: BronzeLayer | None = None,
        storage_backend: str | None = None,
        security_level: SecurityLevel | str = SecurityLevel.STANDARD,
        enable_security_gateway: bool = False,
        quality_thresholds: dict[str, float] | None = None,
    ):
        """Initialize processor with service composition.

        Args:
            bronze_layer: Optional Bronze layer instance
            storage_backend: Optional storage backend identifier
            security_level: Security level enum or string
            enable_security_gateway: Whether to enable security validation
            quality_thresholds: Optional quality threshold configuration
        """
        super().__init__("bronze")

        # Convert storage_backend to Path if provided, otherwise use default
        if bronze_layer is None:
            layer_storage_path = Path(storage_backend) if storage_backend else None
            bronze_layer = BronzeLayer(storage_path=layer_storage_path)

        self.bronze_layer = bronze_layer

        # Initialize focused services with optional security
        self.format_service = FormatDetectionService()
        self.ingestion_service = DataIngestionService(
            self.bronze_layer,
            security_level=security_level,
            enable_security_gateway=enable_security_gateway,
            format_service=self.format_service,
        )
        if quality_thresholds is None:
            self.quality_service = QualityAssessmentService()
        else:
            self.quality_service = QualityAssessmentService(
                high_threshold=quality_thresholds.get("high", 0.9),
                medium_threshold=quality_thresholds.get("medium", 0.7),
                min_quality_for_valid=quality_thresholds.get("min_valid", 0.5),
            )
        self.metadata_service = MetadataService()
        self.validation_service = ValidationService(security_level=str(security_level))

        # Initialize focused helper classes
        self._ingestion_ops = IngestionFacade(self.ingestion_service)
        self._format_ops = FormatDetectionFacade(self.format_service)
        self._quality_ops = QualityAssessmentFacade(self.quality_service)
        self._metadata_ops = MetadataFacade(self.metadata_service)
        self._preview_ops = PreviewOperations(
            self.format_service, self.quality_service, self.metadata_service
        )
        self._layer_ops = DataLayerOperations(
            self.bronze_layer, self.validation_service
        )
        self._integration_ops = IntegrationOperations(
            self.format_service,
            self.quality_service,
            self.metadata_service,
            self.layer_name,
        )
        self._security_ops = SecurityOperations(self.ingestion_service)

        logger.info(
            "Initialized RawDataProcessor with service composition (security=%s)",
            "enabled" if enable_security_gateway else "disabled",
        )

    # Data Ingestion Methods
    def ingest_file(self, file_path: str | Path) -> ProcessingResult:
        """Delegate to ingestion operations."""
        return self._ingestion_ops.ingest_file(file_path)

    def ingest_json_string(
        self, json_string: str, source_name: str = "string_input"
    ) -> ProcessingResult:
        """Delegate to ingestion operations."""
        return self._ingestion_ops.ingest_json_string(json_string, source_name)

    def ingest_data_dict(
        self, data: dict[str, Any], source_name: str = "dict_input"
    ) -> ProcessingResult:
        """Delegate to ingestion operations."""
        return self._ingestion_ops.ingest_data_dict(data, source_name)

    # Format Detection Methods
    def detect_format(self, data: dict[str, Any]) -> SupportedFormat:
        """Delegate to format detection operations."""
        return self._format_ops.detect_format(data)

    def get_format_confidence(
        self, data: dict[str, Any], target_format: SupportedFormat
    ) -> float:
        """Delegate to format detection operations."""
        return self._format_ops.get_format_confidence(data, target_format)

    # Quality Assessment Methods
    def validate_before_ingestion(self, data: dict[str, Any]) -> ValidationResult:
        """Delegate to quality assessment operations."""
        return self._quality_ops.validate_before_ingestion(data)

    def calculate_quality_metrics(self, data: Any) -> DataQualityMetrics:
        """Delegate to quality assessment operations."""
        return self._quality_ops.calculate_quality_metrics(data)

    def validate_bronze_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to quality assessment operations."""
        return self._quality_ops.validate_bronze_data(data)

    # Metadata Methods
    def get_record_metadata(self, record_id: str) -> RecordMetadata | None:
        """Delegate to metadata operations."""
        return self._metadata_ops.get_record_metadata(record_id)

    def get_record_lineage(self, record_id: str) -> DataLineage | None:
        """Delegate to metadata operations."""
        return self._metadata_ops.get_record_lineage(record_id)

    def get_lineage(self, data_id: str) -> LineageInfo:
        """Delegate to metadata operations."""
        return self._metadata_ops.get_lineage(data_id)

    # Preview Methods
    def preview_ingestion(self, file_path: str | Path) -> dict[str, Any]:
        """Delegate to preview operations."""
        return self._preview_ops.preview_ingestion(file_path)

    def preview_ingestion_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to preview operations."""
        return self._preview_ops.preview_ingestion_dict(data)

    # DataLayer Interface Methods
    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Delegate to data layer operations."""
        return self._layer_ops.ingest(data, metadata)

    def retrieve(self, query: LayerQuery) -> LayerData:
        """Delegate to data layer operations."""
        return self._layer_ops.retrieve(query)

    def validate(self, data: Any) -> ValidationResult:
        """Delegate to data layer operations."""
        return self._layer_ops.validate(data)

    def ingest_to_layer(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Delegate to data layer operations."""
        return self._layer_ops.ingest_to_layer(data, metadata)

    def retrieve_from_layer(self, query: LayerQuery) -> LayerData:
        """Delegate to data layer operations."""
        return self._layer_ops.retrieve_from_layer(query)

    def validate_layer_data(self, data: Any) -> ValidationResult:
        """Delegate to data layer operations."""
        return self._layer_ops.validate_layer_data(data)

    # Service Integration Methods
    def ingest_with_detection(
        self,
        data: dict[str, Any],
        source_info: dict[str, Any],
    ) -> BronzeRecord:
        """Delegate to integration operations."""
        return self._integration_ops.ingest_with_detection(data, source_info)

    def get_bronze_records(
        self,
        filter_criteria: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[BronzeRecord]:
        """Delegate to integration operations."""
        return self._integration_ops.get_bronze_records(filter_criteria, limit)

    # Security Management Methods
    def enable_security(
        self, security_level: SecurityLevel | str = SecurityLevel.STANDARD
    ) -> None:
        """Delegate to security operations."""
        self._security_ops.enable_security(security_level)

    def disable_security(self) -> None:
        """Delegate to security operations."""
        self._security_ops.disable_security()

    def _get_security_configuration(self) -> dict[str, Any]:
        """Delegate to security operations."""
        return self._security_ops.get_security_configuration()

    # Configuration Methods
    def configure_quality_thresholds(
        self,
        *,
        high: float | None = None,
        medium: float | None = None,
        min_valid: float | None = None,
    ) -> None:
        """Delegate to quality assessment operations."""
        self._quality_ops.configure_thresholds(
            high=high, medium=medium, min_valid=min_valid
        )
