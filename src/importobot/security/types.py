"""Security type definitions and exceptions.

This module provides foundational types for secure memory operations:
- StringEncoding: Supported text encodings for SecureString
- UnicodeNormalization: Unicode normalization forms
- SecurityError: Exception for security operation failures
"""

from __future__ import annotations

from enum import Enum

from importobot.exceptions import ImportobotError


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


__all__ = [
    "SecurityError",
    "StringEncoding",
    "UnicodeNormalization",
]
