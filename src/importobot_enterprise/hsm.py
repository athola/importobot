"""Software-backed HSM adapter for enterprise deployments."""

from __future__ import annotations

from dataclasses import dataclass

from importobot.security.secure_memory import SecureString
from importobot.utils.logging import get_logger

logger = get_logger(__name__)


class HSMError(RuntimeError):
    """Raised when HSM operations fail."""


@dataclass
class StoredKey:
    """Represents a logical key stored in the software HSM."""

    alias: str
    value: SecureString


class SoftwareHSM:
    """In-memory HSM simulation using SecureString for zeroization."""

    def __init__(self) -> None:
        """Initialize an empty key container."""
        self._keys: dict[str, StoredKey] = {}

    def store_key(self, alias: str, value: str) -> None:
        """Persist a new key using the provided alias."""
        if alias in self._keys:
            raise HSMError(f"Key alias {alias!r} already exists")
        self._keys[alias] = StoredKey(alias=alias, value=SecureString(value))
        logger.debug("Stored HSM key for alias %s", alias)

    def retrieve_key(self, alias: str) -> str:
        """Fetch the plaintext key for the alias."""
        key = self._keys.get(alias)
        if key is None:
            raise HSMError(f"Key alias {alias!r} not found")
        return key.value.value

    def rotate_key(self, alias: str, new_value: str) -> None:
        """Replace an existing key with a new secret."""
        if alias not in self._keys:
            raise HSMError(f"Key alias {alias!r} not found")
        self._keys[alias].value.zeroize()
        self._keys[alias] = StoredKey(alias=alias, value=SecureString(new_value))
        logger.info("Rotated HSM key for alias %s", alias)
