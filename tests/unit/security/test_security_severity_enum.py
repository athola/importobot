"""Tests for SecuritySeverity enum and enum-based severity handling."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from io import StringIO

from importobot.security import SecuritySeverity, SecurityValidator
from importobot.security import SecuritySeverity as ImportedSecuritySeverity


class TestSecuritySeverityEnum:
    """Test the SecuritySeverity enum functionality."""

    def test_enum_values(self) -> None:
        """Test that enum values match expected severity strings."""
        assert SecuritySeverity.ERROR.value == "ERROR"
        assert SecuritySeverity.WARNING.value == "WARNING"
        assert SecuritySeverity.INFO.value == "INFO"

    def test_enum_membership(self) -> None:
        """Test enum membership and identity."""
        assert SecuritySeverity.ERROR in SecuritySeverity
        assert SecuritySeverity.WARNING in SecuritySeverity
        assert SecuritySeverity.INFO in SecuritySeverity

        assert SecuritySeverity.ERROR is SecuritySeverity.ERROR
        assert SecuritySeverity.WARNING is SecuritySeverity.WARNING
        assert SecuritySeverity.INFO is SecuritySeverity.INFO

    def test_enum_ordering(self) -> None:
        """Test that enum has consistent ordering for comparison."""
        # All enums should be orderable by their string values
        severities = [
            SecuritySeverity.ERROR,
            SecuritySeverity.WARNING,
            SecuritySeverity.INFO,
        ]
        sorted_severities = sorted(severities, key=lambda x: x.value)

        # Should be in alphabetical order: ERROR, INFO, WARNING
        expected_order = [
            SecuritySeverity.ERROR,
            SecuritySeverity.INFO,
            SecuritySeverity.WARNING,
        ]
        assert sorted_severities == expected_order

    def test_enum_string_representation(self) -> None:
        """Test string representation of enum values."""
        assert str(SecuritySeverity.ERROR) == "SecuritySeverity.ERROR"
        assert repr(SecuritySeverity.ERROR) == "<SecuritySeverity.ERROR: 'ERROR'>"

    def test_enum_iteration(self) -> None:
        """Test that all enum values can be iterated."""
        all_severities = list(SecuritySeverity)
        assert len(all_severities) == 3
        assert SecuritySeverity.ERROR in all_severities
        assert SecuritySeverity.WARNING in all_severities
        assert SecuritySeverity.INFO in all_severities

    def test_enum_case_insensitive_lookup(self) -> None:
        """Test that enum values are case-sensitive."""
        assert SecuritySeverity.ERROR.value == "ERROR"
        # Should not match lowercase
        lower_value = SecuritySeverity.ERROR.value.lower()
        assert SecuritySeverity.ERROR.value != lower_value


class TestEnumBasedSeverityLogging:
    """Test that logging functions work correctly with enum severity."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = SecurityValidator()
        # Set up StringIO stream to capture log messages
        self.log_stream = StringIO()
        self.mock_handler = logging.StreamHandler(self.log_stream)
        self.mock_handler.setLevel(logging.DEBUG)

        # Create formatter to match expected format
        formatter = logging.Formatter("%(message)s")
        self.mock_handler.setFormatter(formatter)

        # Configure the audit logger
        self.validator.audit_logger.addHandler(self.mock_handler)
        self.validator.audit_logger.setLevel(logging.DEBUG)
        self.validator.audit_logger.propagate = False

    def get_log_messages(self) -> list[str]:
        """Get all logged messages from the StringIO stream."""
        self.log_stream.seek(0)
        content = self.log_stream.read()
        return [line.strip() for line in content.splitlines() if line.strip()]

    def clear_log_messages(self) -> None:
        """Clear logged messages."""
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

    def test_log_with_error_severity(self) -> None:
        """Test logging with SecuritySeverity.ERROR."""
        details = {"test": "data", "severity": "high"}

        self.validator._log_security_event(
            "TEST_EVENT", details, SecuritySeverity.ERROR
        )

        messages = self.get_log_messages()
        assert len(messages) == 1

        # Parse the JSON log message
        log_data = json.loads(messages[0])
        assert log_data["severity"] == "ERROR"
        assert log_data["event_type"] == "TEST_EVENT"
        assert log_data["details"] == details

    def test_log_with_warning_severity(self) -> None:
        """Test logging with SecuritySeverity.WARNING."""
        details = {"test": "data", "severity": "medium"}

        self.validator._log_security_event(
            "TEST_WARNING", details, SecuritySeverity.WARNING
        )

        messages = self.get_log_messages()
        assert len(messages) == 1

        log_data = json.loads(messages[0])
        assert log_data["severity"] == "WARNING"
        assert log_data["event_type"] == "TEST_WARNING"

    def test_log_with_info_severity(self) -> None:
        """Test logging with SecuritySeverity.INFO."""
        details = {"test": "data", "severity": "low"}

        self.validator._log_security_event("TEST_INFO", details, SecuritySeverity.INFO)

        messages = self.get_log_messages()
        assert len(messages) == 1

        log_data = json.loads(messages[0])
        assert log_data["severity"] == "INFO"
        assert log_data["event_type"] == "TEST_INFO"

    def test_log_default_severity(self) -> None:
        """Test that default severity is SecuritySeverity.WARNING."""
        details = {"test": "data"}

        self.validator._log_security_event("TEST_DEFAULT", details)

        messages = self.get_log_messages()
        assert len(messages) == 1

        log_data = json.loads(messages[0])
        assert log_data["severity"] == "WARNING"  # Default should be WARNING
        assert log_data["event_type"] == "TEST_DEFAULT"

    def test_log_timestamp_format(self) -> None:
        """Test that timestamp is properly formatted in audit entry."""
        details = {"test": "data"}

        self.validator._log_security_event(
            "TIMESTAMP_TEST", details, SecuritySeverity.INFO
        )

        messages = self.get_log_messages()
        log_data = json.loads(messages[0])

        # Should be a valid ISO 8601 timestamp
        timestamp_str = log_data["timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Should be within the last few seconds
        now = datetime.now(timezone.utc)
        assert abs((now - timestamp).total_seconds()) < 5.0

    def test_log_security_level_included(self) -> None:
        """Test that security level is included in audit entry."""
        details = {"test": "data"}

        self.validator._log_security_event("SECURITY_LEVEL_TEST", details)

        messages = self.get_log_messages()
        log_data = json.loads(messages[0])

        assert "security_level" in log_data
        assert log_data["security_level"] in ["strict", "standard", "permissive"]

    def test_audit_logging_disabled(self) -> None:
        """Test that no logging occurs when audit logging is disabled."""
        # Create validator with disabled audit logging
        quiet_validator = SecurityValidator(enable_audit_logging=False)

        # Set up StringIO stream to verify no logs
        quiet_log_stream = StringIO()
        quiet_handler = logging.StreamHandler(quiet_log_stream)
        quiet_handler.setLevel(logging.DEBUG)
        quiet_validator.audit_logger.addHandler(quiet_handler)
        quiet_validator.audit_logger.propagate = False

        details = {"test": "data"}
        quiet_validator._log_security_event(
            "SHOULD_NOT_LOG", details, SecuritySeverity.ERROR
        )

        # Should have no log messages
        content = quiet_log_stream.getvalue()
        assert content == ""  # Empty string means no logs were written

    def test_multiple_severity_levels(self) -> None:
        """Test logging multiple events with different severity levels."""
        test_cases = [
            (SecuritySeverity.ERROR, "ERROR_EVENT"),
            (SecuritySeverity.WARNING, "WARNING_EVENT"),
            (SecuritySeverity.INFO, "INFO_EVENT"),
        ]

        for severity, event_type in test_cases:
            details = {"severity": severity.value, "event": event_type}
            self.validator._log_security_event(event_type, details, severity)

        messages = self.get_log_messages()
        assert len(messages) == 3

        # Parse all messages and verify severity levels
        severities = []
        for message in messages:
            log_data = json.loads(message)
            severities.append(log_data["severity"])

        assert "ERROR" in severities
        assert "WARNING" in severities
        assert "INFO" in severities

    def test_complex_details_serialization(self) -> None:
        """Test that complex details are properly serialized."""
        complex_details = {
            "nested": {
                "level": 1,
                "items": ["item1", "item2"],
                "metadata": {
                    "source": "test",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            "list_data": [1, 2, 3, 4, 5],
            "boolean_flag": True,
            "none_value": None,
        }

        self.validator._log_security_event(
            "COMPLEX_TEST", complex_details, SecuritySeverity.INFO
        )

        messages = self.get_log_messages()
        assert len(messages) == 1

        log_data = json.loads(messages[0])
        assert log_data["details"]["nested"]["level"] == 1
        assert log_data["details"]["list_data"] == [1, 2, 3, 4, 5]
        assert log_data["details"]["boolean_flag"] is True
        assert log_data["details"]["none_value"] is None

    def test_enum_value_extraction(self) -> None:
        """Test that enum values can be extracted for external processing."""
        test_severities = [
            SecuritySeverity.ERROR,
            SecuritySeverity.WARNING,
            SecuritySeverity.INFO,
        ]

        severity_strings = [severity.value for severity in test_severities]
        expected_strings = ["ERROR", "WARNING", "INFO"]

        assert severity_strings == expected_strings

        # Test round-trip: string back to enum if needed
        for enum_val, string_val in zip(
            test_severities, expected_strings, strict=False
        ):
            assert SecuritySeverity(string_val) == enum_val

    def test_enum_import_from_security_module(self) -> None:
        """Test that SecuritySeverity can be imported from the security module."""
        # We import SecuritySeverity with an alias at the top of the file
        # to satisfy linter requirements, but the test verifies they're the same
        assert ImportedSecuritySeverity.ERROR == SecuritySeverity.ERROR
        assert ImportedSecuritySeverity.WARNING == SecuritySeverity.WARNING
        assert ImportedSecuritySeverity.INFO == SecuritySeverity.INFO

        # Should be the same object identity
        assert ImportedSecuritySeverity is SecuritySeverity
