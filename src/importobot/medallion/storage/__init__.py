"""Storage abstraction for Medallion architecture layers.

This module provides storage abstractions that can work with local filesystem,
cloud storage, or other backends while maintaining consistent interfaces.
"""

from importobot.medallion.storage.base import StorageBackend
from importobot.medallion.storage.config import StorageConfig
from importobot.medallion.storage.local import LocalStorageBackend

__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
    "StorageConfig",
]
