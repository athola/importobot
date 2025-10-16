"""Base storage interface for Medallion architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from importobot.medallion.interfaces.data_models import (
    LayerData,
    LayerMetadata,
    LayerQuery,
)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the storage backend.

        Args:
            config: Storage configuration parameters
        """
        self.config = config

    @abstractmethod
    def store_data(
        self,
        layer_name: str,
        data_id: str,
        data: dict[str, Any],
        metadata: LayerMetadata,
    ) -> bool:
        """Store data in the specified layer.

        Args:
            layer_name: Name of the layer (bronze, silver, gold)
            data_id: Unique identifier for the data
            data: The data to store
            metadata: Associated metadata

        Returns:
            True if storage was successful, False otherwise
        """

    @abstractmethod
    def retrieve_data(
        self, layer_name: str, data_id: str
    ) -> tuple[dict[str, Any], LayerMetadata] | None:
        """Retrieve specific data from the layer.

        Args:
            layer_name: Name of the layer
            data_id: Unique identifier for the data

        Returns:
            Tuple of (data, metadata) if found, None otherwise
        """

    @abstractmethod
    def query_data(self, layer_name: str, query: LayerQuery) -> LayerData:
        """Query data from the layer based on criteria.

        Args:
            layer_name: Name of the layer
            query: Query specification

        Returns:
            LayerData with matching records
        """

    @abstractmethod
    def delete_data(self, layer_name: str, data_id: str) -> bool:
        """Delete data from the layer.

        Args:
            layer_name: Name of the layer
            data_id: Unique identifier for the data

        Returns:
            True if deletion was successful, False otherwise
        """

    @abstractmethod
    def list_data_ids(self, layer_name: str) -> list[str]:
        """List all data IDs in the specified layer.

        Args:
            layer_name: Name of the layer

        Returns:
            List of data IDs
        """

    @abstractmethod
    def get_storage_info(self) -> dict[str, Any]:
        """Get information about the storage backend.

        Returns:
            Dictionary with storage backend information
        """

    @abstractmethod
    def cleanup_old_data(self, layer_name: str, retention_days: int) -> int:
        """Clean up old data based on retention policy.

        Args:
            layer_name: Name of the layer
            retention_days: Number of days to retain data

        Returns:
            Number of items cleaned up
        """

    @abstractmethod
    def backup_layer(self, layer_name: str, backup_path: Path) -> bool:
        """Create a backup of the entire layer.

        Args:
            layer_name: Name of the layer to backup
            backup_path: Path where backup should be stored

        Returns:
            True if backup was successful, False otherwise
        """

    @abstractmethod
    def restore_layer(self, layer_name: str, backup_path: Path) -> bool:
        """Restore a layer from backup.

        Args:
            layer_name: Name of the layer to restore
            backup_path: Path where backup is stored

        Returns:
            True if restore was successful, False otherwise
        """

    def get_config(self) -> dict[str, Any]:
        """Get the current configuration."""
        return self.config.copy()

    def update_config(self, new_config: dict[str, Any]) -> None:
        """Update the configuration.

        Args:
            new_config: New configuration parameters
        """
        self.config.update(new_config)
