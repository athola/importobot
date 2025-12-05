"""Secure memory management for credential protection.

This module serves as the public facade for secure memory operations,
re-exporting all components from the internal modules for backward compatibility.

Module Structure:
- types.py: Enums (StringEncoding, UnicodeNormalization) and SecurityError
- unicode_utils.py: Encoding detection, normalization, language validation
- memory.py: SecureMemory class with zeroization
- secure_string.py: SecureString class and convenience functions
- pool.py: SecureMemoryPool, context managers, and factory
"""

from __future__ import annotations

# Re-export from memory module
from importobot.security.memory import SecureMemory

# Re-export from pool module
from importobot.security.pool import (
    SecureMemoryPool,
    SecureMemoryPoolContext,
    SecureMemoryPoolFactory,
    ThreadLocalPoolStorage,
    ThreadLocalPoolStorageFactory,
    get_current_memory_pool,
    secure_memory_pool_context,
)

# Re-export from secure_string module
from importobot.security.secure_string import (
    SecureString,
    create_arabic_secure_string,
    create_chinese_secure_string,
    create_japanese_secure_string,
    create_korean_secure_string,
    create_multilingual_secure_string,
    create_russian_secure_string,
    create_secure_string,
    secure_compare_strings,
)

# Re-export from types module
from importobot.security.types import (
    SecurityError,
    StringEncoding,
    UnicodeNormalization,
)

# Re-export from unicode_utils module
from importobot.security.unicode_utils import (
    detect_string_encoding,
    normalize_unicode_string,
    validate_language_characters,
)

# Public API exports (sorted alphabetically per RUF022)
__all__ = [
    "SecureMemory",
    "SecureMemoryPool",
    "SecureMemoryPoolContext",
    "SecureMemoryPoolFactory",
    "SecureString",
    "SecurityError",
    "StringEncoding",
    "ThreadLocalPoolStorage",
    "ThreadLocalPoolStorageFactory",
    "UnicodeNormalization",
    "create_arabic_secure_string",
    "create_chinese_secure_string",
    "create_japanese_secure_string",
    "create_korean_secure_string",
    "create_multilingual_secure_string",
    "create_russian_secure_string",
    "create_secure_string",
    "detect_string_encoding",
    "get_current_memory_pool",
    "normalize_unicode_string",
    "secure_compare_strings",
    "secure_memory_pool_context",
    "validate_language_characters",
]
