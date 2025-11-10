"""Tests for credential management utilities."""

import pytest

from importobot.utils.credential_manager import CredentialManager, EncryptedCredential


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)


def test_encrypt_decrypt_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    # Use deterministic key for reproducibility
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", "A" * 44)
    manager = CredentialManager()

    encrypted = manager.encrypt_credential("s3cr3t!")
    assert isinstance(encrypted, EncryptedCredential)
    assert encrypted.length == 7
    assert "s3cr3t" not in repr(encrypted)

    decrypted = encrypted.reveal()
    assert decrypted == "s3cr3t!"


def test_uses_base64_when_library_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)
    manager = CredentialManager()
    encrypted = manager.encrypt_credential("secondary-secret")
    assert encrypted.length == len("secondary-secret")
    assert encrypted.reveal() == "secondary-secret"


def test_reject_empty_credentials() -> None:
    manager = CredentialManager()
    with pytest.raises(ValueError, match="Credential must be non-empty"):
        manager.encrypt_credential("")
