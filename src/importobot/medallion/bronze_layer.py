"""Bronze layer implementation for raw data ingestion with minimal processing."""

from __future__ import annotations

import contextlib
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import islice
from pathlib import Path
from typing import Any, ClassVar

from importobot.config import (
    BRONZE_LAYER_IN_MEMORY_TTL_SECONDS,
    BRONZE_LAYER_MAX_IN_MEMORY_RECORDS,
)
from importobot.medallion.base_layers import BaseMedallionLayer
from importobot.medallion.interfaces.data_models import (
    DataLineage,
    DataQualityMetrics,
    FormatDetectionResult,
    LayerMetadata,
    LayerQuery,
    LineageInfo,
    ProcessingResult,
)
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.interfaces.records import BronzeRecord, RecordMetadata
from importobot.medallion.storage.base import StorageBackend
from importobot.utils.logging import get_logger
from importobot.utils.string_cache import data_to_lower_cached
from importobot.utils.validation_models import (
    QualitySeverity,
    ValidationResult,
    create_basic_validation_result,
)

logger = get_logger()


@dataclass(slots=True)
class _FilterContext:
    """Container for record attributes used during filter evaluation."""

    record_id: str
    data: dict[str, Any]
    metadata: LayerMetadata
    lineage_info: LineageInfo | None


class BronzeLayer(BaseMedallionLayer):
    """Bronze layer for raw data ingestion with minimal processing."""

    _FILTER_DISPATCH_MAP: ClassVar[dict[str, str]] = {
        "record_id": "_filter_record_id",
        "format_type": "_filter_format_type",
        "source_path": "_filter_source_path",
        "layer_name": "_filter_layer_name",
        "ingestion_timestamp_before": "_filter_ingestion_before",
        "ingestion_timestamp_after": "_filter_ingestion_after",
    }

    def __init__(
        self,
        storage_path: Path | None = None,
        storage_backend: StorageBackend | None = None,
        *,
        max_in_memory_records: int | None = None,
        in_memory_ttl_seconds: int | None = None,
    ) -> None:
        """Initialize the Bronze layer.

        Args:
            storage_path: Optional path for data storage
            storage_backend: Optional storage backend for persistent storage
            max_in_memory_records: Cap for in-memory retained records
            in_memory_ttl_seconds: Optional TTL before records expire in memory
        """
        super().__init__("bronze", storage_path)
        self.storage_backend = storage_backend
        resolved_max = (
            max_in_memory_records
            if max_in_memory_records is not None
            else BRONZE_LAYER_MAX_IN_MEMORY_RECORDS
        )
        if resolved_max < 1:
            logger.warning(
                "BronzeLayer max_in_memory_records %d must be >= 1; using default %d",
                resolved_max,
                BRONZE_LAYER_MAX_IN_MEMORY_RECORDS,
            )
            resolved_max = BRONZE_LAYER_MAX_IN_MEMORY_RECORDS
        self._max_in_memory_records = resolved_max
        resolved_ttl = (
            in_memory_ttl_seconds
            if in_memory_ttl_seconds is not None
            else BRONZE_LAYER_IN_MEMORY_TTL_SECONDS
        )
        self._in_memory_ttl_seconds: int | None = (
            resolved_ttl if resolved_ttl > 0 else None
        )
        self._ingestion_order: deque[str] = deque()
        self._in_memory_timestamps: dict[str, datetime] = {}
        self._record_cache: dict[str, BronzeRecord] = {}

    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Ingest raw data into the Bronze layer."""
        start_time = datetime.now()
        self._purge_expired_records(start_time)

        try:
            # Serialize once for downstream hashing to avoid repeated JSON dumps
            serialized_data = self._serialize_data(data)

            # Generate unique ID for this data
            data_id = self._generate_data_id(
                data, metadata, serialized_data=serialized_data
            )

            # Update metadata with processing information
            metadata.data_hash = self._calculate_data_hash(
                data, serialized_data=serialized_data
            )
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

            # Remove any stale copy before inserting the fresh record
            self._evict_record(data_id, reason="duplicate_ingest_replace")

            # Store data and metadata in memory
            self._data_store[data_id] = data
            self._metadata_store[data_id] = metadata
            self._lineage_store[data_id] = lineage
            self._register_in_memory_record(data_id, start_time)
            self._enforce_in_memory_capacity()
            self._cache_bronze_record(data_id)

            # Store in persistent storage backend if available
            if self.storage_backend:
                try:
                    self.storage_backend.store_data(
                        self.layer_name, data_id, data, metadata
                    )
                except Exception as storage_error:
                    logger.warning(
                        "Failed to store data in storage backend: %s",
                        str(storage_error),
                    )
                    # Continue processing - in-memory storage is still available

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

    def _register_in_memory_record(self, data_id: str, ingested_at: datetime) -> None:
        """Track a record's ingestion order for eviction bookkeeping."""
        self._in_memory_timestamps[data_id] = ingested_at
        self._ingestion_order.append(data_id)

    def _enforce_in_memory_capacity(self) -> None:
        """Ensure the in-memory store respects the configured capacity."""
        while len(self._ingestion_order) > self._max_in_memory_records:
            oldest_id = self._ingestion_order[0]
            self._evict_record(oldest_id, reason="capacity_limit")

    def _purge_expired_records(self, reference_time: datetime) -> None:
        """Evict records older than the configured TTL."""
        if self._in_memory_ttl_seconds is None:
            return
        ttl_delta = timedelta(seconds=self._in_memory_ttl_seconds)
        while self._ingestion_order:
            oldest_id = self._ingestion_order[0]
            ingested_at = self._in_memory_timestamps.get(oldest_id)
            if ingested_at is None:
                self._ingestion_order.popleft()
                continue
            if reference_time - ingested_at <= ttl_delta:
                break
            self._evict_record(oldest_id, reason="ttl_expired")

    def _evict_record(self, data_id: str, reason: str) -> None:
        """Evict a single record from the in-memory caches."""
        was_present = data_id in self._data_store
        if was_present:
            self._data_store.pop(data_id, None)
        self._metadata_store.pop(data_id, None)
        self._lineage_store.pop(data_id, None)
        self._in_memory_timestamps.pop(data_id, None)
        self._record_cache.pop(data_id, None)
        if self._ingestion_order and self._ingestion_order[0] == data_id:
            self._ingestion_order.popleft()
        else:
            with contextlib.suppress(ValueError):
                self._ingestion_order.remove(data_id)
        if was_present:
            logger.debug(
                "Evicted BronzeLayer record %s from in-memory store (%s).",
                data_id,
                reason,
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

        if not data:
            return BronzeRecord(
                data={},
                metadata=record_metadata,
                format_detection=format_detection,
                lineage=lineage,
            )

        return BronzeRecord(
            data=data,
            metadata=record_metadata,
            format_detection=format_detection,
            lineage=lineage,
        )

    def get_record_metadata(self, record_id: str) -> RecordMetadata | None:
        """Retrieve enhanced metadata for a specific record.

        Args:
            record_id: The unique identifier for the record

        Returns:
            Record metadata if found, None otherwise
        """
        layer_metadata = self._metadata_store.get(record_id)
        if not layer_metadata:
            return None

        processing_status = (
            ProcessingStatus.COMPLETED
            if layer_metadata.processing_timestamp is not None
            else ProcessingStatus.PENDING
        )

        custom_attributes = dict(layer_metadata.custom_metadata)
        quality_checks: dict[str, Any] = {}
        if layer_metadata.record_count:
            quality_checks["record_count"] = layer_metadata.record_count
        if layer_metadata.processing_duration_ms:
            quality_checks["processing_duration_ms"] = (
                layer_metadata.processing_duration_ms
            )

        return RecordMetadata(
            record_id=record_id,
            ingestion_timestamp=layer_metadata.ingestion_timestamp,
            processing_status=processing_status,
            processing_duration_ms=(
                int(layer_metadata.processing_duration_ms)
                if layer_metadata.processing_duration_ms
                else None
            ),
            source_system=str(layer_metadata.source_path),
            source_file_size=(
                layer_metadata.file_size_bytes
                if layer_metadata.file_size_bytes > 0
                else None
            ),
            source_checksum=layer_metadata.data_hash or None,
            quality_checks=quality_checks,
            custom_attributes=custom_attributes,
        )

    def get_record_lineage(self, record_id: str) -> DataLineage | None:
        """Retrieve comprehensive lineage information for a specific record.

        Args:
            record_id: The unique identifier for the record

        Returns:
            Data lineage if found, None otherwise
        """
        lineage_info = self._lineage_store.get(record_id)
        if not lineage_info:
            return None

        layer_metadata = self._metadata_store.get(record_id)
        source_location = (
            str(layer_metadata.source_path)
            if layer_metadata
            else lineage_info.source_layer
        )

        transformation_entry = {
            "transformation_type": lineage_info.transformation_type,
            "source_layer": lineage_info.source_layer,
            "target_layer": lineage_info.target_layer,
            "timestamp": lineage_info.transformation_timestamp,
        }
        if lineage_info.transformation_details:
            transformation_entry["details"] = dict(lineage_info.transformation_details)

        return DataLineage(
            source_id=record_id,
            source_type=lineage_info.source_layer,
            source_location=source_location,
            transformation_history=[transformation_entry],
            parent_records=list(lineage_info.parent_ids),
            child_records=list(lineage_info.child_ids),
            created_timestamp=lineage_info.transformation_timestamp,
        )

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
        filter_criteria: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[BronzeRecord]:
        """Retrieve Bronze records based on filter criteria.

        Args:
            filter_criteria: Optional filtering criteria
            limit: Optional limit on number of records

        Returns:
            List of Bronze records matching the criteria
        """
        if limit is not None and limit <= 0:
            return []

        effective_limit = limit if limit is not None else 1000
        records = self._collect_in_memory_records(
            filter_criteria, effective_limit=effective_limit
        )
        if records:
            logger.debug(
                "Retrieved %d bronze records from in-memory store", len(records)
            )
            return records

        if not self.storage_backend:
            return records

        try:
            storage_records = self._collect_persisted_records(
                filter_criteria, effective_limit=effective_limit
            )
        except Exception as error:  # pragma: no cover - defensive guard
            logger.error("Failed to retrieve bronze records: %s", str(error))
            return []

        records.extend(storage_records)
        return records

    def _collect_in_memory_records(
        self,
        filter_criteria: dict[str, Any] | None,
        *,
        effective_limit: int,
    ) -> list[BronzeRecord]:
        """Gather Bronze records from the in-memory store."""
        records: list[BronzeRecord] = []

        if not filter_criteria:
            source_iter: Iterable[tuple[str, dict[str, Any]]] = islice(
                self._data_store.items(), 0, effective_limit
            )
        else:
            source_iter = self._data_store.items()

        for record_id, data in source_iter:
            layer_metadata = self._metadata_store.get(record_id)
            lineage_info = self._lineage_store.get(record_id)

            if not layer_metadata:
                continue

            context = _FilterContext(
                record_id=record_id,
                data=data,
                metadata=layer_metadata,
                lineage_info=lineage_info,
            )

            if filter_criteria and not self._matches_filter(context, filter_criteria):
                continue

            record_metadata = self.get_record_metadata(record_id)
            if not record_metadata:
                continue

            cached_record = self._resolve_cached_record(record_id)
            if cached_record is None:
                continue

            records.append(cached_record)

            if filter_criteria and len(records) >= effective_limit:
                break

        return records

    def _collect_persisted_records(
        self,
        filter_criteria: dict[str, Any] | None,
        *,
        effective_limit: int,
    ) -> list[BronzeRecord]:
        """Gather Bronze records from the persistent storage backend."""
        if not self.storage_backend:
            return []

        query = LayerQuery(
            layer_name=self.layer_name,
            filters=filter_criteria or {},
            limit=effective_limit,
            offset=0,
        )
        layer_data = self.storage_backend.query_data(self.layer_name, query)

        records: list[BronzeRecord] = []
        for data, metadata in zip(
            layer_data.records,
            layer_data.metadata,
            strict=False,
        ):
            record_id = self._generate_data_id(data, metadata, serialized_data=None)

            context = _FilterContext(
                record_id=record_id,
                data=data,
                metadata=metadata,
                lineage_info=None,
            )

            if filter_criteria and not self._matches_filter(context, filter_criteria):
                continue

            record_metadata = RecordMetadata(
                record_id=record_id,
                ingestion_timestamp=metadata.ingestion_timestamp,
                processing_status=(
                    ProcessingStatus.COMPLETED
                    if metadata.processing_timestamp
                    else ProcessingStatus.PENDING
                ),
                source_system=str(metadata.source_path),
                source_file_size=(
                    metadata.file_size_bytes if metadata.file_size_bytes > 0 else None
                ),
                custom_attributes=dict(metadata.custom_metadata),
            )

            records.append(
                self._build_bronze_record(
                    data=data,
                    record_metadata=record_metadata,
                    format_detection=self._create_format_detection(
                        metadata.format_type,
                        method="storage_query",
                        record_id=None,
                    ),
                    lineage=self._resolve_lineage(
                        None,
                        record_id=record_id,
                        source_path=metadata.source_path,
                    ),
                )
            )

            if len(records) >= effective_limit:
                break

        return records

    def _create_format_detection(
        self,
        format_type: Any,
        *,
        method: str,
        record_id: str | None,
    ) -> FormatDetectionResult:
        """Create format detection metadata with consistent evidence details."""
        evidence_details: dict[str, Any] = {
            "source": "bronze_layer",
            "method": method,
        }
        if record_id is not None:
            evidence_details["record_id"] = record_id

        return FormatDetectionResult(
            detected_format=format_type,
            confidence_score=0.8,
            evidence_details=evidence_details,
        )

    def _resolve_lineage(
        self,
        lineage: DataLineage | None,
        *,
        record_id: str,
        source_path: Path | str | None,
    ) -> DataLineage:
        """Return existing lineage or construct a default lineage entry."""
        if lineage is not None:
            return lineage

        return DataLineage(
            source_id=record_id,
            source_type=self.layer_name,
            source_location=str(source_path),
        )

    def _build_bronze_record(
        self,
        *,
        data: Any,
        record_metadata: RecordMetadata,
        format_detection: FormatDetectionResult,
        lineage: DataLineage,
    ) -> BronzeRecord:
        """Create a BronzeRecord instance with the provided metadata."""
        return BronzeRecord(
            data=data,
            metadata=record_metadata,
            format_detection=format_detection,
            lineage=lineage,
        )

    def _cache_bronze_record(self, record_id: str) -> None:
        """Cache immutable BronzeRecord for fast retrieval."""
        self._resolve_cached_record(record_id)

    def _resolve_cached_record(self, record_id: str) -> BronzeRecord | None:
        """Return a cached BronzeRecord, constructing it if absent."""
        cached = self._record_cache.get(record_id)
        if cached is not None:
            return cached

        data = self._data_store.get(record_id)
        metadata = self._metadata_store.get(record_id)
        if data is None or metadata is None:
            return None

        record_metadata = self.get_record_metadata(record_id)
        if record_metadata is None:
            return None

        lineage = self.get_record_lineage(record_id) or self._resolve_lineage(
            None,
            record_id=record_id,
            source_path=metadata.source_path,
        )

        cached_record = self._build_bronze_record(
            data=data,
            record_metadata=record_metadata,
            format_detection=self._create_format_detection(
                metadata.format_type,
                method="metadata_analysis",
                record_id=record_id,
            ),
            lineage=lineage,
        )
        self._record_cache[record_id] = cached_record
        return cached_record

    def _matches_filter(
        self,
        context: _FilterContext,
        filter_criteria: dict[str, Any],
    ) -> bool:
        """Check if a record matches provided filter criteria."""
        for key, expected in filter_criteria.items():
            dispatch_match = self._match_via_dispatch(
                key,
                expected,
                record_id=context.record_id,
                data=context.data,
                metadata=context.metadata,
                lineage=context.lineage_info,
            )
            if dispatch_match is not None:
                if dispatch_match:
                    continue
                return False

            custom_metadata_match = self._match_custom_metadata_filter(
                key, expected, context.metadata
            )
            if custom_metadata_match is not None:
                if custom_metadata_match:
                    continue
                return False

            lineage_match = self._match_lineage_filter(
                key, expected, context.lineage_info
            )
            if lineage_match is not None:
                if lineage_match:
                    continue
                return False

            data_match = self._match_data_filter(key, expected, context.data)
            if data_match is not None:
                if data_match:
                    continue
                return False

            return False

        return True

    def _match_via_dispatch(
        self,
        key: str,
        expected: Any,
        *,
        record_id: str,
        data: dict[str, Any],
        metadata: LayerMetadata,
        lineage: LineageInfo | None,
    ) -> bool | None:
        """Handle filters with dedicated dispatch handlers."""
        handler_name = self._FILTER_DISPATCH_MAP.get(key)
        if handler_name is None:
            return None
        handler = getattr(self, handler_name, None)
        if handler is None:
            return None
        result = handler(
            expected,
            record_id=record_id,
            data=data,
            metadata=metadata,
            lineage=lineage,
        )

        # Explicitly type cast the result to satisfy mypy
        return bool(result) if result is not None else None

    @staticmethod
    def _match_custom_metadata_filter(
        key: str,
        expected: Any,
        metadata: LayerMetadata,
    ) -> bool | None:
        """Handle custom metadata filters."""
        if not key.startswith("custom_metadata."):
            return None
        _, _, meta_key = key.partition(".")
        return bool(metadata.custom_metadata.get(meta_key) == expected)

    @staticmethod
    def _match_lineage_filter(
        key: str,
        expected: Any,
        lineage: LineageInfo | None,
    ) -> bool | None:
        """Handle lineage-based filters."""
        if key != "parent_record" or lineage is None:
            return None
        return expected in getattr(lineage, "parent_ids", [])

    def _match_data_filter(
        self,
        key: str,
        expected: Any,
        data: dict[str, Any],
    ) -> bool | None:
        """Handle direct data and nested structure filters."""
        if isinstance(data, dict) and key in data:
            return bool(data[key] == expected)

        nested_value = self._extract_nested_value(data, key)
        if nested_value is None:
            return None
        return bool(nested_value == expected)

    @staticmethod
    def _extract_nested_value(data: dict[str, Any], key_path: str) -> Any | None:
        """Extract nested value from data using dot notation."""
        current = data
        for part in key_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse incoming filter values into datetime for comparisons."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _filter_record_id(
        self,
        expected: Any,
        *,
        record_id: str,
        **_: Any,
    ) -> bool:
        return bool(record_id == expected)

    def _filter_format_type(
        self,
        expected: Any,
        *,
        metadata: LayerMetadata,
        **_: Any,
    ) -> bool:
        format_value = (
            metadata.format_type.value
            if isinstance(metadata.format_type, SupportedFormat)
            else str(metadata.format_type)
        )
        return str(expected).lower() == format_value.lower()

    def _filter_source_path(
        self,
        expected: Any,
        *,
        metadata: LayerMetadata,
        **_: Any,
    ) -> bool:
        return str(metadata.source_path) == str(expected)

    def _filter_layer_name(
        self,
        expected: Any,
        *,
        metadata: LayerMetadata,
        **_: Any,
    ) -> bool:
        return bool(metadata.layer_name == expected)

    def _filter_ingestion_before(
        self,
        expected: Any,
        *,
        metadata: LayerMetadata,
        **_: Any,
    ) -> bool:
        expected_dt = self._parse_datetime(expected)
        if not expected_dt:
            return True
        return metadata.ingestion_timestamp < expected_dt

    def _filter_ingestion_after(
        self,
        expected: Any,
        *,
        metadata: LayerMetadata,
        **_: Any,
    ) -> bool:
        expected_dt = self._parse_datetime(expected)
        if not expected_dt:
            return True
        return metadata.ingestion_timestamp > expected_dt


__all__ = ["BronzeLayer"]
