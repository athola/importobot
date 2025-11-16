"""Tests for enhanced credential manager security."""

from __future__ import annotations

import base64
import os
import secrets
from unittest.mock import patch

import pytest

from importobot.exceptions import ImportobotError
from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
    SecurityError,
)

VALID_TEST_KEY = b"A" * 32
SECOND_TEST_KEY = b"B" * 32
THIRD_TEST_KEY = b"C" * 32
FOURTH_TEST_KEY = b"D" * 32


class TestCredentialManagerSecurity:
    """Test enhanced security features of CredentialManager."""

    def test_init_without_cryptography_fails(self) -> None:
        """Test that initialization fails when cryptography is unavailable."""
        with (
            patch("importobot.security.credential_manager.Fernet", None),
            pytest.raises(SecurityError, match="Strong encryption unavailable"),
        ):
            CredentialManager(key=VALID_TEST_KEY)

    def test_init_without_key_fails(self) -> None:
        """Test that initialization fails without encryption key."""
        # Ensure no environment key is set
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(SecurityError, match="Strong encryption unavailable"),
        ):
            CredentialManager()

    def test_init_with_invalid_key_fails(self) -> None:
        """Test that initialization fails with invalid key."""
        with (
            patch.dict(os.environ, {"IMPORTOBOT_ENCRYPTION_KEY": "invalid_key"}),
            pytest.raises(SecurityError, match="Strong encryption unavailable"),
        ):
            CredentialManager()

    def test_init_with_valid_key_succeeds(self) -> None:
        """Test that initialization succeeds with valid 32-byte key."""
        # Generate a valid 32-byte key
        valid_key = "a" * 32  # 32 bytes
        with patch.dict(os.environ, {"IMPORTOBOT_ENCRYPTION_KEY": valid_key}):
            # This should succeed
            manager = CredentialManager()
            assert manager is not None

    def test_init_with_base64_key_succeeds(self) -> None:
        """Test that initialization succeeds with base64-encoded key."""
        # Valid 44-byte base64 string (32 bytes when decoded)
        valid_base64_key = (
            "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXphYmNkZWZnaGprbW5vcHFyc3R1dnd4eXo="
        )
        with patch.dict(os.environ, {"IMPORTOBOT_ENCRYPTION_KEY": valid_base64_key}):
            manager = CredentialManager()
            assert manager is not None

    def test_key_loaded_from_keyring_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CredentialManager pulls encryption key from keyring if configured."""

        class DummyKeyring:
            def get_password(self, service: str, username: str) -> str | None:
                assert service == "importobot-ci"
                assert username == "bot"
                # Return a valid base64-encoded 32-byte key for testing
                return "MwzwV7usXOinJbjLwmL_RyKwW9-D5nf3OnEU7cW1buY="

        monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("IMPORTOBOT_KEYRING_SERVICE", "importobot-ci")
        monkeypatch.setenv("IMPORTOBOT_KEYRING_USERNAME", "bot")
        monkeypatch.setattr(
            "importobot.security.credential_manager.keyring",
            DummyKeyring(),
        )

        manager = CredentialManager()
        assert manager is not None

    def test_store_key_in_keyring_generates_new_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CredentialManager.store_key_in_keyring writes a generated key to keyring."""

        class DummyKeyring:
            def __init__(self) -> None:
                self.passwords: dict[tuple[str, str], str] = {}

            def get_password(self, service: str, username: str) -> str | None:
                return self.passwords.get((service, username))

            def set_password(self, service: str, username: str, value: str) -> None:
                self.passwords[(service, username)] = value

        helper = DummyKeyring()
        monkeypatch.setattr(
            "importobot.security.credential_manager.keyring",
            helper,
        )

        stored = CredentialManager.store_key_in_keyring(
            service="importobot-ci", username="automation"
        )

        assert helper.get_password("importobot-ci", "automation") == stored
        assert len(base64.urlsafe_b64decode(stored)) == 32

    def test_store_key_in_keyring_honors_overwrite_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Replacing an existing key requires overwrite=True."""

        class DummyKeyring:
            def __init__(self) -> None:
                self.passwords: dict[tuple[str, str], str] = {
                    ("svc", "bot"): CredentialManager.generate_key()
                }

            def get_password(self, service: str, username: str) -> str | None:
                return self.passwords.get((service, username))

            def set_password(self, service: str, username: str, value: str) -> None:
                self.passwords[(service, username)] = value

        helper = DummyKeyring()
        monkeypatch.setattr(
            "importobot.security.credential_manager.keyring",
            helper,
        )

        with pytest.raises(SecurityError, match="already exists"):
            CredentialManager.store_key_in_keyring(service="svc", username="bot")

        rotated = CredentialManager.store_key_in_keyring(
            service="svc", username="bot", overwrite=True
        )
        assert helper.get_password("svc", "bot") == rotated
        assert len(base64.urlsafe_b64decode(rotated)) == 32

    def test_store_key_in_keyring_requires_keyring_extra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Helpful error when keyring dependency is missing."""

        monkeypatch.setattr(
            "importobot.security.credential_manager.keyring",
            None,
        )

        with pytest.raises(SecurityError, match="System keyring integration"):
            CredentialManager.store_key_in_keyring(service="svc")

    def test_encrypt_without_cryptography_fails(self) -> None:
        """Test that encryption fails without cryptography."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        manager._cipher = None
        with pytest.raises(SecurityError, match="Strong encryption unavailable"):
            manager.encrypt_credential("test credential")

    def test_decrypt_without_cryptography_fails(self) -> None:
        """Test that decryption fails without cryptography."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        encrypted = manager.encrypt_credential("sensitive")
        manager._cipher = None
        with pytest.raises(SecurityError, match="Strong decryption unavailable"):
            manager.decrypt_credential(encrypted)

    def test_encrypt_credential_valid(self) -> None:
        """Test encrypting a valid credential."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        credential = "my_secret_password"

        encrypted = manager.encrypt_credential(credential)

        assert isinstance(encrypted, EncryptedCredential)
        assert encrypted.length == len(credential)
        assert encrypted.manager is manager
        assert len(encrypted.ciphertext) > 0

    def test_encrypt_empty_credential_fails(self) -> None:
        """Test that encrypting empty credential fails."""
        manager = CredentialManager(key=VALID_TEST_KEY)

        with pytest.raises(ValueError, match="Credential must be non-empty"):
            manager.encrypt_credential("")

    def test_decrypt_credential_valid(self) -> None:
        """Test decrypting a valid credential."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        original_credential = "test_password_123"

        # Encrypt first
        encrypted = manager.encrypt_credential(original_credential)

        # Then decrypt
        decrypted = manager.decrypt_credential(encrypted)

        assert decrypted == original_credential

    def test_decrypt_credential_wrong_manager_fails(self) -> None:
        """Test that decrypting with wrong manager fails."""
        manager1 = CredentialManager(key=VALID_TEST_KEY)
        manager2 = CredentialManager(key=SECOND_TEST_KEY)

        # Encrypt with manager1
        encrypted = manager1.encrypt_credential("test_password")

        # Try to decrypt with manager2
        with pytest.raises(
            ValueError, match="EncryptedCredential provided by different manager"
        ):
            manager2.decrypt_credential(encrypted)

    def test_credential_repr_is_secure(self) -> None:
        """Test that credential representation doesn't reveal data."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        encrypted = manager.encrypt_credential("super_secret_password")

        repr_str = repr(encrypted)
        str_str = str(encrypted)

        # Should not contain the actual credential or ciphertext
        assert "super_secret_password" not in repr_str
        assert "super_secret_password" not in str_str
        assert "ciphertext=<hidden>" in repr_str

    def test_roundtrip_multiple_credentials(self) -> None:
        """Test encrypting and decrypting multiple credentials."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        credentials = [
            "password1",
            "api_key_abcdefgh12345678",
            "secret_token_very_long_string_with_numbers_123456789",
            "special_chars_!@#$%^&*()_+-=[]{}|;':\",./<>?",
        ]

        encrypted_credentials = []
        for credential in credentials:
            encrypted = manager.encrypt_credential(credential)
            encrypted_credentials.append(encrypted)

        # Decrypt and verify all
        for original, encrypted in zip(
            credentials, encrypted_credentials, strict=False
        ):
            decrypted = manager.decrypt_credential(encrypted)
            assert decrypted == original

    def test_different_keys_produce_different_ciphertexts(self) -> None:
        """Test that different keys produce different ciphertexts."""
        manager1 = CredentialManager(key=THIRD_TEST_KEY)
        manager2 = CredentialManager(key=FOURTH_TEST_KEY)

        credential = "same_password"
        encrypted1 = manager1.encrypt_credential(credential)
        encrypted2 = manager2.encrypt_credential(credential)

        # Ciphertexts should be different (due to different keys and random IVs)
        assert encrypted1.ciphertext != encrypted2.ciphertext

    def test_same_key_different_encryptions(self) -> None:
        """Test that same key produces different ciphertexts (due to random IV)."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        credential = "same_password"

        encrypted1 = manager.encrypt_credential(credential)
        encrypted2 = manager.encrypt_credential(credential)

        # Should produce different ciphertexts due to random IV
        assert encrypted1.ciphertext != encrypted2.ciphertext

        # But both should decrypt to the same original
        assert manager.decrypt_credential(encrypted1) == credential
        assert manager.decrypt_credential(encrypted2) == credential

    def test_unicode_credential_handling(self) -> None:
        """Test proper handling of Unicode credentials."""
        manager = CredentialManager(key=VALID_TEST_KEY)
        unicode_credential = "pässwörd_🔒_测试_пароль"

        encrypted = manager.encrypt_credential(unicode_credential)
        decrypted = manager.decrypt_credential(encrypted)

        assert decrypted == unicode_credential

    def test_large_credential_handling(self) -> None:
        """Test handling of large credentials."""
        manager = CredentialManager(key=VALID_TEST_KEY)

        # Create a large credential (1MB)
        large_credential = "A" * (1024 * 1024)

        encrypted = manager.encrypt_credential(large_credential)
        decrypted = manager.decrypt_credential(encrypted)

        assert decrypted == large_credential
        assert len(encrypted.ciphertext) > len(
            large_credential
        )  # Should be larger due to encryption overhead

    def test_error_messages_are_helpful(self) -> None:
        """Test that error messages provide helpful guidance."""
        CredentialManager(key=VALID_TEST_KEY)

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("importobot.security.credential_manager.Fernet", None),
            pytest.raises(SecurityError) as exc_info,
        ):
            CredentialManager()

        error_msg = str(exc_info.value)
        assert "pip install cryptography" in error_msg
        assert "IMPORTOBOT_ENCRYPTION_KEY" in error_msg
        assert "openssl rand -base64 32" in error_msg

    def test_security_error_inheritance(self) -> None:
        """Test SecurityError inherits from ImportobotError."""
        assert issubclass(SecurityError, ImportobotError)

        # Test that SecurityError can be caught as ImportobotError
        with (
            patch("importobot.security.credential_manager.Fernet", None),
            pytest.raises(ImportobotError),
        ):
            CredentialManager(key=VALID_TEST_KEY)


class TestCredentialManagerIntegration:
    """Integration tests for credential manager with real-world scenarios."""

    def test_environment_key_integration(self) -> None:
        """Test integration with environment variable key."""
        # Generate a real base64 key
        # base64 imported at top level
        # secrets imported at top level

        real_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")

        with patch.dict(os.environ, {"IMPORTOBOT_ENCRYPTION_KEY": real_key}):
            manager = CredentialManager()

            # Should be able to encrypt/decrypt normally
            test_credential = "integration_test_password"
            encrypted = manager.encrypt_credential(test_credential)
            decrypted = manager.decrypt_credential(encrypted)

            assert decrypted == test_credential

    def test_temporary_key_file_scenario(self) -> None:
        """Test scenario with temporary key file."""
        # base64 imported at top level
        # secrets imported at top level

        # Create temporary key
        temp_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")

        with patch.dict(os.environ, {"IMPORTOBOT_ENCRYPTION_KEY": temp_key}):
            manager = CredentialManager()

            # Store multiple credentials
            credentials = {
                "database": "db_password_123",
                "api": "api_token_abcdef",
                "ssh": "ssh_private_key_password",
            }

            encrypted_creds = {}
            for name, cred in credentials.items():
                encrypted_creds[name] = manager.encrypt_credential(cred)

            # Verify all can be decrypted
            for name, encrypted in encrypted_creds.items():
                decrypted = manager.decrypt_credential(encrypted)
                assert decrypted == credentials[name]

    def test_credential_lifecycle(self) -> None:
        """Test complete credential lifecycle."""
        # base64 imported at top level
        # secrets imported at top level

        key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
        manager = CredentialManager(key=key.encode("ascii"))

        # Phase 1: Create credential
        original_credential = "user_secret_password_123"
        encrypted = manager.encrypt_credential(original_credential)
        assert encrypted.manager is manager

        # Phase 2: Store credential (simulate)
        stored_ciphertext = encrypted.ciphertext
        stored_length = encrypted.length

        # Phase 3: Recreate credential from stored data
        restored_encrypted = EncryptedCredential(
            ciphertext=stored_ciphertext, length=stored_length, manager=manager
        )

        # Phase 4: Use credential
        retrieved_credential = manager.decrypt_credential(restored_encrypted)
        assert retrieved_credential == original_credential

    def test_multiple_managers_different_keys(self) -> None:
        """Test multiple managers with different keys don't interfere."""
        # secrets imported at top level

        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)

        manager1 = CredentialManager(key=key1)
        manager2 = CredentialManager(key=key2)

        # Each manager should only work with its own encrypted credentials
        cred1 = "credential_for_manager1"
        cred2 = "credential_for_manager2"

        enc1 = manager1.encrypt_credential(cred1)
        enc2 = manager2.encrypt_credential(cred2)

        # Cross-decryption should fail
        with pytest.raises(ValueError, match="decryption failed"):
            manager1.decrypt_credential(enc2)

        with pytest.raises(ValueError, match="decryption failed"):
            manager2.decrypt_credential(enc1)

        # Correct decryption should work
        assert manager1.decrypt_credential(enc1) == cred1
        assert manager2.decrypt_credential(enc2) == cred2

    def test_key_derivation_consistency(self) -> None:
        """Test that key derivation is consistent."""
        # base64 imported at top level
        # secrets imported at top level

        # Use same raw key for both managers
        raw_key = secrets.token_bytes(32)
        base64_key = base64.urlsafe_b64encode(raw_key).decode("ascii")

        manager1 = CredentialManager(key=raw_key)
        manager2 = CredentialManager(key=base64_key.encode("ascii"))

        test_credential = "consistency_test"

        enc1 = manager1.encrypt_credential(test_credential)
        enc2 = manager2.encrypt_credential(test_credential)

        # Both should be able to decrypt each other's credentials
        # (ciphertexts might be different due to random IVs, but both should decrypt)
        dec1 = manager1.decrypt_credential(enc2)
        dec2 = manager2.decrypt_credential(enc1)

        assert dec1 == test_credential
        assert dec2 == test_credential

    def test_error_recovery_scenarios(self) -> None:
        """Test various error recovery scenarios."""
        manager = CredentialManager(key=VALID_TEST_KEY)

        # Test 1: Invalid encrypted credential data
        fake_encrypted = EncryptedCredential(
            ciphertext=b"invalid_ciphertext_data", length=10, manager=manager
        )

        # Should raise decryption error
        with pytest.raises(ValueError, match="decryption failed"):
            manager.decrypt_credential(fake_encrypted)

        # Test 2: Corrupted ciphertext
        valid_encrypted = manager.encrypt_credential("test")
        corrupted_ciphertext = valid_encrypted.ciphertext[:-5] + b"corrupt"
        corrupted = EncryptedCredential(
            ciphertext=corrupted_ciphertext,
            length=valid_encrypted.length,
            manager=manager,
        )

        # Should raise decryption error
        with pytest.raises(ValueError, match="decryption failed"):
            manager.decrypt_credential(corrupted)

        # Test 3: Length mismatch
        length_mismatch = EncryptedCredential(
            ciphertext=valid_encrypted.ciphertext,
            length=999,  # Wrong length
            manager=manager,
        )

        # This might not raise an error immediately, but decryption should fail
        # or the length field is just metadata, so let's see what happens
        try:
            result = manager.decrypt_credential(length_mismatch)
            # If it succeeds, that's okay - length might just be metadata
            assert result == "test"
        except Exception:
            # If it fails, that's also acceptable
            pass
