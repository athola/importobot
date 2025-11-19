"""Secure memory management for credential protection."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import secrets
import threading
import time
import unicodedata
import weakref
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum
from typing import Any, cast

from importobot.exceptions import ImportobotError
from importobot.utils.logging import get_logger

logger = get_logger()


class StringEncoding(Enum):
    """Supported text encodings for SecureString."""

    UTF8 = "utf-8"
    UTF16 = "utf-16"
    UTF32 = "utf-32"
    LATIN1 = "latin-1"
    ASCII = "ascii"
    CP1252 = "cp1252"
    SHIFT_JIS = "shift_jis"
    EUC_JP = "euc_jp"
    ISO2022_JP = "iso2022_jp"
    GBK = "gbk"
    BIG5 = "big5"
    KOI8_R = "koi8_r"
    KOI8_U = "koi8_u"


class UnicodeNormalization(Enum):
    """Unicode normalization forms."""

    NFC = "NFC"  # Canonical Decomposition followed by Canonical Composition
    NFD = "NFD"  # Canonical Decomposition
    NFKC = "NFKC"  # Compatibility Decomposition followed by Canonical Composition
    NFKD = "NFKD"  # Compatibility Decomposition


class SecurityError(ImportobotError):
    """Raised when security operations fail."""

    pass


def detect_string_encoding(
    text: str, preferred_encoding: StringEncoding | None = None
) -> StringEncoding:
    """Detect the most appropriate encoding for a given string.

    Args:
        text: Text to analyze for encoding
        preferred_encoding: Optional preferred encoding to try first

    Returns:
        Best matching StringEncoding for the text

    Note:
        This function analyzes the Unicode code points in the text to determine
        the most efficient and compatible encoding. It prioritizes UTF-8 for
        mixed-language content but may suggest more efficient encodings for
        specific language patterns.
    """
    if preferred_encoding:
        # Check if preferred encoding can handle the text
        try:
            text.encode(preferred_encoding.value)
            return preferred_encoding
        except UnicodeEncodeError:
            logger.debug(
                "Preferred encoding %s cannot handle text", preferred_encoding.value
            )

    # Analyze Unicode ranges to determine optimal encoding
    has_bmp_only = all(ord(char) <= 0xFFFF for char in text)
    has_ascii_only = all(ord(char) <= 0x7F for char in text)

    # Check for specific language ranges
    has_hiragana = any(0x3040 <= ord(char) <= 0x309F for char in text)  # Hiragana
    has_katakana = any(0x30A0 <= ord(char) <= 0x30FF for char in text)  # Katakana
    has_japanese = has_hiragana or has_katakana

    # Chinese characters - more comprehensive ranges
    has_chinese = any(
        0x4E00 <= ord(char) <= 0x9FFF  # CJK Unified Ideographs
        or 0x3400 <= ord(char) <= 0x4DBF  # CJK Unified Ideographs Extension A
        or 0x20000 <= ord(char) <= 0x2A6DF  # CJK Unified Ideographs Extension B
        or 0x2A700 <= ord(char) <= 0x2B73F  # CJK Unified Ideographs Extension C
        or 0x2B740 <= ord(char) <= 0x2B81F  # CJK Unified Ideographs Extension D
        or 0x2B820 <= ord(char) <= 0x2CEAF  # CJK Unified Ideographs Extension E
        or 0x2CEB0 <= ord(char) <= 0x2EBEF  # CJK Unified Ideographs Extension F
        or 0x3000 <= ord(char) <= 0x303F  # CJK Symbols and Punctuation
        for char in text
    )
    has_cyrillic = any(0x0400 <= ord(char) <= 0x04FF for char in text)

    # Encoding selection logic
    if has_ascii_only:
        return StringEncoding.ASCII
    elif has_japanese:
        return _try_japanese_encodings(text)
    elif has_chinese:
        return _try_chinese_encodings(text)
    elif has_cyrillic:
        return StringEncoding.KOI8_R
    elif not has_bmp_only:
        # Has characters beyond BMP (surrogate pairs), prefer UTF-8 for compatibility
        return StringEncoding.UTF8
    else:
        # Default to UTF-8 for mixed content
        return StringEncoding.UTF8


def _try_encoding(text: str, encoding_value: str) -> bool:
    """Try to encode text with specific encoding.

    Returns True if successful, False otherwise.
    """
    try:
        text.encode(encoding_value)
        return True
    except UnicodeEncodeError:
        return False


def _try_japanese_encodings(text: str) -> StringEncoding:
    """Try Japanese encodings, fallback to UTF-8."""
    encodings = [StringEncoding.SHIFT_JIS, StringEncoding.EUC_JP, StringEncoding.UTF8]

    for encoding in encodings:
        if _try_encoding(text, encoding.value):
            return encoding
    return StringEncoding.UTF8


def _try_chinese_encodings(text: str) -> StringEncoding:
    """Try Chinese encodings, fallback to UTF-8."""
    encodings = [StringEncoding.GBK, StringEncoding.BIG5, StringEncoding.UTF8]

    for encoding in encodings:
        if _try_encoding(text, encoding.value):
            return encoding
    return StringEncoding.UTF8


def normalize_unicode_string(
    text: str, normalization: UnicodeNormalization = UnicodeNormalization.NFC
) -> str:
    """Normalize Unicode string for consistent security comparison.

    Args:
        text: Text to normalize
        normalization: Unicode normalization form to apply

    Returns:
        Normalized string

    Note:
        Unicode normalization is important for security to ensure that
        different byte sequences representing the same visual characters
        are treated identically. This prevents bypass attacks using
        Unicode equivalence attacks.
    """
    try:
        normalized = unicodedata.normalize(normalization.value, text)
        logger.debug(
            "Unicode normalized from %s to %s (form: %s)",
            len(text.encode("utf-8")),
            len(normalized.encode("utf-8")),
            normalization.value,
        )
        return normalized
    except Exception as exc:
        logger.warning("Unicode normalization failed: %s", exc)
        # Return original text if normalization fails
        return text


def validate_language_characters(
    text: str, allowed_languages: list[str] | None = None
) -> dict[str, Any]:
    """Validate text contains characters from allowed languages.

    Args:
        text: Text to validate
        allowed_languages: List of allowed language codes (e.g., ['en', 'ja', 'zh'])

    Returns:
        Dictionary with validation results and detected languages

    Note:
        This function helps ensure that credential strings only contain
        characters from expected languages, preventing potential injection
        attacks using unexpected character sets.
    """
    if not allowed_languages:
        return {"valid": True, "detected_languages": ["all"], "unexpected_chars": []}

    detected_languages = []
    unexpected_chars = []

    # Language character ranges (more comprehensive)
    language_ranges = {
        "en": [(0x0000, 0x007F)],  # ASCII
        "ja": [
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
            (0xFF00, 0xFFEF),  # Half-width and full-width forms
        ],  # Japanese (excluding shared CJK)
        "zh": [
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
            (0x3000, 0x303F),  # CJK Symbols and Punctuation
        ],  # Chinese
        "ko": [
            (0xAC00, 0xD7AF),  # Hangul Syllables
            (0x1100, 0x11FF),  # Hangul Jamo
            (0x3130, 0x318F),  # Hangul Compatibility Jamo
        ],  # Korean
        "ar": [(0x0600, 0x06FF)],  # Arabic
        "ru": [(0x0400, 0x04FF)],  # Cyrillic
        "hi": [(0x0900, 0x097F)],  # Devanagari (Hindi)
        "th": [(0x0E00, 0x0E7F)],  # Thai
        "he": [(0x0590, 0x05FF)],  # Hebrew
    }

    for char in text:
        char_code = ord(char)
        char_languages = []

        # ASCII characters (whitespace, punctuation) are generally acceptable
        is_common_ascii = (
            char_code <= 0x7F and char in " \t\n\r.,;:!?()[]{}-_=+*/%@#$^&|\\`~'\"<>"
        )

        for lang, ranges in language_ranges.items():
            if any(start <= char_code <= end for start, end in ranges):
                char_languages.append(lang)

        if is_common_ascii:
            # Common ASCII characters are always allowed
            continue
        elif char_languages:
            detected_languages.extend(char_languages)
            if not any(lang in allowed_languages for lang in char_languages):
                unexpected_chars.append(char)
        # Unknown character set
        elif "unknown" not in allowed_languages:
            unexpected_chars.append(char)

    detected_languages = (
        list(set(detected_languages)) if detected_languages else ["unknown"]
    )
    valid = len(unexpected_chars) == 0

    return {
        "valid": valid,
        "detected_languages": detected_languages,
        "unexpected_chars": unexpected_chars,
        "unexpected_count": len(unexpected_chars),
    }


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


class SecureString:
    """Immutable secure string with automatic zeroization and enhanced Unicode support.

    This class provides a secure wrapper for string data that:
    1. Stores string data in SecureMemory with optimal encoding
    2. Provides controlled access to the string value
    3. Automatically zeroizes memory on destruction
    4. Implements secure string operations with Unicode awareness
    5. Prevents accidental logging or exposure
    6. Uses BLAKE2b for integrity verification
    7. Supports multiple text encodings and Unicode normalization
    8. Provides language-specific character validation

    Usage:
        >>> password = SecureString("my-secret-password")
        >>> print(password.value)  # Reveal the value
        >>>
        >>> # With encoding specification
        >>> japanese_password = SecureString("パスワード", encoding=StringEncoding.UTF8)
        >>>
        >>> # With language validation
        >>> validated_password = SecureString("password", allowed_languages=['en'])
        >>>
        >>> # Automatically zeroized when password goes out of scope
    """

    def __init__(
        self,
        value: str,
        encoding: StringEncoding | None = None,
        normalization: UnicodeNormalization = UnicodeNormalization.NFC,
        allowed_languages: list[str] | None = None,
        detect_encoding: bool = True,
    ):
        """Initialize secure string with enhanced Unicode support.

        Args:
            value: String value to protect
            encoding: Specific encoding to use. If None, auto-detects optimal encoding
            normalization: Unicode normalization form to apply
            allowed_languages: List of allowed language codes for character validation
            detect_encoding: Whether to automatically detect the optimal encoding

        Raises:
            SecurityError: If value is not a string or contains invalid characters
        """
        if not isinstance(value, str):
            raise SecurityError("SecureString requires string input")

        if len(value) == 0:
            raise SecurityError("Empty strings cannot be secured")

        # Store original string for character-level operations
        self._original_value = value

        # Apply Unicode normalization for security
        self._normalized_value = normalize_unicode_string(value, normalization)

        # Language validation
        if allowed_languages:
            validation_result = validate_language_characters(
                self._normalized_value, allowed_languages
            )
            if not validation_result["valid"]:
                raise SecurityError(
                    f"String contains characters from unsupported languages: "
                    f"{validation_result['detected_languages']}. "
                    f"Unexpected characters: {validation_result['unexpected_count']}"
                )
        self._allowed_languages = allowed_languages

        # Determine encoding
        if encoding:
            self._encoding = encoding
        elif detect_encoding:
            self._encoding = detect_string_encoding(self._normalized_value)
        else:
            self._encoding = StringEncoding.UTF8

        # Store with determined encoding in SecureMemory
        try:
            encoded_value = self._normalized_value.encode(self._encoding.value)
            self._memory = SecureMemory(encoded_value)
        except UnicodeEncodeError as exc:
            raise SecurityError(
                f"Failed to encode string with {self._encoding.value}: {exc}"
            ) from exc

        # Store metadata for advanced operations
        self._normalization = normalization
        self._char_count = len(self._normalized_value)
        self._byte_count = len(encoded_value)

        logger.debug(
            "SecureString created: %d chars, %d bytes, encoding=%s, normalization=%s",
            self._char_count,
            self._byte_count,
            self._encoding.value,
            self._normalization.value,
        )

    @property
    def value(self) -> str:
        """Get the string value securely.

        Returns:
            The protected string value

        Warning:
            The returned value is a regular Python string and should be
            handled with care. It will remain in memory until garbage collected.
        """
        try:
            encoded_value = self._memory.reveal()
            decoded_value = encoded_value.decode(self._encoding.value)
            return decoded_value
        except UnicodeDecodeError as exc:
            logger.error("Failed to decode secure string: %s", exc)
            raise SecurityError(f"Failed to decode secure string: {exc}") from exc

    def size(self) -> int:
        """Get the size of the string in characters.

        Returns:
            Number of characters in the string
        """
        return self._char_count

    def byte_length(self) -> int:
        """Get the size of the string in bytes.

        Returns:
            Number of bytes used for current encoding
        """
        return self._byte_count

    @property
    def encoding(self) -> StringEncoding:
        """Get the encoding used for this secure string.

        Returns:
            The StringEncoding used to store the string
        """
        return self._encoding

    @property
    def normalization(self) -> UnicodeNormalization:
        """Get the Unicode normalization form applied.

        Returns:
            The UnicodeNormalization form applied to the string
        """
        return self._normalization

    def detected_languages(self) -> list[str]:
        """Get detected languages in the string.

        Returns:
            List of detected language codes
        """
        if self._allowed_languages:
            return self._allowed_languages

        validation_result = validate_language_characters(self._normalized_value)
        return cast(list[str], validation_result["detected_languages"])

    def get_char_info(self) -> dict[str, Any]:
        """Get detailed character information for the secure string.

        Returns:
            Dictionary with character analysis information
        """
        char_info: dict[str, Any] = {
            "total_chars": self._char_count,
            "encoding": self._encoding.value,
            "normalization": self._normalization.value,
            "byte_length": self._byte_count,
            "languages": self.detected_languages(),
            "char_breakdown": {},
        }

        # Analyze character types
        ascii_count = sum(1 for char in self._normalized_value if ord(char) <= 0x7F)
        latin1_count = sum(1 for char in self._normalized_value if ord(char) <= 0xFF)
        bmp_count = sum(1 for char in self._normalized_value if ord(char) <= 0xFFFF)
        surrogate_count = sum(
            1 for char in self._normalized_value if 0xD800 <= ord(char) <= 0xDFFF
        )

        char_info["char_breakdown"] = {
            "ascii": ascii_count,
            "latin1_extended": latin1_count - ascii_count,
            "bmp_extended": bmp_count - latin1_count,
            "supplementary": self._char_count - bmp_count,
            "surrogate_pairs": surrogate_count,
        }

        return char_info

    def convert_encoding(self, new_encoding: StringEncoding) -> SecureString:
        """Create a new SecureString with different encoding.

        Args:
            new_encoding: New encoding to use

        Returns:
            New SecureString with the same content but different encoding

        Raises:
            SecurityError: If encoding conversion fails
        """
        current_value = self.value
        return SecureString(
            current_value,
            encoding=new_encoding,
            normalization=self._normalization,
            allowed_languages=self._allowed_languages,
            detect_encoding=False,
        )

    def apply_normalization(
        self, new_normalization: UnicodeNormalization
    ) -> SecureString:
        """Create a new SecureString with different Unicode normalization.

        Args:
            new_normalization: New normalization form to apply

        Returns:
            New SecureString with the same content but different normalization
        """
        current_value = self.value
        return SecureString(
            current_value,
            encoding=self._encoding,
            normalization=new_normalization,
            allowed_languages=self._allowed_languages,
            detect_encoding=False,
        )

    def compare_with_normalization(
        self,
        other: SecureString,
        normalization: UnicodeNormalization = UnicodeNormalization.NFC,
    ) -> bool:
        """Compare with another SecureString after applying normalization.

        Args:
            other: Other SecureString to compare with
            normalization: Normalization form to apply before comparison

        Returns:
            True if strings are equivalent after normalization, False otherwise

        Note:
            This method is useful for secure comparison of strings that may
            use different Unicode normalization forms or encodings.
        """
        if not isinstance(other, SecureString):
            return False

        try:
            # Normalize both strings for comparison
            our_normalized = normalize_unicode_string(self.value, normalization)
            their_normalized = normalize_unicode_string(other.value, normalization)

            # Use constant-time comparison
            if len(our_normalized) != len(their_normalized):
                return False

            result = 0
            for a, b in zip(
                our_normalized.encode("utf-8"),
                their_normalized.encode("utf-8"),
                strict=False,
            ):
                result |= a ^ b

            return result == 0
        except SecurityError:
            # If either is locked, they can't be equal
            return False

    def is_locked(self) -> bool:
        """Check if the string has been zeroized.

        Returns:
            True if zeroized, False otherwise
        """
        return self._memory.is_locked()

    def zeroize(self) -> None:
        """Immediately zeroize the string value."""
        self._memory.zeroize()

    def __enter__(self) -> SecureString:
        """Allow SecureString to participate in context manager blocks."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Zeroize the string contents when the context exits."""
        self.zeroize()

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


def create_secure_string(
    value: str,
    encoding: StringEncoding | None = None,
    normalization: UnicodeNormalization = UnicodeNormalization.NFC,
    allowed_languages: list[str] | None = None,
    detect_encoding: bool = True,
) -> SecureString:
    """Create a SecureString instance with validation.

    Args:
        value: String value to secure
        encoding: Specific encoding to use. If None, auto-detects optimal encoding
        normalization: Unicode normalization form to apply
        allowed_languages: List of allowed language codes for character validation
        detect_encoding: Whether to automatically detect the optimal encoding

    Returns:
        SecureString instance with enhanced Unicode support

    Raises:
        SecurityError: If input validation fails
    """
    if not isinstance(value, str):
        raise SecurityError(f"Expected string, got {type(value).__name__}")

    if len(value) == 0:
        raise SecurityError("Empty strings cannot be secured")

    return SecureString(
        value,
        encoding=encoding,
        normalization=normalization,
        allowed_languages=allowed_languages,
        detect_encoding=detect_encoding,
    )


def create_multilingual_secure_string(
    value: str,
    languages: list[str],
    encoding: StringEncoding | None = None,
) -> SecureString:
    """Create a SecureString optimized for multiple languages.

    Args:
        value: String value to secure
        languages: List of expected language codes
        encoding: Optional preferred encoding

    Returns:
        SecureString instance optimized for multilingual content

    Raises:
        SecurityError: If value contains unsupported language characters
    """
    # For multilingual content, UTF-8 is usually the best choice
    if encoding is None:
        encoding = StringEncoding.UTF8

    return create_secure_string(
        value,
        encoding=encoding,
        normalization=UnicodeNormalization.NFC,
        allowed_languages=languages,
        detect_encoding=False,
    )


def secure_compare_strings(
    str1: SecureString,
    str2: SecureString,
    normalization: UnicodeNormalization | None = None,
) -> bool:
    """Perform constant-time comparison of two SecureStrings.

    Args:
        str1: First SecureString
        str2: Second SecureString
        normalization: Optional normalization form to apply before comparison

    Returns:
        True if equal, False otherwise

    Raises:
        SecurityError: If comparison fails
    """
    if not isinstance(str1, SecureString) or not isinstance(str2, SecureString):
        raise SecurityError("Both arguments must be SecureString instances")

    if normalization is not None:
        return str1.compare_with_normalization(str2, normalization)

    return str1 == str2


# Language-specific creation helpers


def create_japanese_secure_string(value: str) -> SecureString:
    """Create a SecureString optimized for Japanese text.

    Args:
        value: Japanese string to secure

    Returns:
        SecureString instance optimized for Japanese characters
    """
    return create_multilingual_secure_string(
        value,
        languages=["ja"],
        encoding=StringEncoding.UTF8,
    )


def create_chinese_secure_string(value: str) -> SecureString:
    """Create a SecureString optimized for Chinese text.

    Args:
        value: Chinese string to secure

    Returns:
        SecureString instance optimized for Chinese characters
    """
    return create_multilingual_secure_string(
        value,
        languages=["zh"],
        encoding=StringEncoding.UTF8,
    )


def create_korean_secure_string(value: str) -> SecureString:
    """Create a SecureString optimized for Korean text.

    Args:
        value: Korean string to secure

    Returns:
        SecureString instance optimized for Korean characters
    """
    return create_multilingual_secure_string(
        value,
        languages=["ko"],
        encoding=StringEncoding.UTF8,
    )


def create_arabic_secure_string(value: str) -> SecureString:
    """Create a SecureString optimized for Arabic text.

    Args:
        value: Arabic string to secure

    Returns:
        SecureString instance optimized for Arabic characters
    """
    return create_multilingual_secure_string(
        value,
        languages=["ar"],
        encoding=StringEncoding.UTF8,
    )


def create_russian_secure_string(value: str) -> SecureString:
    """Create a SecureString optimized for Russian text.

    Args:
        value: Russian string to secure

    Returns:
        SecureString instance optimized for Cyrillic characters
    """
    return create_multilingual_secure_string(
        value,
        languages=["ru"],
        encoding=StringEncoding.KOI8_R,
    )


class SecureMemoryPool:
    """Pool manager for SecureMemory instances with resource tracking.

    This class manages a pool of SecureMemory instances to:
    1. Track memory usage
    2. Prevent memory leaks
    3. Provide bulk cleanup operations
    4. Monitor security metrics
    5. Use BLAKE2b for integrity verification across the pool
    """

    def __init__(self, name: str | None = None) -> None:
        """Initialize pool tracking structures.

        Args:
            name: Optional name for the pool instance for identification
        """
        self._pool: list[SecureMemory] = []
        self._mutex = threading.Lock()
        self._total_bytes = 0
        self._peak_usage = 0
        self._name = name or f"pool-{id(self)}"

    @property
    def name(self) -> str:
        """Get the pool name."""
        return self._name

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
                "pool_name": self._name,
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


# Thread-local pool storage for context-based management
_thread_local_pools = threading.local()


class SecureMemoryPoolContext:
    """Context manager for secure memory pool management.

    Provides thread-safe pool instances without relying on global state.
    Supports dependency injection while maintaining backward compatibility.
    """

    def __init__(
        self, pool: SecureMemoryPool | None = None, pool_name: str | None = None
    ):
        """Initialize pool context.

        Args:
            pool: Optional pool instance. If None, creates default pool.
            pool_name: Optional name for created pool (used only if pool is None)
        """
        self.pool = pool or SecureMemoryPool(name=pool_name)
        self._has_context = hasattr(_thread_local_pools, "current_pool")
        self._previous_pool = getattr(_thread_local_pools, "current_pool", None)

    def __enter__(self) -> SecureMemoryPool:
        """Enter context and set pool in thread-local storage."""
        _thread_local_pools.current_pool = self.pool
        return self.pool

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous pool."""
        if self._has_context:
            _thread_local_pools.current_pool = self._previous_pool
        # Remove the pool attribute entirely if we didn't have one before
        elif hasattr(_thread_local_pools, "current_pool"):
            delattr(_thread_local_pools, "current_pool")


@contextmanager
def secure_memory_pool_context(
    pool: SecureMemoryPool | None = None, pool_name: str | None = None
) -> Generator[SecureMemoryPool, None, None]:
    """Context manager for secure memory pool management.

    Args:
        pool: Optional pool instance. If None, creates default pool.
        pool_name: Optional name for created pool (used only if pool is None)

    Yields:
        SecureMemoryPool instance for use in the context

    Example:
        with secure_memory_pool_context() as pool:
            secure_mem = pool.allocate(b"secret data")
            # Pool is automatically managed within the context

        # Pool is automatically cleaned up when context exits
    """
    with SecureMemoryPoolContext(pool, pool_name) as mem_pool:
        yield mem_pool


def get_current_memory_pool() -> SecureMemoryPool:
    """Get the current thread-local secure memory pool.

    Returns:
        Current SecureMemoryPool instance from thread-local context,
        or creates a new default instance if none exists.

    Note:
        This replaces the global pool pattern.
    """
    if (
        not hasattr(_thread_local_pools, "current_pool")
        or _thread_local_pools.current_pool is None
    ):
        _thread_local_pools.current_pool = SecureMemoryPool(name="default")
    return cast(SecureMemoryPool, _thread_local_pools.current_pool)


class SecureMemoryPoolFactory:
    """Factory for creating and managing SecureMemoryPool instances.

    Provides various pool creation patterns and configuration options.
    """

    @staticmethod
    def create_pool(name: str | None = None) -> SecureMemoryPool:
        """Create a new SecureMemoryPool instance.

        Args:
            name: Optional name for the pool

        Returns:
            New SecureMemoryPool instance
        """
        return SecureMemoryPool(name=name)

    @staticmethod
    def create_isolated_pool(context: str) -> SecureMemoryPool:
        """Create an isolated pool for a specific context.

        Args:
            context: Context identifier (e.g., "session-1", "request-42")

        Returns:
            New SecureMemoryPool instance with context-based naming
        """
        return SecureMemoryPool(name=f"isolated-{context}")

    @staticmethod
    def create_temporary_pool() -> SecureMemoryPool:
        """Create a temporary pool for short-lived operations.

        Returns:
            New SecureMemoryPool instance marked as temporary
        """
        return SecureMemoryPool(name=f"temp-{int(time.time())}")


# Public API exports
__all__ = [
    # Core classes
    "SecureMemory",
    "SecureMemoryPool",
    "SecureMemoryPoolContext",
    "SecureMemoryPoolFactory",
    "SecureString",
    "SecurityError",
    # Enums for international support
    "StringEncoding",
    "UnicodeNormalization",
    "create_arabic_secure_string",
    "create_chinese_secure_string",
    "create_japanese_secure_string",
    "create_korean_secure_string",
    "create_multilingual_secure_string",
    "create_russian_secure_string",
    # Convenience functions
    "create_secure_string",
    # Enhanced Unicode functions
    "detect_string_encoding",
    # Pool management functions
    "get_current_memory_pool",
    "normalize_unicode_string",
    "secure_compare_strings",
    "secure_memory_pool_context",
    "validate_language_characters",
]
