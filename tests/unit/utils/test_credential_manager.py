"""Tests for credential management utilities."""

import base64

import pytest

from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
    SecurityError,
)


@pytest.fixture(autouse=True)
def configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    deterministic_key = base64.urlsafe_b64encode(b"A" * 32).decode("ascii")
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", deterministic_key)


def test_encrypt_decrypt_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    # Use deterministic key for reproducibility
    deterministic_key = base64.urlsafe_b64encode(b"A" * 32).decode("ascii")
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", deterministic_key)
    manager = CredentialManager()

    encrypted = manager.encrypt_credential("s3cr3t!")
    assert isinstance(encrypted, EncryptedCredential)
    assert encrypted.length == 7
    assert "s3cr3t" not in repr(encrypted)

    decrypted = encrypted.reveal()
    assert decrypted == "s3cr3t!"


def test_fail_closed_when_library_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)
    with pytest.raises(SecurityError, match="Strong encryption unavailable"):
        CredentialManager()


def test_reject_empty_credentials() -> None:
    manager = CredentialManager()
    with pytest.raises(ValueError, match="Credential must be non-empty"):
        manager.encrypt_credential("")
