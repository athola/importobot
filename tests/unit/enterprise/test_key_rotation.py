"""Tests for credential rotation helpers."""

from __future__ import annotations

import pytest

from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
)
from importobot_enterprise.key_rotation import RotationPlan, rotate_credentials


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


def test_rotate_credentials_partial_failure_propagates() -> None:
    """PR #90 review I12: mid-iteration failure must propagate.

    The previous test exercised only the happy path. If the 5th of 100
    credentials fails to decrypt, callers must see the exception
    rather than receiving a silently-truncated rotated list. The
    successful prefix retains its integrity (each entry is independent
    of subsequent ciphertexts).
    """
    old_manager = CredentialManager(key=b"0" * 32)
    new_manager = CredentialManager(key=b"1" * 32)

    valid_first = old_manager.encrypt_credential("alpha")
    valid_third = old_manager.encrypt_credential("gamma")
    # A ciphertext that cannot be decrypted by old_manager - inserted
    # in the middle of an otherwise valid batch.
    corrupt = EncryptedCredential(
        ciphertext=b"not-a-real-fernet-token",
        length=5,
        manager=old_manager,
    )
    plan = RotationPlan(
        items=[valid_first, corrupt, valid_third],
        source_manager=old_manager,
        target_manager=new_manager,
    )

    with pytest.raises(ValueError, match="decryption failed"):
        plan.execute()

    # The successful prefix's ciphertext is untouched - re-decrypting
    # it against the source manager still returns the original value.
    assert old_manager.decrypt_credential(valid_first) == "alpha"
