"""Hardware Security Module (HSM) integration for managed key storage.

Implements providers (software, AWS CloudHSM, Azure Dedicated HSM, etc.),
derivation helpers, and rotation hooks that follow NIST SP 800-57 guidance.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import threading
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from importobot.exceptions import ImportobotError
from importobot.utils.runtime_paths import get_runtime_subdir

logger = logging.getLogger(__name__)


class HSMProvider(Enum):
    """Supported HSM providers."""

    SOFTWARE = "software"
    AWS_CLOUDHSM = "aws_cloudhsm"
    AZURE_DEDICATED_HSM = "azure_dedicated_hsm"
    THALES_LUNA = "thales_luna"
    UTIMACO_SENTRY = "utimaco_sentry"
    SOFTHSM = "softhsm"


@dataclass
class HSMKeyMetadata:
    """Metadata for HSM-managed keys."""

    key_id: str
    key_type: str
    key_size: int
    creation_date: datetime
    last_rotation: datetime | None
    next_rotation: datetime
    usage_count: int
    max_usage_count: int | None
    algorithm: str
    provider: HSMProvider
    is_active: bool
    version: int


class HSMError(ImportobotError):
    """Base exception for HSM operations."""

    pass


class HSMConnectionError(HSMError):
    """HSM connection or communication errors."""

    pass


class HSMKeyError(HSMError):
    """HSM key management errors."""

    pass


class HSMProviderUnavailableError(HSMError):
    """Raised when HSM provider is not available."""

    pass


class KeyRotationError(HSMError):
    """Key rotation operation errors."""

    pass


class HSMInterface(ABC):
    """Abstract interface for HSM providers."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to HSM."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close HSM connection."""
        pass

    @abstractmethod
    def generate_key(
        self, key_type: str, key_size: int, algorithm: str | None = None
    ) -> str:
        """Generate a new key in HSM."""
        pass

    @abstractmethod
    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive encryption key from HSM master key."""
        pass

    @abstractmethod
    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt data using HSM-managed key."""
        pass

    @abstractmethod
    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt data using HSM-managed key."""
        pass

    @abstractmethod
    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using HSM-managed key."""
        pass

    @abstractmethod
    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature using HSM-managed key."""
        pass

    @abstractmethod
    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Retrieve key metadata from HSM."""
        pass

    @abstractmethod
    def rotate_key(self, key_id: str) -> str:
        """Rotate an existing key."""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> None:
        """Delete a key from HSM."""
        pass

    @abstractmethod
    def list_keys(self) -> list[str]:
        """List all keys in HSM."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if HSM is connected."""
        pass


class SoftwareHSMProvider(HSMInterface):
    """Software-based HSM implementation for development and testing.

    This implementation provides HSM-like functionality using software
    encryption. It maintains compatibility with the HSM interface but
    operates entirely in software.
    """

    def __init__(self, storage_path: str | Path | None = None):
        """Initialize software HSM provider."""
        if storage_path is not None:
            self._storage_path = Path(storage_path)
            self._storage_path.mkdir(parents=True, exist_ok=True)
        else:
            self._storage_path = get_runtime_subdir("hsm")
        self._keys_file = self._storage_path / "keys.json"
        self._connected = False
        self._lock = threading.Lock()
        self._keys: dict[str, dict[str, Any]] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load keys from storage."""
        try:
            if self._keys_file.exists():
                with open(self._keys_file, encoding="utf-8") as f:
                    self._keys = json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load keys from {self._keys_file}: {exc}")
            self._keys = {}

    def _save_keys(self) -> None:
        """Save keys to storage."""
        try:
            with open(self._keys_file, "w", encoding="utf-8") as f:
                json.dump(self._keys, f, indent=2, default=str)
        except Exception as exc:
            logger.error(f"Failed to save keys to {self._keys_file}: {exc}")
            raise HSMError(f"Failed to save keys: {exc}") from exc

    def _derive_key_material(self, key_id: str, context: bytes | None = None) -> bytes:
        """Derive key material using PBKDF2."""
        key_data = self._keys[key_id]["key_material"]
        salt = context or b"importobot_hsm_derivation"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(key_data.encode())

    def connect(self) -> None:
        """Establish connection (no-op for software HSM)."""
        with self._lock:
            self._connected = True
            logger.debug("Software HSM connected")

    def disconnect(self) -> None:
        """Close connection (no-op for software HSM)."""
        with self._lock:
            self._connected = False
            logger.debug("Software HSM disconnected")

    def generate_key(
        self, key_type: str = "AES", key_size: int = 256, algorithm: str | None = None
    ) -> str:
        """Generate a new key."""
        # secrets imported at top level

        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        key_id = f"key_{secrets.token_hex(16)}"
        key_material = secrets.token_urlsafe(key_size // 8)

        now = datetime.now(timezone.utc)
        self._keys[key_id] = {
            "key_material": key_material,
            "key_type": key_type,
            "key_size": key_size,
            "algorithm": algorithm or "AES-256-GCM",
            "creation_date": now.isoformat(),
            "last_rotation": now.isoformat(),
            "next_rotation": (now + timedelta(days=90)).isoformat(),
            "usage_count": 0,
            "max_usage_count": 1000000,
            "provider": HSMProvider.SOFTWARE.value,
            "is_active": True,
            "version": 1,
        }

        self._save_keys()
        logger.info(f"Generated software HSM key: {key_id}")
        return key_id

    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive encryption key from master key."""
        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        derived_key = self._derive_key_material(key_id, context)
        self._keys[key_id]["usage_count"] += 1
        self._save_keys()

        return derived_key

    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt data using HSM key."""
        # secrets imported at top level

        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        key_material = self._derive_key_material(key_id)
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM

        cipher = Cipher(algorithms.AES(key_material), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()

        # Combine IV + ciphertext + tag
        encrypted_data = iv + ciphertext + encryptor.tag

        self._keys[key_id]["usage_count"] += 1
        self._save_keys()

        return encrypted_data

    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt data using HSM key."""
        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        if len(ciphertext) < 28:  # 12 bytes IV + 16 bytes tag minimum
            raise HSMError("Invalid ciphertext length")

        key_material = self._derive_key_material(key_id)
        iv = ciphertext[:12]
        tag = ciphertext[-16:]
        data = ciphertext[12:-16]

        cipher = Cipher(algorithms.AES(key_material), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()

        try:
            plaintext = decryptor.update(data) + decryptor.finalize()
        except InvalidTag as exc:
            raise HSMError("Invalid ciphertext or authentication tag") from exc

        return plaintext

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using HMAC."""
        # hmac imported at top level

        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        key_material = self._derive_key_material(key_id)
        signature = hmac.new(key_material, data, digestmod="sha256").digest()

        self._keys[key_id]["usage_count"] += 1
        self._save_keys()

        return signature

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify HMAC signature."""
        # hmac imported at top level

        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        key_material = self._derive_key_material(key_id)
        expected_signature = hmac.new(key_material, data, digestmod="sha256").digest()

        return hmac.compare_digest(signature, expected_signature)

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get key metadata."""
        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        key_data = self._keys[key_id]
        return HSMKeyMetadata(
            key_id=key_id,
            key_type=key_data["key_type"],
            key_size=key_data["key_size"],
            creation_date=datetime.fromisoformat(key_data["creation_date"]),
            last_rotation=datetime.fromisoformat(key_data["last_rotation"]),
            next_rotation=datetime.fromisoformat(key_data["next_rotation"]),
            usage_count=key_data["usage_count"],
            max_usage_count=key_data["max_usage_count"],
            algorithm=key_data["algorithm"],
            provider=HSMProvider.SOFTWARE,
            is_active=key_data["is_active"],
            version=key_data["version"],
        )

    def rotate_key(self, key_id: str) -> str:
        """Rotate an existing key."""
        # secrets imported at top level

        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        # Generate new key material
        old_key = self._keys[key_id]
        new_key_material = secrets.token_urlsafe(old_key["key_size"] // 8)

        # Update key
        old_key["key_material"] = new_key_material
        now = datetime.now(timezone.utc)
        old_key["last_rotation"] = now.isoformat()
        old_key["next_rotation"] = (now + timedelta(days=90)).isoformat()
        old_key["version"] += 1
        old_key["usage_count"] = 0

        self._save_keys()
        logger.info(f"Rotated software HSM key: {key_id}")
        return key_id

    def delete_key(self, key_id: str) -> None:
        """Delete a key."""
        if not self._connected:
            raise HSMConnectionError("HSM not connected")

        if key_id not in self._keys:
            raise HSMKeyError(f"Key {key_id} not found")

        del self._keys[key_id]
        self._save_keys()
        logger.info(f"Deleted software HSM key: {key_id}")

    def list_keys(self) -> list[str]:
        """List all keys."""
        return list(self._keys.keys())

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected


class HSMManager:
    """Hardware Security Module manager for Importobot credential workflows.

    This class provides a unified interface for HSM operations across
    different providers, including software fallback for development.
    """

    def __init__(self, provider: str | HSMProvider | None = None):
        """Initialize HSM manager.

        Args:
            provider: HSM provider to use. If None, auto-detects or uses software.
        """
        self._provider_name = self._determine_provider(provider)
        self._hsm: HSMInterface | None = None
        self._lock = threading.Lock()
        self._connected = False

    def _determine_provider(self, provider: str | HSMProvider | None) -> HSMProvider:
        """Determine which HSM provider to use."""
        if provider is None:
            # Auto-detect based on environment
            if os.getenv("AWS_CLOUDHSM_KEY_ID"):
                return HSMProvider.AWS_CLOUDHSM
            elif os.getenv("AZURE_KEYVAULT_URL"):
                return HSMProvider.AZURE_DEDICATED_HSM
            elif os.getenv("HSM_PROVIDER"):
                try:
                    return HSMProvider(os.getenv("HSM_PROVIDER", "").lower())
                except ValueError:
                    pass

            return HSMProvider.SOFTWARE

        if isinstance(provider, str):
            return HSMProvider(provider.lower())

        return provider

    def _initialize_hsm(self) -> HSMInterface:
        """Initialize the appropriate HSM provider."""
        if self._provider_name == HSMProvider.SOFTWARE:
            return SoftwareHSMProvider()
        elif self._provider_name == HSMProvider.AWS_CLOUDHSM:
            return AWSCloudHSMProvider()
        elif self._provider_name == HSMProvider.AZURE_DEDICATED_HSM:
            return AzureDedicatedHSMProvider()
        elif self._provider_name == HSMProvider.THALES_LUNA:
            return ThalesLunaProvider()
        elif self._provider_name == HSMProvider.UTIMACO_SENTRY:
            return UtimacoSentryProvider()
        elif self._provider_name == HSMProvider.SOFTHSM:
            return SoftHSMProvider()
        else:
            raise HSMProviderUnavailableError(
                f"Unsupported HSM provider: {self._provider_name}"
            )

    def connect(self) -> None:
        """Connect to HSM."""
        with self._lock:
            if self._connected:
                return

            try:
                if self._hsm is None:
                    self._hsm = self._initialize_hsm()

                self._hsm.connect()
                self._connected = True
                logger.info(f"Connected to HSM provider: {self._provider_name.value}")

            except HSMProviderUnavailableError:
                raise
            except Exception as exc:
                raise HSMConnectionError(f"Failed to connect to HSM: {exc}") from exc

    def disconnect(self) -> None:
        """Disconnect from HSM."""
        with self._lock:
            if not self._connected:
                return

            try:
                if self._hsm:
                    self._hsm.disconnect()
                self._connected = False
                logger.info("Disconnected from HSM")

            except Exception as exc:
                logger.warning(f"Error disconnecting from HSM: {exc}")

    @property
    def is_connected(self) -> bool:
        """Check if HSM is connected."""
        return self._connected and (self._hsm is not None) and self._hsm.is_connected

    def ensure_connected(self) -> None:
        """Ensure HSM is connected, raising error if not."""
        if not self.is_connected:
            raise HSMConnectionError("HSM not connected. Call connect() first.")

    # Key management operations
    def generate_key(
        self, key_type: str = "AES", key_size: int = 256, algorithm: str | None = None
    ) -> str:
        """Generate a new encryption key in HSM."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.generate_key(key_type, key_size, algorithm)

    def encrypt_credential(self, key_id: str, credential: str) -> bytes:
        """Encrypt a credential using HSM."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.encrypt_data(key_id, credential.encode())

    def decrypt_credential(self, key_id: str, encrypted_credential: bytes) -> str:
        """Decrypt a credential using HSM."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.decrypt_data(key_id, encrypted_credential).decode()

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using HSM."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.sign_data(key_id, data)

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature using HSM."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.verify_signature(key_id, data, signature)

    def rotate_key(self, key_id: str) -> str:
        """Rotate an existing key."""
        self.ensure_connected()
        assert self._hsm is not None

        try:
            new_key_id = self._hsm.rotate_key(key_id)
            logger.info(f"Successfully rotated key: {key_id}")
            return new_key_id
        except Exception as exc:
            raise KeyRotationError(f"Failed to rotate key {key_id}: {exc}") from exc

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get key metadata."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.get_key_metadata(key_id)

    def list_keys(self) -> list[str]:
        """List all keys."""
        self.ensure_connected()
        assert self._hsm is not None
        return self._hsm.list_keys()

    def delete_key(self, key_id: str) -> None:
        """Delete a key."""
        self.ensure_connected()
        assert self._hsm is not None
        self._hsm.delete_key(key_id)

    @contextmanager
    def managed_session(self) -> Generator[HSMManager, None, None]:
        """Context manager for HSM session management."""
        self.connect()
        try:
            yield self
        finally:
            self.disconnect()


# Placeholder implementations for other HSM providers
# These would be implemented based on specific vendor SDKs


class AWSCloudHSMProvider(HSMInterface):
    """AWS CloudHSM provider implementation."""

    def connect(self) -> None:
        """Connect to AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def disconnect(self) -> None:
        """Disconnect from AWS CloudHSM."""
        pass

    def generate_key(
        self, key_type: str, key_size: int, algorithm: str | None = None
    ) -> str:
        """Generate key in AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive key from AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt with AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt with AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign with AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify with AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get metadata from AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def rotate_key(self, key_id: str) -> str:
        """Rotate key in AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def delete_key(self, key_id: str) -> None:
        """Delete key from AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    def list_keys(self) -> list[str]:
        """List keys in AWS CloudHSM."""
        raise HSMProviderUnavailableError("AWS CloudHSM provider not implemented")

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return False


class AzureDedicatedHSMProvider(HSMInterface):
    """Azure Dedicated HSM provider implementation."""

    def connect(self) -> None:
        """Connect to Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def disconnect(self) -> None:
        """Disconnect from Azure Dedicated HSM."""
        pass

    def generate_key(
        self, key_type: str, key_size: int, algorithm: str | None = None
    ) -> str:
        """Generate key in Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive key from Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt with Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt with Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign with Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify with Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get metadata from Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def rotate_key(self, key_id: str) -> str:
        """Rotate key in Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def delete_key(self, key_id: str) -> None:
        """Delete key from Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    def list_keys(self) -> list[str]:
        """List keys in Azure Dedicated HSM."""
        raise HSMProviderUnavailableError(
            "Azure Dedicated HSM provider not implemented"
        )

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return False


class ThalesLunaProvider(HSMInterface):
    """Thales Luna HSM provider implementation."""

    def connect(self) -> None:
        """Connect to Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def disconnect(self) -> None:
        """Disconnect from Thales Luna HSM."""
        pass

    def generate_key(
        self, key_type: str, key_size: int, algorithm: str | None = None
    ) -> str:
        """Generate key in Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive key from Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt with Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt with Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign with Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify with Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get metadata from Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def rotate_key(self, key_id: str) -> str:
        """Rotate key in Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def delete_key(self, key_id: str) -> None:
        """Delete key from Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    def list_keys(self) -> list[str]:
        """List keys in Thales Luna HSM."""
        raise HSMProviderUnavailableError("Thales Luna provider not implemented")

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return False


class UtimacoSentryProvider(HSMInterface):
    """Utimaco Sentry HSM provider implementation."""

    def connect(self) -> None:
        """Connect to Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def disconnect(self) -> None:
        """Disconnect from Utimaco Sentry HSM."""
        pass

    def generate_key(
        self, key_type: str, key_size: int, algorithm: str | None = None
    ) -> str:
        """Generate key in Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive key from Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt with Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt with Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign with Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify with Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get metadata from Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def rotate_key(self, key_id: str) -> str:
        """Rotate key in Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def delete_key(self, key_id: str) -> None:
        """Delete key from Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    def list_keys(self) -> list[str]:
        """List keys in Utimaco Sentry HSM."""
        raise HSMProviderUnavailableError("Utimaco Sentry provider not implemented")

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return False


class SoftHSMProvider(HSMInterface):
    """SoftHSM provider implementation."""

    def connect(self) -> None:
        """Connect to SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def disconnect(self) -> None:
        """Disconnect from SoftHSM."""
        pass

    def generate_key(
        self, key_type: str, key_size: int, algorithm: str | None = None
    ) -> str:
        """Generate key in SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def derive_key(
        self, key_id: str, context: bytes | None = None, length: int = 32
    ) -> bytes:
        """Derive key from SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt with SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def decrypt_data(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt with SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign with SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify with SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def get_key_metadata(self, key_id: str) -> HSMKeyMetadata:
        """Get metadata from SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def rotate_key(self, key_id: str) -> str:
        """Rotate key in SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def delete_key(self, key_id: str) -> None:
        """Delete key from SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    def list_keys(self) -> list[str]:
        """List keys in SoftHSM."""
        raise HSMProviderUnavailableError("SoftHSM provider not implemented")

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return False


# Global HSM manager instance
_hsm_manager: HSMManager | None = None
_hsm_lock = threading.Lock()


def get_hsm_manager(provider: str | HSMProvider | None = None) -> HSMManager:
    """Get the global HSM manager instance."""
    global _hsm_manager  # noqa: PLW0603

    with _hsm_lock:
        if _hsm_manager is None:
            _hsm_manager = HSMManager(provider)
        return _hsm_manager


def reset_hsm_manager() -> None:
    """Reset the global HSM manager (for testing)."""
    global _hsm_manager  # noqa: PLW0603

    with _hsm_lock:
        if _hsm_manager is not None:
            _hsm_manager.disconnect()
        _hsm_manager = None


__all__ = [
    "HSMConnectionError",
    "HSMError",
    "HSMInterface",
    "HSMKeyError",
    "HSMKeyMetadata",
    "HSMManager",
    "HSMProvider",
    "HSMProviderUnavailableError",
    "KeyRotationError",
    "SoftwareHSMProvider",
    "get_hsm_manager",
    "reset_hsm_manager",
]
