"""Security utilities for test generation and Robot Framework operations.

This module provides the main SecurityValidator class that orchestrates
security validation using specialized modules for audit logging, pattern
matching, and various security checks.
"""

import os
import secrets
import time
from typing import Any

from importobot.security.audit import SecurityAuditLogger, SecuritySeverity
from importobot.security.checkers import (
    check_credential_patterns,
    check_dangerous_commands,
    check_hardcoded_credentials,
    check_injection_patterns,
    check_production_indicators,
    check_sensitive_paths,
    sanitize_command_parameters,
    sanitize_error_message,
    validate_file_operations,
)
from importobot.security.credential_manager import CredentialManager
from importobot.security.credential_patterns import (
    CredentialPatternRegistry,
    get_current_registry,
)
from importobot.security.patterns import SecurityPatterns
from importobot.security.recommendations import (
    SSH_SECURITY_GUIDELINES,  # noqa: F401 - re-export for backwards compatibility
    extract_security_warnings,  # noqa: F401 - re-export for backwards compatibility
    generate_security_recommendations,
    get_ssh_security_guidelines,  # noqa: F401 - re-export for backwards compatibility
)
from importobot.security.test_validation import validate_test_security
from importobot.services.security_types import SecurityLevel

# Re-exports for backwards compatibility are handled by imports above:
# - SSH_SECURITY_GUIDELINES
# - get_ssh_security_guidelines
# - extract_security_warnings
# - validate_test_security


class SecurityValidator:
    """Validate and sanitizes test parameters for security concerns.

    Supports configurable security policies for different environments.
    Logs security validation failures with specific rule violations and context.

    Security Levels:
        strict: Maximum security for production environments.
            - Additional dangerous patterns: proc filesystem access, network
              process enumeration, user enumeration, external network
              requests
            - Additional sensitive paths: /proc/, /sys/, Kubernetes configs, Docker
              configs, system logs, Windows
              ProgramData
            - Recommended for: Production systems, environments with
              compliance requirements

        standard: Balanced security for general development and testing.
            - Default dangerous patterns: rm -rf, sudo, chmod 777, command substitution,
              eval/exec, fork bombs, system file access, disk
              operations
            - Default sensitive paths: system files, SSH keys, AWS credentials, root
              access, Windows system
              directories
            - Recommended for: Most development environments, CI/CD pipelines,
              testing

        permissive: Relaxed security for trusted development environments.
            - Reduced dangerous patterns: removes curl, wget, and /dev/null
              redirection
            - Standard sensitive paths: maintains basic system protection
            - Recommended for: Local development, trusted environments, educational
              purposes

    Attributes:
        security_level: The configured security level.
        dangerous_patterns: List of dangerous command patterns.
        sensitive_paths: List of sensitive path patterns.
        enable_audit_logging: Whether audit logging is enabled.
        credential_registry: Registry for credential patterns.
        credential_manager: Manager for encrypting credentials.
    """

    # Expose class constants for backwards compatibility
    DEFAULT_DANGEROUS_PATTERNS = SecurityPatterns.DEFAULT_DANGEROUS_PATTERNS
    DEFAULT_SENSITIVE_PATHS = SecurityPatterns.DEFAULT_SENSITIVE_PATHS

    def __init__(
        self,
        dangerous_patterns: list[str] | None = None,
        sensitive_paths: list[str] | None = None,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
        enable_audit_logging: bool = True,
        credential_registry: CredentialPatternRegistry | None = None,
        *,
        additional_dangerous_patterns: list[str] | None = None,
        additional_sensitive_paths: list[str] | None = None,
        additional_injection_patterns: list[str] | None = None,
        additional_sanitization_patterns: list[tuple[str, str]] | None = None,
    ):
        r"""Initialize security validator with configurable patterns.

        Args:
            dangerous_patterns: Custom dangerous command patterns to replace defaults.
                If provided, completely replaces the default patterns.
            sensitive_paths: Custom sensitive path patterns to replace defaults.
                If provided, completely replaces the default paths.
            security_level: Security level determining validation strictness:
                - 'strict': Maximum security for production and other hardened
                  environments
                - 'standard': Balanced security for general development and testing
                  (default)
                - 'permissive': Relaxed security for trusted development environments
            enable_audit_logging: Enable detailed audit logging for security events
            credential_registry: Optional credential pattern registry instance.
                If None, uses current thread-local registry.
            additional_dangerous_patterns: Extra patterns to add to the defaults.
                Use this to extend rather than replace the default patterns.
            additional_sensitive_paths: Extra paths to add to the defaults.
                Use this to extend rather than replace the default paths.
            additional_injection_patterns: Extra injection patterns to add to defaults.
                Use this to extend injection detection coverage.
            additional_sanitization_patterns: Extra (pattern, replacement) tuples
                for error message sanitization. Use this to redact additional
                sensitive information from error messages.

        Example:
            # Replace all defaults with custom patterns:
            validator = SecurityValidator(dangerous_patterns=[r"my_pattern"])

            # Extend defaults with additional patterns:
            validator = SecurityValidator(
                additional_dangerous_patterns=[r"my_custom_cmd"],
                additional_sensitive_paths=[r"/opt/secrets/"],
                additional_injection_patterns=[r"UNION\\s+SELECT"],
                additional_sanitization_patterns=[(r"secret-\\d+", "[SECRET]")],
            )
        """
        self.security_level = security_level
        self.dangerous_patterns = SecurityPatterns.get_dangerous_patterns(
            dangerous_patterns, security_level, additional_dangerous_patterns
        )
        self.sensitive_paths = SecurityPatterns.get_sensitive_paths(
            sensitive_paths, security_level, additional_sensitive_paths
        )
        self.injection_patterns = SecurityPatterns.get_injection_patterns(
            additional_injection_patterns
        )
        self.sanitization_patterns = SecurityPatterns.get_sanitization_patterns(
            additional_sanitization_patterns
        )
        self.enable_audit_logging = enable_audit_logging
        self.credential_registry = credential_registry or get_current_registry()

        # Initialize audit logger
        self._audit_logger = SecurityAuditLogger(
            security_level=security_level,
            enable_audit_logging=enable_audit_logging,
            logger_name=f"{__name__}.audit",
        )

        # Initialize credential manager
        env_key = os.getenv("IMPORTOBOT_ENCRYPTION_KEY")
        if env_key:
            self.credential_manager = CredentialManager()
        else:
            ephemeral_key = secrets.token_bytes(32)
            self.credential_manager = CredentialManager(key=ephemeral_key)

    @property
    def audit_logger(self) -> Any:
        """Get the underlying audit logger for backwards compatibility."""
        return self._audit_logger.audit_logger

    def _log_security_event(
        self,
        event_type: str,
        details: dict[str, Any],
        severity: SecuritySeverity = SecuritySeverity.WARNING,
    ) -> None:
        """Log a security event with structured audit information."""
        self._audit_logger.log_security_event(event_type, details, severity)

    def log_validation_start(
        self, validation_type: str, context: dict[str, Any]
    ) -> None:
        """Log the start of a security validation operation."""
        self._audit_logger.log_validation_start(
            validation_type,
            context,
            patterns_count=len(self.dangerous_patterns),
            sensitive_paths_count=len(self.sensitive_paths),
        )

    def log_validation_complete(
        self, validation_type: str, warnings_count: int, duration_ms: float
    ) -> None:
        """Log the completion of a security validation operation."""
        self._audit_logger.log_validation_complete(
            validation_type, warnings_count, duration_ms
        )

    def validate_ssh_parameters(self, parameters: dict[str, Any]) -> list[str]:
        """Validate SSH operation parameters for security issues.

        Performs security validation based on the configured security level:
        - Checks for hardcoded credentials and password exposure
        - Detects credential patterns in parameter values
        - Validates against dangerous command patterns
        - Scans for injection patterns and command sequences
        - Identifies sensitive file paths and path traversal attempts
        - Detects production environment indicators

        Args:
            parameters: Dictionary of SSH parameters to validate

        Returns:
            List of security warnings found during validation

        Security Level Impact:
            strict: Maximum pattern matching, validation
            standard: Balanced validation with coverage
            permissive: Reduced pattern matching, fewer false positives
        """
        start_time = time.time()
        self.log_validation_start(
            "SSH_PARAMETERS", {"parameter_count": len(parameters)}
        )

        warnings = []

        # Check for hardcoded credentials
        warnings.extend(
            check_hardcoded_credentials(
                parameters, self.credential_manager, self._audit_logger
            )
        )

        # Check for sensitive file paths and path traversal
        warnings.extend(
            check_sensitive_paths(
                parameters,
                self.sensitive_paths,
                self._audit_logger,
                self.validate_file_operations,
            )
        )

        # Check for exposed credential patterns
        warnings.extend(
            check_credential_patterns(
                parameters,
                self.credential_registry,
                self.credential_manager,
                self._audit_logger,
            )
        )

        # Check for dangerous commands
        warnings.extend(
            check_dangerous_commands(
                parameters,
                self.dangerous_patterns,
                self._audit_logger,
                self.security_level.value,
            )
        )

        # Check for injection patterns
        warnings.extend(
            check_injection_patterns(
                parameters, self._audit_logger, self.injection_patterns
            )
        )

        # Check for production indicators
        warnings.extend(check_production_indicators(parameters, self._audit_logger))

        duration_ms = (time.time() - start_time) * 1000
        self.log_validation_complete("SSH_PARAMETERS", len(warnings), duration_ms)

        return warnings

    def sanitize_command_parameters(self, command: Any) -> str:
        """Sanitize command parameters to prevent injection attacks."""
        return sanitize_command_parameters(command)

    def validate_file_operations(self, file_path: str, operation: str) -> list[str]:
        """Validate file operations for security concerns.

        Validates file operations against security threats:
        - Path traversal detection (.., // patterns)
        - Sensitive file access based on security level patterns
        - Destructive operation warnings (delete, remove, truncate, drop)

        Args:
            file_path: File path to validate
            operation: Type of operation being performed (e.g., 'read', 'write',
                'delete')

        Returns:
            List of security warnings found during validation

        Security Level Impact:
            strict: Checks against expanded sensitive path list
            standard: Checks against default sensitive paths
            permissive: Uses standard sensitive path validation (no reduction)
        """
        return validate_file_operations(
            file_path, operation, self.sensitive_paths, self._audit_logger
        )

    def sanitize_error_message(self, error_msg: Any) -> str:
        """Sanitize error messages to prevent information disclosure."""
        return sanitize_error_message(error_msg, self.sanitization_patterns)

    def generate_security_recommendations(self, test_data: dict[str, Any]) -> list[str]:
        """Generate security recommendations for test case."""
        return generate_security_recommendations(test_data)

    def validate_test_security(self, test_case: dict[str, Any]) -> dict[str, list[str]]:
        """Validate test case security.

        Performs security validation of test cases:
        - Extracts and validates SSH parameters from test steps
        - Applies security validation based on configured security level
        - Generates security recommendations for different test types
        - Provides structured results with warnings, recommendations, and errors

        Args:
            test_case: Test case dictionary containing steps and test data

        Returns:
            Dictionary with validation results:
            - 'warnings': List of security warnings found
            - 'recommendations': List of security recommendations
            - 'sanitized_errors': List of sanitized error messages

        Security Level Impact:
            strict: Validation with expanded pattern matching
            standard: Balanced validation suitable for most environments
            permissive: Reduced validation to minimize false positives
        """
        return validate_test_security(test_case)

    # Backwards compatibility: expose pattern methods
    def _get_patterns(
        self, custom_patterns: list[str] | None, level: SecurityLevel
    ) -> list[str]:
        """Get dangerous patterns based on security level."""
        return SecurityPatterns.get_dangerous_patterns(custom_patterns, level)

    def _get_sensitive_paths(
        self, custom_paths: list[str] | None, level: SecurityLevel
    ) -> list[str]:
        """Get sensitive paths based on security level."""
        return SecurityPatterns.get_sensitive_paths(custom_paths, level)


# Internal utility - not part of public API
__all__: list[str] = []
