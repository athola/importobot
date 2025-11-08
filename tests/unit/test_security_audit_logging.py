"""Test security validation audit logging functionality."""

import json
from unittest.mock import MagicMock, patch

import pytest

from importobot.utils.security import SecurityValidator, validate_test_security


class TestSecurityAuditLogging:  # pylint: disable=attribute-defined-outside-init
    """Test security validation audit logging."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = SecurityValidator(enable_audit_logging=True)

        # Mock the audit logger to capture log messages
        self.mock_audit_logger = MagicMock()
        self.validator.audit_logger = self.mock_audit_logger

    def test_audit_logging_setup(self) -> None:
        """Test that audit logger is properly configured."""
        validator = SecurityValidator(enable_audit_logging=True)

        # Check that audit logger exists
        assert hasattr(validator, "audit_logger")
        assert validator.audit_logger is not None

    def test_audit_logging_disabled(self) -> None:
        """Test that audit logging can be disabled."""
        validator = SecurityValidator(enable_audit_logging=False)

        # Mock the logger to verify no calls are made
        mock_logger = MagicMock()
        validator.audit_logger = mock_logger

        # Perform validation that would normally trigger logging
        parameters = {"password": "secret123"}
        validator.validate_ssh_parameters(parameters)

        # Verify no audit logging occurred
        mock_logger.info.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    def test_hardcoded_password_audit_logging(self) -> None:
        """Test audit logging for hardcoded password detection."""
        parameters = {"password": "secret123"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify audit log was called for hardcoded password
        self.mock_audit_logger.warning.assert_called()
        warning_calls = list(self.mock_audit_logger.warning.call_args_list)

        # Check that HARDCODED_PASSWORD event was logged
        logged_events = []
        for call in warning_calls:
            args, _ = call
            if args:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "HARDCODED_PASSWORD" in logged_events

    def test_credential_exposure_audit_logging(self) -> None:
        """Test audit logging for credential exposure."""
        parameters = {"password": "long_secret_password"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify audit log was called for credential exposure
        self.mock_audit_logger.error.assert_called()
        error_calls = list(self.mock_audit_logger.error.call_args_list)

        # Check that CREDENTIAL_EXPOSURE event was logged
        logged_events = []
        for call in error_calls:
            args, _ = call
            if args:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "CREDENTIAL_EXPOSURE" in logged_events

    def test_dangerous_command_audit_logging(self) -> None:
        """Test audit logging for dangerous command detection."""
        parameters = {"command": "rm -rf /tmp/test"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify audit log was called for dangerous command
        self.mock_audit_logger.error.assert_called()
        error_calls = list(self.mock_audit_logger.error.call_args_list)

        # Check that DANGEROUS_COMMAND event was logged
        logged_events = []
        for call in error_calls:
            args, _ = call
            if args:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "DANGEROUS_COMMAND" in logged_events

    def test_injection_pattern_audit_logging(self) -> None:
        """Test audit logging for injection pattern detection."""
        parameters = {"param": "test; rm -rf /tmp"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify audit log was called for injection pattern
        self.mock_audit_logger.error.assert_called()
        error_calls = list(self.mock_audit_logger.error.call_args_list)

        # Check that INJECTION_PATTERN event was logged
        logged_events = []
        for call in error_calls:
            args, _ = call
            if args:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "INJECTION_PATTERN" in logged_events

    def test_sensitive_path_audit_logging(self) -> None:
        """Test audit logging for sensitive path detection."""
        parameters = {"path": "/etc/passwd"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify audit log was called for sensitive path
        self.mock_audit_logger.warning.assert_called()
        warning_calls = list(self.mock_audit_logger.warning.call_args_list)

        # Check that SENSITIVE_PATH event was logged
        logged_events = []
        for call in warning_calls:
            args, _ = call
            if args and len(args) > 0:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "SENSITIVE_PATH" in logged_events

    def test_production_environment_audit_logging(self) -> None:
        """Test audit logging for production environment detection."""
        parameters = {"env": "production", "host": "prod-server.example.com"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify audit log was called for production environment
        self.mock_audit_logger.warning.assert_called()
        warning_calls = list(self.mock_audit_logger.warning.call_args_list)

        # Check that PRODUCTION_ENVIRONMENT event was logged
        logged_events = []
        for call in warning_calls:
            args, _ = call
            if args and len(args) > 0:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "PRODUCTION_ENVIRONMENT" in logged_events

    def test_validation_start_and_complete_logging(self) -> None:
        """Test that validation start and complete events are logged."""
        parameters = {"command": "ls -la"}

        self.validator.validate_ssh_parameters(parameters)

        # Verify both start and complete events were logged
        self.mock_audit_logger.info.assert_called()
        info_calls = list(self.mock_audit_logger.info.call_args_list)

        logged_events = []
        for call in info_calls:
            args, _ = call
            if args and len(args) > 0:
                try:
                    event_data = json.loads(args[0])
                    logged_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "VALIDATION_START" in logged_events
        assert "VALIDATION_COMPLETE" in logged_events

    def test_audit_log_structure(self) -> None:
        """Test that audit log entries have proper structure."""
        parameters = {"password": "test123"}

        self.validator.validate_ssh_parameters(parameters)

        # Check that log entries are properly structured JSON
        self.mock_audit_logger.warning.assert_called()
        warning_calls = list(self.mock_audit_logger.warning.call_args_list)

        for call in warning_calls:
            args, _ = call
            if args and len(args) > 0:
                try:
                    event_data = json.loads(args[0])

                    # Verify required fields
                    required_fields = [
                        "timestamp",
                        "event_type",
                        "security_level",
                        "severity",
                        "details",
                    ]
                    for field in required_fields:
                        assert field in event_data

                    # Verify field types
                    assert isinstance(event_data["timestamp"], str)
                    assert isinstance(event_data["event_type"], str)
                    assert isinstance(event_data["security_level"], str)
                    assert isinstance(event_data["severity"], str)
                    assert isinstance(event_data["details"], dict)

                except json.JSONDecodeError:
                    pytest.fail("Audit log entry is not valid JSON")

    def test_file_operations_audit_logging(self) -> None:
        """Test audit logging for file operations validation."""
        # Test path traversal
        self.validator.validate_file_operations("../../etc/passwd", "read")

        # Verify audit log was called for path traversal
        self.mock_audit_logger.error.assert_called()

        # Test sensitive file access
        self.validator.validate_file_operations("/etc/shadow", "read")

        # Verify audit log was called for sensitive file access
        self.mock_audit_logger.warning.assert_called()

        # Test destructive operation
        self.validator.validate_file_operations("/tmp/test.txt", "delete")

        # Verify audit log was called for destructive operation
        self.mock_audit_logger.warning.assert_called()

    def test_comprehensive_test_case_audit_logging(self) -> None:
        """Test audit logging for comprehensive test case validation."""
        test_case = {
            "name": "SSH Test",
            "steps": [
                {
                    "library": "SSHLibrary",
                    "test_data": "password: secret123\ncommand: rm -rf /tmp/test\n"
                    "host: prod-server.example.com",
                }
            ],
        }

        # Capture logs from actual audit logger
        with patch("importobot.utils.security.SecurityValidator") as mock_validator:
            # Configure mock to use our validator with mocked logger
            mock_validator.return_value = self.validator

            validate_test_security(test_case)

        # Verify multiple audit events were logged
        assert self.mock_audit_logger.info.call_count >= 2  # Start and complete
        assert self.mock_audit_logger.warning.call_count >= 1  # Various warnings
        assert self.mock_audit_logger.error.call_count >= 1  # High-risk events

    def test_audit_log_performance_timing(self) -> None:
        """Test that audit logging includes performance timing."""
        parameters = {"command": "echo 'test'"}

        # Mock time to ensure consistent timing
        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000.0, 1000.1]  # 100ms difference

            self.validator.validate_ssh_parameters(parameters)

            # Verify validation complete event includes timing
            self.mock_audit_logger.info.assert_called()
            info_calls = list(self.mock_audit_logger.info.call_args_list)

            complete_events = []
            for call in info_calls:
                args, _ = call
                if args and len(args) > 0:
                    try:
                        event_data = json.loads(args[0])
                        if event_data["event_type"] == "VALIDATION_COMPLETE":
                            complete_events.append(event_data)
                    except (json.JSONDecodeError, IndexError):
                        pass

            assert len(complete_events) == 1
            assert "duration_ms" in complete_events[0]["details"]
            # Allow for floating point precision
            assert abs(complete_events[0]["details"]["duration_ms"] - 100.0) < 0.001

    def test_risk_level_assignment(self) -> None:
        """Test that risk levels are properly assigned in audit logs."""
        # Test HIGH risk events
        parameters = {"password": "secret123", "command": "rm -rf /tmp"}

        self.validator.validate_ssh_parameters(parameters)

        # Check that HIGH risk events are logged as ERROR
        error_calls = list(self.mock_audit_logger.error.call_args_list)
        high_risk_events = []

        for call in error_calls:
            args, _ = call
            if args and len(args) > 0:
                try:
                    event_data = json.loads(args[0])
                    if event_data["details"].get("risk_level") == "HIGH":
                        high_risk_events.append(event_data["event_type"])
                except (json.JSONDecodeError, IndexError):
                    pass

        assert "CREDENTIAL_EXPOSURE" in high_risk_events
        assert "DANGEROUS_COMMAND" in high_risk_events

    def test_audit_log_with_sensitive_data_sanitization(self) -> None:
        """Test that sensitive data is properly sanitized in audit logs."""
        parameters = {"password": "very_long_secret_password_that_should_be_sanitized"}

        self.validator.validate_ssh_parameters(parameters)

        # Check that credential length is logged but not the full password
        self.mock_audit_logger.error.assert_called()
        error_calls = list(self.mock_audit_logger.error.call_args_list)

        for call in error_calls:
            args, _ = call
            if args and len(args) > 0:
                try:
                    event_data = json.loads(args[0])
                    if event_data["event_type"] == "CREDENTIAL_EXPOSURE":
                        details = event_data["details"]
                        assert "credential_length" in details
                        assert details["credential_length"] > 0
                        # Ensure the actual password is not in the log
                        log_content = args[0]
                        assert "very_long_secret_password" not in log_content
                except (json.JSONDecodeError, IndexError):
                    pass
