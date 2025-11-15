"""Automated key rotation system for cryptographic keys.

Provides rotation scheduling, lifecycle tracking, and policy enforcement that
align with NIST SP 800-57 guidance.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from importobot.security.hsm_integration import (
    HSMError,
    HSMKeyMetadata,
    HSMManager,
    get_hsm_manager,
)
from importobot.utils.runtime_paths import get_runtime_subdir

logger = logging.getLogger(__name__)


class RotationPolicy(Enum):
    """Key rotation policy types."""

    TIME_BASED = "time_based"
    USAGE_BASED = "usage_based"
    EVENT_BASED = "event_based"
    COMPLIANCE_BASED = "compliance_based"


class RotationStatus(Enum):
    """Status of key rotation operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RotationConfig:
    """Configuration for key rotation."""

    policy: RotationPolicy
    rotation_interval: timedelta  # For time-based rotation
    max_usage_count: int | None = None  # For usage-based rotation
    compliance_interval: timedelta | None = None  # For compliance-based
    rotation_warning_days: int = 7  # Days before rotation to warn
    auto_rotate: bool = True
    rotation_retention_days: int = 30  # Keep old keys for X days
    require_approval: bool = False  # Require manual approval for rotation
    notification_callbacks: list[Callable[[str, RotationStatus, str], None]] = field(
        default_factory=list
    )
    rotation_hooks: dict[str, Callable[[str, str], None]] = field(
        default_factory=dict
    )  # pre/post rotation hooks


RotationNotification = Callable[[str, RotationStatus, str], None]


@dataclass
class RotationEvent:
    """Record of a key rotation event."""

    key_id: str
    rotation_time: datetime
    status: RotationStatus
    old_key_id: str | None = None
    new_key_id: str | None = None
    reason: str = ""
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class KeyRotator:
    """Automated key rotation manager.

    Handles scheduling, lifecycle tracking, compliance checks, and event
    logging for each managed key.
    """

    def __init__(self, hsm_manager: HSMManager | None = None):
        """Initialize key rotator.

        Args:
            hsm_manager: HSM manager instance. If None, uses global instance.
        """
        self._hsm_manager = hsm_manager or get_hsm_manager()
        self._rotation_configs: dict[str, RotationConfig] = {}
        self._rotation_events: list[RotationEvent] = []
        self._monitored_keys: set[str] = set()
        self._running = False
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._storage_path = get_runtime_subdir("key_rotation")

        # Load existing configuration and events
        self._load_configuration()
        self._load_rotation_events()

    def _load_configuration(self) -> None:
        """Load rotation configuration from storage."""
        try:
            # json imported at top level

            config_file = self._storage_path / "rotation_config.json"
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    config_data = json.load(f)

                for key_id, config_dict in config_data.items():
                    # Convert string intervals back to timedelta
                    if "rotation_interval" in config_dict:
                        days = config_dict["rotation_interval"].get("days", 0)
                        hours = config_dict["rotation_interval"].get("hours", 0)
                        minutes = config_dict["rotation_interval"].get("minutes", 0)
                        config_dict["rotation_interval"] = timedelta(
                            days=days, hours=hours, minutes=minutes
                        )

                    if config_dict.get("compliance_interval"):
                        days = config_dict["compliance_interval"].get("days", 0)
                        hours = config_dict["compliance_interval"].get("hours", 0)
                        config_dict["compliance_interval"] = timedelta(
                            days=days, hours=hours
                        )

                    # Convert enum strings back to enums
                    config_dict["policy"] = RotationPolicy(config_dict["policy"])

                    # Reconstruct RotationConfig
                    self._rotation_configs[key_id] = RotationConfig(**config_dict)

        except Exception as exc:
            logger.warning(f"Failed to load rotation configuration: {exc}")

    def _save_configuration(self) -> None:
        """Save rotation configuration to storage."""
        try:
            # json imported at top level

            # Convert rotation configs to JSON-serializable format
            serializable_configs = {}
            for key_id, config in self._rotation_configs.items():
                config_dict: dict[str, Any] = {
                    "policy": config.policy.value,
                    "rotation_interval": {
                        "days": config.rotation_interval.days,
                        "hours": config.rotation_interval.seconds // 3600,
                        "minutes": (config.rotation_interval.seconds % 3600) // 60,
                    },
                    "max_usage_count": config.max_usage_count,
                    "compliance_interval": {
                        "days": config.compliance_interval.days,
                        "hours": config.compliance_interval.seconds // 3600,
                        "minutes": (config.compliance_interval.seconds % 3600) // 60,
                    }
                    if config.compliance_interval
                    else None,
                    "rotation_warning_days": config.rotation_warning_days,
                    "auto_rotate": config.auto_rotate,
                    "rotation_retention_days": config.rotation_retention_days,
                    "require_approval": config.require_approval,
                    "notification_callbacks": [],  # Callbacks can't be serialized
                    "rotation_hooks": {},
                }
                serializable_configs[key_id] = config_dict

            config_file = self._storage_path / "rotation_config.json"
            self._storage_path.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(serializable_configs, f, indent=2)

        except Exception as exc:
            logger.error(f"Failed to save rotation configuration: {exc}")

    def _load_rotation_events(self) -> None:
        """Load rotation events from storage."""
        try:
            # json imported at top level

            events_file = self._storage_path / "rotation_events.json"
            if events_file.exists():
                with open(events_file, encoding="utf-8") as f:
                    events_data = json.load(f)

                for event_dict in events_data:
                    # Convert string datetime back to datetime
                    event_dict["rotation_time"] = datetime.fromisoformat(
                        event_dict["rotation_time"]
                    )
                    event_dict["status"] = RotationStatus(event_dict["status"])

                    event = RotationEvent(**event_dict)
                    self._rotation_events.append(event)

        except Exception as exc:
            logger.warning(f"Failed to load rotation events: {exc}")

    def _save_rotation_events(self) -> None:
        """Save rotation events to storage."""
        try:
            # json imported at top level

            # Convert events to JSON-serializable format
            serializable_events = []
            for event in self._rotation_events:
                event_dict = {
                    "key_id": event.key_id,
                    "rotation_time": event.rotation_time.isoformat(),
                    "status": event.status.value,
                    "old_key_id": event.old_key_id,
                    "new_key_id": event.new_key_id,
                    "reason": event.reason,
                    "error_message": event.error_message,
                    "metadata": event.metadata,
                }
                serializable_events.append(event_dict)

            events_file = self._storage_path / "rotation_events.json"
            self._storage_path.mkdir(parents=True, exist_ok=True)
            with open(events_file, "w", encoding="utf-8") as f:
                json.dump(serializable_events, f, indent=2, default=str)

        except Exception as exc:
            logger.error(f"Failed to save rotation events: {exc}")

    def configure_key_rotation(self, key_id: str, config: RotationConfig) -> None:
        """Configure rotation for a specific key.

        Args:
            key_id: HSM key identifier
            config: Rotation configuration
        """
        with self._lock:
            self._rotation_configs[key_id] = config
            self._monitored_keys.add(key_id)
            self._save_configuration()

            logger.info(
                f"Configured rotation for key {key_id} "
                f"with policy {config.policy.value}"
            )

    def remove_key_rotation(self, key_id: str) -> None:
        """Remove rotation configuration for a key.

        Args:
            key_id: HSM key identifier
        """
        with self._lock:
            self._rotation_configs.pop(key_id, None)
            self._monitored_keys.discard(key_id)
            self._save_configuration()

            logger.info(f"Removed rotation configuration for key {key_id}")

    def get_rotation_config(self, key_id: str) -> RotationConfig | None:
        """Get rotation configuration for a key.

        Args:
            key_id: HSM key identifier

        Returns:
            Rotation configuration or None if not configured
        """
        with self._lock:
            config = self._rotation_configs.get(key_id)
            if config is None:
                self._load_configuration()
                config = self._rotation_configs.get(key_id)
            return config

    def list_monitored_keys(self) -> list[str]:
        """Get list of keys being monitored for rotation."""
        with self._lock:
            return list(self._monitored_keys)

    def _check_rotation_needed(
        self, key_id: str, metadata: HSMKeyMetadata, config: RotationConfig
    ) -> bool:
        """Check if a key needs rotation."""
        now = datetime.now(timezone.utc)

        if config.policy == RotationPolicy.TIME_BASED:
            return now >= metadata.next_rotation

        elif config.policy == RotationPolicy.USAGE_BASED:
            if config.max_usage_count is None:
                return False
            return metadata.usage_count >= config.max_usage_count

        elif config.policy == RotationPolicy.COMPLIANCE_BASED:
            if config.compliance_interval is None or metadata.last_rotation is None:
                return False
            return (now - metadata.last_rotation) >= config.compliance_interval

        return False

    def _should_warn_rotation(
        self, key_id: str, metadata: HSMKeyMetadata, config: RotationConfig
    ) -> bool:
        """Check if we should warn about upcoming rotation."""
        if config.rotation_warning_days <= 0:
            return False

        warning_time = metadata.next_rotation - timedelta(
            days=config.rotation_warning_days
        )
        return datetime.now(timezone.utc) >= warning_time

    def _notify_rotation_event(
        self,
        key_id: str,
        status: RotationStatus,
        message: str,
        config: RotationConfig | None = None,
    ) -> None:
        """Notify about rotation events."""
        logger.info(f"Key rotation {status.value}: {key_id} - {message}")

        # Call notification callbacks if configured
        if config:
            for callback in config.notification_callbacks:
                self._invoke_notification_callback(callback, key_id, status, message)

    def _invoke_notification_callback(
        self,
        callback: RotationNotification,
        key_id: str,
        status: RotationStatus,
        message: str,
    ) -> None:
        """Call a rotation notification callback with uniform error handling."""
        try:
            callback(key_id, status, message)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Rotation notification callback failed: %s", exc)

    def _execute_rotation_hook(
        self,
        hook_name: str,
        key_id: str,
        new_key_id: str | None = None,
        config: RotationConfig | None = None,
    ) -> None:
        """Execute rotation hook."""
        if config and hook_name in config.rotation_hooks:
            try:
                config.rotation_hooks[hook_name](key_id, new_key_id or "")
            except Exception as exc:
                logger.warning(f"Rotation hook {hook_name} failed: {exc}")

    def rotate_key(self, key_id: str, reason: str = "manual") -> RotationEvent:
        """Manually rotate a key.

        Args:
            key_id: HSM key identifier
            reason: Reason for rotation

        Returns:
            Rotation event record
        """
        with self._lock:
            config = self._rotation_configs.get(key_id)
            status = RotationStatus.IN_PROGRESS
            error_message = None
            new_key_id = None
            metadata = {}

            if config is None:
                error_message = f"Key {key_id} not found in rotation configuration"
                event = RotationEvent(
                    key_id=key_id,
                    rotation_time=datetime.now(timezone.utc),
                    status=RotationStatus.FAILED,
                    old_key_id=key_id,
                    new_key_id=None,
                    reason=reason,
                    error_message=error_message,
                    metadata={},
                )
                self._rotation_events.append(event)
                self._save_rotation_events()
                return event

            try:
                # Get current key metadata
                old_metadata = self._hsm_manager.get_key_metadata(key_id)

                # Execute pre-rotation hook
                if config:
                    self._execute_rotation_hook("pre_rotation", key_id, config=config)

                # Perform rotation
                self._notify_rotation_event(
                    key_id, status, f"Starting rotation: {reason}", config
                )

                new_key_id = self._hsm_manager.rotate_key(key_id)

                # Get new key metadata
                new_metadata = self._hsm_manager.get_key_metadata(new_key_id)

                status = RotationStatus.COMPLETED
                metadata = {
                    "old_key_metadata": {
                        "creation_date": old_metadata.creation_date.isoformat(),
                        "usage_count": old_metadata.usage_count,
                        "version": old_metadata.version,
                    },
                    "new_key_metadata": {
                        "creation_date": new_metadata.creation_date.isoformat(),
                        "usage_count": new_metadata.usage_count,
                        "version": new_metadata.version,
                    },
                }

                self._notify_rotation_event(
                    key_id,
                    status,
                    f"Successfully rotated key. New key ID: {new_key_id}",
                    config,
                )

                # Execute post-rotation hook
                if config:
                    self._execute_rotation_hook(
                        "post_rotation", key_id, new_key_id, config
                    )

            except Exception as exc:
                status = RotationStatus.FAILED
                error_message = str(exc)
                self._notify_rotation_event(
                    key_id, status, f"Rotation failed: {error_message}", config
                )

            # Create rotation event
            event = RotationEvent(
                key_id=key_id,
                rotation_time=datetime.now(timezone.utc),
                status=status,
                old_key_id=key_id,
                new_key_id=new_key_id,
                reason=reason,
                error_message=error_message,
                metadata=metadata,
            )

            self._rotation_events.append(event)
            self._save_rotation_events()

            return event

    def _check_all_keys(self) -> None:
        """Check all monitored keys for rotation needs."""
        try:
            if not self._hsm_manager.is_connected:
                return

            monitored_keys = self.list_monitored_keys()
            hsm_keys = set(self._hsm_manager.list_keys())

            for key_id in monitored_keys:
                if key_id not in hsm_keys:
                    logger.warning(f"Monitored key {key_id} not found in HSM")
                    continue

                config = self._rotation_configs.get(key_id)
                if not config:
                    continue

                try:
                    metadata = self._hsm_manager.get_key_metadata(key_id)

                    # Check for rotation warnings
                    if self._should_warn_rotation(key_id, metadata, config):
                        self._notify_rotation_event(
                            key_id,
                            RotationStatus.PENDING,
                            f"Key rotation due in {config.rotation_warning_days} days",
                            config,
                        )

                    # Check if rotation is needed
                    if self._check_rotation_needed(key_id, metadata, config):
                        if config.auto_rotate:
                            logger.info(f"Auto-rotating key {key_id}")
                            self.rotate_key(
                                key_id, f"automatic_{config.policy.value}_rotation"
                            )
                        else:
                            self._notify_rotation_event(
                                key_id,
                                RotationStatus.PENDING,
                                "Manual rotation required",
                                config,
                            )

                except HSMError as exc:
                    logger.error(f"Error checking key {key_id}: {exc}")

        except Exception as exc:
            logger.error(f"Error in key monitoring loop: {exc}")

    def _monitor_loop(self) -> None:
        """Run the monitoring loop for automated rotation."""
        logger.info("Key rotation monitoring started")

        while not self._stop_event.wait(300):  # Check every 5 minutes
            if not self._running:
                break

            try:
                self._check_all_keys()
            except Exception as exc:
                logger.error(f"Error in monitoring loop: {exc}")

        logger.info("Key rotation monitoring stopped")

    def start_monitoring(self) -> None:
        """Start automated key rotation monitoring."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, name="KeyRotationMonitor", daemon=True
            )
            self._monitor_thread.start()

            logger.info("Started key rotation monitoring")

    def stop_monitoring(self) -> None:
        """Stop automated key rotation monitoring."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=10)

            logger.info("Stopped key rotation monitoring")

    @property
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._running

    def get_rotation_history(
        self, key_id: str | None = None, limit: int = 100
    ) -> list[RotationEvent]:
        """Get rotation history.

        Args:
            key_id: Filter by specific key (optional)
            limit: Maximum number of events to return

        Returns:
            List of rotation events
        """
        with self._lock:
            events = self._rotation_events

            if key_id:
                events = [e for e in events if e.key_id == key_id]

            # Sort by rotation time descending
            events.sort(key=lambda e: e.rotation_time, reverse=True)

            return events[:limit]

    def get_rotation_statistics(self, key_id: str | None = None) -> dict[str, Any]:
        """Get rotation statistics.

        Args:
            key_id: Filter by specific key (optional)

        Returns:
            Rotation statistics
        """
        with self._lock:
            events = self._rotation_events

            if key_id:
                events = [e for e in events if e.key_id == key_id]

            total_rotations = len(events)
            successful_rotations = len(
                [e for e in events if e.status == RotationStatus.COMPLETED]
            )
            failed_rotations = len(
                [e for e in events if e.status == RotationStatus.FAILED]
            )

            # Calculate rotation frequency
            if events and len(events) > 1:
                events_sorted = sorted(events, key=lambda e: e.rotation_time)
                rotation_intervals = [
                    (
                        events_sorted[i].rotation_time
                        - events_sorted[i - 1].rotation_time
                    ).days
                    for i in range(1, len(events_sorted))
                ]
                avg_rotation_days = (
                    sum(rotation_intervals) / len(rotation_intervals)
                    if rotation_intervals
                    else 0
                )
            else:
                avg_rotation_days = 0

            return {
                "total_rotations": total_rotations,
                "successful_rotations": successful_rotations,
                "failed_rotations": failed_rotations,
                "success_rate": successful_rotations / total_rotations
                if total_rotations > 0
                else 0,
                "average_rotation_days": avg_rotation_days,
                "last_rotation": events[0].rotation_time.isoformat()
                if events
                else None,
                "monitored_keys": len(self._monitored_keys),
            }

    @contextmanager
    def rotation_session(self) -> Generator[KeyRotator, None, None]:
        """Context manager for key rotation session."""
        try:
            self.start_monitoring()
            yield self
        finally:
            self.stop_monitoring()

    def cleanup_old_events(self, retention_days: int = 90) -> None:
        """Clean up old rotation events.

        Args:
            retention_days: Number of days to retain events
        """
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            original_count = len(self._rotation_events)

            self._rotation_events = [
                event
                for event in self._rotation_events
                if event.rotation_time >= cutoff_time
            ]

            removed_count = original_count - len(self._rotation_events)
            if removed_count > 0:
                self._save_rotation_events()
                logger.info(f"Cleaned up {removed_count} old rotation events")


# Global key rotator instance
_key_rotator: KeyRotator | None = None
_rotator_lock = threading.Lock()


def get_key_rotator(hsm_manager: HSMManager | None = None) -> KeyRotator:
    """Get the global key rotator instance."""
    global _key_rotator  # noqa: PLW0603

    with _rotator_lock:
        if _key_rotator is None:
            _key_rotator = KeyRotator(hsm_manager)
        return _key_rotator


def reset_key_rotator() -> None:
    """Reset the global key rotator (for testing)."""
    global _key_rotator  # noqa: PLW0603

    with _rotator_lock:
        if _key_rotator is not None:
            _key_rotator.stop_monitoring()
        _key_rotator = None


# Convenience functions for common operations
def configure_90_day_rotation(key_id: str, auto_rotate: bool = True) -> None:
    """Configure 90-day automatic rotation for a key.

    Args:
        key_id: HSM key identifier
        auto_rotate: Whether to automatically rotate
    """
    rotator = get_key_rotator()
    config = RotationConfig(
        policy=RotationPolicy.TIME_BASED,
        rotation_interval=timedelta(days=90),
        auto_rotate=auto_rotate,
        rotation_warning_days=7,
    )
    rotator.configure_key_rotation(key_id, config)


def configure_usage_based_rotation(
    key_id: str, max_usage: int, auto_rotate: bool = True
) -> None:
    """Configure usage-based rotation for a key.

    Args:
        key_id: HSM key identifier
        max_usage: Maximum usage count before rotation
        auto_rotate: Whether to automatically rotate
    """
    rotator = get_key_rotator()
    config = RotationConfig(
        policy=RotationPolicy.USAGE_BASED,
        rotation_interval=timedelta(days=90),  # Fallback
        max_usage_count=max_usage,
        auto_rotate=auto_rotate,
        rotation_warning_days=3,
    )
    rotator.configure_key_rotation(key_id, config)


def configure_compliance_rotation(
    key_id: str, compliance_days: int = 30, auto_rotate: bool = True
) -> None:
    """Configure compliance-based rotation for a key.

    Args:
        key_id: HSM key identifier
        compliance_days: Compliance interval in days
        auto_rotate: Whether to automatically rotate
    """
    rotator = get_key_rotator()
    config = RotationConfig(
        policy=RotationPolicy.COMPLIANCE_BASED,
        rotation_interval=timedelta(days=90),  # Fallback
        compliance_interval=timedelta(days=compliance_days),
        auto_rotate=auto_rotate,
        rotation_warning_days=7,
    )
    rotator.configure_key_rotation(key_id, config)


__all__ = [
    "KeyRotator",
    "RotationConfig",
    "RotationEvent",
    "RotationPolicy",
    "RotationStatus",
    "configure_90_day_rotation",
    "configure_compliance_rotation",
    "configure_usage_based_rotation",
    "get_key_rotator",
    "reset_key_rotator",
]
