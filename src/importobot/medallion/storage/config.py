"""Storage configuration for Medallion architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["VALID_BACKEND_TYPES", "StorageConfig"]

# Valid storage backend types
VALID_BACKEND_TYPES = ["local", "s3", "azure", "gcp"]


@dataclass
class StorageConfig:
    """Configuration for storage backends."""

    backend_type: str = "local"  # Valid types: see VALID_BACKEND_TYPES
    base_path: Path = field(default_factory=lambda: Path("./medallion_data"))

    # Local storage specific
    compression: bool = False
    auto_backup: bool = False
    retention_days: int = 365

    # Cloud storage specific (for future implementations)
    cloud_config: dict[str, Any] = field(default_factory=dict)

    # Performance settings
    cache_size_mb: int = 100
    batch_size: int = 1000

    # Security settings
    encryption_enabled: bool = False
    encryption_key_path: Path | None = None

    # Backup settings
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "backend_type": self.backend_type,
            "base_path": str(self.base_path),
            "compression": self.compression,
            "auto_backup": self.auto_backup,
            "retention_days": self.retention_days,
            "cloud_config": self.cloud_config.copy(),
            "cache_size_mb": self.cache_size_mb,
            "batch_size": self.batch_size,
            "encryption_enabled": self.encryption_enabled,
            "encryption_key_path": (
                str(self.encryption_key_path) if self.encryption_key_path else None
            ),
            "backup_enabled": self.backup_enabled,
            "backup_interval_hours": self.backup_interval_hours,
            "backup_retention_days": self.backup_retention_days,
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> StorageConfig:
        """Create configuration from dictionary."""
        config = cls()

        # Apply configuration settings in groups
        config._apply_basic_settings(config_dict)
        config._apply_storage_settings(config_dict)
        config._apply_backup_settings(config_dict)
        config._apply_encryption_settings(config_dict)

        return config

    def _apply_basic_settings(self, config_dict: dict[str, Any]) -> None:
        """Apply basic configuration settings."""
        if "backend_type" in config_dict:
            self.backend_type = config_dict["backend_type"]

        if "base_path" in config_dict:
            self.base_path = Path(config_dict["base_path"])

        if "compression" in config_dict:
            self.compression = config_dict["compression"]

    def _apply_storage_settings(self, config_dict: dict[str, Any]) -> None:
        """Apply storage-related configuration settings."""
        if "retention_days" in config_dict:
            self.retention_days = config_dict["retention_days"]

        if "cloud_config" in config_dict:
            self.cloud_config = config_dict["cloud_config"].copy()

        if "cache_size_mb" in config_dict:
            self.cache_size_mb = config_dict["cache_size_mb"]

        if "batch_size" in config_dict:
            self.batch_size = config_dict["batch_size"]

    def _apply_backup_settings(self, config_dict: dict[str, Any]) -> None:
        """Apply backup-related configuration settings."""
        if "auto_backup" in config_dict:
            self.auto_backup = config_dict["auto_backup"]

        if "backup_enabled" in config_dict:
            self.backup_enabled = config_dict["backup_enabled"]

        if "backup_interval_hours" in config_dict:
            self.backup_interval_hours = config_dict["backup_interval_hours"]

        if "backup_retention_days" in config_dict:
            self.backup_retention_days = config_dict["backup_retention_days"]

    def _apply_encryption_settings(self, config_dict: dict[str, Any]) -> None:
        """Apply encryption-related configuration settings."""
        if "encryption_enabled" in config_dict:
            self.encryption_enabled = config_dict["encryption_enabled"]

        if config_dict.get("encryption_key_path"):
            self.encryption_key_path = Path(config_dict["encryption_key_path"])

    def validate(self) -> list[str]:
        """Validate the configuration and return any issues."""
        issues = []

        if self.backend_type not in VALID_BACKEND_TYPES:
            issues.append(f"Invalid backend_type: {self.backend_type}")

        if self.retention_days is not None and self.retention_days < 1:
            issues.append(
                f"retention_days must be at least 1, got {self.retention_days}"
            )

        if self.cache_size_mb is not None and self.cache_size_mb < 1:
            issues.append(f"cache_size_mb must be at least 1, got {self.cache_size_mb}")

        if self.batch_size is not None and self.batch_size < 1:
            issues.append(f"batch_size must be at least 1, got {self.batch_size}")

        if self.backup_interval_hours is not None and self.backup_interval_hours < 1:
            issues.append(
                f"backup_interval_hours must be at least 1, got "
                f"{self.backup_interval_hours}"
            )

        if self.backup_retention_days is not None and self.backup_retention_days < 1:
            issues.append(
                f"backup_retention_days must be at least 1, got "
                f"{self.backup_retention_days}"
            )

        if self.encryption_enabled and not self.encryption_key_path:
            issues.append("encryption_key_path is required when encryption is enabled")

        if self.encryption_key_path and not self.encryption_key_path.exists():
            issues.append(
                f"encryption_key_path does not exist: {self.encryption_key_path}"
            )

        return issues
