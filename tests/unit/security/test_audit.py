"""Tests for security audit logging.

Covers the ``SecuritySeverity`` enum and the ``SecurityAuditLogger``
class in ``importobot.security.audit``. The audit logger is load-bearing
for SIEM forwarding and compliance reporting, so structural contracts
(JSON entry shape, severity mapping, no-op when disabled) are
explicitly tested.
"""

from __future__ import annotations

import json
import logging

import pytest

from importobot.security import audit
from importobot.security.audit import SecurityAuditLogger, SecuritySeverity
from importobot.services.security_types import SecurityLevel


class TestSecuritySeverityEnum:
    """SecuritySeverity is a small Enum with three documented levels."""

    def test_three_documented_levels_exist(self) -> None:
        assert {s.name for s in SecuritySeverity} == {"ERROR", "WARNING", "INFO"}

    def test_values_are_uppercase_strings(self) -> None:
        # SIEM consumers parse the string value; keeping them uppercase
        # matches the standard logging level names.
        assert SecuritySeverity.ERROR.value == "ERROR"
        assert SecuritySeverity.WARNING.value == "WARNING"
        assert SecuritySeverity.INFO.value == "INFO"


class TestSecurityAuditLoggerInit:
    """Construction-time behaviour."""

    def test_default_construction_enables_audit_logging(self) -> None:
        logger = SecurityAuditLogger(SecurityLevel.STANDARD)
        assert logger.enable_audit_logging is True
        assert logger.security_level == SecurityLevel.STANDARD

    def test_can_disable_audit_logging(self) -> None:
        logger = SecurityAuditLogger(SecurityLevel.STANDARD, enable_audit_logging=False)
        assert logger.enable_audit_logging is False

    def test_custom_logger_name_is_used(self) -> None:
        logger = SecurityAuditLogger(
            SecurityLevel.STANDARD, logger_name="custom.audit.logger"
        )
        assert logger.audit_logger.name == "custom.audit.logger"

    def test_handler_setup_is_idempotent(self) -> None:
        # Two loggers sharing the same name must not stack handlers
        # (would duplicate every log line on every construction).
        name = "tests.audit.idempotent"
        first = SecurityAuditLogger(SecurityLevel.STANDARD, logger_name=name)
        before = len(first.audit_logger.handlers)
        SecurityAuditLogger(SecurityLevel.STANDARD, logger_name=name)
        after = len(first.audit_logger.handlers)
        assert before == after


class TestLogSecurityEvent:
    """log_security_event emits structured JSON at the right severity."""

    @pytest.fixture
    def audit_logger(self, caplog: pytest.LogCaptureFixture) -> SecurityAuditLogger:
        # Each test gets its own logger-name so caplog records do not
        # bleed across tests via the shared logger cache.
        return SecurityAuditLogger(
            SecurityLevel.STANDARD,
            logger_name=f"tests.audit.{id(caplog)}",
        )

    def test_warning_severity_logs_as_json_warning(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)
        audit_logger.log_security_event(
            "DANGEROUS_COMMAND",
            {"command": "rm -rf /"},
            SecuritySeverity.WARNING,
        )
        record = caplog.records[-1]
        assert record.levelname == "WARNING"
        payload = json.loads(record.message)
        assert payload["event_type"] == "DANGEROUS_COMMAND"
        assert payload["severity"] == "WARNING"
        assert payload["security_level"] == SecurityLevel.STANDARD.value
        assert payload["details"] == {"command": "rm -rf /"}
        assert "timestamp" in payload

    def test_error_severity_routes_to_error_level(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)
        audit_logger.log_security_event("BREACH", {"who": "x"}, SecuritySeverity.ERROR)
        record = caplog.records[-1]
        assert record.levelname == "ERROR"

    def test_info_severity_routes_to_info_level(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)
        audit_logger.log_security_event("CHECK_RUN", {"x": 1}, SecuritySeverity.INFO)
        record = caplog.records[-1]
        assert record.levelname == "INFO"

    def test_default_severity_is_warning(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # The default severity is part of the contract: most callers
        # rely on it for routine policy events.
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)
        audit_logger.log_security_event("DEFAULT_TEST", {})
        record = caplog.records[-1]
        assert record.levelname == "WARNING"

    def test_disabled_audit_logger_emits_nothing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = SecurityAuditLogger(
            SecurityLevel.STANDARD,
            enable_audit_logging=False,
            logger_name="tests.audit.disabled",
        )
        caplog.set_level(logging.INFO, logger=logger.audit_logger.name)
        logger.log_security_event("X", {}, SecuritySeverity.ERROR)
        assert not [r for r in caplog.records if r.name == logger.audit_logger.name]

    def test_non_jsonable_details_are_coerced_via_default(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # json.dumps(..., default=str) lets non-serialisable objects
        # be stringified rather than raise. Encoding a non-jsonable
        # entry must not blow up the audit pipeline.
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)

        class _Custom:
            def __str__(self) -> str:
                return "custom-repr"

        audit_logger.log_security_event(
            "CUSTOM", {"thing": _Custom()}, SecuritySeverity.INFO
        )
        payload = json.loads(caplog.records[-1].message)
        assert payload["details"]["thing"] == "custom-repr"


class TestValidationStartComplete:
    """Convenience wrappers preserve event_type and severity."""

    @pytest.fixture
    def audit_logger(self, caplog: pytest.LogCaptureFixture) -> SecurityAuditLogger:
        return SecurityAuditLogger(
            SecurityLevel.STANDARD,
            logger_name=f"tests.audit.wrap.{id(caplog)}",
        )

    def test_log_validation_start_uses_info_severity(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)
        audit_logger.log_validation_start("TEST_CASE", {"k": "v"})
        payload = json.loads(caplog.records[-1].message)
        assert payload["event_type"] == "VALIDATION_START"
        assert payload["severity"] == "INFO"
        assert payload["details"]["validation_type"] == "TEST_CASE"
        assert payload["details"]["context"] == {"k": "v"}

    def test_log_validation_complete_records_counts_and_duration(
        self,
        audit_logger: SecurityAuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.INFO, logger=audit_logger.audit_logger.name)
        audit_logger.log_validation_complete("X", warnings_count=3, duration_ms=12.5)
        payload = json.loads(caplog.records[-1].message)
        assert payload["event_type"] == "VALIDATION_COMPLETE"
        assert payload["details"]["warnings_count"] == 3
        assert payload["details"]["duration_ms"] == 12.5

    def test_validation_wrappers_no_op_when_disabled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = SecurityAuditLogger(
            SecurityLevel.STANDARD,
            enable_audit_logging=False,
            logger_name="tests.audit.wrap.disabled",
        )
        caplog.set_level(logging.INFO, logger=logger.audit_logger.name)
        logger.log_validation_start("X", {})
        logger.log_validation_complete("X", 0, 0.0)
        assert not [r for r in caplog.records if r.name == logger.audit_logger.name]


class TestModulePrivacy:
    """Encode that audit's surface is internal-only by name."""

    def test_all_is_empty(self) -> None:
        assert audit.__all__ == []
