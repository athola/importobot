"""Tests for credential management utilities."""

import pytest

from importobot.exceptions import SecurityError
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


def test_missing_cryptography_raises_security_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # PR #90 review I7: the previous base64 fallback was removed because
    # plaintext-equivalent encoding gave callers false confidence. With
    # neither IMPORTOBOT_ENCRYPTION_KEY nor an importable cryptography
    # backend, constructing a CredentialManager must surface a
    # SecurityError rather than silently degrading.
    monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr("importobot.security.credential_manager.Fernet", None)
    with pytest.raises(SecurityError):
        CredentialManager()


def test_reject_empty_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", "A" * 44)
    manager = CredentialManager()
    with pytest.raises(ValueError, match="Credential must be non-empty"):
        manager.encrypt_credential("")
