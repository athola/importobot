"""Security utilities and components for Importobot.

This package provides core security features for the test conversion tool:
- Credential detection and management
- Secure memory for sensitive data
- Template security scanning
- Input validation

Enterprise-only helpers (HSM, SIEM, compliance, key rotation) now live under
``importobot_enterprise`` so production builds can omit them by default.
"""

from importobot.security.credential_manager import (
    CredentialManager,
    SecurityError,
)
from importobot.security.credential_patterns import (
    CredentialPattern,
    CredentialPatternRegistry,
    CredentialType,
    get_credential_registry,
    scan_for_credentials,
)
from importobot.security.secure_memory import (
    SecureMemory,
    SecureString,
)
from importobot.security.security_validator import (
    SecurityValidator,
)
from importobot.security.template_scanner import (
    TemplateSecurityScanner,
    scan_template_file_for_security,
)

__all__ = [
    "CredentialManager",
    "CredentialPattern",
    "CredentialPatternRegistry",
    "CredentialType",
    "SecureMemory",
    "SecureString",
    "SecurityError",
    "SecurityValidator",
    "TemplateSecurityScanner",
    "get_credential_registry",
    "scan_for_credentials",
    "scan_template_file_for_security",
]
