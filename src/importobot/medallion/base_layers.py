"""Base implementations for Bronze, Silver, and Gold layers."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

from importobot.medallion.interfaces.base_interfaces import DataLayer
from importobot.medallion.interfaces.data_models import (
    DataQualityMetrics,
    LayerData,
    LayerMetadata,
    LayerQuery,
    LineageInfo,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.medallion.utils.query_filters import matches_query_filters
from importobot.utils.logging import get_logger

logger = get_logger()

if TYPE_CHECKING:
    from importobot.medallion.bronze.format_detector import FormatDetector


class BaseMedallionLayer(DataLayer):
    """Base implementation for all Medallion layers with common functionality."""

    def __init__(self, layer_name: str, storage_path: Path | None = None) -> None:
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
        self._format_detector: FormatDetector | None = None

        logger.debug(
            "Initialized %s layer with storage at %s", layer_name, self.storage_path
        )

    def _serialize_data(self, data: Any) -> str:
        """Serialize data to a canonical JSON string for hashing operations."""

        def _default(obj: Any) -> Any:
            if isinstance(obj, datetime | date):
                logger.debug(
                    "Serializing %s via ISO-8601 in %s layer",
                    type(obj).__name__,
                    self.layer_name,
                )
                return obj.isoformat()
            if isinstance(obj, Path):
                logger.debug("Serializing Path '%s' in %s layer", obj, self.layer_name)
                return str(obj)

            logger.warning(
                "Falling back to string serialization for %s in %s layer",
                type(obj).__name__,
                self.layer_name,
            )
            try:
                return str(obj)
            except Exception:  # pragma: no cover - extreme edge case
                return repr(obj)

        return json.dumps(data, sort_keys=True, default=_default)

    def _generate_data_id(
        self,
        data: Any,
        metadata: LayerMetadata,
        *,
        serialized_data: str | None = None,
    ) -> str:
        """Generate a unique ID for data based on content and metadata."""
        content_str = serialized_data or self._serialize_data(data)
        hash_input = (
            f"{metadata.source_path}:{content_str}:{metadata.ingestion_timestamp}"
        )
        # Use Blake2b for faster hashing on large content dumps
        return hashlib.blake2b(hash_input.encode(), digest_size=8).hexdigest()

    def _calculate_data_hash(
        self, data: Any, *, serialized_data: str | None = None
    ) -> str:
        """Calculate hash for data integrity verification."""
        content_str = serialized_data or self._serialize_data(data)
        # Use Blake2b for faster data integrity hashing
        return hashlib.blake2b(content_str.encode()).hexdigest()

    def _detect_format_type(self, data: dict[str, Any]) -> SupportedFormat:
        """Detect the test format type from data structure."""
        if not isinstance(data, dict):
            return SupportedFormat.UNKNOWN

        detector = self._get_format_detector()
        return detector.detect_format(data)

    def _get_format_detector(self) -> FormatDetector:
        if self._format_detector is None:
            module = import_module("importobot.medallion.bronze.format_detector")
            FormatDetectorCls: type[FormatDetector] = module.FormatDetector
            self._format_detector = FormatDetectorCls()
        return self._format_detector

    def _create_lineage(
        self,
        data_id: str,
        source_layer: str,
        target_layer: str,
        *,
        transformation_type: str,
        parent_ids: list[str] | None = None,
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

        # Apply filtering
        filtered_records, filtered_metadata = self._filter_records(query)

        # Apply pagination
        final_records, final_metadata = self._apply_pagination(
            filtered_records, filtered_metadata, query
        )

        return LayerData(
            records=final_records,
            metadata=final_metadata,
            total_count=len(filtered_records),
            retrieved_count=len(final_records),
            query=query,
            retrieved_at=start_time,
        )

    def _filter_records(self, query: LayerQuery) -> tuple[list[Any], list[Any]]:
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
        self, data_id: str, record: dict[str, Any], metadata: Any, query: LayerQuery
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
        self, records: list[Any], metadata: list[Any], query: LayerQuery
    ) -> tuple[list[Any], list[Any]]:
        """Apply pagination to filtered results."""
        start_idx = query.offset
        end_idx = start_idx + query.limit if query.limit is not None else len(records)

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
            if (
                isinstance(value, str | int | float | bool | list | dict)
                and value != ""
            ):
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
