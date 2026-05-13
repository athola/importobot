"""Backward-compatibility shim for the legacy ``utils.security`` API.

The canonical implementations now live under :mod:`importobot.security`.
This module re-exports them so callers that still import from
``importobot.utils.security`` get a single class (``SecurityValidator``),
a single enum (``SecuritySeverity``), and a single credential dataclass
(``EncryptedCredential``) — see PR #90 review C5/C6/C7/I5.
"""

from importobot.security.audit import SecuritySeverity
from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
)
from importobot.security.recommendations import (
    extract_security_warnings,
    get_ssh_security_guidelines,
)
from importobot.security.security_validator import SecurityValidator
from importobot.utils.command_security import (
    CommandValidationResult,
    CommandValidator,
    validate_command_safely,
)

__all__ = [
    "CommandValidationResult",
    "CommandValidator",
    "CredentialManager",
    "EncryptedCredential",
    "SecuritySeverity",
    "SecurityValidator",
    "extract_security_warnings",
    "get_ssh_security_guidelines",
    "validate_command_safely",
]
