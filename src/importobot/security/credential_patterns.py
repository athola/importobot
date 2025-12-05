"""Credential pattern registry for 2025 security standards.

Defines regex-based detectors for API keys, tokens, passwords, certificates,
and other sensitive values while aiming to minimize false positives.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from re import Pattern
from typing import Any, TypedDict

from importobot import config as importobot_config
from importobot.utils.logging import get_logger


class CredentialMatch(TypedDict, total=False):
    """TypedDict for credential match results."""

    credential_type: str
    pattern: str
    confidence: float
    severity: str
    match_text: str
    start_pos: int
    end_pos: int
    line_number: int
    remediation: str
    examples: list[str]
    file_path: str  # Optional, added for file scanning


logger = get_logger()


class CredentialStatistics(TypedDict):
    """TypedDict for credential pattern statistics."""

    total_patterns: int
    high_confidence_patterns: int
    medium_confidence_patterns: int
    patterns_by_type: dict[str, int]
    patterns_by_severity: dict[str, int]


class CredentialType(Enum):
    """Types of credentials that can be detected."""

    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH = "oauth"
    DATABASE = "database"
    SSH_KEY = "ssh_key"
    SERVICE_ACCOUNT = "service_account"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    JWT = "jwt"
    WEBHOOK = "webhook"
    ENCRYPTION_KEY = "encryption_key"


@dataclass
class CredentialPattern:
    """Credential detection pattern definition."""

    credential_type: CredentialType
    regex_pattern: Pattern[str]
    confidence: float  # 0.0 to 1.0
    context_keywords: list[str]
    description: str
    remediation: str
    examples: list[str]
    severity: str = "high"  # low, medium, high, critical

    def matches(self, text: str) -> bool:
        """Check if the pattern matches the given text.

        Args:
            text: Text to check for pattern matches

        Returns:
            True if pattern matches, False otherwise
        """
        return bool(self.regex_pattern.search(text))

    def find_matches(self, text: str) -> list[re.Match[str]]:
        """Find all matches of this pattern in the text.

        Args:
            text: Text to search

        Returns:
            List of regex match objects
        """
        return list(self.regex_pattern.finditer(text))


class CredentialPatternRegistry:
    """Registry of credential detection patterns with 2025 security standards.

    This registry contains patterns for detecting various types of credentials
    across multiple platforms and services. The patterns are designed to:
    - Catch modern credential formats
    - Minimize false positives
    - Provide context-specific detection
    - Support remediation guidance
    """

    def __init__(self) -> None:
        """Initialize the pattern registry with the full pattern set."""
        self.patterns = self._load_modern_patterns()
        self._build_pattern_index()

    def _load_modern_patterns(self) -> dict[CredentialType, list[CredentialPattern]]:
        """Load credential detection patterns.

        Returns:
            Dictionary mapping credential types to their patterns
        """
        return {
            CredentialType.PASSWORD: [
                CredentialPattern(
                    credential_type=CredentialType.PASSWORD,
                    regex_pattern=re.compile(
                        r"(?i)(?:password|pwd|passwd|pass)[\s\'\":=]+([^\s\'\"<>]{6,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=["password", "pwd", "passwd", "pass"],
                    description="Password assignment or configuration",
                    remediation=(
                        "Use environment variables or secure credential manager"
                    ),
                    examples=[
                        "password: secret123",
                        "pwd = mypassword",
                        '"passwd":"mypassword"',
                    ],
                    severity="high",
                ),
                CredentialPattern(
                    credential_type=CredentialType.PASSWORD,
                    regex_pattern=re.compile(
                        r"(?i)(?:db_password|database_password|db_pass)[\s\'\":=]+([^\s\'\"<>]{6,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["db_password", "database_password", "db_pass"],
                    description="Database password configuration",
                    remediation="Use connection pooling with credential injection",
                    examples=[
                        "db_password: secretdb",
                        'database_password="secret"',
                    ],
                    severity="critical",
                ),
            ],
            CredentialType.API_KEY: [
                CredentialPattern(
                    credential_type=CredentialType.API_KEY,
                    regex_pattern=re.compile(
                        r"(?i)(?:x[-_]?api[-_]?key|api[_-]?key|apikey)[\s\'\":=\-]+([a-zA-Z0-9_\-]{20,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=["api_key", "apikey", "x-api-key"],
                    description="API key in configuration",
                    remediation="Store in secure vault or environment variable",
                    examples=[
                        "api_key: sk_live_example1234567890",
                        "x-api-key: abcdef123456789",
                        '"apikey":"1234567890abcdef"',
                    ],
                    severity="high",
                ),
                CredentialPattern(
                    credential_type=CredentialType.API_KEY,
                    regex_pattern=re.compile(
                        r"(?i)(?:x[-_]?api[-_]?key|authorization[\s:]+bearer[\s]+)([a-zA-Z0-9_\-]{20,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["x-api-key", "x_api_key", "authorization"],
                    description="HTTP API key header format",
                    remediation="Use API gateway or secure proxy",
                    examples=[
                        "X-API-Key: sk_live_1234567890",
                        "Authorization: Bearer abcdef123456789",
                    ],
                    severity="high",
                ),
            ],
            CredentialType.AWS: [
                CredentialPattern(
                    credential_type=CredentialType.AWS,
                    regex_pattern=re.compile(
                        r"(?i)(?:aws[_-]?access[_-]?key[_-]?id|aws_access_key_id)[\s\'\":=]+([A-Z0-9]{20})",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=["aws_access_key_id", "aws_access_key", "AKIA"],
                    description="AWS Access Key ID",
                    remediation=("Use AWS IAM roles or temporary credentials"),
                    examples=[
                        "aws_access_key_id: AKIAIOSFODNN7EXAMPLE",
                        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
                    ],
                    severity="critical",
                ),
                CredentialPattern(
                    credential_type=CredentialType.AWS,
                    regex_pattern=re.compile(
                        r"(?i)(?:aws[_-]?secret[_-]?access[_-]?key|aws_secret_access_key)[\s\'\":=]+([a-zA-Z0-9/+]{40})",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=["aws_secret_access_key", "aws_secret_key"],
                    description="AWS Secret Access Key",
                    remediation=("Use AWS IAM roles or temporary credentials"),
                    examples=[
                        "aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/"
                        "bPxRfiCYEXAMPLEKEY",
                        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/"
                        "bPxRfiCYEXAMPLEKEY",
                    ],
                    severity="critical",
                ),
                CredentialPattern(
                    credential_type=CredentialType.AWS,
                    regex_pattern=re.compile(
                        r"(?i)(?:aws[_-]?session[_-]?token|aws_session_token)[\s\'\":=]*(?:\(|\s)*([a-zA-Z0-9/+]{16,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["aws_session_token", "aws_security_token"],
                    description="AWS Session Token",
                    remediation=("Use AWS IAM roles or temporary credentials"),
                    examples=[
                        "aws_session_token: AQoEXAMPLEH4aoAH0gNCAPy...",
                    ],
                    severity="high",
                ),
            ],
            CredentialType.JWT: [
                CredentialPattern(
                    credential_type=CredentialType.JWT,
                    regex_pattern=re.compile(
                        r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["jwt", "bearer", "authorization"],
                    description="JSON Web Token",
                    remediation="Validate JWT signature and expiration",
                    examples=[
                        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    ],
                    severity="high",
                ),
            ],
            CredentialType.PRIVATE_KEY: [
                CredentialPattern(
                    credential_type=CredentialType.PRIVATE_KEY,
                    regex_pattern=re.compile(
                        r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE
                    ),
                    confidence=1.0,
                    context_keywords=["private_key", "rsa_private", "key"],
                    description="Private key PEM format",
                    remediation="Move to HSM or key management service",
                    examples=[
                        "-----BEGIN PRIVATE KEY-----",
                        "-----BEGIN RSA PRIVATE KEY-----",
                    ],
                    severity="critical",
                ),
                CredentialPattern(
                    credential_type=CredentialType.PRIVATE_KEY,
                    regex_pattern=re.compile(
                        r"(?i)(?:private[_-]?key|rsa[_-]?private)[\s\'\":=]+([^\s\'\"<>]{20,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=["private_key", "privatekey", "rsa_private"],
                    description="Private key reference",
                    remediation="Move to HSM or key management service",
                    examples=[
                        "private_key: -----BEGIN...",
                        '"rsa_private":"MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC..."',
                    ],
                    severity="critical",
                ),
            ],
            CredentialType.SSH_KEY: [
                CredentialPattern(
                    credential_type=CredentialType.SSH_KEY,
                    regex_pattern=re.compile(
                        r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----", re.IGNORECASE
                    ),
                    confidence=1.0,
                    context_keywords=["ssh_private", "openssh_key"],
                    description="OpenSSH private key",
                    remediation="Use SSH agent or hardware token",
                    examples=[
                        "-----BEGIN OPENSSH PRIVATE KEY-----",
                    ],
                    severity="critical",
                ),
                CredentialPattern(
                    credential_type=CredentialType.SSH_KEY,
                    regex_pattern=re.compile(
                        r"ssh-(?:rsa|ed25519|ecdsa)\s+[a-zA-Z0-9/+]+[=]*\s+\S+",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["ssh_key", "ssh_public", "authorized_keys"],
                    description="SSH public or private key",
                    remediation="Use SSH agent forwarding",
                    examples=[
                        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC...",
                        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG...",
                    ],
                    severity="medium",
                ),
            ],
            CredentialType.DATABASE: [
                CredentialPattern(
                    credential_type=CredentialType.DATABASE,
                    regex_pattern=re.compile(
                        r"(?i)(?:mongodb|redis|postgres).*://[^\s:]+:([^\s@]+)@",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=[
                        "mongodb",
                        "redis",
                        "postgres",
                        "connection_string",
                    ],
                    description="Database connection string with password",
                    remediation="Use SSL/TLS and separate credential management",
                    examples=[
                        "mongodb://user:password@localhost:27017",
                        "redis://:password@localhost:6379",
                        "postgresql://user:password@localhost:5432",
                    ],
                    severity="high",
                ),
                CredentialPattern(
                    credential_type=CredentialType.DATABASE,
                    regex_pattern=re.compile(
                        r"(?i)(?:mysql|postgresql)://[^\s:]+:([^\s@]+)@", re.IGNORECASE
                    ),
                    confidence=0.90,
                    context_keywords=["mysql", "postgresql", "database", "connection"],
                    description="SQL database connection string",
                    remediation="Use SSL/TLS and separate credential management",
                    examples=[
                        "mysql://user:password@localhost:3306",
                        "postgresql://user:password@localhost:5432",
                    ],
                    severity="high",
                ),
            ],
            CredentialType.OAUTH: [
                CredentialPattern(
                    credential_type=CredentialType.OAUTH,
                    regex_pattern=re.compile(
                        r"(?i)(?:client[_-]?secret|oauth[_-]?secret)[\s\'\":=]+([a-zA-Z0-9_\-]{20,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.95,
                    context_keywords=["client_secret", "oauth_secret", "app_secret"],
                    description="OAuth client secret",
                    remediation="Use PKCE flow or rotate secrets regularly",
                    examples=[
                        "client_secret: abcdef1234567890abcdef12",
                        "OAUTH_CLIENT_SECRET=secret123",
                    ],
                    severity="high",
                ),
                CredentialPattern(
                    credential_type=CredentialType.OAUTH,
                    regex_pattern=re.compile(
                        r"(?i)(?:refresh[_-]?token)[\s\'\":=]+([a-zA-Z0-9._\-]{30,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["refresh_token", "refresh"],
                    description="OAuth refresh token",
                    remediation="Store in secure vault with rotation policy",
                    examples=[
                        "refresh_token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        '"refresh_token":"1//0gX..."',
                    ],
                    severity="high",
                ),
            ],
            CredentialType.WEBHOOK: [
                CredentialPattern(
                    credential_type=CredentialType.WEBHOOK,
                    regex_pattern=re.compile(
                        r"(?i)(?:webhook[_-]?secret|webhook[_-]?url)[\s\'\":=]+([^\s\'\"<>]{10,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.85,
                    context_keywords=["webhook_secret", "webhook_url"],
                    description="Webhook secret or URL",
                    remediation="Use HMAC signature verification",
                    examples=[
                        "webhook_secret: whsec_1234567890abcdef",
                        "webhook_url: https://example.com/webhook",
                    ],
                    severity="medium",
                ),
            ],
            CredentialType.ENCRYPTION_KEY: [
                CredentialPattern(
                    credential_type=CredentialType.ENCRYPTION_KEY,
                    regex_pattern=re.compile(
                        r"(?i)(?:encryption[_-]?key|encrypt[_-]?key|secret[_-]?key)[\s\'\":=]+([a-zA-Z0-9+/=]{16,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["encryption_key", "secret_key", "encrypt_key"],
                    description="Encryption key",
                    remediation="Use key management service or HSM",
                    examples=[
                        "encryption_key: base64encodedkey==",
                        "SECRET_KEY=mysupersecretkey123",
                    ],
                    severity="high",
                ),
            ],
            CredentialType.SERVICE_ACCOUNT: [
                CredentialPattern(
                    credential_type=CredentialType.SERVICE_ACCOUNT,
                    regex_pattern=re.compile(
                        r"(?i)(?:service[_-]?account[_-]?key|service[_-]?account)[\s\'\":=]+([^\s\'\"<>]{50,})",
                        re.IGNORECASE,
                    ),
                    confidence=0.90,
                    context_keywords=["service_account_key", "service_account"],
                    description="Service account key",
                    remediation=("Use managed service accounts or short-lived tokens"),
                    examples=[
                        'service_account_key: {"type":"service_account",'
                        '"project_id":"my-project"...}',
                    ],
                    severity="high",
                ),
            ],
        }

    def _build_pattern_index(self) -> None:
        """Build efficient lookup structures for pattern matching."""
        self._high_confidence_patterns = []
        self._medium_confidence_patterns = []
        self._all_patterns = []

        for patterns in self.patterns.values():
            for pattern in patterns:
                self._all_patterns.append(pattern)
                if pattern.confidence >= 0.9:
                    self._high_confidence_patterns.append(pattern)
                elif pattern.confidence >= 0.7:
                    self._medium_confidence_patterns.append(pattern)

        # Sort by confidence (highest first)
        self._all_patterns.sort(key=lambda p: p.confidence, reverse=True)
        self._high_confidence_patterns.sort(key=lambda p: p.confidence, reverse=True)
        self._medium_confidence_patterns.sort(key=lambda p: p.confidence, reverse=True)

    def get_all_patterns(self) -> list[CredentialPattern]:
        """Get all registered patterns.

        Returns:
            List of all credential patterns sorted by confidence
        """
        return self._all_patterns.copy()

    def get_patterns_by_confidence(
        self, min_confidence: float = 0.7
    ) -> list[CredentialPattern]:
        """Get patterns above confidence threshold.

        Args:
            min_confidence: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            List of patterns meeting confidence requirement
        """
        return [p for p in self._all_patterns if p.confidence >= min_confidence]

    def get_patterns_by_type(
        self, credential_type: CredentialType
    ) -> list[CredentialPattern]:
        """Get patterns for specific credential type.

        Args:
            credential_type: Type of credential patterns to retrieve

        Returns:
            List of patterns for the specified type
        """
        return self.patterns.get(credential_type, []).copy()

    def get_patterns_by_severity(self, severity: str) -> list[CredentialPattern]:
        """Get patterns by severity level.

        Args:
            severity: Severity level (low, medium, high, critical)

        Returns:
            List of patterns with specified severity
        """
        return [p for p in self._all_patterns if p.severity == severity]

    def search_text(
        self,
        text: str,
        min_confidence: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search text for credential patterns.

        Args:
            text: Text to search for credentials
            min_confidence: Minimum confidence threshold

        Returns:
            List of dictionaries with match information
        """
        matches = []
        patterns_to_use = self.get_patterns_by_confidence(min_confidence)

        for pattern in patterns_to_use:
            pattern_matches = pattern.find_matches(text)
            for match in pattern_matches:
                match_text = match.group(0)
                confidence = pattern.confidence

                # Enhanced false positive reduction with context awareness
                context_window = importobot_config.CREDENTIAL_CONTEXT_WINDOW
                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end].lower()

                # Check both match text and broader context for placeholder indicators
                if self._looks_like_placeholder(
                    match_text
                ) or self._looks_like_placeholder(context):
                    confidence = min(confidence, 0.3)  # Lower confidence for context

                # Additional context-specific reductions
                if self._is_robot_framework_variable(match_text, text[: match.start()]):
                    confidence = min(
                        confidence, 0.2
                    )  # Very low confidence for variable names

                matches.append(
                    {
                        "credential_type": pattern.credential_type.value,
                        "pattern": pattern.description,
                        "confidence": confidence,
                        "severity": pattern.severity,
                        "match_text": match_text,
                        "start_pos": match.start(),
                        "end_pos": match.end(),
                        "line_number": text[: match.start()].count("\n") + 1,
                        "remediation": pattern.remediation,
                        "examples": pattern.examples,
                    }
                )

        # Sort by confidence and position
        matches.sort(key=lambda m: (-m["confidence"], m["start_pos"]))  # type: ignore[operator]
        return matches

    def scan_file(
        self,
        file_path: str,
        min_confidence: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Scan a file for credential patterns.

        Args:
            file_path: Path to file to scan
            min_confidence: Minimum confidence threshold

        Returns:
            List of dictionaries with match information including file path
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            matches = self.search_text(content, min_confidence)

            # Add file path to all matches
            for match in matches:
                match["file_path"] = file_path

            return matches

        except Exception as exc:
            logger.error("Failed to scan file %s: %s", file_path, exc)
            return []

    def get_statistics(self) -> CredentialStatistics:
        """Get statistics about loaded patterns.

        Returns:
            Dictionary with pattern statistics
        """
        stats: CredentialStatistics = {
            "total_patterns": len(self._all_patterns),
            "high_confidence_patterns": len(self._high_confidence_patterns),
            "medium_confidence_patterns": len(self._medium_confidence_patterns),
            "patterns_by_type": {},
            "patterns_by_severity": {},
        }

        for cred_type, patterns in self.patterns.items():
            stats["patterns_by_type"][cred_type.value] = len(patterns)

        severity_counts: dict[str, int] = {}
        for pattern in self._all_patterns:
            severity_counts[pattern.severity] = (
                severity_counts.get(pattern.severity, 0) + 1
            )
        stats["patterns_by_severity"] = severity_counts

        return stats

    @staticmethod
    def _looks_like_placeholder(match_text: str) -> bool:
        """Return True when the matched text resembles placeholder content."""
        text = match_text.lower()
        placeholder_tokens = (
            "example_",
            "example-",
            "example ",
            "sample_",
            "sample-",
            "sample ",
            "fake_",
            "fake-",
            "fake ",
            "dummy_",
            "dummy-",
            "dummy ",
            "test_",
            "test-",
            "test ",
            "demo ",
            "demo_",
            "demo-",
            "placeholder",
            "your_",
            "your-",
            "your ",
            "replace_with",
            "replace_with_actual",
            "placeholder_key",
            "placeholder_key_value",
            "use_env_variable_for",
        )
        return any(token in text for token in placeholder_tokens)

    @staticmethod
    def _is_robot_framework_variable(match_text: str, preceding_text: str) -> bool:
        """Return True if the match appears to be a Robot Framework variable name."""
        # Check if this looks like a Robot Framework variable assignment
        # Pattern: ${VARIABLE_NAME}    value
        preceding_lower = preceding_text.strip().lower()

        # Look for variable assignment patterns
        if "${" in match_text and "}" in match_text:
            # This is likely a variable name, not a credential value
            return True

        # Check if the preceding text looks like a variable declaration
        if "*** variables ***" in preceding_lower:
            return True

        # Check for variable assignment patterns
        lines_before = preceding_lower.split("\n")
        if lines_before:
            last_line = lines_before[-1].strip()
            # If the last line contains variable indicators, this is likely a var name
            indicators = ["${", "variables", "*** variables ***"]
            if any(indicator in last_line for indicator in indicators):
                return True

        return False


class _ThreadLocalRegistryStorage:
    """Encapsulates thread-local storage for credential registries.

    Uses lazy initialization to avoid creating threading.local() at module
    import time. This improves testability and avoids potential issues with
    module-level global state.
    """

    def __init__(self) -> None:
        self._storage: threading.local | None = None

    def _get_storage(self) -> threading.local:
        """Lazily initialize and return the thread-local storage."""
        if self._storage is None:
            self._storage = threading.local()
        return self._storage

    def get_registry(self) -> CredentialPatternRegistry | None:
        """Get the current thread's registry, if any."""
        storage = self._get_storage()
        return getattr(storage, "registry", None)

    def set_registry(self, registry: CredentialPatternRegistry | None) -> None:
        """Set the current thread's registry."""
        storage = self._get_storage()
        storage.registry = registry

    def has_registry(self) -> bool:
        """Check if the current thread has a registry set."""
        storage = self._get_storage()
        return hasattr(storage, "registry")

    def clear_registry(self) -> None:
        """Remove the registry from the current thread's storage."""
        storage = self._get_storage()
        if hasattr(storage, "registry"):
            delattr(storage, "registry")


# Single instance - the class encapsulates the lazy threading.local creation
_registry_storage = _ThreadLocalRegistryStorage()


class CredentialRegistryContext:
    """Context manager for credential pattern registry management.

    Provides thread-safe registry instances without relying on global state.
    Supports dependency injection while maintaining backward compatibility.
    """

    def __init__(self, registry: CredentialPatternRegistry | None = None):
        """Initialize registry context.

        Args:
            registry: Optional registry instance. If None, creates default.
        """
        self.registry = registry or CredentialPatternRegistry()
        self._has_context = _registry_storage.has_registry()
        self._previous_registry = _registry_storage.get_registry()

    def __enter__(self) -> CredentialPatternRegistry:
        """Enter context and set registry in thread-local storage."""
        _registry_storage.set_registry(self.registry)
        return self.registry

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous registry."""
        if self._has_context:
            _registry_storage.set_registry(self._previous_registry)
        else:
            _registry_storage.clear_registry()


@contextmanager
def credential_registry_context(
    registry: CredentialPatternRegistry | None = None,
) -> Generator[CredentialPatternRegistry, None, None]:
    """Context manager for credential pattern registry management.

    Args:
        registry: Optional registry instance. If None, creates default.

    Yields:
        CredentialPatternRegistry instance for use in the context

    Example:
        with credential_registry_context() as registry:
            matches = registry.search_text(text, min_confidence=0.8)

        # Registry is automatically cleaned up when context exits
    """
    with CredentialRegistryContext(registry) as reg:
        yield reg


def get_current_registry() -> CredentialPatternRegistry:
    """Get the current thread-local credential pattern registry.

    Returns:
        Current CredentialPatternRegistry instance from thread-local context,
        or creates a new default instance if none exists.

    Note:
        This replaces the global registry pattern while maintaining
        backward compatibility for existing code.
    """
    registry = _registry_storage.get_registry()
    if registry is None:
        registry = CredentialPatternRegistry()
        _registry_storage.set_registry(registry)
    return registry


# Backward compatibility functions
def get_credential_registry() -> CredentialPatternRegistry:
    """Get the default credential pattern registry.

    Returns:
        Default CredentialPatternRegistry instance

    Note:
        This function is maintained for backward compatibility.
        New code should use get_current_registry() or credential_registry_context().
    """
    return get_current_registry()


def scan_for_credentials(
    text: str,
    min_confidence: float = 0.7,
    registry: CredentialPatternRegistry | None = None,
) -> list[dict[str, Any]]:
    """Scan text for credentials.

    Args:
        text: Text to scan
        min_confidence: Minimum confidence threshold
        registry: Optional registry instance. If None, uses current context registry.

    Returns:
        List of credential matches
    """
    if registry is None:
        registry = get_current_registry()
    return registry.search_text(text, min_confidence)
