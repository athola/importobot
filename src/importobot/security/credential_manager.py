"""Secure credential handling utilities."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, cast

try:  # Optional dependency provided via the "security" extra
    import keyring
except ImportError:  # pragma: no cover - optional dependency
    keyring = None  # type: ignore[assignment]

from importobot.exceptions import ImportobotError
from importobot.utils.logging import get_logger

Fernet: Any | None
InvalidToken: type[Exception]

# SECURITY: Cryptography is now required for secure credential management
try:  # pragma: no cover - should never happen in production
    from cryptography.fernet import Fernet as _CryptographyFernet
    from cryptography.fernet import InvalidToken as _CryptographyInvalidToken

    Fernet = _CryptographyFernet
    InvalidToken = _CryptographyInvalidToken
except ImportError:  # pragma: no cover - required dependency
    Fernet = None

    class _FallbackInvalidToken(Exception):
        """Fallback cryptography error when Fernet is unavailable."""

        pass

    InvalidToken = _FallbackInvalidToken


logger = get_logger()


class SecurityError(ImportobotError):
    """Raised when security requirements cannot be met."""

    pass


@dataclass
class EncryptedCredential:
    """Container for encrypted credential data."""

    ciphertext: bytes
    length: int
    manager: CredentialManager
    key_fingerprint: bytes | None = field(default=None, repr=False)

    def reveal(self) -> str:
        """Decrypt and return the plaintext credential."""
        return self.manager.decrypt_credential(self)

    def __repr__(self) -> str:  # pragma: no cover - defensive string repr only
        """Return a redacted representation of the credential."""
        return f"EncryptedCredential(length={self.length}, ciphertext=<hidden>)"

    __str__ = __repr__


class CredentialManager:
    """Encrypts and decrypts credentials held in memory."""

    def __init__(self, key: bytes | str | None = None) -> None:
        """Initialize a credential manager using the provided key."""
        self._key_fingerprint: bytes | None = None
        self._key = self._prepare_key(key) or self._load_key()
        self._cipher = self._build_cipher(self._key)
        if self._cipher is None:
            raise SecurityError(_ENCRYPTION_ERROR_MESSAGE)

    def encrypt_credential(self, credential: str) -> EncryptedCredential:
        """Encrypt credential text and return container object."""
        if not credential:
            raise ValueError("Credential must be non-empty")
        ciphertext = self._encrypt(credential.encode("utf-8"))
        if self._key_fingerprint is None:
            raise SecurityError(_ENCRYPTION_ERROR_MESSAGE)
        return EncryptedCredential(
            ciphertext=ciphertext,
            length=len(credential),
            manager=self,
            key_fingerprint=self._key_fingerprint,
        )

    def decrypt_credential(self, credential: EncryptedCredential) -> str:
        """Decrypt credential container and return plaintext."""
        if credential.manager is not self:
            if not (
                credential.key_fingerprint is not None
                and self._key_fingerprint is not None
                and credential.key_fingerprint == self._key_fingerprint
            ):
                raise ValueError(
                    "EncryptedCredential provided by different manager "
                    "(decryption failed)"
                )
        elif (
            credential.key_fingerprint is not None
            and self._key_fingerprint is not None
            and credential.key_fingerprint != self._key_fingerprint
        ):
            raise ValueError(
                "EncryptedCredential provided by different manager (decryption failed)"
            )
        try:
            plaintext = self._decrypt(credential.ciphertext)
        except InvalidToken as exc:
            raise ValueError("decryption failed") from exc
        return plaintext.decode("utf-8")

    def _encrypt(self, payload: bytes) -> bytes:
        """Encrypt the given payload."""
        if self._cipher is not None:
            return cast(bytes, self._cipher.encrypt(payload))

        # SECURITY: Fail loudly instead of silently degrading to base64
        raise SecurityError(_ENCRYPTION_ERROR_MESSAGE)

    def _decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt the given ciphertext."""
        if self._cipher is not None:
            return cast(bytes, self._cipher.decrypt(ciphertext))

        # SECURITY: Fail loudly instead of silently decrypting base64
        raise SecurityError(_DECRYPTION_ERROR_MESSAGE)

    @staticmethod
    def _prepare_key(provided: bytes | str | None) -> bytes | None:
        """Normalize the provided key into bytes."""
        if provided is None:
            return None
        if isinstance(provided, bytes):
            return provided
        if isinstance(provided, str):
            return provided.strip().encode("utf-8")
        raise TypeError("Encryption key must be bytes, str, or None")

    def _load_key(self) -> bytes | None:
        """Load the encryption key from environment variables."""
        key = os.getenv("IMPORTOBOT_ENCRYPTION_KEY")
        if key:
            return key.encode("utf-8")
        service = os.getenv("IMPORTOBOT_KEYRING_SERVICE")
        if service:
            username = os.getenv("IMPORTOBOT_KEYRING_USERNAME", "importobot")
            if keyring is None:
                logger.warning(
                    "IMPORTOBOT_KEYRING_SERVICE is set but the 'keyring' package is "
                    "missing; install the 'security' extra to enable key retrieval."
                )
            else:
                stored = keyring.get_password(service, username)
                if stored:
                    logger.info(
                        "Loaded encryption key from keyring service %s", service
                    )
                    return stored.encode("utf-8")
                logger.warning(
                    "Keyring service %s has no password for user %s", service, username
                )
        return None

    @classmethod
    def generate_key(cls) -> str:
        """Return a base64 Fernet key suitable for IMPORTOBOT_ENCRYPTION_KEY."""
        return cls._normalized_key_text(None)

    @classmethod
    def store_key_in_keyring(
        cls,
        *,
        service: str,
        username: str = "importobot",
        key: bytes | str | None = None,
        overwrite: bool = False,
    ) -> str:
        """Generate or persist a Fernet key inside the system keyring."""
        if keyring is None:
            raise SecurityError(
                "System keyring integration requires the 'security' extra. "
                'Install it via `pip install "importobot[security]"`.'
            )
        if not service:
            raise ValueError("Keyring service name must be provided.")
        if not username:
            raise ValueError("Keyring username must be provided.")

        normalized_text = cls._normalized_key_text(key)
        existing = keyring.get_password(service, username)
        if existing and not overwrite:
            raise SecurityError(
                "An encryption key already exists in the keyring. "
                "Pass overwrite=True to rotate it."
            )

        keyring.set_password(service, username, normalized_text)
        logger.info(
            "Stored encryption key in keyring service %s for user %s",
            service,
            username,
        )
        return normalized_text

    def _build_cipher(self, key: bytes | None) -> Any | None:
        """Build the Fernet cipher from the provided key."""
        if Fernet is None or key is None:
            return None

        normalized_key = self._normalize_key(key)
        if normalized_key is None:
            return None
        self._key_fingerprint = self._fingerprint_key(normalized_key)
        try:
            return Fernet(normalized_key)
        except Exception as exc:  # pragma: no cover - invalid key edge cases
            logger.warning(
                "Invalid encryption key provided; using base64 instead: %s",
                exc,
            )
            return None

    @staticmethod
    def _normalize_key(key: bytes) -> bytes | None:
        """Normalize the encryption key to a valid Fernet key format."""
        candidate = key
        if not candidate:
            return None

        # Accept raw 32-byte keys directly
        if len(candidate) == 32:
            return base64.urlsafe_b64encode(candidate)

        decoded = CredentialManager._try_decode_base64(candidate)
        if decoded is not None:
            if len(decoded) == 32:
                return base64.urlsafe_b64encode(decoded)
            if len(decoded) > 32:
                derived = hashlib.blake2b(decoded, digest_size=32).digest()
                return base64.urlsafe_b64encode(derived)

        if len(candidate) > 32:
            derived = hashlib.blake2b(candidate, digest_size=32).digest()
            return base64.urlsafe_b64encode(derived)

        return None

    @staticmethod
    def _try_decode_base64(candidate: bytes) -> bytes | None:
        """Attempt to base64-decode the provided key."""
        try:
            return base64.urlsafe_b64decode(candidate)
        except (binascii.Error, ValueError):
            return None

    @staticmethod
    def _fingerprint_key(normalized_key: bytes) -> bytes:
        """Return a stable fingerprint for the active key."""
        decoded = base64.urlsafe_b64decode(normalized_key)
        return hashlib.blake2b(decoded, digest_size=32).digest()

    @classmethod
    def _normalized_key_text(cls, key: bytes | str | None) -> str:
        """Return a base64 text key suitable for storage or environment variables."""
        raw = os.urandom(32) if key is None else cls._prepare_key(key)

        if raw is None:
            raise ValueError("Encryption key material cannot be empty.")

        normalized = cls._normalize_key(raw)
        if normalized is None:
            raise ValueError(
                "Encryption key must be 32 bytes or a base64-encoded 32-byte string."
            )

        return normalized.decode("utf-8")


_ENCRYPTION_ERROR_MESSAGE = (
    "Strong encryption unavailable. Please:\n"
    "1. Install cryptography package: pip install cryptography\n"
    "2. Set IMPORTOBOT_ENCRYPTION_KEY environment variable to a 32-byte key\n"
    "3. Or generate a key with: openssl rand -base64 32\n"
    "\n"
    "For security reasons, credentials cannot be stored with weak encryption."
)


_DECRYPTION_ERROR_MESSAGE = (
    "Strong decryption unavailable. Please:\n"
    "1. Install cryptography package: pip install cryptography\n"
    "2. Set IMPORTOBOT_ENCRYPTION_KEY environment variable to a 32-byte key\n"
    "3. Or generate a key with: openssl rand -base64 32\n"
    "\n"
    "For security reasons, credentials cannot be accessed with weak encryption."
)
