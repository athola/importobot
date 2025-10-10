"""Tests for security gateway service."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from importobot.services import security_gateway
from importobot.services.security_gateway import SecurityError, SecurityGateway
from importobot.services.security_types import SecurityLevel


@pytest.fixture
def standard_security_gateway():
    """Create a SecurityGateway instance for testing."""
    return SecurityGateway(SecurityLevel.STANDARD)


@pytest.fixture
def strict_security_gateway():
    """Create a SecurityGateway instance with strict security."""
    return SecurityGateway(SecurityLevel.STRICT)


@pytest.fixture
def permissive_security_gateway():
    """Create a SecurityGateway instance with lenient security."""
    return SecurityGateway(SecurityLevel.PERMISSIVE)


class TestSecurityGatewayInitialization:
    """Test SecurityGateway initialization."""

    def test_init_with_enum(self):
        """Test initialization with SecurityLevel enum."""
        gateway = SecurityGateway(SecurityLevel.STRICT)
        assert gateway.security_level == SecurityLevel.STRICT

    def test_init_with_string(self):
        """Test initialization with string security level."""
        gateway = SecurityGateway("standard")
        assert gateway.security_level == SecurityLevel.STANDARD

    def test_init_default_level(self):
        """Test initialization with default security level."""
        gateway = SecurityGateway()
        assert gateway.security_level == SecurityLevel.STANDARD

    def test_dangerous_patterns_initialized(self, standard_security_gateway):
        """Test that dangerous patterns are properly initialized."""
        # pylint: disable=protected-access
        patterns = standard_security_gateway._dangerous_patterns
        assert len(patterns) > 0
        # Patterns are now tuples of (compiled_regex, description)
        pattern_strings = [p[0].pattern for p in patterns]
        assert any("script" in p for p in pattern_strings)
        assert any("javascript" in p for p in pattern_strings)
        assert any("\\.\\." in p for p in pattern_strings)

    def test_security_level_comparison(self):
        """Test different security levels."""
        strict_gateway = SecurityGateway(SecurityLevel.STRICT)
        standard_gateway = SecurityGateway(SecurityLevel.STANDARD)
        lenient_gateway = SecurityGateway(SecurityLevel.PERMISSIVE)

        test_data = {"test": "data"}

        strict_result = strict_gateway.sanitize_api_input(test_data, "json")
        standard_result = standard_gateway.sanitize_api_input(test_data, "json")
        lenient_result = lenient_gateway.sanitize_api_input(test_data, "json")

        # All should handle safe data the same way
        assert strict_result["is_safe"] is True
        assert standard_result["is_safe"] is True
        assert lenient_result["is_safe"] is True


class TestSecurityGatewayRateLimiting:
    """Test rate limiting behaviour for security operations."""

    def test_rate_limit_sanitize_api_input(self):
        """Rate limiter should block sanitization after allowed calls."""
        gateway = SecurityGateway(
            SecurityLevel.STANDARD,
            rate_limit_max_calls=2,
            rate_limit_interval_seconds=60.0,
        )

        payload = {"test": "data"}
        gateway.sanitize_api_input(payload, "json")
        gateway.sanitize_api_input(payload, "json")

        with pytest.raises(SecurityError):
            gateway.sanitize_api_input(payload, "json")

    def test_rate_limit_file_operations(self, tmp_path: Path) -> None:
        """Rate limiter should block excessive file validation requests."""
        gateway = SecurityGateway(
            SecurityLevel.STANDARD,
            rate_limit_max_calls=1,
            rate_limit_interval_seconds=60.0,
        )

        test_file = tmp_path / "example.txt"
        test_file.write_text("hello", encoding="utf-8")

        gateway.validate_file_operation(test_file, "read")
        with pytest.raises(SecurityError):
            gateway.validate_file_operation(test_file, "read")


class TestSecurityGatewayBleachFallback:
    """Tests for bleach optional dependency handling."""

    def test_string_sanitization_without_bleach(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Fallback sanitizer should warn when bleach is unavailable."""
        monkeypatch.setattr(security_gateway, "bleach", None, raising=False)
        monkeypatch.setattr(
            security_gateway._BleachState, "warned", False, raising=False
        )

        gateway = SecurityGateway(SecurityLevel.STANDARD)

        with caplog.at_level("WARNING"):
            # pylint: disable=protected-access
            sanitized, issues = gateway._sanitize_string_input(
                "<script>alert('hi')</script>"
            )

        assert sanitized == "alert('hi')"
        assert issues
        assert "Bleach dependency not available" in caplog.text


class TestJSONSanitization:
    """Test JSON input sanitization."""

    def test_sanitize_json_input_valid(self, standard_security_gateway):
        """Test sanitizing valid JSON input."""
        data = {"test": "data", "items": [1, 2, 3]}
        result = standard_security_gateway.sanitize_api_input(data, "json")

        assert result["is_safe"] is True
        assert result["sanitized_data"] == data
        assert len(result["security_issues"]) == 0
        assert result["input_type"] == "json"

    def test_sanitize_json_input_string(self, standard_security_gateway):
        """Test sanitizing JSON string input."""
        data = '{"test": "data", "value": 123}'
        result = standard_security_gateway.sanitize_api_input(data, "json")

        assert result["is_safe"] is True
        assert result["sanitized_data"] == {"test": "data", "value": 123}

    def test_sanitize_json_input_invalid(self, standard_security_gateway):
        """Test sanitizing invalid JSON input."""
        data = '{"invalid": json}'
        result = standard_security_gateway.sanitize_api_input(data, "json")

        assert result["is_safe"] is False
        assert len(result["security_issues"]) > 0
        assert "JSON validation failed" in result["security_issues"][0]

    def test_sanitize_json_input_with_xss(self, standard_security_gateway):
        """Test sanitizing JSON with XSS content."""
        data = {"content": "<script>alert('xss')</script>"}
        result = standard_security_gateway.sanitize_api_input(data, "json")

        assert result["is_safe"] is False
        assert len(result["security_issues"]) > 0

    def test_sanitize_with_context(self, standard_security_gateway):
        """Test sanitization with additional context."""
        data = {"test": "data"}
        context = {"source": "api", "user": "test_user"}

        result = standard_security_gateway.sanitize_api_input(data, "json", context)

        assert "security_level" in result
        assert result["input_type"] == "json"

    def test_sanitize_json_includes_correlation_id(self, standard_security_gateway):
        """Correlation IDs propagate through sanitization results."""
        result = standard_security_gateway.sanitize_api_input(
            {"test": "data"},
            "json",
            context={"source": "api", "correlation_id": "abc-123"},
        )

        assert result["correlation_id"] == "abc-123"

    def test_json_input_none_result(self, standard_security_gateway):
        """Test JSON input sanitization returning None."""
        # Test with invalid JSON that results in None
        with patch.object(
            standard_security_gateway,
            "_sanitize_json_input",
            return_value=(None, ["JSON error"]),
        ):
            result = standard_security_gateway.sanitize_api_input("invalid", "json")

            assert result["is_safe"] is False
            assert result["sanitized_data"] is None


class TestFilePathSanitization:
    """Test file path sanitization."""

    def test_sanitize_file_path_valid(self, standard_security_gateway):
        """Test sanitizing valid file path."""
        data = "/home/user/documents/file.txt"
        result = standard_security_gateway.sanitize_api_input(data, "file_path")

        assert result["is_safe"] is True
        assert isinstance(result["sanitized_data"], str)

    def test_sanitize_file_path_traversal(self, standard_security_gateway):
        """Test sanitizing file path with traversal attempt."""
        data = "/home/user/../../../etc/passwd"
        result = standard_security_gateway.sanitize_api_input(data, "file_path")

        assert result["is_safe"] is False
        assert len(result["security_issues"]) > 0

    def test_sanitize_file_path_dangerous_patterns(self, standard_security_gateway):
        """Test sanitizing file path with dangerous patterns."""
        dangerous_paths = [
            "javascript:void(0)",
            "file://etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
        ]

        for path in dangerous_paths:
            result = standard_security_gateway.sanitize_api_input(path, "file_path")
            assert result["is_safe"] is False
            assert len(result["security_issues"]) > 0

    def test_sanitize_file_path_normalization_failure(self, standard_security_gateway):
        """Test file path sanitization with normalization failure."""
        # pylint: disable=protected-access
        with patch(
            "pathlib.Path.resolve",
            side_effect=OSError("Path resolution failed"),
        ):
            _, issues = standard_security_gateway._sanitize_file_path("/some/path")

            assert len(issues) > 0
            assert "Path normalization failed" in issues[0]


class TestStringSanitization:
    """Test string input sanitization."""

    def test_sanitize_string_input_clean(self, standard_security_gateway):
        """Test sanitizing clean string input."""
        data = "This is a clean string with no dangerous content"
        result = standard_security_gateway.sanitize_api_input(data, "string")

        assert result["is_safe"] is True
        assert result["sanitized_data"] == data

    def test_sanitize_string_input_with_html(self, standard_security_gateway):
        """Test sanitizing string input with HTML tags."""
        data = "Hello <b>world</b> and <script>alert('xss')</script>"
        result = standard_security_gateway.sanitize_api_input(data, "string")

        assert result["is_safe"] is False
        assert len(result["security_issues"]) > 0
        # HTML tags should be removed
        assert "<b>" not in result["sanitized_data"]
        assert "<script>" not in result["sanitized_data"]

    def test_sanitize_string_input_dangerous_patterns(self, standard_security_gateway):
        """Test sanitizing string with dangerous patterns."""
        dangerous_strings = [
            "javascript:alert('xss')",
            "vbscript:msgbox('test')",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
        ]

        for dangerous_string in dangerous_strings:
            result = standard_security_gateway.sanitize_api_input(
                dangerous_string, "string"
            )
            assert result["is_safe"] is False
            assert len(result["security_issues"]) > 0

    def test_sanitize_string_input_no_html(self, standard_security_gateway):
        """Test string sanitization without HTML content."""
        # pylint: disable=protected-access
        data = "Plain text without any HTML tags"
        sanitized, issues = standard_security_gateway._sanitize_string_input(data)

        assert sanitized == data
        assert len(issues) == 0


class TestNestedStructures:
    """Test sanitization of nested data structures."""

    def test_sanitize_nested_dict(self, standard_security_gateway):
        """Test sanitizing nested dictionary structures."""
        data = {
            "level1": {
                "level2": {
                    "safe_content": "This is safe",
                    "dangerous_content": "<script>alert('xss')</script>",
                },
                "list_content": [
                    "safe item",
                    "<img src=x onerror=alert('xss')>",
                ],
            }
        }

        result = standard_security_gateway.sanitize_api_input(data, "json")

        assert result["is_safe"] is False
        assert len(result["security_issues"]) > 0
        # Check that dangerous content was sanitized
        sanitized = result["sanitized_data"]
        assert "script" not in str(sanitized)

    def test_sanitize_list_values(self, standard_security_gateway):
        """Test sanitizing list values."""
        data = [
            "safe content",
            "<script>alert('xss')</script>",
            {"nested": "<b>bold</b>"},
            ["nested", "list", "<i>italic</i>"],
        ]

        result = standard_security_gateway.sanitize_api_input(data, "json")

        assert result["is_safe"] is False
        assert len(result["security_issues"]) > 0

    def test_sanitize_dict_values_recursive(self, standard_security_gateway):
        """Test recursive dictionary value sanitization."""
        # pylint: disable=protected-access
        data = {
            "level1": {
                "level2": {
                    "level3": "<script>alert('deep xss')</script>",
                }
            }
        }

        sanitized, issues = standard_security_gateway._sanitize_dict_values(data)

        assert len(issues) > 0
        assert "script" not in str(sanitized)

    def test_sanitize_list_values_recursive(self, standard_security_gateway):
        """Test recursive list value sanitization."""
        # pylint: disable=protected-access
        data = [
            "safe",
            ["nested", "<script>alert('xss')</script>"],
            {"dict_in_list": "<b>bold</b>"},
        ]

        sanitized, issues = standard_security_gateway._sanitize_list_values(data)

        assert len(issues) > 0
        assert "script" not in str(sanitized)


class TestFileOperationValidation:
    """Test file operation validation."""

    def test_validate_file_operation_safe(self, standard_security_gateway):
        """Test validating safe file operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            file_path.write_text("test content")

            result = standard_security_gateway.validate_file_operation(
                file_path, "read", correlation_id="xyz"
            )

            assert result["is_safe"] is True
            assert result["operation"] == "read"
            assert result["file_path"] == str(file_path)
            assert "normalized_path" in result
            assert result["correlation_id"] == "xyz"

    def test_validate_file_operation_dangerous(self, standard_security_gateway):
        """Test validating dangerous file operation."""
        dangerous_paths = [
            "../../../etc/passwd",
            "/proc/version",
            "C:\\Windows\\System32\\config\\system",
        ]

        for path in dangerous_paths:
            result = standard_security_gateway.validate_file_operation(path, "read")
            assert result["is_safe"] is False
            assert len(result["security_issues"]) > 0

    def test_validate_file_operation_different_operations(
        self, standard_security_gateway
    ):
        """Test validating different file operations."""
        operations = ["read", "write", "delete"]

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"

            for operation in operations:
                result = standard_security_gateway.validate_file_operation(
                    file_path, operation
                )
                assert result["operation"] == operation

    def test_validate_file_operation_failure(self, standard_security_gateway):
        """Test file operation validation failure handling."""
        # Use a path that will cause validation to fail
        with patch(
            "importobot.services.security_gateway.validate_file_path",
            side_effect=Exception("Validation error"),
        ):
            result = standard_security_gateway.validate_file_operation(
                "/some/path", "read"
            )

            assert result["is_safe"] is False
            assert len(result["security_issues"]) > 0
            assert "Validation error" in result["security_issues"][0]


class TestJSONParserConfiguration:
    """Test JSON parser configuration."""

    def test_create_secure_json_parser_default(self, standard_security_gateway):
        """Test creating secure JSON parser with default settings."""
        parser_config = standard_security_gateway.create_secure_json_parser()

        assert parser_config["max_size_mb"] == 10
        assert parser_config["allow_duplicate_keys"] is False
        assert parser_config["strict_mode"] is True
        assert "forbidden_patterns" in parser_config
        assert parser_config["validate_before_parse"] is True

    def test_create_secure_json_parser_custom(self, standard_security_gateway):
        """Test creating secure JSON parser with custom settings."""
        parser_config = standard_security_gateway.create_secure_json_parser(
            max_size_mb=5
        )

        assert parser_config["max_size_mb"] == 5

    def test_create_secure_json_parser_lenient(self, permissive_security_gateway):
        """Test creating secure JSON parser with lenient security."""
        parser_config = permissive_security_gateway.create_secure_json_parser()

        assert parser_config["strict_mode"] is False


class TestSecurityChecks:
    """Test security checks and pattern detection."""

    def test_universal_security_checks(self, standard_security_gateway):
        """Test universal security checks."""
        dangerous_content = [
            "eval(malicious_code)",
            "exec(dangerous_command)",
            "system('rm -rf /')",
            "subprocess.call(['rm', '-rf', '/'])",
            "__import__('os').system('evil')",
        ]

        for content in dangerous_content:
            result = standard_security_gateway.sanitize_api_input(content, "string")
            assert result["is_safe"] is False
            assert len(result["security_issues"]) > 0

    def test_check_path_traversal(self, standard_security_gateway):
        """Test path traversal detection."""
        # pylint: disable=protected-access
        traversal_paths = [
            "../config",
            "dir/../../../etc",
            "/path/../secrets",
            "folder\\..\\windows",
            "file/..",
        ]

        for path in traversal_paths:
            issues = standard_security_gateway._check_path_traversal(path)
            assert len(issues) > 0
            assert "Path traversal attempt detected" in issues[0]

    def test_check_path_traversal_safe(self, standard_security_gateway):
        """Test path traversal detection with safe paths."""
        # pylint: disable=protected-access
        safe_paths = [
            "/home/user/documents",
            "folder/subfolder/file.txt",
            "normal_filename.jpg",
        ]

        for path in safe_paths:
            issues = standard_security_gateway._check_path_traversal(path)
            assert len(issues) == 0

    def test_perform_universal_security_checks(self, standard_security_gateway):
        """Test universal security checks."""
        # pylint: disable=protected-access
        dangerous_data = [
            "eval(dangerous_code)",
            "exec(malicious_script)",
            "system(rm_command)",
            "subprocess.dangerous_call",
            "__import__('dangerous_module')",
            "rm -rf /important_data",
        ]

        for data in dangerous_data:
            issues = standard_security_gateway._perform_universal_security_checks(data)
            assert len(issues) > 0

    def test_perform_universal_security_checks_safe(self, standard_security_gateway):
        """Test universal security checks with safe data."""
        # pylint: disable=protected-access
        safe_data = [
            "regular text content",
            {"normal": "json", "data": 123},
            ["safe", "list", "items"],
        ]

        for data in safe_data:
            issues = standard_security_gateway._perform_universal_security_checks(data)
            assert len(issues) == 0

    def test_comprehensive_dangerous_pattern_detection(self, standard_security_gateway):
        """Test comprehensive dangerous pattern detection."""
        patterns_to_test = [
            ("<script>alert('xss')</script>", "XSS script"),
            ("javascript:void(0)", "JavaScript protocol"),
            ("data:text/html;base64,PHNjcmlwdD4=", "Base64 data URI"),
            ("vbscript:msgbox('test')", "VBScript protocol"),
            ("file:///etc/passwd", "File protocol"),
            ("../../../etc/passwd", "Directory traversal"),
            ("\\..\\.\\windows", "Windows traversal"),
            ("/proc/version", "Process filesystem"),
            ("C:\\Windows\\System32\\config", "Windows system directory"),
        ]

        for pattern, description in patterns_to_test:
            result = standard_security_gateway.sanitize_api_input(pattern, "string")
            assert result["is_safe"] is False, f"Failed to detect: {description}"
            assert len(result["security_issues"]) > 0, (
                f"No issues found for: {description}"
            )


class TestIntegration:
    """Test integration with other services."""

    @patch("importobot.services.security_gateway.ValidationService")
    def test_validation_service_integration(self, mock_validation_service):
        """Test integration with validation service."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(
            is_valid=False, messages=["Validation failed"]
        )
        mock_validation_service.return_value = mock_validator

        gateway = SecurityGateway(SecurityLevel.STANDARD)
        result = gateway.sanitize_api_input({"test": "data"}, "json")

        assert result["is_safe"] is False
        assert "Validation failed" in result["validation_issues"]

    @patch("importobot.services.security_gateway.SecurityValidator")
    def test_security_validator_integration(self, mock_security_validator):
        """Test integration with security validator."""
        mock_validator = Mock()
        mock_validator.validate_file_operations.return_value = ["Security warning"]
        mock_security_validator.return_value = mock_validator

        gateway = SecurityGateway(SecurityLevel.STANDARD)
        result = gateway.validate_file_operation("/some/path", "read")

        # The actual result depends on other validation steps
        assert (
            "Security warning" in result["security_issues"]
            or result["is_safe"] is False
        )


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_sanitize_api_input_exception_handling(self, standard_security_gateway):
        """Test exception handling in sanitize_api_input."""
        with patch.object(
            standard_security_gateway,
            "_sanitize_json_input",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(SecurityError):
                standard_security_gateway.sanitize_api_input({"test": "data"}, "json")

    def test_edge_cases(self, standard_security_gateway):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            ("", "Empty string"),
            ({}, "Empty dict"),
            ([], "Empty list"),
            (None, "None value"),
            (123, "Integer"),
            (True, "Boolean"),
        ]

        for data, description in edge_cases:
            try:
                result = standard_security_gateway.sanitize_api_input(data, "json")
                # Should not raise exceptions for basic types
                assert "security_level" in result, f"Failed for: {description}"
            except Exception as e:
                pytest.fail(f"Unexpected exception for {description}: {e}")


class TestSecurityError:
    """Test SecurityError exception."""

    def test_security_error_creation(self):
        """Test SecurityError exception creation."""
        error = SecurityError("Test security error")
        assert str(error) == "Test security error"

    def test_security_error_inheritance(self):
        """Test SecurityError inheritance."""
        error = SecurityError("Test error")
        assert isinstance(error, Exception)
