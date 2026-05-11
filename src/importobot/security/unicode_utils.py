"""Unicode utilities for secure string handling.

This module provides Unicode-aware functions for secure operations:
- Encoding detection for optimal string storage
- Unicode normalization for consistent security comparisons
- Language character validation for injection prevention
"""

from __future__ import annotations

import unicodedata
from typing import Any

from importobot.security.types import StringEncoding, UnicodeNormalization
from importobot.utils.logging import get_logger

logger = get_logger()


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

    detected_languages: list[str] = []
    unexpected_chars: list[str] = []

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
        char_languages: list[str] = []

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


__all__ = [
    "detect_string_encoding",
    "normalize_unicode_string",
    "validate_language_characters",
]
