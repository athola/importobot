"""Security utilities and components for Importobot.

This package provides core security features for the test conversion tool:
- Credential detection and management
- Secure memory for sensitive data
- Template security scanning
- Input validation

Enterprise-only helpers (HSM, SIEM, compliance, key rotation) now live under
``importobot_enterprise`` so production builds can omit them by default.
"""

from importobot.security.audit import SecuritySeverity
from importobot.security.credential_manager import (
    CredentialManager,
    SecurityError,
)
from importobot.security.credential_patterns import (
    CredentialPattern,
    CredentialPatternRegistry,
    CredentialRegistryContext,
    CredentialType,
    credential_registry_context,
    get_current_registry,
    scan_for_credentials,
)
from importobot.security.secure_memory import (
    SecureMemory,
    SecureMemoryPool,
    SecureMemoryPoolContext,
    SecureMemoryPoolFactory,
    SecureString,
    StringEncoding,
    UnicodeNormalization,
    create_arabic_secure_string,
    create_chinese_secure_string,
    create_japanese_secure_string,
    create_korean_secure_string,
    create_russian_secure_string,
    create_secure_string,
    detect_string_encoding,
    get_current_memory_pool,
    normalize_unicode_string,
    secure_compare_strings,
    secure_memory_pool_context,
    validate_language_characters,
)
from importobot.security.security_validator import SecurityValidator
from importobot.security.template_scanner import (
    TemplateSecurityScanner,
    scan_template_file_for_security,
)

__all__ = [
    "CredentialManager",
    "CredentialPattern",
    "CredentialPatternRegistry",
    "CredentialRegistryContext",
    "CredentialType",
    "SecureMemory",
    "SecureMemoryPool",
    "SecureMemoryPoolContext",
    "SecureMemoryPoolFactory",
    "SecureString",
    "SecurityError",
    "SecuritySeverity",
    "SecurityValidator",
    "StringEncoding",
    "TemplateSecurityScanner",
    "UnicodeNormalization",
    "create_arabic_secure_string",
    "create_chinese_secure_string",
    "create_japanese_secure_string",
    "create_korean_secure_string",
    "create_russian_secure_string",
    "create_secure_string",
    "credential_registry_context",
    "detect_string_encoding",
    "get_current_memory_pool",
    "get_current_registry",
    "normalize_unicode_string",
    "scan_for_credentials",
    "scan_template_file_for_security",
    "secure_compare_strings",
    "secure_memory_pool_context",
    "validate_language_characters",
]
