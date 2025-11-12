"""Secure credential handling utilities."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any, cast

from importobot.utils.logging import get_logger

Fernet: Any | None

try:  # pragma: no cover - optional dependency
    from cryptography.fernet import Fernet as _CryptographyFernet

    Fernet = _CryptographyFernet
except ImportError:  # pragma: no cover - cryptography is an optional dependency
    Fernet = None


logger = get_logger()


@dataclass
class EncryptedCredential:
    """Container for encrypted credential data."""

    ciphertext: bytes
    length: int
    manager: CredentialManager

    def reveal(self) -> str:
        """Decrypt and return the plaintext credential."""
        return self.manager.decrypt_credential(self)

    def __repr__(self) -> str:  # pragma: no cover - defensive string repr only
        """Return a redacted representation of the credential."""
        return f"EncryptedCredential(length={self.length}, ciphertext=<hidden>)"

    __str__ = __repr__


class CredentialManager:
    """Encrypts and decrypts credentials held in memory."""

    def __init__(self, key: bytes | None = None) -> None:
        """Initialize a credential manager using the provided key."""
        self._key = key or self._load_key()
        self._cipher = self._build_cipher(self._key)

    def encrypt_credential(self, credential: str) -> EncryptedCredential:
        """Encrypt credential text and return container object."""
        if not credential:
            raise ValueError("Credential must be non-empty")
        ciphertext = self._encrypt(credential.encode("utf-8"))
        return EncryptedCredential(
            ciphertext=ciphertext,
            length=len(credential),
            manager=self,
        )

    def decrypt_credential(self, credential: EncryptedCredential) -> str:
        """Decrypt credential container and return plaintext."""
        if credential.manager is not self:
            raise ValueError("EncryptedCredential provided by different manager")
        plaintext = self._decrypt(credential.ciphertext)
        return plaintext.decode("utf-8")

    def _encrypt(self, payload: bytes) -> bytes:
        """Encrypt the given payload."""
        if self._cipher is not None:
            return cast(bytes, self._cipher.encrypt(payload))
        encoded = base64.urlsafe_b64encode(payload)
        logger.warning(
            "CredentialManager is using base64 encoding; set "
            "IMPORTOBOT_ENCRYPTION_KEY for stronger security."
        )
        return encoded

    def _decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt the given ciphertext."""
        if self._cipher is not None:
            return cast(bytes, self._cipher.decrypt(ciphertext))
        return base64.urlsafe_b64decode(ciphertext)

    def _load_key(self) -> bytes | None:
        """Load the encryption key from environment variables."""
        key = os.getenv("IMPORTOBOT_ENCRYPTION_KEY")
        if key:
            return key.encode("utf-8")
        return None

    def _build_cipher(self, key: bytes | None) -> Any | None:
        """Build the Fernet cipher from the provided key."""
        if Fernet is None or key is None:
            return None

        normalized_key = self._normalize_key(key)
        try:
            return Fernet(normalized_key)
        except Exception as exc:  # pragma: no cover - invalid key edge cases
            logger.warning(
                "Invalid encryption key provided; using base64 instead: %s",
                exc,
            )
            return None

    @staticmethod
    def _normalize_key(key: bytes) -> bytes:
        """Normalize the encryption key to a valid Fernet key format."""
        # Fernet keys must be 32 url-safe base64-encoded bytes. Accept raw
        # 32-byte keys or base64 strings.
        if len(key) == 44:
            return key
        if len(key) == 32:
            return base64.urlsafe_b64encode(key)
        # Derive deterministic key from arbitrary length input using base64
        return base64.urlsafe_b64encode(key[:32].ljust(32, b"0"))
