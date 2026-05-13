"""Software-backed key store for enterprise development scenarios.

PR #90 review C2: this module ships an in-memory key container, not a
real HSM. It is renamed to :class:`InMemoryKeyStore` so deployers
cannot mistake it for hardware-backed key storage. The previous
``SoftwareHSM`` alias remains for transitional compatibility and is
scheduled for removal in 0.2.0.

NOT FOR PRODUCTION SECRETS. Specifically this implementation:

- has no persistence (everything is lost on process exit);
- has no tamper protection or audit log;
- does not implement key escrow or quorum approval;
- uses ``threading.Lock`` for in-process mutual exclusion only;
- exposes the key plaintext via ``retrieve_key`` for callers that
  cannot operate on a :class:`SecureString` handle.

If a real HSM-shaped API is needed, define a ``BaseHSM`` Protocol and
let this class serve as a test fixture only.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from importobot.security.secure_memory import SecureString
from importobot.utils.logging import get_logger

logger = get_logger(__name__)


class HSMError(RuntimeError):
    """Raised when key-store operations fail."""


@dataclass
class StoredKey:
    """Represents a logical key stored in the in-memory key store."""

    alias: str
    value: SecureString


class InMemoryKeyStore:
    """In-memory key container using SecureString for zeroization.

    NOT A REAL HSM. See module docstring for the full caveats.
    """

    def __init__(self) -> None:
        """Initialize an empty key container."""
        self._keys: dict[str, StoredKey] = {}
        # Serialize mutating operations to remove the obvious TOCTOU
        # window the previous implementation exposed in
        # ``store_key`` / ``rotate_key`` (PR #90 review C2).
        self._mutex = Lock()

    def store_key(self, alias: str, value: str) -> None:
        """Persist a new key using the provided alias."""
        with self._mutex:
            if alias in self._keys:
                raise HSMError(f"Key alias {alias!r} already exists")
            self._keys[alias] = StoredKey(alias=alias, value=SecureString(value))
            logger.debug("Stored in-memory key for alias %s", alias)

    def retrieve_key(self, alias: str) -> str:
        """Fetch the plaintext key for the alias."""
        key = self._keys.get(alias)
        if key is None:
            raise HSMError(f"Key alias {alias!r} not found")
        return key.value.value

    def rotate_key(self, alias: str, new_value: str) -> None:
        """Replace an existing key with a new secret.

        Rolls back to the original key if constructing the new
        :class:`SecureString` fails - the previous version could leave
        the store half-rotated with the old key already zeroized.
        """
        with self._mutex:
            existing = self._keys.get(alias)
            if existing is None:
                raise HSMError(f"Key alias {alias!r} not found")
            try:
                replacement = SecureString(new_value)
            except Exception as exc:
                raise HSMError(
                    f"Failed to wrap replacement key for {alias!r}: {exc}"
                ) from exc
            existing.value.zeroize()
            self._keys[alias] = StoredKey(alias=alias, value=replacement)
            logger.info("Rotated in-memory key for alias %s", alias)


# Backwards-compatible alias (PR #90 review C2).
SoftwareHSM = InMemoryKeyStore
