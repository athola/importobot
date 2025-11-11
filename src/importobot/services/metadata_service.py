"""Metadata service extracted from RawDataProcessor.

Handles metadata creation, lineage tracking, and record management.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from importobot.medallion.interfaces.data_models import (
    DataLineage,
    LayerMetadata,
    LineageInfo,
)
from importobot.medallion.interfaces.records import RecordMetadata
from importobot.utils.data_analysis import count_data_elements, get_data_types
from importobot.utils.logging import get_logger
from importobot.utils.validation_models import calculate_nesting_depth

logger = get_logger()


class MetadataService:
    """Service for managing metadata, lineage, and record tracking."""

    def __init__(self) -> None:
        """Initialize metadata service."""
        self._metadata_store: dict[str, RecordMetadata] = {}
        self._lineage_store: dict[str, DataLineage] = {}

    def create_metadata(self, source_path: Path, data: dict[str, Any]) -> LayerMetadata:
        """Create metadata for ingested data.

        Args:
            source_path: Path to the data source
            data: The data being processed

        Returns:
            LayerMetadata with information about the data
        """
        return LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
            record_count=count_data_elements(data),
        )

    def get_record_metadata(self, record_id: str) -> RecordMetadata | None:
        """Retrieve metadata for a specific record.

        Args:
            record_id: Unique identifier for the record

        Returns:
            RecordMetadata if found, None otherwise
        """
        return self._metadata_store.get(record_id)

    def store_record_metadata(self, record_id: str, metadata: RecordMetadata) -> None:
        """Store metadata for a record.

        Args:
            record_id: Unique identifier for the record
            metadata: Metadata to store
        """
        self._metadata_store[record_id] = metadata
        logger.debug("Stored metadata for record %s", record_id)

    def get_record_lineage(self, record_id: str) -> DataLineage | None:
        """Retrieve lineage information for a specific record.

        Args:
            record_id: Unique identifier for the record

        Returns:
            DataLineage if found, None otherwise
        """
        return self._lineage_store.get(record_id)

    def create_lineage_info(self, data_id: str) -> LineageInfo:
        """Create lineage information for data processing.

        Args:
            data_id: Unique identifier for the data

        Returns:
            LineageInfo tracking the data processing history
        """
        return LineageInfo(
            data_id=data_id,
            source_layer="raw",
            target_layer="bronze",
            transformation_type="ingestion",
            transformation_timestamp=datetime.now(),
            transformation_details={
                "step": "ingestion",
                "processor": "RawDataProcessor",
                "source_system": "bronze_layer",
            },
        )

    def store_record_lineage(self, record_id: str, lineage: DataLineage) -> None:
        """Store lineage information for a record.

        Args:
            record_id: Unique identifier for the record
            lineage: Lineage information to store
        """
        self._lineage_store[record_id] = lineage
        logger.debug("Stored lineage for record %s", record_id)

    def calculate_preview_stats(self, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate preview statistics for data.

        Args:
            data: Data to generate preview statistics for

        Returns:
            Dictionary containing preview statistics
        """
        return {
            "total_keys": len(data) if isinstance(data, dict) else 0,
            "data_types": get_data_types(data),
            "max_depth": calculate_nesting_depth(data, 0, 20),
            "sample_keys": list(data.keys())[:10] if isinstance(data, dict) else [],
        }
