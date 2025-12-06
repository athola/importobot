"""Secure string wrapper with Unicode support.

This module provides SecureString and related convenience functions
for protecting string data with automatic zeroization and Unicode awareness.
"""

from __future__ import annotations

import contextlib
from typing import Any, cast

from importobot.security.memory import SecureMemory
from importobot.security.types import (
    SecurityError,
    StringEncoding,
    UnicodeNormalization,
)
from importobot.security.unicode_utils import (
    detect_string_encoding,
    normalize_unicode_string,
    validate_language_characters,
)
from importobot.utils.logging import get_logger

logger = get_logger()


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


__all__ = [
    "SecureString",
    "create_arabic_secure_string",
    "create_chinese_secure_string",
    "create_japanese_secure_string",
    "create_korean_secure_string",
    "create_multilingual_secure_string",
    "create_russian_secure_string",
    "create_secure_string",
    "secure_compare_strings",
]
