"""Security audit logging utilities.

Provides structured audit logging for security events with configurable
severity levels and JSON-formatted output for easy parsing.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from importobot.services.security_types import SecurityLevel
from importobot.utils.logging import get_logger


class SecuritySeverity(Enum):
    """Security event severity levels for consistent logging and classification.

    Provides type-safe severity levels with clear semantic meaning for
    security-related events and audit logging.
    """

    ERROR = "ERROR"
    """High severity security events that require immediate attention.

    Examples: Security violations, credential exposure, policy breaches
    """

    WARNING = "WARNING"
    """Medium severity security events that should be reviewed.

    Examples: Suspicious patterns, potential misconfigurations, near-threshold
    """

    INFO = "INFO"
    """Low severity security events for information purposes.

    Examples: Routine security checks, policy compliance, configuration changes
    """


class SecurityAuditLogger:
    """Handles structured audit logging for security events.

    Attributes:
        security_level: The configured security level for context.
        enable_audit_logging: Whether audit logging is enabled.
        audit_logger: The underlying logger instance.
    """

    def __init__(
        self,
        security_level: SecurityLevel,
        enable_audit_logging: bool = True,
        logger_name: str | None = None,
    ) -> None:
        """Initialize the audit logger.

        Args:
            security_level: Security level for context in log entries.
            enable_audit_logging: Whether to enable audit logging.
            logger_name: Optional custom logger name.
        """
        self.security_level = security_level
        self.enable_audit_logging = enable_audit_logging
        self.audit_logger = get_logger(logger_name or f"{__name__}.audit")

        if self.enable_audit_logging:
            self._setup_audit_logger()

    def _setup_audit_logger(self) -> None:
        """Set up audit logger with structured formatting for security events."""
        if not self.audit_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - SECURITY_AUDIT - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.audit_logger.setLevel(logging.INFO)
            self.audit_logger.addHandler(handler)

    def log_security_event(
        self,
        event_type: str,
        details: dict[str, Any],
        severity: SecuritySeverity = SecuritySeverity.WARNING,
    ) -> None:
        """Log a security event with structured audit information.

        Args:
            event_type: Type of security event (e.g., 'DANGEROUS_COMMAND',
                           'SENSITIVE_PATH')
            details: Dictionary containing event details
            severity: Severity level (SecuritySeverity enum value)
        """
        if not self.enable_audit_logging:
            return

        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "security_level": self.security_level.value,
            "severity": severity.value,
            "details": details,
        }

        log_message = json.dumps(audit_entry, default=str)

        if severity == SecuritySeverity.ERROR:
            self.audit_logger.error(log_message)
        elif severity == SecuritySeverity.WARNING:
            self.audit_logger.warning(log_message)
        else:
            self.audit_logger.info(log_message)

    def log_validation_start(
        self,
        validation_type: str,
        context: dict[str, Any],
        patterns_count: int = 0,
        sensitive_paths_count: int = 0,
    ) -> None:
        """Log the start of a security validation operation.

        Args:
            validation_type: Type of validation being performed
            context: Context information about the validation
            patterns_count: Number of dangerous patterns configured
            sensitive_paths_count: Number of sensitive paths configured
        """
        if not self.enable_audit_logging:
            return

        self.log_security_event(
            "VALIDATION_START",
            {
                "validation_type": validation_type,
                "context": context,
                "patterns_count": patterns_count,
                "sensitive_paths_count": sensitive_paths_count,
            },
            SecuritySeverity.INFO,
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

        self.log_security_event(
            "VALIDATION_COMPLETE",
            {
                "validation_type": validation_type,
                "warnings_count": warnings_count,
                "duration_ms": duration_ms,
            },
            SecuritySeverity.INFO,
        )


# Internal utility - not part of public API
__all__: list[str] = []
