"""Key rotation utilities built on top of CredentialManager."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
)
from importobot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RotationPlan:
    """Encapsulates a key rotation workflow."""

    items: list[EncryptedCredential]
    source_manager: CredentialManager
    target_manager: CredentialManager

    def execute(self) -> list[EncryptedCredential]:
        """Decrypt credentials with the old key and re-encrypt with the new one."""
        rotated: list[EncryptedCredential] = []
        for item in self.items:
            plaintext = self.source_manager.decrypt_credential(item)
            rotated.append(self.target_manager.encrypt_credential(plaintext))
        logger.info("Rotated %d credential(s) to new key", len(rotated))
        return rotated


def rotate_credentials(
    credentials: Iterable[EncryptedCredential],
    source_manager: CredentialManager,
    target_manager: CredentialManager,
) -> list[EncryptedCredential]:
    """One-shot helper to rotate credentials without instantiating RotationPlan."""
    plan = RotationPlan(
        items=list(credentials),
        source_manager=source_manager,
        target_manager=target_manager,
    )
    return plan.execute()
