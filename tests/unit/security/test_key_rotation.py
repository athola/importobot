"""Tests for automated key rotation functionality."""

from __future__ import annotations

import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from importobot.security.hsm_integration import HSMManager, HSMProvider
from importobot.security.key_rotation import (
    KeyRotator,
    RotationConfig,
    RotationEvent,
    RotationPolicy,
    RotationStatus,
    configure_90_day_rotation,
    configure_compliance_rotation,
    configure_usage_based_rotation,
    get_key_rotator,
    reset_key_rotator,
)


class TestRotationConfig:
    """Test rotation configuration."""

    def test_time_based_config_creation(self) -> None:
        """Test time-based rotation configuration."""
        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED,
            rotation_interval=timedelta(days=90),
            auto_rotate=True,
            rotation_warning_days=7,
        )

        assert config.policy == RotationPolicy.TIME_BASED
        assert config.rotation_interval == timedelta(days=90)
        assert config.auto_rotate is True
        assert config.rotation_warning_days == 7

    def test_usage_based_config_creation(self) -> None:
        """Test usage-based rotation configuration."""
        config = RotationConfig(
            policy=RotationPolicy.USAGE_BASED,
            rotation_interval=timedelta(days=90),
            max_usage_count=1000,
            auto_rotate=False,
        )

        assert config.policy == RotationPolicy.USAGE_BASED
        assert config.max_usage_count == 1000
        assert config.auto_rotate is False

    def test_compliance_based_config_creation(self) -> None:
        """Test compliance-based rotation configuration."""
        config = RotationConfig(
            policy=RotationPolicy.COMPLIANCE_BASED,
            rotation_interval=timedelta(days=90),
            compliance_interval=timedelta(days=30),
            require_approval=True,
        )

        assert config.policy == RotationPolicy.COMPLIANCE_BASED
        assert config.compliance_interval == timedelta(days=30)
        assert config.require_approval is True


class TestRotationEvent:
    """Test rotation event records."""

    def test_rotation_event_creation(self) -> None:
        """Test rotation event creation."""
        now = datetime.now(timezone.utc)
        event = RotationEvent(
            key_id="test_key",
            rotation_time=now,
            status=RotationStatus.COMPLETED,
            old_key_id="old_key",
            new_key_id="new_key",
            reason="scheduled_rotation",
        )

        assert event.key_id == "test_key"
        assert event.rotation_time == now
        assert event.status == RotationStatus.COMPLETED
        assert event.old_key_id == "old_key"
        assert event.new_key_id == "new_key"
        assert event.reason == "scheduled_rotation"
        assert event.error_message is None

    def test_rotation_event_with_error(self) -> None:
        """Test rotation event with error."""
        now = datetime.now(timezone.utc)
        event = RotationEvent(
            key_id="test_key",
            rotation_time=now,
            status=RotationStatus.FAILED,
            reason="auto_rotation",
            error_message="Connection timeout",
        )

        assert event.status == RotationStatus.FAILED
        assert event.error_message == "Connection timeout"


class TestKeyRotator:
    """Test key rotator functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_key_rotator()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_key_rotator()

    def test_key_rotator_initialization(self) -> None:
        """Test key rotator initialization."""
        hsm_manager = HSMManager(HSMProvider.SOFTWARE)
        rotator = KeyRotator(hsm_manager)

        assert rotator._hsm_manager is hsm_manager
        assert not rotator.is_monitoring
        assert len(rotator.list_monitored_keys()) == 0

    def test_configure_key_rotation(self) -> None:
        """Test configuring key rotation."""
        rotator = KeyRotator()

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED, rotation_interval=timedelta(days=90)
        )

        rotator.configure_key_rotation("test_key", config)

        retrieved_config = rotator.get_rotation_config("test_key")
        assert retrieved_config is config
        assert "test_key" in rotator.list_monitored_keys()

    def test_remove_key_rotation(self) -> None:
        """Test removing key rotation configuration."""
        rotator = KeyRotator()

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED, rotation_interval=timedelta(days=90)
        )

        rotator.configure_key_rotation("test_key", config)
        assert "test_key" in rotator.list_monitored_keys()

        rotator.remove_key_rotation("test_key")
        assert "test_key" not in rotator.list_monitored_keys()
        assert rotator.get_rotation_config("test_key") is None

    def test_manual_key_rotation(self) -> None:
        """Test manual key rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            _ = Path(temp_dir) / "hsm"
            hsm_manager = HSMManager(HSMProvider.SOFTWARE)
            hsm_manager.connect()

            rotator = KeyRotator(hsm_manager)

            # Generate a key
            key_id = hsm_manager.generate_key()

            # Configure rotation
            config = RotationConfig(
                policy=RotationPolicy.TIME_BASED, rotation_interval=timedelta(days=90)
            )
            rotator.configure_key_rotation(key_id, config)

            # Perform manual rotation
            event = rotator.rotate_key(key_id, "manual_test")

            assert event.key_id == key_id
            assert event.status == RotationStatus.COMPLETED
            assert event.reason == "manual_test"
            assert event.old_key_id == key_id
            assert event.new_key_id == key_id  # Software HSM reuses key ID

    def test_rotation_with_nonexistent_key(self) -> None:
        """Test rotation with non-existent key."""
        rotator = KeyRotator()

        event = rotator.rotate_key("nonexistent_key", "test_rotation")

        assert event.key_id == "nonexistent_key"
        assert event.status == RotationStatus.FAILED
        assert event.error_message is not None
        assert "not found" in event.error_message.lower()

    def test_time_based_rotation_checking(self) -> None:
        """Test time-based rotation logic."""
        rotator = KeyRotator()

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED,
            rotation_interval=timedelta(days=90),
            auto_rotate=True,
        )

        # Mock key metadata
        past_rotation = datetime.now(timezone.utc) - timedelta(days=100)
        next_rotation = datetime.now(timezone.utc) - timedelta(days=10)  # Past due

        metadata = Mock()
        metadata.next_rotation = next_rotation
        metadata.last_rotation = past_rotation

        # Should need rotation
        assert rotator._check_rotation_needed("test_key", metadata, config)

        # Should not need rotation if next_rotation is in future
        metadata.next_rotation = datetime.now(timezone.utc) + timedelta(days=10)
        assert not rotator._check_rotation_needed("test_key", metadata, config)

    def test_usage_based_rotation_checking(self) -> None:
        """Test usage-based rotation logic."""
        rotator = KeyRotator()

        config = RotationConfig(
            policy=RotationPolicy.USAGE_BASED,
            rotation_interval=timedelta(days=90),
            max_usage_count=1000,
        )

        # Mock key metadata
        metadata = Mock()
        metadata.usage_count = 1500

        # Should need rotation
        assert rotator._check_rotation_needed("test_key", metadata, config)

        # Should not need rotation if under limit
        metadata.usage_count = 500
        assert not rotator._check_rotation_needed("test_key", metadata, config)

    def test_compliance_based_rotation_checking(self) -> None:
        """Test compliance-based rotation logic."""
        rotator = KeyRotator()

        config = RotationConfig(
            policy=RotationPolicy.COMPLIANCE_BASED,
            rotation_interval=timedelta(days=90),
            compliance_interval=timedelta(days=30),
        )

        # Mock key metadata with old last_rotation
        metadata = Mock()
        metadata.last_rotation = datetime.now(timezone.utc) - timedelta(days=40)

        # Should need rotation
        assert rotator._check_rotation_needed("test_key", metadata, config)

        # Should not need rotation if within compliance interval
        metadata.last_rotation = datetime.now(timezone.utc) - timedelta(days=20)
        assert not rotator._check_rotation_needed("test_key", metadata, config)

    def test_rotation_warning_checking(self) -> None:
        """Test rotation warning logic."""
        rotator = KeyRotator()

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED,
            rotation_interval=timedelta(days=90),
            rotation_warning_days=7,
        )

        # Mock key metadata with rotation soon
        metadata = Mock()
        metadata.next_rotation = datetime.now(timezone.utc) + timedelta(
            days=5
        )  # Within warning period

        # Should warn
        assert rotator._should_warn_rotation("test_key", metadata, config)

        # Should not warn if rotation is far
        metadata.next_rotation = datetime.now(timezone.utc) + timedelta(days=15)
        assert not rotator._should_warn_rotation("test_key", metadata, config)

    def test_rotation_statistics(self) -> None:
        """Test rotation statistics calculation."""
        rotator = KeyRotator()

        # Add some mock rotation events
        now = datetime.now(timezone.utc)

        # Successful rotation
        success_event = RotationEvent(
            key_id="key1",
            rotation_time=now - timedelta(days=5),
            status=RotationStatus.COMPLETED,
        )

        # Failed rotation
        failed_event = RotationEvent(
            key_id="key2",
            rotation_time=now - timedelta(days=3),
            status=RotationStatus.FAILED,
        )

        rotator._rotation_events = [success_event, failed_event]

        stats = rotator.get_rotation_statistics()

        assert stats["total_rotations"] == 2
        assert stats["successful_rotations"] == 1
        assert stats["failed_rotations"] == 1
        assert stats["success_rate"] == 0.5

    def test_rotation_history_filtering(self) -> None:
        """Test rotation history filtering."""
        rotator = KeyRotator()

        now = datetime.now(timezone.utc)

        # Add events for different keys
        events = [
            RotationEvent(
                key_id="key1",
                rotation_time=now - timedelta(days=1),
                status=RotationStatus.COMPLETED,
            ),
            RotationEvent(
                key_id="key2",
                rotation_time=now - timedelta(days=2),
                status=RotationStatus.COMPLETED,
            ),
            RotationEvent(
                key_id="key1",
                rotation_time=now - timedelta(days=3),
                status=RotationStatus.FAILED,
            ),
        ]

        rotator._rotation_events = events

        # Get all events
        all_events = rotator.get_rotation_history()
        assert len(all_events) == 3

        # Get events for specific key
        key1_events = rotator.get_rotation_history("key1")
        assert len(key1_events) == 2
        assert all(e.key_id == "key1" for e in key1_events)

        # Test limit
        limited_events = rotator.get_rotation_history(limit=2)
        assert len(limited_events) == 2

    def test_configuration_persistence(self) -> None:
        """Test configuration persistence across instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "rotation"

            # Create first rotator
            rotator1 = KeyRotator()
            rotator1._storage_path = storage_path

            config = RotationConfig(
                policy=RotationPolicy.TIME_BASED,
                rotation_interval=timedelta(days=60),
                auto_rotate=False,
                rotation_warning_days=14,
            )

            rotator1.configure_key_rotation("persistent_key", config)

            # Create second rotator and load configuration
            rotator2 = KeyRotator()
            rotator2._storage_path = storage_path

            loaded_config = rotator2.get_rotation_config("persistent_key")
            assert loaded_config is not None
            assert loaded_config.policy == RotationPolicy.TIME_BASED
            assert loaded_config.rotation_interval == timedelta(days=60)
            assert loaded_config.auto_rotate is False
            assert loaded_config.rotation_warning_days == 14

    def test_event_persistence(self) -> None:
        """Test event persistence across instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "rotation"
            now = datetime.now(timezone.utc)

            # Create first rotator and add events
            rotator1 = KeyRotator()
            rotator1._storage_path = storage_path

            event = RotationEvent(
                key_id="test_key",
                rotation_time=now,
                status=RotationStatus.COMPLETED,
                reason="persistence_test",
            )

            rotator1._rotation_events = [event]
            rotator1._save_rotation_events()

            # Create second rotator and load events
            rotator2 = KeyRotator()
            rotator2._storage_path = storage_path
            rotator2._load_rotation_events()

            assert len(rotator2._rotation_events) == 1
            loaded_event = rotator2._rotation_events[0]
            assert loaded_event.key_id == "test_key"
            assert loaded_event.status == RotationStatus.COMPLETED
            assert loaded_event.reason == "persistence_test"

    def test_notification_callbacks(self) -> None:
        """Test notification callback functionality."""
        rotator = KeyRotator()

        # Mock callback
        callback_called = []

        def test_callback(key_id: str, status: RotationStatus, message: str) -> None:
            callback_called.append((key_id, status, message))

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED,
            rotation_interval=timedelta(days=90),
            notification_callbacks=[test_callback],
        )

        # Test notification
        rotator._notify_rotation_event(
            "test_key", RotationStatus.PENDING, "Test message", config
        )

        assert len(callback_called) == 1
        assert callback_called[0] == (
            "test_key",
            RotationStatus.PENDING,
            "Test message",
        )

    def test_rotation_hooks(self) -> None:
        """Test rotation hook functionality."""
        rotator = KeyRotator()

        # Mock hooks
        pre_hook_called = []
        post_hook_called = []

        def pre_hook(key_id: str, new_key_id: str) -> None:
            pre_hook_called.append((key_id, new_key_id))

        def post_hook(key_id: str, new_key_id: str) -> None:
            post_hook_called.append((key_id, new_key_id))

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED,
            rotation_interval=timedelta(days=90),
            rotation_hooks={"pre_rotation": pre_hook, "post_rotation": post_hook},
        )

        # Test hooks
        rotator._execute_rotation_hook("pre_rotation", "test_key", config=config)
        rotator._execute_rotation_hook(
            "post_rotation", "test_key", "new_key", config=config
        )

        assert len(pre_hook_called) == 1
        assert pre_hook_called[0] == ("test_key", "")
        assert len(post_hook_called) == 1
        assert post_hook_called[0] == ("test_key", "new_key")

    def test_old_events_cleanup(self) -> None:
        """Test cleanup of old rotation events."""
        rotator = KeyRotator()

        now = datetime.now(timezone.utc)

        # Add old and recent events
        old_event = RotationEvent(
            key_id="old_key",
            rotation_time=now - timedelta(days=100),
            status=RotationStatus.COMPLETED,
        )

        recent_event = RotationEvent(
            key_id="recent_key",
            rotation_time=now - timedelta(days=10),
            status=RotationStatus.COMPLETED,
        )

        rotator._rotation_events = [old_event, recent_event]

        # Clean up events older than 30 days
        rotator.cleanup_old_events(retention_days=30)

        assert len(rotator._rotation_events) == 1
        assert rotator._rotation_events[0].key_id == "recent_key"


class TestKeyRotatorIntegration:
    """Integration tests for key rotator."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_key_rotator()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_key_rotator()

    def test_end_to_end_rotation_workflow(self) -> None:
        """Test complete rotation workflow."""
        hsm_manager = HSMManager(HSMProvider.SOFTWARE)
        hsm_manager.connect()

        rotator = KeyRotator(hsm_manager)

        # Generate key and configure rotation
        key_id = hsm_manager.generate_key()

        config = RotationConfig(
            policy=RotationPolicy.TIME_BASED,
            rotation_interval=timedelta(days=90),
            auto_rotate=True,
        )

        rotator.configure_key_rotation(key_id, config)

        # Verify configuration
        assert key_id in rotator.list_monitored_keys()
        retrieved_config = rotator.get_rotation_config(key_id)
        assert retrieved_config is not None

        # Perform rotation
        event = rotator.rotate_key(key_id, "integration_test")
        assert event.status == RotationStatus.COMPLETED

        # Verify key is still functional
        test_data = "test_data"
        encrypted = hsm_manager.encrypt_credential(key_id, test_data)
        decrypted = hsm_manager.decrypt_credential(key_id, encrypted)
        assert decrypted == test_data

    def test_concurrent_rotation_operations(self) -> None:
        """Test concurrent rotation operations."""
        hsm_manager = HSMManager(HSMProvider.SOFTWARE)
        hsm_manager.connect()

        rotator = KeyRotator(hsm_manager)

        # Generate multiple keys
        key_ids = [hsm_manager.generate_key() for _ in range(3)]

        # Configure rotation for all keys
        for key_id in key_ids:
            config = RotationConfig(
                policy=RotationPolicy.TIME_BASED, rotation_interval=timedelta(days=90)
            )
            rotator.configure_key_rotation(key_id, config)

        def rotate_key_worker(key_id: str) -> RotationEvent:
            return rotator.rotate_key(key_id, "concurrent_test")

        # Rotate keys concurrently
        threads = []
        results = []

        for key_id in key_ids:
            thread = threading.Thread(
                target=lambda k=key_id: results.append(rotate_key_worker(k))
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All rotations should succeed
        assert len(results) == 3
        for event in results:
            assert event.status == RotationStatus.COMPLETED
            assert event.reason == "concurrent_test"


class TestGlobalKeyRotator:
    """Test global key rotator functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_key_rotator()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_key_rotator()

    def test_get_key_rotator_singleton(self) -> None:
        """Test that get_key_rotator returns singleton instance."""
        rotator1 = get_key_rotator()
        rotator2 = get_key_rotator()

        assert rotator1 is rotator2
        assert isinstance(rotator1, KeyRotator)

    def test_reset_key_rotator(self) -> None:
        """Test key rotator reset."""
        rotator1 = get_key_rotator()
        reset_key_rotator()

        rotator2 = get_key_rotator()
        assert rotator1 is not rotator2
        assert isinstance(rotator2, KeyRotator)


class TestConvenienceFunctions:
    """Test convenience configuration functions."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_key_rotator()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_key_rotator()

    def test_configure_90_day_rotation(self) -> None:
        """Test 90-day rotation configuration."""
        rotator = get_key_rotator()
        configure_90_day_rotation("test_key", auto_rotate=False)

        config = rotator.get_rotation_config("test_key")
        assert config is not None
        assert config.policy == RotationPolicy.TIME_BASED
        assert config.rotation_interval == timedelta(days=90)
        assert config.auto_rotate is False
        assert config.rotation_warning_days == 7

    def test_configure_usage_based_rotation(self) -> None:
        """Test usage-based rotation configuration."""
        rotator = get_key_rotator()
        configure_usage_based_rotation("test_key", max_usage=5000, auto_rotate=True)

        config = rotator.get_rotation_config("test_key")
        assert config is not None
        assert config.policy == RotationPolicy.USAGE_BASED
        assert config.max_usage_count == 5000
        assert config.auto_rotate is True

    def test_configure_compliance_rotation(self) -> None:
        """Test compliance-based rotation configuration."""
        rotator = get_key_rotator()
        configure_compliance_rotation("test_key", compliance_days=45, auto_rotate=False)

        config = rotator.get_rotation_config("test_key")
        assert config is not None
        assert config.policy == RotationPolicy.COMPLIANCE_BASED
        assert config.compliance_interval == timedelta(days=45)
        assert config.auto_rotate is False
