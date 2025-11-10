"""Security utilities for test generation and Robot Framework operations."""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, ClassVar

from importobot.utils.credential_manager import CredentialManager, EncryptedCredential
from importobot.utils.logging import get_logger
from importobot.utils.string_cache import data_to_lower_cached

logger = get_logger()


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
    """

    # Default dangerous command patterns
    DEFAULT_DANGEROUS_PATTERNS: ClassVar[list[str]] = [
        r"rm\s+-rf",
        r"sudo\s+",
        r"chmod\s+777",
        r">\s*/dev/null",
        r"\|\s*sh",
        r"\|\s*bash",
        r"eval\s*\(",
        r"exec\s*\(",
        r"`[^`]*`",  # Command substitution
        r"\$\([^)]*\)",  # Command substitution
        r"&&\s*rm",
        r";\s*rm",
        r"curl.*\|\s*sh",
        r"wget.*\|\s*sh",
        # Additional dangerous patterns
        r"dd\s+if=.*of=/dev/",  # Disk dump operations
        r"mkfs\.",  # Format filesystem
        r"fdisk\s",  # Disk partitioning
        r":\(\)\{.*:\|:&.*\};:",  # Fork bomb pattern
        r"cat\s+/etc/shadow",  # Reading shadow file
        r">\s*/etc/passwd",  # Overwriting passwd
        r"/dev/sda",  # Direct disk access
        r"/dev/hda",  # Direct disk access
    ]

    # Default sensitive path patterns
    DEFAULT_SENSITIVE_PATHS: ClassVar[list[str]] = [
        r"/etc/passwd",
        r"/etc/shadow",
        r"/home/[^/]+/\.ssh",
        r"\.aws/credentials",
        r"\.ssh/id_rsa",
        r"/root/",
        r"C:\\Windows\\System32",
        r"%USERPROFILE%",
    ]

    def __init__(
        self,
        dangerous_patterns: list[str] | None = None,
        sensitive_paths: list[str] | None = None,
        security_level: str = "standard",
        enable_audit_logging: bool = True,
    ):
        """Initialize security validator with configurable patterns.

        Args:
            dangerous_patterns: Custom dangerous command patterns to override defaults
            sensitive_paths: Custom sensitive path patterns to override defaults
            security_level: Security level determining validation strictness:
                - 'strict': Maximum security for enterprise/production environments
                - 'standard': Balanced security for general development and testing
                  (default)
                - 'permissive': Relaxed security for trusted development environments
            enable_audit_logging: Enable detailed audit logging for security events
        """
        self.security_level = security_level
        self.dangerous_patterns = self._get_patterns(dangerous_patterns, security_level)
        self.sensitive_paths = self._get_sensitive_paths(
            sensitive_paths, security_level
        )
        self.enable_audit_logging = enable_audit_logging
        self.audit_logger = get_logger(f"{__name__}.audit")

        self.credential_manager = CredentialManager()

        # Set up audit logger with specific formatting if enabled
        if self.enable_audit_logging:
            self._setup_audit_logger()

    def _setup_audit_logger(self) -> None:
        """Set up audit logger with structured formatting for security events."""
        # Prevent adding multiple handlers
        if not self.audit_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - SECURITY_AUDIT - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.audit_logger.setLevel(logging.INFO)
            self.audit_logger.addHandler(handler)

    def _log_security_event(
        self, event_type: str, details: dict[str, Any], severity: str = "WARNING"
    ) -> None:
        """Log a security event with structured audit information.

        Args:
            event_type: Type of security event (e.g., 'DANGEROUS_COMMAND',
                           'SENSITIVE_PATH')
            details: Dictionary containing event details
            severity: Severity level ('INFO', 'WARNING', 'ERROR')
        """
        if not self.enable_audit_logging:
            return

        # Create structured audit log entry
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "security_level": self.security_level,
            "severity": severity,
            "details": details,
        }

        # Log as JSON for structured parsing
        log_message = json.dumps(audit_entry, default=str)

        if severity == "ERROR":
            self.audit_logger.error(log_message)
        elif severity == "WARNING":
            self.audit_logger.warning(log_message)
        else:
            self.audit_logger.info(log_message)

    def log_validation_start(
        self, validation_type: str, context: dict[str, Any]
    ) -> None:
        """Log the start of a security validation operation.

        Args:
            validation_type: Type of validation being performed
            context: Context information about the validation
        """
        if not self.enable_audit_logging:
            return

        self._log_security_event(
            "VALIDATION_START",
            {
                "validation_type": validation_type,
                "context": context,
                "patterns_count": len(self.dangerous_patterns),
                "sensitive_paths_count": len(self.sensitive_paths),
            },
            "INFO",
        )

    def log_validation_complete(
        self, validation_type: str, warnings_count: int, duration_ms: float
    ) -> None:
        """Log the completion of a security validation operation.

        Args:
            validation_type: Type of validation that was performed
            warnings_count: Number of warnings generated
            duration_ms: Duration of validation in milliseconds
        """
        if not self.enable_audit_logging:
            return

        self._log_security_event(
            "VALIDATION_COMPLETE",
            {
                "validation_type": validation_type,
                "warnings_count": warnings_count,
                "duration_ms": duration_ms,
            },
            "INFO",
        )

    def _get_patterns(self, custom_patterns: list[str] | None, level: str) -> list[str]:
        """Get dangerous patterns based on security level.

        Args:
            custom_patterns: Custom patterns to use instead of defaults
            level: Security level ('strict', 'standard', 'permissive')

        Returns:
            List of dangerous command patterns for the specified security level

        Security Level Behavior:
            strict: Adds patterns for proc filesystem, network enumeration,
                   process enumeration, user enumeration, and external network requests
            standard: Uses default patterns covering system commands, file operations,
                     and dangerous shell operations
            permissive: Removes development-friendly patterns (curl, wget, /dev/null)
                       to reduce false positives in trusted environments
        """
        base_patterns = custom_patterns or self.DEFAULT_DANGEROUS_PATTERNS

        if level == "strict":
            # Add stricter patterns for production environments
            strict_additions = [
                r"cat\s+/proc/",  # Reading proc filesystem
                r"netstat\s",  # Network enumeration
                r"ps\s+aux",  # Process enumeration
                r"whoami",  # User enumeration
                r"id\s",  # User ID enumeration
                r"curl\s+",  # External network requests
                r"wget\s+",  # External network requests
            ]
            return base_patterns + strict_additions
        if level == "permissive":
            # Remove some patterns for development environments
            permissive_removals = {r"curl\s+", r"wget\s+", r">\s*/dev/null"}
            return [p for p in base_patterns if p not in permissive_removals]

        return base_patterns

    def _get_sensitive_paths(
        self, custom_paths: list[str] | None, level: str
    ) -> list[str]:
        """Get sensitive paths based on security level.

        Args:
            custom_paths: Custom paths to use instead of defaults
            level: Security level ('strict', 'standard', 'permissive')

        Returns:
            List of sensitive file path patterns for the specified security level

        Security Level Behavior:
            strict: Add paths for system directories (/proc/, /sys/),
                   Kubernetes configs, Docker configs, system logs, and Windows
                   ProgramData
            standard: Uses default paths covering system files, SSH keys, cloud
                     credentials, root access, and Windows system directories
            permissive: Uses standard paths (no reduction in sensitive path
                       protection)
        """
        base_paths = custom_paths or self.DEFAULT_SENSITIVE_PATHS

        if level == "strict":
            # Add more paths for production environments
            strict_additions = [
                r"/proc/",
                r"/sys/",
                r"\.kube/config",
                r"\.docker/config\.json",
                r"/var/log/",
                r"C:\\ProgramData",
            ]
            return base_paths + strict_additions

        return base_paths

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
        credential_warnings = self._check_hardcoded_credentials(parameters)
        warnings.extend(credential_warnings)

        # Check for exposed credential patterns in parameter values
        pattern_warnings = self._check_credential_patterns(parameters)
        warnings.extend(pattern_warnings)

        # Check for dangerous commands
        command_warnings = self._check_dangerous_commands(parameters)
        warnings.extend(command_warnings)

        # Check for injection patterns in all parameter values
        injection_warnings = self._check_injection_patterns(parameters)
        warnings.extend(injection_warnings)

        # Check for sensitive file paths and path traversal
        path_warnings = self._check_sensitive_paths(parameters)
        warnings.extend(path_warnings)

        # Check for production indicators
        production_warnings = self._check_production_indicators(parameters)
        warnings.extend(production_warnings)

        duration_ms = (time.time() - start_time) * 1000
        self.log_validation_complete("SSH_PARAMETERS", len(warnings), duration_ms)

        return warnings

    def _check_hardcoded_credentials(self, parameters: dict[str, Any]) -> list[str]:
        """Check for hardcoded credentials in parameters."""
        warnings = []

        password_value = parameters.get("password")
        if isinstance(password_value, EncryptedCredential):
            warnings.append("Password encrypted in memory")
            return warnings

        if password_value:
            warning_msg = (
                "WARNING: SSH password found - consider using key-based authentication"
            )
            warnings.append(warning_msg)

            # Log audit event for password detection
            self._log_security_event(
                "HARDCODED_PASSWORD",
                {
                    "parameter": "password",
                    "has_value": bool(parameters.get("password")),
                    "recommendation": "Use key-based authentication",
                },
                "WARNING",
            )

            # Also flag as credential exposure
            if isinstance(password_value, str) and len(password_value) > 1:
                exposure_warning = (
                    "WARNING: Hardcoded credential detected - avoid exposing "
                    "secrets in test data"
                )
                warnings.append(exposure_warning)

                # Log audit event for credential exposure
                self._log_security_event(
                    "CREDENTIAL_EXPOSURE",
                    {
                        "parameter": "password",
                        "credential_length": len(password_value),
                        "risk_level": "HIGH",
                    },
                    "ERROR",
                )

            if isinstance(password_value, str):
                try:
                    encrypted = self.credential_manager.encrypt_credential(
                        password_value
                    )
                    parameters["password"] = encrypted
                    warnings.append("Password encrypted in memory")
                    self._log_security_event(
                        "PASSWORD_ENCRYPTED",
                        {
                            "parameter": "password",
                            "credential_length": encrypted.length,
                        },
                        "INFO",
                    )
                except Exception as exc:  # pragma: no cover - encryption failed
                    logger.warning("Failed to encrypt password parameter: %s", exc)

        return warnings

    def _check_credential_patterns(self, parameters: dict[str, Any]) -> list[str]:
        """Check for exposed credential patterns in parameter values."""
        warnings = []
        credential_patterns = [
            r"password.*[:\s]+\w{6,}",  # password: something
            r"secret.*[:\s]+\w{6,}",  # secret: something
            r"token.*[:\s]+\w{10,}",  # token: something
            r"key.*[:\s]+[\w/]{10,}",  # key: something
            r"hardcoded.*secret",  # hardcoded_secret_123
        ]

        for key, value in parameters.items():
            if isinstance(value, EncryptedCredential):
                continue

            if isinstance(value, str) and "password" in key.lower():
                try:
                    parameters[key] = self.credential_manager.encrypt_credential(value)
                    warnings.append(f"✓ {key} encrypted in memory to reduce exposure")
                except Exception as exc:  # pragma: no cover - encryption failed
                    logger.warning(
                        "Failed to encrypt credential parameter %s: %s",
                        key,
                        exc,
                    )
                continue

            if isinstance(value, str):
                for pattern in credential_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        warning_msg = (
                            f"WARNING: Potential hardcoded credential exposure "
                            f"detected in {key}"
                        )
                        warnings.append(warning_msg)

                        # Log audit event for credential pattern detection
                        self._log_security_event(
                            "CREDENTIAL_PATTERN_DETECTED",
                            {
                                "parameter": key,
                                "pattern": pattern,
                                "value_preview": (
                                    value[:20] + "..." if len(value) > 20 else value
                                ),
                                "risk_level": "MEDIUM",
                            },
                            "WARNING",
                        )
                        break

        return warnings

    def _check_dangerous_commands(self, parameters: dict[str, Any]) -> list[str]:
        """Check for dangerous command patterns."""
        warnings = []

        if "command" in parameters:
            command = str(parameters["command"])
            for pattern in self.dangerous_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    warning_msg = (
                        f"Potentially dangerous command pattern detected: {pattern}"
                    )
                    warnings.append(warning_msg)

                    # Log audit event for dangerous command detection
                    self._log_security_event(
                        "DANGEROUS_COMMAND",
                        {
                            "pattern": pattern,
                            "command_preview": (
                                command[:50] + "..." if len(command) > 50 else command
                            ),
                            "security_level": self.security_level,
                            "risk_level": "HIGH",
                        },
                        "ERROR",
                    )

        return warnings

    def _check_injection_patterns(self, parameters: dict[str, Any]) -> list[str]:
        """Check for injection patterns in parameter values."""
        warnings = []
        injection_patterns = [
            r";.*rm\s",
            r"`[^`]*`",
            r"\$\([^)]*\)",
            r"&&.*wget",
            r"\|\s*sh",
            r"'.*OR.*'",
            r"\".*OR.*\"",
            r"cat\s+/etc/",
            r"curl.*\|",
            r"wget.*\|",
            r"eval\s*\(",
            r"exec\s*\(",
        ]

        for key, value in parameters.items():
            if isinstance(value, str):
                for pattern in injection_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        warning_msg = (
                            f"WARNING: Potential injection pattern detected in {key}: "
                            f"suspicious command sequence"
                        )
                        warnings.append(warning_msg)

                        # Log audit event for injection pattern
                        # detection
                        self._log_security_event(
                            "INJECTION_PATTERN",
                            {
                                "parameter": key,
                                "pattern": pattern,
                                "value_preview": (
                                    value[:30] + "..." if len(value) > 30 else value
                                ),
                                "injection_type": "command_injection",
                                "risk_level": "HIGH",
                            },
                            "ERROR",
                        )
                        break

        return warnings

    def _check_sensitive_paths(self, parameters: dict[str, Any]) -> list[str]:
        """Check for sensitive file paths and path traversal."""
        warnings = []

        for key, value in parameters.items():
            if isinstance(value, str) and (
                "path" in key.lower() or key in ["source_path", "destination_path"]
            ):
                # Check for path traversal using validate_file_operations
                file_warnings = self.validate_file_operations(value, "access")
                warnings.extend(file_warnings)

            if isinstance(value, str):
                for pattern in self.sensitive_paths:
                    if re.search(pattern, value, re.IGNORECASE):
                        warning_msg = f"Sensitive path detected in {key}: {pattern}"
                        warnings.append(warning_msg)

                        # Log audit event for sensitive path
                        # detection
                        self._log_security_event(
                            "SENSITIVE_PATH",
                            {
                                "parameter": key,
                                "pattern": pattern,
                                "value_preview": (
                                    value[:40] + "..." if len(value) > 40 else value
                                ),
                                "risk_level": "MEDIUM",
                            },
                            "WARNING",
                        )

        return warnings

    def _check_production_indicators(self, parameters: dict[str, Any]) -> list[str]:
        """Check for production environment indicators."""
        warnings = []
        lowered = data_to_lower_cached(parameters)

        if any(env in lowered for env in ["prod", "production", "live"]):
            warning_msg = (
                "WARNING: Production environment detected - ensure proper authorization"
            )
            warnings.append(warning_msg)

            # Log audit event for production environment
            # detection
            self._log_security_event(
                "PRODUCTION_ENVIRONMENT",
                {
                    "detected_indicators": [
                        env for env in ["prod", "production", "live"] if env in lowered
                    ],
                    "parameter_preview": (
                        str(parameters)[:100] + "..."
                        if len(str(parameters)) > 100
                        else str(parameters)
                    ),
                    "risk_level": "MEDIUM",
                    "recommendation": "Ensure proper authorization for production",
                },
                "WARNING",
            )

        return warnings

    def sanitize_command_parameters(self, command: Any) -> str:
        """Sanitize command parameters to prevent injection attacks."""
        if not isinstance(command, str):
            return str(command)

        # Remove potentially dangerous characters and patterns
        sanitized = command

        # Escape shell metacharacters
        dangerous_chars = ["|", "&", ";", "$(", "`", ">", "<", "*", "?", "[", "]"]
        for char in dangerous_chars:
            if char in sanitized:
                logger.warning(
                    "Potentially dangerous character '%s' found in command, escaping",
                    char,
                )
                sanitized = sanitized.replace(char, f"\\{char}")

        return sanitized

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
        warnings = []

        # Check for path traversal attempts
        if ".." in file_path or "//" in file_path:
            warning_msg = "WARNING: Potential path traversal detected in file path"
            warnings.append(warning_msg)

            # Log audit event for path traversal detection
            self._log_security_event(
                "PATH_TRAVERSAL",
                {
                    "file_path": file_path,
                    "operation": operation,
                    "traversal_patterns": ["..", "//"],
                    "risk_level": "HIGH",
                },
                "ERROR",
            )

        # Check for sensitive file access
        for pattern in self.sensitive_paths:
            if re.search(pattern, file_path, re.IGNORECASE):
                warning_msg = f"WARNING: Sensitive file access detected: {file_path}"
                warnings.append(warning_msg)

                # Log audit event for sensitive file access
                self._log_security_event(
                    "SENSITIVE_FILE_ACCESS",
                    {
                        "file_path": file_path,
                        "operation": operation,
                        "matched_pattern": pattern,
                        "risk_level": "MEDIUM",
                    },
                    "WARNING",
                )

        # Warn about destructive operations
        if operation.lower() in ["delete", "remove", "truncate", "drop"]:
            warning_msg = (
                f"Destructive operation '{operation}' - ensure proper safeguards"
            )
            warnings.append(warning_msg)

            # Log audit event for destructive operation
            self._log_security_event(
                "DESTRUCTIVE_OPERATION",
                {
                    "file_path": file_path,
                    "operation": operation,
                    "risk_level": "MEDIUM",
                    "recommendation": "Ensure proper safeguards and authorization",
                },
                "WARNING",
            )

        return warnings

    def sanitize_error_message(self, error_msg: Any) -> str:
        """Sanitize error messages to prevent information disclosure."""
        if not isinstance(error_msg, str):
            return str(error_msg)

        sanitized = error_msg

        # Remove sensitive path information
        sensitive_patterns = [
            (r"/home/[^/\s]+", "/home/[USER]"),
            (r"C:\\Users\\[^\\]+", "C:/Users/[USER]"),
            (r"/Users/[^/\s]+", "/Users/[USER]"),
            (
                r"(/[^/\s]*){3,}",
                "[PATH]",
            ),  # Long absolute paths (must come after specific patterns)
            (r"[a-zA-Z]:\\[^\\]+\\[^\\]+\\[^\\]+", "[PATH]"),  # Long Windows paths
        ]

        for pattern, replacement in sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    def generate_security_recommendations(self, test_data: dict[str, Any]) -> list[str]:
        """Generate security recommendations for test case."""
        recommendations = []

        # Check for SSH usage
        if any(
            "ssh" in data_to_lower_cached(value) or "ssh" in key.lower()
            for key, value in test_data.items()
        ):
            recommendations.extend(
                [
                    "Use key-based authentication instead of passwords for SSH",
                    "Implement connection timeouts for SSH operations",
                    "Use dedicated test environments, not production systems",
                    "Validate host key fingerprints in automated tests",
                ]
            )

        # Check for database operations
        if any(
            "database" in data_to_lower_cached(value)
            or "sql" in data_to_lower_cached(value)
            or "select" in data_to_lower_cached(value)
            or "insert" in data_to_lower_cached(value)
            or "update" in data_to_lower_cached(value)
            or "delete" in data_to_lower_cached(value)
            or "database" in key.lower()
            or "query" in key.lower()
            for key, value in test_data.items()
        ):
            recommendations.extend(
                [
                    "Use parameterized queries to prevent SQL injection",
                    "Test with minimal database privileges",
                    "Sanitize all user inputs in database tests",
                ]
            )

        # Check for web operations
        if any(
            "browser" in data_to_lower_cached(value)
            or "web" in data_to_lower_cached(value)
            or "browser" in key.lower()
            or "url" in key.lower()
            for key, value in test_data.items()
        ):
            recommendations.extend(
                [
                    "TIP: Validate all form inputs for XSS prevention",
                    "TIP: Test authentication and authorization flows",
                    "TIP: Use secure test data, avoid production credentials",
                ]
            )

        return recommendations

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


def validate_test_security(test_case: dict[str, Any]) -> dict[str, list[str]]:
    """Security validation for test cases.

    Creates a SecurityValidator with standard security level and performs validation.

    Args:
        test_case: Test case dictionary containing steps and test data

    Returns:
        Dictionary with validation results:
        - 'warnings': List of security warnings found
        - 'recommendations': List of security recommendations
        - 'sanitized_errors': List of sanitized error messages

    Note:
        Uses standard security level by default. For custom security levels,
        create a SecurityValidator instance directly with the desired level.
    """
    start_time = time.time()
    validator = SecurityValidator()

    # Log validation start
    validator.log_validation_start(
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

    # Validate SSH operations
    if "ssh" in data_to_lower_cached(test_case):
        # Extract SSH parameters from test case steps
        for step in test_case.get("steps", []):
            if (
                "ssh" in data_to_lower_cached(step)
                or step.get("library") == "SSHLibrary"
            ):
                # Parse test_data for SSH parameters
                test_data = step.get("test_data", "")
                ssh_params = {}

                # Extract various SSH parameters using comprehensive patterns
                parameter_patterns = {
                    "password": r"password:\s*([^,\n\s]+)",
                    "username": r"username:\s*([^,\n\s]+)",
                    "keyfile": r"keyfile:\s*([^,\n\s]+)",
                    "command": r"command:\s*([^,\n]+)",
                    "host": r"host:\s*([^,\n\s]+)",
                    "source_path": r"source:\s*([^,\n]+)",
                    "destination_path": r"destination:\s*([^,\n]+)",
                    # Also extract parameters without colons for generic patterns
                    "parameter": r"parameter:\s*([^,\n]+)",
                }

                for param_name, pattern in parameter_patterns.items():
                    match = re.search(pattern, test_data)
                    if match:
                        ssh_params[param_name] = match.group(1).strip()

                # Additional processing: ensure password detection includes the value
                # for pattern matching
                if "password:" in test_data and "password" not in ssh_params:
                    ssh_params["password"] = True

                ssh_warnings = validator.validate_ssh_parameters(ssh_params)
                results["warnings"].extend(ssh_warnings)

    # Generate security recommendations
    recommendations = validator.generate_security_recommendations(test_case)
    results["recommendations"].extend(recommendations)

    # Log security analysis
    if results["warnings"]:
        logger.warning(
            "Security warnings for test case: %d issues found", len(results["warnings"])
        )

    # Log validation completion
    duration_ms = (time.time() - start_time) * 1000
    validator.log_validation_complete(
        "TEST_CASE_SECURITY", len(results["warnings"]), duration_ms
    )

    return results


def get_ssh_security_guidelines() -> list[str]:
    """Get SSH security guidelines for test automation."""
    return [
        "SSH Security Guidelines:",
        "• Use key-based authentication instead of passwords",
        "• Implement connection timeouts (default: 30 seconds)",
        "• Validate host key fingerprints",
        "• Use dedicated test environments",
        "• Limit SSH user privileges to minimum required",
        "• Log all SSH operations for audit trails",
        "• Never hardcode credentials in test scripts",
        "• Use environment variables or secure vaults for secrets",
        "• Implement proper error handling to avoid information disclosure",
        "• Regular security audits of SSH configurations",
        "• Monitor for unusual SSH activity patterns",
        "• Implement continuous monitoring and alerting",
        "• Restrict network access to SSH services",
        "• Use strong encryption algorithms and key sizes",
    ]


# Shared SSH security guidelines constant
SSH_SECURITY_GUIDELINES = [
    "SSH Security Guidelines for Test Automation:",
    "• Use key-based authentication instead of passwords",
    "• Implement connection timeouts (default: 30 seconds)",
    "• Validate host key fingerprints in production",
    "• Use dedicated test environments, not production systems",
    "• Limit SSH user privileges to minimum required",
    "• Log all SSH operations for audit trails",
    "• Never hardcode credentials in test scripts",
    "• Use environment variables or secure vaults for secrets",
    "• Implement proper error handling to avoid information disclosure",
    "• Regular security audits of SSH configurations",
    "• Monitor for unusual SSH activity patterns",
    "• Implement continuous monitoring and alerting",
    "• Restrict network access to SSH services",
    "• Use strong encryption algorithms and key sizes",
]


def extract_security_warnings(keyword_info: dict[str, Any]) -> list[str]:
    """Extract security warnings from keyword information.

    Args:
        keyword_info: Dictionary containing keyword information

    Returns:
        List of security warnings and notes
    """
    warnings = []
    if "security_warning" in keyword_info:
        warnings.append(keyword_info["security_warning"])
    if "security_note" in keyword_info:
        warnings.append(keyword_info["security_note"])
    return warnings


# Internal utility - not part of public API
__all__: list[str] = []
