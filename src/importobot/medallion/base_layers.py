"""Base implementations for Bronze, Silver, and Gold layers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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
from importobot.medallion.utils.query_filters import matches_query_filters
from importobot.utils.logging import setup_logger
from importobot.utils.string_cache import data_to_lower_cached
from importobot.utils.validation_models import (
    QualitySeverity,
    ValidationResult,
    create_basic_validation_result,
)

logger = setup_logger(__name__)


class BaseMedallionLayer(DataLayer):
    """Base implementation for all Medallion layers with common functionality."""

    def __init__(self, layer_name: str, storage_path: Optional[Path] = None) -> None:
        """Initialize the base layer.

        Args:
            layer_name: The name of this layer
            storage_path: Optional path for data storage
        """
        super().__init__(layer_name)
        self.storage_path = storage_path or Path(f"./medallion_data/{layer_name}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory storage for development/testing
        self._data_store: dict[str, dict[str, Any]] = {}
        self._metadata_store: dict[str, LayerMetadata] = {}
        self._lineage_store: dict[str, LineageInfo] = {}

        logger.info(
            "Initialized %s layer with storage at %s", layer_name, self.storage_path
        )

    def _generate_data_id(self, data: Any, metadata: LayerMetadata) -> str:
        """Generate a unique ID for data based on content and metadata."""
        content_str = json.dumps(data, sort_keys=True, default=str)
        hash_input = (
            f"{metadata.source_path}:{content_str}:{metadata.ingestion_timestamp}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash for data integrity verification."""
        content_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _detect_format_type(self, data: dict[str, Any]) -> SupportedFormat:
        """Detect the test format type from data structure."""
        if not isinstance(data, dict):
            return SupportedFormat.UNKNOWN

        # Check for Zephyr indicators
        if any(key in data for key in ["testCase", "execution", "cycle"]):
            return SupportedFormat.ZEPHYR

        # Check for TestLink indicators
        if any(key in data for key in ["testsuites", "testsuite", "testcase"]):
            return SupportedFormat.TESTLINK

        # Check for JIRA/Xray indicators
        data_str = data_to_lower_cached(data)
        if any(key in data for key in ["issues", "key", "fields"]) and (
            "xray" in data_str or "test" in data_str or "issuetype" in data_str
        ):
            return SupportedFormat.JIRA_XRAY

        # Check for TestRail indicators
        if any(
            key in data for key in ["runs", "tests", "cases"]
        ) and "testrail" in data_to_lower_cached(data):
            return SupportedFormat.TESTRAIL

        # Generic test structure detection
        if any(key in data for key in ["tests", "test_cases", "testcases"]):
            return SupportedFormat.GENERIC

        return SupportedFormat.UNKNOWN

    def _create_lineage(
        self,
        data_id: str,
        source_layer: str,
        target_layer: str,
        *,
        transformation_type: str,
        parent_ids: Optional[list[str]] = None,
    ) -> LineageInfo:
        """Create lineage information for data transformation."""
        return LineageInfo(
            data_id=data_id,
            source_layer=source_layer,
            target_layer=target_layer,
            transformation_type=transformation_type,
            transformation_timestamp=datetime.now(),
            parent_ids=parent_ids or [],
            child_ids=[],
        )

    def retrieve(self, query: LayerQuery) -> LayerData:
        """Retrieve data from this layer based on query."""
        start_time = datetime.now()

        # Normalize query input
        normalized_query = self._normalize_query(query)

        # Apply filtering
        filtered_records, filtered_metadata = self._filter_records(normalized_query)

        # Apply pagination
        final_records, final_metadata = self._apply_pagination(
            filtered_records, filtered_metadata, normalized_query
        )

        return LayerData(
            records=final_records,
            metadata=final_metadata,
            total_count=len(filtered_records),
            retrieved_count=len(final_records),
            query=normalized_query,
            retrieved_at=start_time,
        )

    def _normalize_query(self, query: LayerQuery) -> LayerQuery:
        """Normalize query input to LayerQuery object."""
        return query

    def _filter_records(self, query: LayerQuery) -> tuple[list, list]:
        """Apply filters to records based on query parameters."""
        filtered_records = []
        filtered_metadata = []

        for data_id, record in self._data_store.items():
            metadata = self._metadata_store.get(data_id)
            if not metadata:
                continue

            if self._record_matches_query(data_id, record, metadata, query):
                filtered_records.append(record)
                filtered_metadata.append(metadata)

        return filtered_records, filtered_metadata

    def _record_matches_query(
        self, data_id: str, record: dict, metadata: Any, query: LayerQuery
    ) -> bool:
        """Check if a record matches the query criteria."""
        # Use shared query filter logic
        if not matches_query_filters(data_id, metadata, query):
            return False

        # Apply custom filters
        if query.filters:
            for filter_key, filter_value in query.filters.items():
                if filter_key in record and record[filter_key] != filter_value:
                    return False

        return True

    def _apply_pagination(
        self, records: list, metadata: list, query: LayerQuery
    ) -> tuple[list, list]:
        """Apply pagination to filtered results."""
        start_idx = query.offset
        end_idx = start_idx + query.limit if query.limit else len(records)

        return records[start_idx:end_idx], metadata[start_idx:end_idx]

    def get_lineage(self, data_id: str) -> LineageInfo:
        """Get lineage information for a specific data item."""
        lineage = self._lineage_store.get(data_id)
        if not lineage:
            raise ValueError(f"No lineage found for data ID: {data_id}")
        return lineage

    def calculate_quality_metrics(self, data: Any) -> DataQualityMetrics:
        """Calculate basic quality metrics for the provided data."""
        start_time = datetime.now()

        if not isinstance(data, dict):
            return DataQualityMetrics(
                overall_score=0.0,
                quality_issues=["Data is not a dictionary structure"],
                validation_errors=1,
                calculated_at=start_time,
            )

        # Basic quality calculations
        total_fields = len(data)
        populated_fields = sum(1 for v in data.values() if v is not None and v != "")
        completeness_score = (
            (populated_fields / total_fields * 100) if total_fields > 0 else 0
        )

        # Simple validity check
        validity_score = 100.0  # Assume valid if it's a dict

        # Basic consistency check (non-empty strings, proper types)
        consistent_fields = 0
        for value in data.values():
            if isinstance(value, (str, int, float, bool, list, dict)) and value != "":
                consistent_fields += 1
        consistency_score = (
            (consistent_fields / total_fields * 100) if total_fields > 0 else 0
        )

        # Overall score as weighted average
        overall_score = (
            completeness_score * 0.4 + validity_score * 0.3 + consistency_score * 0.3
        )

        end_time = datetime.now()
        calculation_duration = (end_time - start_time).total_seconds() * 1000

        return DataQualityMetrics(
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            validity_score=validity_score,
            overall_score=overall_score,
            calculated_at=start_time,
            calculation_duration_ms=calculation_duration,
        )


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
                status=ProcessingStatus.COMPLETED
                if validation_result.is_valid
                else ProcessingStatus.FAILED,
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
                errors=validation_result.issues
                if not validation_result.is_valid
                else [],
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


class SilverLayer(BaseMedallionLayer):
    """Silver layer for curated and standardized data."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        """Initialize the Silver layer."""
        super().__init__("silver", storage_path)

    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Ingest and standardize data into the Silver layer."""
        # Placeholder implementation - will be completed in MR2
        start_time = datetime.now()

        return ProcessingResult(
            status=ProcessingStatus.PENDING,
            processed_count=0,
            success_count=0,
            error_count=0,
            warning_count=0,
            skipped_count=1,
            processing_time_ms=0.0,
            start_timestamp=start_time,
            metadata=metadata,
            quality_metrics=DataQualityMetrics(),
            errors=["Silver layer implementation pending MR2"],
        )

    def validate(self, data: Any) -> ValidationResult:
        """Validate data for Silver layer processing."""
        return ValidationResult(
            is_valid=False,
            severity=QualitySeverity.INFO,
            error_count=0,
            warning_count=1,
            issues=["Silver layer validation pending MR2"],
        )


class GoldLayer(BaseMedallionLayer):
    """Gold layer for consumption-ready, optimized data."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        """Initialize the Gold layer."""
        super().__init__("gold", storage_path)

    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Ingest and optimize data into the Gold layer."""
        # Placeholder implementation - will be completed in MR3
        start_time = datetime.now()

        return ProcessingResult(
            status=ProcessingStatus.PENDING,
            processed_count=0,
            success_count=0,
            error_count=0,
            warning_count=0,
            skipped_count=1,
            processing_time_ms=0.0,
            start_timestamp=start_time,
            metadata=metadata,
            quality_metrics=DataQualityMetrics(),
            errors=["Gold layer implementation pending MR3"],
        )

    def validate(self, data: Any) -> ValidationResult:
        """Validate data for Gold layer processing."""
        return ValidationResult(
            is_valid=False,
            severity=QualitySeverity.INFO,
            error_count=0,
            warning_count=1,
            issues=["Gold layer validation pending MR3"],
        )
