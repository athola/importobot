"""Security check functions for validation.

Provides individual check functions for credentials, commands, paths,
injection patterns, and production indicators.
"""

import re
from typing import Any

from importobot.security.audit import SecurityAuditLogger, SecuritySeverity
from importobot.security.credential_manager import (
    CredentialManager,
    EncryptedCredential,
)
from importobot.security.credential_patterns import (
    CredentialPattern,
    CredentialPatternRegistry,
)
from importobot.security.patterns import SecurityPatterns
from importobot.utils.logging import get_logger
from importobot.utils.string_cache import data_to_lower_cached

logger = get_logger()


def check_hardcoded_credentials(
    parameters: dict[str, Any],
    credential_manager: CredentialManager,
    audit_logger: SecurityAuditLogger,
) -> list[str]:
    """Check for hardcoded credentials in parameters.

    Args:
        parameters: Dictionary of parameters to check
        credential_manager: Manager for encrypting detected credentials
        audit_logger: Logger for audit events

    Returns:
        List of security warnings
    """
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

        audit_logger.log_security_event(
            "HARDCODED_PASSWORD",
            {
                "parameter": "password",
                "has_value": bool(parameters.get("password")),
                "recommendation": "Use key-based authentication",
            },
            SecuritySeverity.WARNING,
        )

        if isinstance(password_value, str) and len(password_value) > 1:
            exposure_warning = (
                "WARNING: Hardcoded credential detected - avoid exposing "
                "secrets in test data"
            )
            warnings.append(exposure_warning)

            audit_logger.log_security_event(
                "CREDENTIAL_EXPOSURE",
                {
                    "parameter": "password",
                    "credential_length": len(password_value),
                    "risk_level": "HIGH",
                },
                SecuritySeverity.ERROR,
            )

        if isinstance(password_value, str):
            try:
                encrypted = credential_manager.encrypt_credential(password_value)
                parameters["password"] = encrypted
                warnings.append("Password encrypted in memory")
                audit_logger.log_security_event(
                    "PASSWORD_ENCRYPTED",
                    {
                        "parameter": "password",
                        "credential_length": encrypted.length,
                    },
                    SecuritySeverity.INFO,
                )
            except Exception as exc:  # pragma: no cover - encryption failed
                logger.warning("Failed to encrypt password parameter: %s", exc)

    return warnings


def check_credential_patterns(
    parameters: dict[str, Any],
    credential_registry: CredentialPatternRegistry,
    credential_manager: CredentialManager,
    audit_logger: SecurityAuditLogger,
) -> list[str]:
    """Check for exposed credential patterns in parameter values.

    Args:
        parameters: Dictionary of parameters to check
        credential_registry: Registry of credential patterns
        credential_manager: Manager for encrypting detected credentials
        audit_logger: Logger for audit events

    Returns:
        List of security warnings
    """
    warnings: list[str] = []

    patterns_to_check = credential_registry.get_patterns_by_confidence(0.8)

    for key, value in parameters.items():
        if _should_skip_credential_check(value):
            continue

        if _try_encrypt_password_parameter(
            parameters, key, value, credential_manager, warnings
        ):
            continue

        if not isinstance(value, str):
            continue

        found_patterns = [
            pattern for pattern in patterns_to_check if pattern.matches(value)
        ]
        warnings.extend(_build_pattern_warnings(key, found_patterns))

        if not found_patterns:
            continue

        highest_confidence = max(found_patterns, key=lambda p: p.confidence)
        _auto_encrypt_high_confidence_match(
            parameters, key, value, highest_confidence, credential_manager, warnings
        )
        _log_pattern_detection_event(key, value, highest_confidence, audit_logger)

    return warnings


def _should_skip_credential_check(value: Any) -> bool:
    """Return True when a parameter value should be skipped."""
    return isinstance(value, EncryptedCredential)


def _try_encrypt_password_parameter(
    parameters: dict[str, Any],
    key: str,
    value: Any,
    credential_manager: CredentialManager,
    warnings: list[str],
) -> bool:
    """Auto-encrypt obvious password parameters."""
    if isinstance(value, str) and "password" in key.lower():
        message = f"[ENCRYPTED] {key} encrypted in memory to reduce exposure"
        return _encrypt_parameter(
            parameters, key, value, credential_manager, warnings, message
        )
    return False


def _build_pattern_warnings(
    key: str, found_patterns: list[CredentialPattern]
) -> list[str]:
    """Build user-facing warnings for detected credential patterns."""
    return [
        (
            "[DETECTED] "
            f"{pattern_obj.credential_type.value.title()} detected in {key}: "
            f"{pattern_obj.description}"
        )
        for pattern_obj in found_patterns
    ]


def _auto_encrypt_high_confidence_match(
    parameters: dict[str, Any],
    key: str,
    value: str,
    match: CredentialPattern,
    credential_manager: CredentialManager,
    warnings: list[str],
) -> None:
    """Auto-encrypt the parameter when the detection is high confidence."""
    should_encrypt = match.confidence >= 0.9 and match.severity in [
        "high",
        "critical",
    ]
    if not should_encrypt:
        return

    warning_msg = (
        f"[AUTO-ENCRYPTED] {key} auto-encrypted due to "
        f"{match.credential_type.value} detection"
    )
    _encrypt_parameter(
        parameters, key, value, credential_manager, warnings, warning_msg
    )


def _encrypt_parameter(
    parameters: dict[str, Any],
    key: str,
    value: str,
    credential_manager: CredentialManager,
    warnings: list[str],
    warning_message: str,
) -> bool:
    """Encrypt a parameter value and append the corresponding warning."""
    try:
        parameters[key] = credential_manager.encrypt_credential(value)
        warnings.append(warning_message)
        return True
    except Exception as exc:  # pragma: no cover - encryption failed
        logger.warning(
            "Failed to encrypt credential parameter %s: %s",
            key,
            exc,
        )
        return False


def _log_pattern_detection_event(
    key: str,
    value: str,
    match: CredentialPattern,
    audit_logger: SecurityAuditLogger,
) -> None:
    """Log a credential pattern detection event for auditing."""
    audit_logger.log_security_event(
        "CREDENTIAL_PATTERN_DETECTED",
        {
            "parameter": key,
            "credential_type": match.credential_type.value,
            "confidence": match.confidence,
            "severity": match.severity,
            "pattern": match.description,
            "value_preview": value[:20] + "..." if len(value) > 20 else value,
            "risk_level": match.severity.upper(),
            "remediation": match.remediation,
        },
        (
            SecuritySeverity.WARNING
            if match.severity in ["high", "critical"]
            else SecuritySeverity.INFO
        ),
    )


def check_dangerous_commands(
    parameters: dict[str, Any],
    dangerous_patterns: list[str],
    audit_logger: SecurityAuditLogger,
    security_level_value: str,
) -> list[str]:
    """Check for dangerous command patterns.

    Args:
        parameters: Dictionary of parameters to check
        dangerous_patterns: List of regex patterns for dangerous commands
        audit_logger: Logger for audit events
        security_level_value: String value of current security level

    Returns:
        List of security warnings
    """
    warnings = []

    if "command" in parameters:
        command = str(parameters["command"])
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                warning_msg = (
                    f"Potentially dangerous command pattern detected: {pattern}"
                )
                warnings.append(warning_msg)

                audit_logger.log_security_event(
                    "DANGEROUS_COMMAND",
                    {
                        "pattern": pattern,
                        "command_preview": (
                            command[:50] + "..." if len(command) > 50 else command
                        ),
                        "security_level": security_level_value,
                        "risk_level": "HIGH",
                    },
                    SecuritySeverity.ERROR,
                )

    return warnings


def check_injection_patterns(
    parameters: dict[str, Any],
    audit_logger: SecurityAuditLogger,
    injection_patterns: list[str] | None = None,
) -> list[str]:
    """Check for injection patterns in parameter values.

    Args:
        parameters: Dictionary of parameters to check
        audit_logger: Logger for audit events
        injection_patterns: List of injection patterns to check against.
            If None, uses default patterns from SecurityPatterns.

    Returns:
        List of security warnings
    """
    warnings = []
    patterns = injection_patterns or SecurityPatterns.get_injection_patterns()

    for key, value in parameters.items():
        if isinstance(value, str):
            for pattern in patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    warning_msg = (
                        f"WARNING: Potential injection pattern detected in {key}: "
                        f"suspicious command sequence"
                    )
                    warnings.append(warning_msg)

                    audit_logger.log_security_event(
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
                        SecuritySeverity.ERROR,
                    )
                    break

    return warnings


def check_sensitive_paths(
    parameters: dict[str, Any],
    sensitive_paths: list[str],
    audit_logger: SecurityAuditLogger,
    validate_file_ops_func: Any,
) -> list[str]:
    """Check for sensitive file paths and path traversal.

    Args:
        parameters: Dictionary of parameters to check
        sensitive_paths: List of regex patterns for sensitive paths
        audit_logger: Logger for audit events
        validate_file_ops_func: Function to validate file operations

    Returns:
        List of security warnings
    """
    warnings = []

    for key, value in parameters.items():
        if isinstance(value, str):
            looks_like_path = (
                "/" in value
                or value.startswith(("~", "\\"))
                or re.search(r"[a-zA-Z]:\\", value) is not None
            )
            if (
                looks_like_path
                or "path" in key.lower()
                or key in ["source_path", "destination_path"]
            ):
                file_warnings = validate_file_ops_func(value, "access")
                warnings.extend(file_warnings)

        if isinstance(value, str):
            for pattern in sensitive_paths:
                if re.search(pattern, value, re.IGNORECASE):
                    warning_msg = f"Sensitive path detected in {key}: {pattern}"
                    warnings.append(warning_msg)

                    audit_logger.log_security_event(
                        "SENSITIVE_PATH",
                        {
                            "parameter": key,
                            "pattern": pattern,
                            "value_preview": (
                                value[:40] + "..." if len(value) > 40 else value
                            ),
                            "risk_level": "MEDIUM",
                        },
                        SecuritySeverity.WARNING,
                    )

    return warnings


def check_production_indicators(
    parameters: dict[str, Any],
    audit_logger: SecurityAuditLogger,
) -> list[str]:
    """Check for production environment indicators.

    Args:
        parameters: Dictionary of parameters to check
        audit_logger: Logger for audit events

    Returns:
        List of security warnings
    """
    warnings = []
    lowered = data_to_lower_cached(parameters)

    if any(env in lowered for env in ["prod", "production", "live"]):
        warning_msg = (
            "WARNING: Production environment detected - ensure proper authorization"
        )
        warnings.append(warning_msg)

        audit_logger.log_security_event(
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
            SecuritySeverity.WARNING,
        )

    return warnings


def validate_file_operations(
    file_path: str,
    operation: str,
    sensitive_paths: list[str],
    audit_logger: SecurityAuditLogger,
) -> list[str]:
    """Validate file operations for security concerns.

    Validates file operations against security threats:
    - Path traversal detection (.., // patterns)
    - Sensitive file access based on security level patterns
    - Destructive operation warnings (delete, remove, truncate, drop)

    Args:
        file_path: File path to validate
        operation: Type of operation being performed
        sensitive_paths: List of sensitive path patterns
        audit_logger: Logger for audit events

    Returns:
        List of security warnings found during validation
    """
    warnings = []

    # Check for path traversal attempts
    if ".." in file_path or "//" in file_path:
        warning_msg = "WARNING: Potential path traversal detected in file path"
        warnings.append(warning_msg)

        audit_logger.log_security_event(
            "PATH_TRAVERSAL",
            {
                "file_path": file_path,
                "operation": operation,
                "traversal_patterns": ["..", "//"],
                "risk_level": "HIGH",
            },
            SecuritySeverity.ERROR,
        )

    # Check for sensitive file access
    for pattern in sensitive_paths:
        if re.search(pattern, file_path, re.IGNORECASE):
            warning_msg = f"WARNING: Sensitive file access detected: {file_path}"
            warnings.append(warning_msg)

            audit_logger.log_security_event(
                "SENSITIVE_FILE_ACCESS",
                {
                    "file_path": file_path,
                    "operation": operation,
                    "matched_pattern": pattern,
                    "risk_level": "MEDIUM",
                },
                SecuritySeverity.WARNING,
            )

    # Warn about destructive operations
    if operation.lower() in ["delete", "remove", "truncate", "drop"]:
        warning_msg = f"Destructive operation '{operation}' - ensure proper safeguards"
        warnings.append(warning_msg)

        audit_logger.log_security_event(
            "DESTRUCTIVE_OPERATION",
            {
                "file_path": file_path,
                "operation": operation,
                "risk_level": "MEDIUM",
                "recommendation": "Ensure proper safeguards and authorization",
            },
            SecuritySeverity.WARNING,
        )

    return warnings


def sanitize_command_parameters(command: Any) -> str:
    """Sanitize command parameters to prevent injection attacks.

    Args:
        command: Command string to sanitize

    Returns:
        Sanitized command string
    """
    if not isinstance(command, str):
        return str(command)

    sanitized = command

    dangerous_chars = ["|", "&", ";", "$(", "`", ">", "<", "*", "?", "[", "]"]
    for char in dangerous_chars:
        if char in sanitized:
            logger.warning(
                "Potentially dangerous character '%s' found in command, escaping",
                char,
            )
            sanitized = sanitized.replace(char, f"\\{char}")

    return sanitized


def sanitize_error_message(
    error_msg: Any,
    sanitization_patterns: list[tuple[str, str]] | None = None,
) -> str:
    """Sanitize error messages to prevent information disclosure.

    Args:
        error_msg: Error message to sanitize
        sanitization_patterns: List of (pattern, replacement) tuples.
            If None, uses default patterns from SecurityPatterns.

    Returns:
        Sanitized error message
    """
    if not isinstance(error_msg, str):
        return str(error_msg)

    sanitized = error_msg
    patterns = sanitization_patterns or SecurityPatterns.get_sanitization_patterns()

    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized


# Internal utility - not part of public API
__all__: list[str] = []
