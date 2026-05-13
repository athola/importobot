"""Security utilities for test generation and Robot Framework operations.

This module provides the main SecurityValidator class that orchestrates
security validation using specialized modules for audit logging, pattern
matching, and various security checks.
"""

import contextlib
import os
import secrets
import subprocess
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
from importobot.security.test_validation import _extract_ssh_parameters
from importobot.services.security_types import SecurityLevel, SecurityPolicy
from importobot.utils.command_security import (
    CommandValidationResult,
    CommandValidator,
)
from importobot.utils.string_cache import data_to_lower_cached

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
        command_security_policy: SecurityPolicy = SecurityPolicy.BLOCK,
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

        Note (encryption key fallback - PR #90 review I9):
            If the ``IMPORTOBOT_ENCRYPTION_KEY`` environment variable is
            **not** set when this validator is constructed, an ephemeral
            32-byte key is generated for the lifetime of the process.
            Credentials encrypted with that key become undecryptable on
            process restart - this is a hard data-loss footgun for
            callers that persist ciphertext. Set
            ``IMPORTOBOT_ENCRYPTION_KEY`` to a stable value to enable
            cross-process decryption.

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

        # Initialize credential manager. When IMPORTOBOT_ENCRYPTION_KEY is
        # unset we fall back to an ephemeral 32-byte key for the lifetime
        # of the process: encrypted credentials become undecryptable after
        # restart (this is a hard data-loss footgun for callers that
        # persist ciphertext — see CHANGELOG).
        env_key = os.getenv("IMPORTOBOT_ENCRYPTION_KEY")
        if env_key:
            self.credential_manager = CredentialManager()
        else:
            ephemeral_key = secrets.token_bytes(32)
            self.credential_manager = CredentialManager(key=ephemeral_key)

        # Command-execution helpers retained for callers migrated from
        # ``importobot.utils.security.SecurityValidator`` (now an alias).
        self.command_security_policy = command_security_policy
        self.command_validator = CommandValidator(
            security_level=security_level,
            policy=command_security_policy,
            enable_audit_logging=enable_audit_logging,
        )

    def validate_command_for_execution(
        self,
        command: str,
        args: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, str, list[str]]:
        """Run the full ``CommandValidator`` and return a structured result."""
        if args is not None:
            result, full_command, warnings = (
                self.command_validator.validate_command_args(command, args)
            )
        else:
            result, full_command, warnings = self.command_validator.validate_command(
                command, context
            )
        is_safe = result in (
            CommandValidationResult.ALLOWED,
            CommandValidationResult.MODIFIED,
        )
        return is_safe, full_command, warnings

    def create_safe_subprocess(
        self, command: str, args: list[str] | None = None, **kwargs: Any
    ) -> tuple[bool, subprocess.Popen[str] | None, list[str]]:
        """Spawn a subprocess only after the command passes validation."""
        return self.command_validator.create_safe_process(command, args, **kwargs)

    @property
    def audit_logger(self) -> Any:
        """Get the underlying audit logger for backwards compatibility."""
        return self._audit_logger.audit_logger

    @audit_logger.setter
    def audit_logger(self, value: Any) -> None:
        """Replace the underlying audit logger (used by tests for mocking)."""
        self._audit_logger.audit_logger = value

    @audit_logger.deleter
    def audit_logger(self) -> None:
        """Reset the underlying audit logger (used by unittest.mock teardown)."""
        with contextlib.suppress(AttributeError):
            del self._audit_logger.audit_logger

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
        """Sanitize command parameters honouring ``command_security_policy``.

        - ``BLOCK``: return ``""`` if the command is not safe to execute;
          otherwise return the original string. Matches the contract
          callers migrated from ``utils.security.SecurityValidator`` rely
          on (PR #90 review C6).
        - ``SANITIZE``: drop dangerous tokens (``rm``, ``&&``, …) via
          ``CommandValidator`` and return the residue.
        - ``ESCAPE``: escape dangerous characters and return the result.
        - ``WARN``: log warnings via ``CommandValidator`` and pass the
          original string through unchanged.
        """
        if not isinstance(command, str):
            command = str(command)

        policy = self.command_security_policy
        if policy in (
            SecurityPolicy.BLOCK,
            SecurityPolicy.SANITIZE,
            SecurityPolicy.WARN,
        ):
            is_safe, processed, _warnings = self.validate_command_for_execution(command)
            if policy is SecurityPolicy.BLOCK and not is_safe:
                return ""
            return processed
        return sanitize_command_parameters(command)

    def validate_file_operations(self, file_path: str, operation: str) -> list[str]:
        """Validate file operations for security concerns.

        Validates file operations against security threats:
        - Path traversal detection (.., // patterns)
        - Sensitive file access against the sensitive paths configured
          at construction time
        - Destructive operation warnings (delete, remove, truncate, drop)

        Args:
            file_path: File path to validate
            operation: Type of operation being performed (e.g., 'read', 'write',
                'delete')

        Returns:
            List of security warnings found during validation

        Note:
            The sensitive-path filter is fixed at constructor time (it
            consults ``self.sensitive_paths``). Per-call security levels
            are not consulted here - PR #90 review I8 corrects the
            earlier docstring claim to that effect.
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
        # Run the validation in-process so events flow through ``self``'s
        # audit logger; the free ``_validate_test_security`` function
        # creates its own internal validator which would not honour
        # mocks attached to ``self``.
        start_time = time.time()
        self.log_validation_start(
            "TEST_CASE_SECURITY",
            {
                "test_case_keys": list(test_case.keys()),
                "has_steps": "steps" in test_case,
                "steps_count": len(test_case.get("steps", [])),
            },
        )

        results: dict[str, list[str]] = {
            "warnings": [],
            "recommendations": [],
            "sanitized_errors": [],
        }

        if "ssh" in data_to_lower_cached(test_case):
            for step in test_case.get("steps", []):
                if (
                    "ssh" in data_to_lower_cached(step)
                    or step.get("library") == "SSHLibrary"
                ):
                    ssh_params = _extract_ssh_parameters(step.get("test_data", ""))
                    results["warnings"].extend(self.validate_ssh_parameters(ssh_params))

        results["recommendations"].extend(generate_security_recommendations(test_case))

        duration_ms = (time.time() - start_time) * 1000
        self.log_validation_complete(
            "TEST_CASE_SECURITY", len(results["warnings"]), duration_ms
        )
        return results

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
