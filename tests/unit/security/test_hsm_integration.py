"""Tests for HSM integration functionality."""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from importobot.exceptions import ImportobotError
from importobot.security.hsm_integration import (
    AWSCloudHSMProvider,
    AzureDedicatedHSMProvider,
    HSMConnectionError,
    HSMError,
    HSMKeyError,
    HSMKeyMetadata,
    HSMManager,
    HSMProvider,
    HSMProviderUnavailableError,
    KeyRotationError,
    SoftHSMProvider,
    SoftwareHSMProvider,
    ThalesLunaProvider,
    UtimacoSentryProvider,
    get_hsm_manager,
    reset_hsm_manager,
)


class TestSoftwareHSMProvider:
    """Test the software HSM provider implementation."""

    def test_provider_initialization(self) -> None:
        """Test HSM provider initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "hsm"
            provider = SoftwareHSMProvider(storage_path)

            assert provider._storage_path == storage_path
            assert not provider._connected

    def test_connection_management(self) -> None:
        """Test HSM connection management."""
        provider = SoftwareHSMProvider()

        # Initially disconnected
        assert not provider.is_connected

        # Connect
        provider.connect()
        assert provider.is_connected

        # Disconnect
        provider.disconnect()
        assert not provider.is_connected

    def test_key_generation(self) -> None:
        """Test key generation."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key("AES", 256)

        assert key_id is not None
        assert key_id.startswith("key_")
        assert len(key_id) > 10

        # Key should be in the keys list
        assert key_id in provider.list_keys()

    def test_key_metadata(self) -> None:
        """Test key metadata retrieval."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key("AES", 256, "AES-256-GCM")
        metadata = provider.get_key_metadata(key_id)

        assert isinstance(metadata, HSMKeyMetadata)
        assert metadata.key_id == key_id
        assert metadata.key_type == "AES"
        assert metadata.key_size == 256
        assert metadata.algorithm == "AES-256-GCM"
        assert metadata.provider == HSMProvider.SOFTWARE
        assert metadata.is_active is True
        assert metadata.version == 1
        assert metadata.usage_count == 0

    def test_encryption_decryption(self) -> None:
        """Test data encryption and decryption."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()
        plaintext = b"This is a test message for encryption"

        # Encrypt
        ciphertext = provider.encrypt_data(key_id, plaintext)
        assert ciphertext != plaintext
        assert len(ciphertext) > len(plaintext)

        # Decrypt
        decrypted = provider.decrypt_data(key_id, ciphertext)
        assert decrypted == plaintext

    def test_encryption_with_different_keys(self) -> None:
        """Test encryption with different keys."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key1 = provider.generate_key()
        key2 = provider.generate_key()
        plaintext = b"Test message"

        # Encrypt with key1
        ciphertext1 = provider.encrypt_data(key1, plaintext)

        # Should fail to decrypt with key2
        with pytest.raises(HSMError):
            provider.decrypt_data(key2, ciphertext1)

        # Should succeed with key1
        decrypted = provider.decrypt_data(key1, ciphertext1)
        assert decrypted == plaintext

    def test_invalid_ciphertext(self) -> None:
        """Test decryption with invalid ciphertext."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()

        # Invalid ciphertext (too short)
        with pytest.raises(HSMError):
            provider.decrypt_data(key_id, b"short")

        # Invalid ciphertext (corrupted)
        with pytest.raises(HSMError):
            provider.decrypt_data(key_id, b"invalid_ciphertext_data_here")

    def test_signing_verification(self) -> None:
        """Test data signing and verification."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()
        data = b"Important data to sign"

        # Sign data
        signature = provider.sign_data(key_id, data)
        assert len(signature) == 32  # HMAC-SHA256 length
        assert signature != data

        # Verify signature
        assert provider.verify_signature(key_id, data, signature) is True

        # Should fail with different data
        assert provider.verify_signature(key_id, b"different_data", signature) is False

    def test_key_derivation(self) -> None:
        """Test key derivation with context."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()

        # Derive keys with different contexts
        derived1 = provider.derive_key(key_id, b"context1")
        derived2 = provider.derive_key(key_id, b"context2")
        derived3 = provider.derive_key(key_id, b"context1")  # Same as first

        assert derived1 != derived2
        assert derived1 == derived3
        assert len(derived1) == 32  # Default length

    def test_key_rotation(self) -> None:
        """Test key rotation."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()
        original_metadata = provider.get_key_metadata(key_id)
        original_version = original_metadata.version

        # Rotate key
        new_key_id = provider.rotate_key(key_id)
        assert new_key_id == key_id  # Software HSM reuses key ID

        # Check that version was incremented
        new_metadata = provider.get_key_metadata(key_id)
        assert new_metadata.version == original_version + 1
        assert new_metadata.usage_count == 0

        # Original encrypted data should still decrypt
        test_data = b"test data"
        encrypted_before = provider.encrypt_data(key_id, test_data)
        decrypted_after = provider.decrypt_data(key_id, encrypted_before)
        assert decrypted_after == test_data

    def test_key_deletion(self) -> None:
        """Test key deletion."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()
        assert key_id in provider.list_keys()

        provider.delete_key(key_id)
        assert key_id not in provider.list_keys()

        # Should not be able to use deleted key
        with pytest.raises(HSMKeyError):
            provider.get_key_metadata(key_id)

    def test_error_handling_disconnected(self) -> None:
        """Test error handling when not connected."""
        provider = SoftwareHSMProvider()  # Not connected

        with pytest.raises(HSMConnectionError):
            provider.generate_key()

        with pytest.raises(HSMConnectionError):
            provider.encrypt_data("nonexistent", b"data")

        with pytest.raises(HSMConnectionError):
            provider.decrypt_data("nonexistent", b"data")

    def test_persistence_across_instances(self) -> None:
        """Test that keys persist across provider instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "hsm"

            # Create first instance and generate key
            provider1 = SoftwareHSMProvider(storage_path)
            provider1.connect()
            key_id = provider1.generate_key()
            test_data = b"persistent test data"
            encrypted = provider1.encrypt_data(key_id, test_data)
            provider1.disconnect()

            # Create second instance and use existing key
            provider2 = SoftwareHSMProvider(storage_path)
            provider2.connect()
            assert key_id in provider2.list_keys()

            decrypted = provider2.decrypt_data(key_id, encrypted)
            assert decrypted == test_data

    def test_usage_count_tracking(self) -> None:
        """Test usage count tracking."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()

        # Perform operations
        provider.encrypt_data(key_id, b"data1")
        provider.encrypt_data(key_id, b"data2")
        provider.sign_data(key_id, b"data3")
        provider.derive_key(key_id, b"context")

        metadata = provider.get_key_metadata(key_id)
        assert metadata.usage_count == 4


class TestHSMManager:
    """Test the HSM manager functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_hsm_manager()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_hsm_manager()

    def test_manager_initialization_with_software_provider(self) -> None:
        """Test manager initialization with software provider."""
        manager = HSMManager(HSMProvider.SOFTWARE)
        assert manager._provider_name == HSMProvider.SOFTWARE

    def test_manager_auto_detection(self) -> None:
        """Test manager auto-detection of HSM provider."""
        # Should default to software when no environment variables set
        manager = HSMManager()
        assert manager._provider_name == HSMProvider.SOFTWARE

    def test_connect_disconnect(self) -> None:
        """Test HSM connection management."""
        manager = HSMManager(HSMProvider.SOFTWARE)

        assert not manager.is_connected

        manager.connect()
        assert manager.is_connected

        manager.disconnect()
        assert not manager.is_connected

    def test_credential_encryption_decryption(self) -> None:
        """Test credential encryption and decryption."""
        manager = HSMManager(HSMProvider.SOFTWARE)
        manager.connect()

        key_id = manager.generate_key()
        credential = "super_secret_password"

        encrypted = manager.encrypt_credential(key_id, credential)
        assert isinstance(encrypted, bytes)
        assert encrypted != credential.encode()

        decrypted = manager.decrypt_credential(key_id, encrypted)
        assert decrypted == credential

    def test_signing_verification(self) -> None:
        """Test data signing and verification."""
        manager = HSMManager(HSMProvider.SOFTWARE)
        manager.connect()

        key_id = manager.generate_key()
        data = b"important document"

        signature = manager.sign_data(key_id, data)
        assert manager.verify_signature(key_id, data, signature)

        # Should fail with different data
        assert not manager.verify_signature(key_id, b"different data", signature)

    def test_key_rotation(self) -> None:
        """Test key rotation through manager."""
        manager = HSMManager(HSMProvider.SOFTWARE)
        manager.connect()

        key_id = manager.generate_key()
        original_metadata = manager.get_key_metadata(key_id)

        new_key_id = manager.rotate_key(key_id)
        new_metadata = manager.get_key_metadata(new_key_id)

        assert new_metadata.version > original_metadata.version

    def test_error_handling_not_connected(self) -> None:
        """Test error handling when HSM not connected."""
        manager = HSMManager(HSMProvider.SOFTWARE)  # Not connected

        with pytest.raises(HSMConnectionError):
            manager.generate_key()

        with pytest.raises(HSMConnectionError):
            manager.encrypt_credential("key", "data")

    def test_key_management_operations(self) -> None:
        """Test key management operations."""
        manager = HSMManager(HSMProvider.SOFTWARE)
        manager.connect()

        # Generate key
        key_id = manager.generate_key()
        keys = manager.list_keys()
        assert key_id in keys

        # Get metadata
        metadata = manager.get_key_metadata(key_id)
        assert isinstance(metadata, HSMKeyMetadata)
        assert metadata.key_id == key_id

        # Delete key
        manager.delete_key(key_id)
        keys = manager.list_keys()
        assert key_id not in keys

    def test_context_manager(self) -> None:
        """Test context manager usage."""
        with HSMManager(HSMProvider.SOFTWARE).managed_session() as manager:
            assert manager.is_connected
            key_id = manager.generate_key()
            assert key_id is not None

        # Should be disconnected after context
        assert not manager.is_connected

    def test_unsupported_provider(self) -> None:
        """Test error handling for unsupported provider."""
        manager = HSMManager(HSMProvider.AWS_CLOUDHSM)

        with pytest.raises(HSMProviderUnavailableError):
            manager.connect()


class TestGlobalHSMManager:
    """Test global HSM manager functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_hsm_manager()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_hsm_manager()

    def test_get_hsm_manager_singleton(self) -> None:
        """Test that get_hsm_manager returns singleton instance."""
        manager1 = get_hsm_manager()
        manager2 = get_hsm_manager()

        assert manager1 is manager2
        assert isinstance(manager1, HSMManager)

    def test_reset_hsm_manager(self) -> None:
        """Test HSM manager reset."""
        manager1 = get_hsm_manager()
        reset_hsm_manager()

        manager2 = get_hsm_manager()
        assert manager1 is not manager2
        assert isinstance(manager2, HSMManager)


class TestHSMProviderUnavailability:
    """Test behavior when HSM providers are unavailable."""

    def test_aws_cloudhsm_provider_unavailable(self) -> None:
        """Test AWS CloudHSM provider unavailability."""
        # AWS CloudHSM provider imported at top level

        provider = AWSCloudHSMProvider()

        with pytest.raises(HSMProviderUnavailableError):
            provider.connect()

        with pytest.raises(HSMProviderUnavailableError):
            provider.generate_key("AES", 256)

        assert not provider.is_connected

    def test_azure_hsm_provider_unavailable(self) -> None:
        """Test Azure Dedicated HSM provider unavailability."""
        # Azure Dedicated HSM provider imported at top level

        provider = AzureDedicatedHSMProvider()

        with pytest.raises(HSMProviderUnavailableError):
            provider.connect()

    def test_other_providers_unavailable(self) -> None:
        """Test other HSM provider unavailability."""
        # Other HSM providers imported at top level

        providers = [SoftHSMProvider(), ThalesLunaProvider(), UtimacoSentryProvider()]

        for provider in providers:
            with pytest.raises(HSMProviderUnavailableError):
                provider.connect()


class TestHSMErrorHandling:
    """Test HSM error handling."""

    def test_hsm_error_inheritance(self) -> None:
        """Test that HSM errors inherit from ImportobotError."""
        assert issubclass(HSMError, ImportobotError)
        assert issubclass(HSMConnectionError, HSMError)
        assert issubclass(HSMKeyError, HSMError)
        assert issubclass(HSMProviderUnavailableError, HSMError)
        assert issubclass(KeyRotationError, HSMError)

    def test_key_not_found_error(self) -> None:
        """Test error when key is not found."""
        provider = SoftwareHSMProvider()
        provider.connect()

        with pytest.raises(HSMKeyError, match="Key nonexistent_key not found"):
            provider.get_key_metadata("nonexistent_key")

    def test_invalid_key_id_format(self) -> None:
        """Test error handling for invalid operations."""
        provider = SoftwareHSMProvider()
        provider.connect()

        key_id = provider.generate_key()

        # Try to decrypt invalid data
        with pytest.raises(HSMError):
            provider.decrypt_data(key_id, b"invalid_encrypted_data")


class TestHSMConcurrency:
    """Test HSM operations under concurrent access."""

    def test_concurrent_key_operations(self) -> None:
        """Test concurrent key operations."""
        provider = SoftwareHSMProvider()
        provider.connect()

        def worker(worker_id: int) -> tuple[str, bytes, str]:
            key_id = provider.generate_key()
            plaintext = f"Worker {worker_id} data".encode()
            ciphertext = provider.encrypt_data(key_id, plaintext)
            decrypted = provider.decrypt_data(key_id, ciphertext).decode()
            return key_id, ciphertext, decrypted

        # Run multiple workers concurrently
        threads = []
        results = []

        def worker_wrapper(worker_id: int) -> None:
            results.append(worker(worker_id))

        for i in range(5):
            thread = threading.Thread(target=worker_wrapper, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 5
        results.sort(key=lambda item: item[2])
        for i, (_key_id, ciphertext, decrypted) in enumerate(results):
            assert decrypted == f"Worker {i} data"
            assert len(ciphertext) > len(f"Worker {i} data".encode())

    def test_concurrent_connection_management(self) -> None:
        """Test concurrent connection management."""
        provider = SoftwareHSMProvider()

        def connect_worker() -> bool:
            try:
                provider.connect()
                time.sleep(0.1)
                provider.disconnect()
                return True
            except Exception:
                return False

        # Run multiple connection attempts
        threads = []
        results = []

        for _ in range(10):
            thread = threading.Thread(target=lambda: results.append(connect_worker()))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should succeed
        assert all(results)
        assert len(results) == 10
        assert not provider.is_connected


class TestHSMConfiguration:
    """Test HSM configuration and environment handling."""

    @patch.dict("os.environ", {"AWS_CLOUDHSM_KEY_ID": "test-key"})
    def test_aws_environment_detection(self) -> None:
        """Test AWS CloudHSM detection via environment."""
        manager = HSMManager()
        assert manager._provider_name == HSMProvider.AWS_CLOUDHSM

    @patch.dict("os.environ", {"AZURE_KEYVAULT_URL": "https://test.vault.azure.net"})
    def test_azure_environment_detection(self) -> None:
        """Test Azure HSM detection via environment."""
        manager = HSMManager()
        assert manager._provider_name == HSMProvider.AZURE_DEDICATED_HSM

    @patch.dict("os.environ", {"HSM_PROVIDER": "software"})
    def test_explicit_provider_environment(self) -> None:
        """Test explicit provider via environment."""
        manager = HSMManager()
        assert manager._provider_name == HSMProvider.SOFTWARE

    @patch.dict("os.environ", {"HSM_PROVIDER": "invalid_provider"})
    def test_invalid_provider_environment(self) -> None:
        """Test invalid provider via environment."""
        manager = HSMManager()
        # Should fallback to software provider
        assert manager._provider_name == HSMProvider.SOFTWARE
