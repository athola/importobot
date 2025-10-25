"""Abstract base interfaces for Medallion architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from importobot.utils.validation_models import ValidationResult

from .data_models import (
    DataLineage,
    DataQualityMetrics,
    LayerData,
    LayerMetadata,
    LayerQuery,
    LineageInfo,
    ProcessingResult,
)
from .records import BronzeRecord, RecordMetadata


class StorageBackend(ABC):
    """Abstract storage backend for medallion layer data persistence with versioning."""

    @abstractmethod
    def store(self, record: BronzeRecord) -> str:
        """Store a Bronze record and return storage location."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def retrieve(
        self, record_id: str, version: str | None = None
    ) -> BronzeRecord | None:
        """Retrieve a Bronze record by ID and optional version."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def list_versions(self, record_id: str) -> list[str]:
        """List all available versions for a record."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def delete(self, record_id: str, version: str | None = None) -> bool:
        """Delete a record or specific version."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def exists(self, record_id: str, version: str | None = None) -> bool:
        """Check if a record or version exists."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def get_metadata_index(self) -> dict[str, Any]:
        """Get metadata index for all stored records."""
        pass  # pylint: disable=unnecessary-pass


class DataLayer(ABC):
    """Abstract base class for all Medallion architecture layers."""

    def __init__(self, layer_name: str) -> None:
        """Initialize the data layer.

        Args:
            layer_name: The name of this layer (bronze, silver, gold)
        """
        self.layer_name = layer_name

    @abstractmethod
    def ingest(self, data: Any, metadata: LayerMetadata) -> ProcessingResult:
        """Ingest data into this layer.

        Args:
            data: The data to ingest
            metadata: Associated metadata for tracking

        Returns:
            Processing result with status and metrics
        """

    @abstractmethod
    def retrieve(self, query: LayerQuery) -> LayerData:
        """Retrieve data from this layer.

        Args:
            query: Query specification for data retrieval

        Returns:
            Retrieved data with metadata
        """

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Validate data according to layer-specific rules.

        Args:
            data: The data to validate

        Returns:
            Validation result with issues and metrics
        """

    @abstractmethod
    def get_lineage(self, data_id: str) -> LineageInfo:
        """Get lineage information for a specific data item.

        Args:
            data_id: The unique identifier for the data item

        Returns:
            Lineage information tracking data transformations
        """

    @abstractmethod
    def calculate_quality_metrics(self, data: Any) -> DataQualityMetrics:
        """Calculate quality metrics for the provided data.

        Args:
            data: The data to analyze

        Returns:
            Quality metrics with scores and issue details
        """

    def get_layer_name(self) -> str:
        """Get the name of this layer."""
        return self.layer_name

    # Enhanced methods for Bronze layer integration
    @abstractmethod
    def ingest_with_detection(
        self, data: dict[str, Any], source_info: dict[str, Any]
    ) -> BronzeRecord:
        """Ingest data with format detection and create BronzeRecord."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def get_record_metadata(self, record_id: str) -> RecordMetadata | None:
        """Retrieve enhanced metadata for a specific record."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def get_record_lineage(self, record_id: str) -> DataLineage | None:
        """Retrieve comprehensive lineage information for a specific record."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def validate_bronze_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate raw data quality and return quality metrics."""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def get_bronze_records(
        self,
        filter_criteria: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[BronzeRecord]:
        """Retrieve Bronze records based on filter criteria."""
        pass  # pylint: disable=unnecessary-pass

    def get_quality_summary(self) -> dict[str, Any]:
        """Get overall data quality summary for the layer."""
        return {
            "total_records": 0,
            "quality_distribution": {},
            "average_quality_score": 0.0,
            "format_distribution": {},
            "last_updated": datetime.now().isoformat(),
        }
