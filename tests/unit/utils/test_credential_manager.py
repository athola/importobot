"""Tests for credential management utilities."""

import pytest

from importobot.utils.credential_manager import CredentialManager, EncryptedCredential


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)


def test_encrypt_decrypt_roundtrip(monkeypatch):
    # Use deterministic key for reproducibility
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", "A" * 44)
    manager = CredentialManager()

    encrypted = manager.encrypt_credential("s3cr3t!")
    assert isinstance(encrypted, EncryptedCredential)
    assert encrypted.length == 7
    assert "s3cr3t" not in repr(encrypted)

    decrypted = encrypted.reveal()
    assert decrypted == "s3cr3t!"


def test_fallback_to_base64_when_library_missing(monkeypatch):
    monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)
    manager = CredentialManager()
    encrypted = manager.encrypt_credential("fallback-secret")
    assert encrypted.length == len("fallback-secret")
    assert encrypted.reveal() == "fallback-secret"


def test_reject_empty_credentials():
    manager = CredentialManager()
    with pytest.raises(ValueError):
        manager.encrypt_credential("")
