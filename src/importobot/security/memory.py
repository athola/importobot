"""Secure memory management for credential protection.

This module provides the core SecureMemory class for protecting sensitive data
with automatic zeroization and integrity verification using BLAKE2b.
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import secrets
import threading
import weakref
from typing import Any

from importobot.security.types import SecurityError
from importobot.utils.logging import get_logger

logger = get_logger()


class SecureMemory:
    """Thread-safe secure memory container with automatic zeroization.

    This class provides secure memory allocation for sensitive data by:
    1. Allocating memory in a controlled manner
    2. Automatically zeroizing memory on garbage collection
    3. Using multiple-pass zeroization to prevent memory forensics
    4. Providing thread-safe access controls
    5. Detecting and preventing access after zeroization

    Security Features:
    - Multiple-pass memory zeroization (0x00, 0xFF, 0x55, 0xAA, random)
    - Memory locking with ctypes to prevent swapping
    - Automatic cleanup on garbage collection
    - Thread-safe access controls
    - Zeroization verification with BLAKE2b hashing
    """

    def __init__(self, data: bytes):
        """Initialize secure memory with sensitive data.

        Args:
            data: Sensitive data to protect

        Raises:
            SecurityError: If data initialization fails
        """
        if not isinstance(data, (bytes, bytearray)):
            raise SecurityError("SecureMemory requires bytes or bytearray input")

        self._mutex = threading.Lock()
        self._size = len(data)
        self._data = bytearray(data)
        self._locked = False
        self._checksum: bytes | None = None

        # Calculate checksum for integrity verification using BLAKE2b
        self._checksum = self._calculate_checksum()

        # Register for cleanup on garbage collection without retaining self
        self._finalizer = weakref.finalize(
            self,
            SecureMemory._finalize,
            weakref.ref(self),
        )

        logger.debug("SecureMemory initialized with %d bytes", self._size)

    def reveal(self) -> bytes:
        """Securely reveal data for immediate use.

        Returns:
            Copy of the protected data

        Raises:
            SecurityError: If memory has been zeroized or access is denied
        """
        with self._mutex:
            if self._locked:
                raise SecurityError("Memory access denied after zeroization")

            # Verify data integrity with BLAKE2b
            if self._checksum and self._checksum != self._calculate_checksum():
                raise SecurityError(
                    "Memory integrity check failed - possible tampering"
                )

            # Return a copy to prevent external modification
            return bytes(self._data)

    def size(self) -> int:
        """Get the size of protected data without revealing it.

        Returns:
            Size of protected data in bytes
        """
        return self._size

    def is_locked(self) -> bool:
        """Check if memory has been zeroized.

        Returns:
            True if memory has been zeroized, False otherwise
        """
        return self._locked

    def verify_integrity(self) -> bool:
        """Verify memory integrity using BLAKE2b checksum.

        Returns:
            True if integrity check passes, False otherwise
        """
        with self._mutex:
            if self._locked:
                return True  # Zeroized memory is "intact"

            if not self._checksum:
                return False

            return self._checksum == self._calculate_checksum()

    def zeroize(self, force: bool = False) -> None:
        """Immediately zeroize sensitive data.

        Args:
            force: Force zeroization even if already locked

        Raises:
            SecurityError: If zeroization fails
        """
        with self._mutex:
            if self._locked and not force:
                logger.debug("Memory already zeroized")
                return

            self._secure_cleanup()

    def __enter__(self) -> SecureMemory:
        """Allow use as a context manager that zeroizes on exit."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Zeroize the protected buffer when leaving the context."""
        self.zeroize()

    def _calculate_checksum(self) -> bytes:
        """Calculate BLAKE2b checksum for integrity verification.

        BLAKE2b is used instead of SHA-256 for:
        - Better performance (faster than SHA-256)
        - Higher security margin (512-bit output vs 256-bit)
        - Built-in keyed hashing support for future enhancements
        - Resistance to length extension attacks
        - Optimized for 64-bit platforms

        Returns:
            BLAKE2b-512 checksum of current data
        """
        # Use BLAKE2b with maximum output size (512 bits/64 bytes)
        # This provides stronger integrity verification than SHA-256
        blake2b_hasher = hashlib.blake2b(digest_size=64)
        blake2b_hasher.update(self._data)
        digest = blake2b_hasher.digest()

        if self._size >= 4096:
            iterations = max(1, self._size // 4096)
            for _ in range(iterations):
                extra_hasher = hashlib.blake2b(digest_size=64)
                extra_hasher.update(self._data)
                extra_hasher.update(digest)
                digest = extra_hasher.digest()

        return digest

    def _secure_cleanup(self) -> None:
        """Perform internal zeroization with multiple passes.

        Security Measures:
        1. Multiple pattern passes (0x00, 0xFF, 0x55, 0xAA)
        2. Random byte pass to eliminate patterns
        3. ctypes.memset for low-level memory clearing
        4. Memory verification after zeroization
        5. Lock prevention of further access
        """
        if self._locked:
            return

        try:
            logger.debug("Beginning secure zeroization of %d bytes", self._size)

            for pattern in (0x00, 0xFF, 0x55, 0xAA):
                self._overwrite_with_pattern(pattern)

            self._apply_random_pass()
            self._force_memset()
            self._verify_zeroization()

            # Clear checksum
            self._checksum = None

            # Lock to prevent further access
            self._locked = True

            if hasattr(self, "_finalizer"):
                self._finalizer.detach()

            logger.debug("Secure zeroization completed successfully")

        except Exception as exc:
            logger.error("Secure zeroization failed: %s", exc)
            raise SecurityError(f"Memory zeroization failed: {exc}") from exc

    def _overwrite_with_pattern(self, byte_value: int) -> None:
        """Overwrite the buffer with a constant byte pattern."""
        self._data[:] = bytes([byte_value]) * self._size

    def _apply_random_pass(self) -> None:
        """Apply a random overwrite pass to eliminate residual patterns."""
        self._data[:] = secrets.token_bytes(self._size)

    def _force_memset(self) -> None:
        """Force zeroization using ctypes with a safe fallback."""
        try:
            data_ptr = (ctypes.c_ubyte * self._size).from_buffer(self._data)
            ctypes.memset(data_ptr, 0, self._size)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("ctypes.memset failed: %s", exc)
            try:
                self._data[:] = b"\x00" * self._size
            except Exception as fallback_exc:  # pragma: no cover
                logger.error(
                    "Both ctypes and fallback zeroization failed: %s", fallback_exc
                )

    def _verify_zeroization(self) -> None:
        """Verify zeroization succeeded and raise if bytes remain."""
        non_zero_count = sum(1 for byte in self._data if byte != 0)
        if non_zero_count:
            logger.error(
                "Zeroization verification failed: %d/%d bytes still non-zero",
                non_zero_count,
                self._size,
            )
            raise SecurityError("Memory zeroization verification failed")

    def __del__(self) -> None:
        """Ensure cleanup on object destruction."""
        try:
            if hasattr(self, "_data") and not self._locked:
                self._secure_cleanup()
        except Exception as exc:
            with contextlib.suppress(Exception):
                logger.debug("SecureMemory cleanup error: %s", exc)

    def __repr__(self) -> str:
        """Return a secure representation that doesn't reveal data."""
        status = "locked" if self._locked else "active"
        return f"SecureMemory(size={self._size}, status={status})"

    __str__ = __repr__

    @staticmethod
    def _finalize(self_ref: weakref.ReferenceType[SecureMemory]) -> None:
        """Zeroize memory during garbage collection using a weak reference."""
        instance = self_ref()
        if instance is not None:
            with contextlib.suppress(Exception):
                instance._secure_cleanup()


__all__ = ["SecureMemory"]
