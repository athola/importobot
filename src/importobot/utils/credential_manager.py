"""Backward-compatibility shim for ``utils.credential_manager``.

The canonical implementation lives in
:mod:`importobot.security.credential_manager`. This module preserves the
old import path used by tests and external integrations — see PR #90
review C7. The shim also forwards :class:`SecurityError` so
``except SecurityError`` works regardless of which entry point a caller
imports the credential manager from.
"""

from importobot.exceptions import SecurityError
from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
)

__all__ = [
    "CredentialManager",
    "EncryptedCredential",
    "SecurityError",
]
