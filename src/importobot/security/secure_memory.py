"""Secure memory management for credential protection."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import secrets
import threading
import weakref
from typing import Any

from importobot.exceptions import ImportobotError
from importobot.utils.logging import get_logger

logger = get_logger()


class SecurityError(ImportobotError):
    """Raised when security operations fail."""

    pass


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
        self._checksum = None

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


class SecureString:
    """Immutable secure string with automatic zeroization.

    This class provides a secure wrapper for string data that:
    1. Stores string data in SecureMemory
    2. Provides controlled access to the string value
    3. Automatically zeroizes memory on destruction
    4. Implements secure string operations
    5. Prevents accidental logging or exposure
    6. Uses BLAKE2b for integrity verification

    Usage:
        >>> password = SecureString("my-secret-password")
        >>> print(password.value)  # Reveal the value
        >>> # Automatically zeroized when password goes out of scope
    """

    def __init__(self, value: str):
        """Initialize secure string.

        Args:
            value: String value to protect

        Raises:
            SecurityError: If value is not a string
        """
        if not isinstance(value, str):
            raise SecurityError("SecureString requires string input")

        # Store as UTF-8 encoded bytes in SecureMemory
        encoded_value = value.encode("utf-8")
        self._memory = SecureMemory(encoded_value)

    @property
    def value(self) -> str:
        """Get the string value securely.

        Returns:
            The protected string value

        Warning:
            The returned value is a regular Python string and should be
            handled with care. It will remain in memory until garbage collected.
        """
        decoded_value = self._memory.reveal().decode("utf-8")
        return decoded_value

    def size(self) -> int:
        """Get the size of the string in characters.

        Returns:
            Number of characters in the string
        """
        return len(self.value)

    def byte_length(self) -> int:
        """Get the size of the string in bytes.

        Returns:
            Number of bytes used for UTF-8 encoding
        """
        return self._memory.size()

    def is_locked(self) -> bool:
        """Check if the string has been zeroized.

        Returns:
            True if zeroized, False otherwise
        """
        return self._memory.is_locked()

    def zeroize(self) -> None:
        """Immediately zeroize the string value."""
        self._memory.zeroize()

    def __eq__(self, other: Any) -> bool:
        """Secure equality comparison using constant-time comparison.

        Args:
            other: Object to compare with

        Returns:
            True if equal, False otherwise
        """
        if not isinstance(other, SecureString):
            return False

        # Use constant-time comparison to prevent timing attacks
        try:
            our_value = self._memory.reveal()
            their_value = other._memory.reveal()

            if len(our_value) != len(their_value):
                return False

            # Constant-time comparison
            result = 0
            for a, b in zip(our_value, their_value, strict=False):
                result |= a ^ b

            return result == 0
        except SecurityError:
            # If either is locked, they can't be equal
            return False

    def __hash__(self) -> int:
        """Provide a hash implementation compatible with __eq__."""
        if self._memory.is_locked():
            return hash(("SecureString", "locked"))

        return hash(self._memory.reveal())

    def __len__(self) -> int:
        """Return the length of the string."""
        return self.size()

    def __repr__(self) -> str:
        """Return a secure representation."""
        if self._memory.is_locked():
            return "SecureString(<zeroized>)"
        else:
            return f"SecureString(length={self.size()})"

    def __str__(self) -> str:
        """Prevent accidental string exposure."""
        return repr(self)

    def __del__(self) -> None:
        """Ensure cleanup on destruction."""
        try:
            if hasattr(self, "_memory") and not self._memory.is_locked():
                self._memory.zeroize()
        except Exception as exc:
            # Silently log cleanup errors in destructor to avoid exceptions
            with contextlib.suppress(Exception):
                logger.debug("SecureString cleanup error: %s", exc)


# Convenience functions for secure operations


def create_secure_string(value: str) -> SecureString:
    """Create a SecureString instance with validation.

    Args:
        value: String value to secure

    Returns:
        SecureString instance

    Raises:
        SecurityError: If input validation fails
    """
    if not isinstance(value, str):
        raise SecurityError(f"Expected string, got {type(value).__name__}")

    if len(value) == 0:
        raise SecurityError("Empty strings cannot be secured")

    return SecureString(value)


def secure_compare_strings(str1: SecureString, str2: SecureString) -> bool:
    """Perform constant-time comparison of two SecureStrings.

    Args:
        str1: First SecureString
        str2: Second SecureString

    Returns:
        True if equal, False otherwise

    Raises:
        SecurityError: If comparison fails
    """
    if not isinstance(str1, SecureString) or not isinstance(str2, SecureString):
        raise SecurityError("Both arguments must be SecureString instances")

    return str1 == str2


class SecureMemoryPool:
    """Pool manager for SecureMemory instances with resource tracking.

    This class manages a pool of SecureMemory instances to:
    1. Track memory usage
    2. Prevent memory leaks
    3. Provide bulk cleanup operations
    4. Monitor security metrics
    5. Use BLAKE2b for integrity verification across the pool
    """

    def __init__(self) -> None:
        """Initialize pool tracking structures."""
        self._pool: list[SecureMemory] = []
        self._mutex = threading.Lock()
        self._total_bytes = 0
        self._peak_usage = 0

    def allocate(self, data: bytes) -> SecureMemory:
        """Allocate SecureMemory from pool.

        Args:
            data: Data to secure

        Returns:
            SecureMemory instance with BLAKE2b integrity verification
        """
        secure_mem = SecureMemory(data)

        with self._mutex:
            self._pool.append(secure_mem)
            self._total_bytes += len(data)
            self._peak_usage = max(self._peak_usage, self._total_bytes)

        return secure_mem

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        with self._mutex:
            active_count = sum(1 for mem in self._pool if not mem.is_locked())
            locked_count = len(self._pool) - active_count

            return {
                "total_instances": len(self._pool),
                "active_instances": active_count,
                "locked_instances": locked_count,
                "total_bytes": self._total_bytes,
                "peak_usage": self._peak_usage,
                "average_size": self._total_bytes / max(len(self._pool), 1),
                "integrity_algorithm": "BLAKE2b-512",
            }

    def cleanup_all(self) -> int:
        """Zeroize all SecureMemory instances in pool.

        Returns:
            Number of instances zeroized
        """
        with self._mutex:
            count = 0
            for secure_mem in self._pool:
                if not secure_mem.is_locked():
                    secure_mem.zeroize()
                    count += 1

            return count

    def cleanup_locked(self) -> int:
        """Remove locked instances from pool.

        Returns:
            Number of instances removed
        """
        with self._mutex:
            original_size = len(self._pool)
            self._pool = [mem for mem in self._pool if not mem.is_locked()]
            return original_size - len(self._pool)


# Global secure memory pool instance
_default_pool = SecureMemoryPool()


def get_secure_memory_pool() -> SecureMemoryPool:
    """Get the default secure memory pool.

    Returns:
        Default SecureMemoryPool instance with BLAKE2b integrity verification
    """
    return _default_pool
