"""Tests for credential rotation helpers."""

from __future__ import annotations

from importobot.security.credential_manager import CredentialManager
from importobot_enterprise.key_rotation import rotate_credentials


def test_rotate_credentials_rewraps_ciphertexts() -> None:
    old_manager = CredentialManager(key=b"0" * 32)
    new_manager = CredentialManager(key=b"1" * 32)
    encrypted = [
        old_manager.encrypt_credential("alpha"),
        old_manager.encrypt_credential("beta"),
    ]

    rotated = rotate_credentials(encrypted, old_manager, new_manager)

    assert [new_manager.decrypt_credential(item) for item in rotated] == [
        "alpha",
        "beta",
    ]
