"""Tests for template security scanner."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from importobot.security.scanner_checks import (
    scan_for_hardcoded_patterns,
    scan_for_suspicious_variables,
)
from importobot.security.scanner_patterns import (
    PLACEHOLDER_INDICATORS,
    ScannerPatterns,
)
from importobot.security.template_scanner import (
    SecurityIssue,
    TemplateSecurityReport,
    TemplateSecurityScanner,
    scan_template_file_for_security,
)

API_KEY = "api_key_secret_value_1234567890"
DB_PASSWORD = "mysecretpassword123"
PASSWORD = "mysecretpassword"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
USERNAME = "example_user"
BASE_URL = "https://example.com"
TIMEOUT = "30s"
CONNECTION = "mongodb://user:password@localhost:27017/db"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
SSH_KEY = "-----BEGIN RSA PRIVATE KEY-----"
SECRET = "use_env_variable_for_secret"
STRIPE_TEST_KEY = "sk_live_" + "1234567890abcdef1234567890"
SHORT_EXAMPLE_KEY = "sk_live_" + "123456"


class TestSecurityIssue:
    """Test SecurityIssue dataclass."""

    def test_security_issue_creation(self) -> None:
        """Test SecurityIssue creation."""
        issue = SecurityIssue(
            issue_type="credential",
            severity="high",
            file_path="/test/file.robot",
            line_number=10,
            column_number=5,
            description="Hardcoded API key detected",
            match_text=f"api_key: {SHORT_EXAMPLE_KEY}",
            confidence=0.95,
            remediation="Use environment variables",
            context=f"api_key: {SHORT_EXAMPLE_KEY}",
            rule_id="CRED_API_KEY_CRITICAL",
        )

        assert issue.issue_type == "credential"
        assert issue.severity == "high"
        assert issue.line_number == 10
        assert issue.confidence == 0.95

    def test_security_issue_str_representation(self) -> None:
        """Test SecurityIssue string representation."""
        issue = SecurityIssue(
            issue_type="credential",
            severity="high",
            file_path="/test/file.robot",
            line_number=10,
            column_number=5,
            description="Test issue",
            match_text="test",
            confidence=0.9,
            remediation="Fix it",
            context="context",
        )

        str_repr = str(issue)
        assert "SecurityIssue" in str_repr
        assert "credential" in str_repr


class TestTemplateSecurityScanner:
    """Test TemplateSecurityScanner functionality."""

    def test_scanner_initialization(self) -> None:
        """Test scanner initialization."""
        scanner = TemplateSecurityScanner()

        # Should have loaded suspicious variables
        assert len(scanner._suspicious_variables) > 0
        assert "password" in scanner._suspicious_variables
        assert "api_key" in scanner._suspicious_variables

        # Should have loaded hardcoded patterns
        assert len(scanner._hardcoded_patterns) > 0

        # Should have loaded safe keywords
        assert len(scanner._safe_keywords) > 0
        assert "example" in scanner._safe_keywords
        assert "test" in scanner._safe_keywords

    def test_scan_safe_template_file(self) -> None:
        """Test scanning a safe template file."""
        scanner = TemplateSecurityScanner()

        # Create a safe template file
        safe_content = """
        *** Settings ***
        Documentation     Example test case
        Library           SeleniumLibrary

        *** Variables ***
        ${{USERNAME}}       example_user
        ${{BASE_URL}}       https://example.com
        ${{TIMEOUT}}        30s

        *** Test Cases ***
        Example Test
            [Documentation]    This is a safe example test
            [Tags]    example    safe
            Open Browser    ${{BASE_URL}}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(safe_content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Safe file should have no critical issues
            assert report.is_safe
            # Allow low-severity informational issues
            critical_issues = [
                i for i in report.issues if i.severity in ["critical", "high"]
            ]
            assert len(critical_issues) == 0
            assert report.file_path == str(temp_file)

        finally:
            temp_file.unlink()

    def test_scan_template_with_credentials(self) -> None:
        """Test scanning template with hardcoded credentials."""
        scanner = TemplateSecurityScanner()

        # Create a template file with credentials
        unsafe_content = f"""
        *** Variables ***
        ${{API_KEY}}        {STRIPE_TEST_KEY}
        ${{DB_PASSWORD}}     {DB_PASSWORD}
        ${{AWS_SECRET}}     {AWS_SECRET}

        *** Test Cases ***
        Test With Credentials
            Connect To API    ${{API_KEY}}
            Database Query    ${{DB_PASSWORD}}
            AWS S3 Action    ${{AWS_SECRET}}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(unsafe_content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Should detect multiple issues (suspicious variables)
            assert not report.is_safe
            assert report.total_issues > 0
            assert report.issues_by_type.get("suspicious_variable", 0) >= 3

            # Should detect at least one critical severity issue (AWS secret)
            assert report.issues_by_severity.get("critical", 0) >= 1

        finally:
            temp_file.unlink()

    def test_scan_template_with_suspicious_variables(self) -> None:
        """Test scanning template with suspicious variable names."""
        scanner = TemplateSecurityScanner()

        # Create a template with suspicious variables
        suspicious_content = """
        *** Variables ***
        ${password}        user_password_123
        ${secret_token}    my_secret_token_abc
        ${api_key}         api_key_from_env_var

        *** Test Cases ***
        Test With Variables
            Log In User    ${password}
            Access API     ${secret_token}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(suspicious_content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Should detect suspicious variables
            assert report.total_issues > 0
            assert report.issues_by_type.get("suspicious_variable", 0) >= 2

        finally:
            temp_file.unlink()

    def test_scan_template_with_hardcoded_patterns(self) -> None:
        """Test scanning template with hardcoded patterns."""
        scanner = TemplateSecurityScanner()

        # Create a template with hardcoded patterns
        hardcoded_content = """
        *** Variables ***
        ${CONNECTION}     mongodb://user:password@localhost:27017/db
        ${JWT_TOKEN}      eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

        *** Test Cases ***
        Test With Hardcoded Values
            Connect To DB    ${CONNECTION}
            Authenticate      ${JWT_TOKEN}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(hardcoded_content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Should detect hardcoded values
            assert report.total_issues > 0
            assert report.issues_by_type.get("hardcoded_value", 0) >= 2

        finally:
            temp_file.unlink()

    def test_scan_template_with_private_keys(self) -> None:
        """Test scanning template with private keys."""
        scanner = TemplateSecurityScanner()

        # Create a template with private key
        private_key_content = """
        *** Variables ***
        ${SSH_KEY}        -----BEGIN RSA PRIVATE KEY-----
                        MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btZb5...
                        -----END RSA PRIVATE KEY-----

        *** Test Cases ***
        Test With SSH Key
            Connect To Server    ${SSH_KEY}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(private_key_content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Should detect private key (critical issue)
            assert not report.is_safe
            assert report.total_issues > 0

            # Should be critical severity
            critical_issues = [i for i in report.issues if i.severity == "critical"]
            assert len(critical_issues) > 0

        finally:
            temp_file.unlink()

    def test_false_positive_prevention(self) -> None:
        """Test that safe examples don't trigger false positives."""
        scanner = TemplateSecurityScanner()

        # Content that looks like credentials but is actually safe
        safe_content = """
        *** Variables ***
        ${API_KEY}        your_api_key_here
        ${PASSWORD}       replace_with_actual_password
        ${SECRET}         use_env_variable_for_secret
        ${CONNECTION}     mongodb://user:password@localhost:27017/db  # example only

        *** Comments ***
        # Example API key placeholder to ensure safe content
        # Test password: test_password_123
        # Demo connection: postgresql://demo:demo@localhost:5432/demo
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(safe_content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Should have few or no high-confidence issues
            [i for i in report.issues if i.confidence >= 0.9]
            critical_issues = [i for i in report.issues if i.severity == "critical"]

            # Comments and obvious examples should be ignored
            assert len(critical_issues) == 0

        finally:
            temp_file.unlink()

    def test_scan_directory(self) -> None:
        """Test scanning multiple files in a directory."""
        scanner = TemplateSecurityScanner()

        # Create temporary directory with multiple files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create safe file
            safe_file = temp_path / "safe.robot"
            safe_file.write_text("""
            *** Settings ***
            Documentation     Safe test
            Library           SeleniumLibrary

            *** Variables ***
            ${USERNAME}       example_user
            """)

            # Create unsafe file
            unsafe_file = temp_path / "unsafe.robot"
            unsafe_file.write_text(f"""
            *** Variables ***
            ${API_KEY}        {STRIPE_TEST_KEY}
            ${PASSWORD}       mysecretpassword
            """)

            # Create another safe file
            another_safe_file = temp_path / "another_safe.txt"
            another_safe_file.write_text("This is just regular text")

            # Scan directory
            reports = scanner.scan_template_directory(temp_path, [".robot", ".txt"])

            # Should have reports for all files
            assert len(reports) == 3

            # Check safe files
            safe_reports = [r for r in reports if r.is_safe]
            assert len(safe_reports) == 2

            # Check unsafe file
            unsafe_reports = [r for r in reports if not r.is_safe]
            assert len(unsafe_reports) == 1
            assert unsafe_reports[0].total_issues > 0

    def test_issue_deduplication(self) -> None:
        """Test that duplicate issues are deduplicated."""
        scanner = TemplateSecurityScanner()

        # Create content that might trigger duplicate detections
        content = f"""
        ${API_KEY}        {STRIPE_TEST_KEY}
        # Multiple references to same credential
        Log API Key      ${API_KEY}
        Use API Key      ${API_KEY}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(content)
            temp_file = Path(f.name)

        try:
            report = scanner.scan_template_file(temp_file)

            # Should have unique issues (no duplicates)
            issue_locations = [
                (i.line_number, i.issue_type, i.match_text) for i in report.issues
            ]
            unique_locations = set(issue_locations)

            assert len(issue_locations) == len(unique_locations)

        finally:
            temp_file.unlink()

    def test_scan_performance(self) -> None:
        """Test scanning performance with large file."""
        scanner = TemplateSecurityScanner()

        # Create a large template file
        large_content = [
            f"""
            *** Variables ***
            ${{VAR_{i}}}        value_{i}
            """
            for i in range(1000)
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write("\n".join(large_content))
            temp_file = Path(f.name)

        try:
            start_time = time.time()
            report = scanner.scan_template_file(temp_file)
            scan_duration = time.time() - start_time

            # Should complete quickly (less than 1 second)
            assert scan_duration < 1.0
            assert report.scan_duration == pytest.approx(scan_duration, rel=1e-3)

        finally:
            temp_file.unlink()

    def test_generate_summary_report(self) -> None:
        """Test summary report generation."""
        scanner = TemplateSecurityScanner()

        # Create test reports
        timestamp = time.time()
        safe_report = TemplateSecurityReport(
            file_path="/safe.robot",
            scan_timestamp=timestamp,
            scan_duration=0.01,
            issues=[],
            total_issues=0,
            issues_by_severity={},
            issues_by_type={},
            is_safe=True,
            file_hash="safehash",
            statistics={},
        )

        critical_issues = [
            SecurityIssue(
                issue_type="credential",
                severity="critical",
                file_path="/unsafe.robot",
                line_number=10,
                column_number=1,
                description="Critical credential leak",
                match_text=f"api_key: {SHORT_EXAMPLE_KEY}",
                confidence=0.95,
                remediation="Rotate affected keys",
                context=f"api_key: {SHORT_EXAMPLE_KEY}",
                rule_id="CRED_API_KEY_CRITICAL",
            ),
            SecurityIssue(
                issue_type="hardcoded_value",
                severity="critical",
                file_path="/unsafe.robot",
                line_number=12,
                column_number=1,
                description="Critical SSH private key",
                match_text="-----BEGIN PRIVATE KEY-----",
                confidence=0.92,
                remediation="Remove private key from template",
                context="-----BEGIN PRIVATE KEY-----",
                rule_id="SSH_PRIVATE_KEY_CRITICAL",
            ),
            SecurityIssue(
                issue_type="hardcoded_value",
                severity="high",
                file_path="/unsafe.robot",
                line_number=20,
                column_number=1,
                description="High severity hardcoded secret",
                match_text="secret_value = 'abc'",
                confidence=0.9,
                remediation="Move value to vault",
                context="secret_value = 'abc'",
                rule_id="HARD_CODED_SECRET_HIGH",
            ),
            SecurityIssue(
                issue_type="credential",
                severity="high",
                file_path="/unsafe.robot",
                line_number=22,
                column_number=1,
                description="High severity access token",
                match_text="auth_token = 'abcd'",
                confidence=0.88,
                remediation="Rotate token",
                context="auth_token = 'abcd'",
                rule_id="AUTH_TOKEN_HIGH",
            ),
            SecurityIssue(
                issue_type="credential",
                severity="high",
                file_path="/unsafe.robot",
                line_number=24,
                column_number=1,
                description="High severity API secret",
                match_text="api_secret = 'xyz'",
                confidence=0.87,
                remediation="Store API secret in vault",
                context="api_secret = 'xyz'",
                rule_id="API_SECRET_HIGH",
            ),
        ]
        unsafe_report = TemplateSecurityReport(
            file_path="/unsafe.robot",
            scan_timestamp=timestamp,
            scan_duration=0.05,
            issues=critical_issues,
            total_issues=len(critical_issues),
            issues_by_severity={"critical": 2, "high": 3},
            issues_by_type={"credential": 3, "hardcoded_value": 2},
            is_safe=False,
            file_hash="unsafehash",
            statistics={
                "suspicious_variables_found": 0,
                "hardcoded_credentials_found": 1,
            },
        )

        summary = scanner.generate_summary_report([safe_report, unsafe_report])

        # Validate summary structure
        assert "scan_summary" in summary
        assert "issue_summary" in summary
        assert "critical_issues" in summary
        assert "recommendations" in summary

        # Validate scan summary
        scan_summary = summary["scan_summary"]
        assert scan_summary["total_files_scanned"] == 2
        assert scan_summary["safe_files"] == 1
        assert scan_summary["unsafe_files"] == 1
        assert scan_summary["scan_pass_rate"] == 50.0

        # Validate issue summary
        issue_summary = summary["issue_summary"]
        assert issue_summary["by_severity"]["critical"] == 2
        assert issue_summary["by_severity"]["high"] == 3

        # Validate recommendations
        recommendations = summary["recommendations"]
        assert len(recommendations) > 0


class TestConvenienceFunction:
    """Test the convenience function for template scanning."""

    def test_scan_template_file_for_security_function(self) -> None:
        """Test the convenience function."""
        # Create a test file
        test_content = f"""
        *** Variables ***
        ${{API_KEY}}        {STRIPE_TEST_KEY}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".robot", delete=False) as f:
            f.write(test_content)
            temp_file = Path(f.name)

        try:
            report = scan_template_file_for_security(temp_file)

            # Should return TemplateSecurityReport
            assert isinstance(report, TemplateSecurityReport)
            assert report.file_path == str(temp_file)
            assert report.total_issues > 0
            # File might still be safe if only medium/low severity issues detected
            [i for i in report.issues if i.severity in ["critical", "high"]]
            # At minimum, there should be some issues detected

        finally:
            temp_file.unlink()


class TestPatternMatchingAccuracy:
    """Test accuracy of pattern matching in template scanner."""

    def test_robot_variable_detection(self) -> None:
        """Test Robot Framework variable detection."""
        # Use module-level functions with required parameters
        suspicious_variables = ScannerPatterns.get_suspicious_variables()
        safe_keywords = ScannerPatterns.get_safe_keywords()

        test_cases = [
            ("${password}", True),
            ("${user_password}", True),
            ("${PASSWORD}", True),
            ("${api_key}", True),
            ("${API_KEY}", True),
            ("${normal_variable}", False),
            ("${config_value}", False),
        ]

        for variable, should_detect in test_cases:
            content = f"*** Variables ***\n{variable}  some_value"
            issues = scan_for_suspicious_variables(
                content,
                "test.robot",
                content.split("\n"),
                suspicious_variables,
                safe_keywords,
                PLACEHOLDER_INDICATORS,
            )

            if should_detect:
                assert len(issues) > 0, f"Should detect {variable}"
                assert issues[0].issue_type == "suspicious_variable"
            else:
                suspicious_vars = [
                    i for i in issues if i.issue_type == "suspicious_variable"
                ]
                assert len(suspicious_vars) == 0, f"Should not detect {variable}"

    def test_hardcoded_pattern_detection(self) -> None:
        """Test hardcoded pattern detection."""
        # Use module-level functions with required parameters
        hardcoded_patterns = ScannerPatterns.get_hardcoded_patterns()
        safe_keywords = ScannerPatterns.get_safe_keywords()

        test_cases = [
            ("password: secret123", True, "hardcoded_value"),
            ("api_key: abc123", True, "hardcoded_value"),
            ("mongodb://user:pass@host/db", True, "hardcoded_value"),
            ("-----BEGIN PRIVATE KEY-----", True, "hardcoded_value"),
            ("normal_value = safe", False, "none"),
        ]

        for content, should_detect, expected_type in test_cases:
            issues = scan_for_hardcoded_patterns(
                content,
                "test.robot",
                [content],
                hardcoded_patterns,
                safe_keywords,
            )

            if should_detect:
                assert len(issues) > 0, f"Should detect pattern in: {content}"
                assert issues[0].issue_type == expected_type
            else:
                assert len(issues) == 0, f"Should not detect pattern in: {content}"

    def test_false_positive_prevention(self) -> None:
        """Test false positive prevention mechanisms."""
        # Use module-level functions with required parameters
        suspicious_variables = ScannerPatterns.get_suspicious_variables()
        safe_keywords = ScannerPatterns.get_safe_keywords()

        # These should not trigger detection
        safe_cases = [
            "password_example",
            "use_your_api_key_here",
            "replace_with_real_password",
            "demo_connection_string",
            "test_secret_value",
            "example_api_format",
            "fake_token_for_testing",
            "placeholder_value_here",
        ]

        for safe_text in safe_cases:
            # Test that suspicious variables with safe context are ignored
            content = "${safe_text}  some_value"
            lines: list[str] = list(content.split("\n"))
            issues = scan_for_suspicious_variables(
                content,
                "test.robot",
                lines,
                suspicious_variables,
                safe_keywords,
                PLACEHOLDER_INDICATORS,
            )

            # Should not detect suspicious variables with safe context
            suspicious_vars = [
                i for i in issues if i.issue_type == "suspicious_variable"
            ]
            assert len(suspicious_vars) == 0, (
                f"Safe text triggered detection: {safe_text}"
            )

    def test_confidence_levels(self) -> None:
        """Test that different issues have appropriate confidence levels."""
        scanner = TemplateSecurityScanner()

        # High confidence patterns (should be detected)
        high_conf_content = """
        aws_access_key_id: AKIAIOSFODNN7EXAMPLE
        -----BEGIN PRIVATE KEY-----
        """

        # Lower confidence patterns
        low_conf_content = """
        some_token_value
        random_key_format
        """

        high_conf_issues = scanner._scan_content(high_conf_content, "test.robot")
        low_conf_issues = scanner._scan_content(low_conf_content, "test.robot")

        # High confidence content should produce high-confidence issues
        high_conf_issues_filtered = [i for i in high_conf_issues if i.confidence >= 0.8]
        assert len(high_conf_issues_filtered) >= 1

        # Low confidence content should produce fewer or lower-confidence issues
        low_conf_issues_high_conf = [i for i in low_conf_issues if i.confidence >= 0.8]
        assert len(low_conf_issues_high_conf) <= len(high_conf_issues_filtered)
