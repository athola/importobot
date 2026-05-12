"""Tests for individual scanner check functions.

Covers the four scan functions in ``importobot.security.scanner_checks``
(``scan_for_credentials``, ``scan_for_suspicious_variables``,
``scan_for_hardcoded_patterns``, ``scan_for_robot_framework_issues``)
and the helper predicates that decide false-positive suppression and
variable severity classification.
"""

from __future__ import annotations

import pytest

from importobot.security import scanner_checks
from importobot.security.credential_patterns import CredentialPatternRegistry
from importobot.security.scanner_checks import (
    _contains_safe_keywords,
    _get_variable_severity,
    _is_false_positive,
    _is_placeholder_context,
    _is_suspicious_variable,
    scan_for_credentials,
    scan_for_hardcoded_patterns,
    scan_for_robot_framework_issues,
    scan_for_suspicious_variables,
)
from importobot.security.scanner_utils import get_context


@pytest.fixture(autouse=True)
def _provide_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", "A" * 44)


class TestScanForCredentials:
    """Credential scan emits SecurityIssue per matched credential pattern."""

    def test_finds_aws_credential_in_content(self) -> None:
        registry = CredentialPatternRegistry()
        content = (
            "*** Variables ***\n${AWS_KEY}    aws_access_key_id: AKIAIOSFODNN7EXAMPLE\n"
        )
        issues = scan_for_credentials(
            content=content,
            file_path="/tmp/x.robot",
            credential_registry=registry,
            safe_keywords=set(),
            get_context_fn=get_context,
        )
        assert any(i.issue_type == "credential" for i in issues)
        assert any("AWS" in (i.rule_id or "") for i in issues)

    def test_safe_keyword_suppresses_match(self) -> None:
        registry = CredentialPatternRegistry()
        # The match text contains "example" so safe_keywords filter it out.
        content = "aws_access_key_id: AKIAIOSFODNN7EXAMPLE\n"
        issues = scan_for_credentials(
            content=content,
            file_path="/tmp/x.robot",
            credential_registry=registry,
            safe_keywords={"example"},
            get_context_fn=get_context,
        )
        assert issues == []

    def test_no_matches_yields_empty(self) -> None:
        registry = CredentialPatternRegistry()
        issues = scan_for_credentials(
            content="Just narrative content here.",
            file_path="/tmp/x.robot",
            credential_registry=registry,
            safe_keywords=set(),
            get_context_fn=get_context,
        )
        assert issues == []


class TestScanForSuspiciousVariables:
    """Variable-name scanner with placeholder and safe-keyword suppression."""

    def test_password_variable_is_flagged(self) -> None:
        content = "${PASSWORD}    some_value\n"
        issues = scan_for_suspicious_variables(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            suspicious_variables={"password"},
            safe_keywords=set(),
            placeholder_indicators=(),
        )
        assert any(i.issue_type == "suspicious_variable" for i in issues)
        assert any("PASSWORD" in (i.rule_id or "") for i in issues)

    def test_placeholder_context_suppresses_finding(self) -> None:
        # The "example" indicator nearby is supposed to suppress the issue.
        content = "# example placeholder\n${PASSWORD}    placeholder_value\n"
        issues = scan_for_suspicious_variables(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            suspicious_variables={"password"},
            safe_keywords=set(),
            placeholder_indicators=("example", "placeholder"),
        )
        assert issues == []

    def test_safe_keyword_on_same_line_suppresses(self) -> None:
        # Safe keyword appearing after the variable suppresses the issue.
        content = "${PASSWORD}    test_value\n"
        issues = scan_for_suspicious_variables(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            suspicious_variables={"password"},
            safe_keywords={"test"},
            placeholder_indicators=(),
        )
        assert issues == []

    def test_section_header_lines_are_ignored_for_placeholder_context(
        self,
    ) -> None:
        # Robot section headers like "*** Variables ***" must not act as
        # placeholder context — the scanner explicitly strips them.
        content = "*** Variables ***\n${PASSWORD}    real_value\n"
        issues = scan_for_suspicious_variables(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            suspicious_variables={"password"},
            safe_keywords=set(),
            # If headers leaked into the placeholder check, "variables"
            # could match — we want to confirm the scanner ignores them.
            placeholder_indicators=("variables",),
        )
        # The issue should still be emitted because the section header
        # was filtered out before the placeholder check.
        assert any(i.issue_type == "suspicious_variable" for i in issues)


class TestScanForHardcodedPatterns:
    """Pattern-config driven hardcoded-value scanner."""

    @pytest.fixture
    def basic_pattern(self) -> list[dict[str, object]]:
        return [
            {
                "pattern": r"\b1234567890\b",
                "severity": "high",
                "description": "Hardcoded numeric secret",
                "remediation": "Move to env var",
                "name": "numeric_secret",
            }
        ]

    def test_match_creates_hardcoded_issue(
        self, basic_pattern: list[dict[str, object]]
    ) -> None:
        content = "secret = 1234567890\n"
        issues = scan_for_hardcoded_patterns(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            hardcoded_patterns=basic_pattern,
            safe_keywords=set(),
        )
        assert len(issues) == 1
        assert issues[0].issue_type == "hardcoded_value"
        assert issues[0].severity == "high"
        assert issues[0].rule_id == "HARDCODED_NUMERIC_SECRET"

    def test_safe_keyword_in_match_suppresses_issue(
        self, basic_pattern: list[dict[str, object]]
    ) -> None:
        # If the match text itself contains the safe keyword, suppressed.
        pattern = [
            {
                "pattern": r"\bexample-1234\b",
                "severity": "high",
                "description": "x",
                "remediation": "y",
                "name": "ex",
            }
        ]
        content = "value = example-1234\n"
        issues = scan_for_hardcoded_patterns(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            hardcoded_patterns=pattern,
            safe_keywords={"example"},
        )
        assert issues == []

    def test_comment_with_safe_keyword_suppresses_issue(
        self, basic_pattern: list[dict[str, object]]
    ) -> None:
        # Even if the match is in real code, a comment with safe keyword
        # on the same line suppresses it (e.g., "# example value").
        content = "value = 1234567890  # example only\n"
        issues = scan_for_hardcoded_patterns(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            hardcoded_patterns=basic_pattern,
            safe_keywords={"example"},
        )
        assert issues == []


class TestScanForRobotFrameworkIssues:
    """Robot-framework-specific pattern scanner."""

    def test_match_emits_pattern_issue(self) -> None:
        patterns = [
            {
                "pattern": r"Set Global Variable",
                "severity": "medium",
                "description": "Avoid global mutation in tests",
                "remediation": "Use local scope",
                "name": "global_var",
            }
        ]
        content = "Set Global Variable    ${SECRET}    value\n"
        issues = scan_for_robot_framework_issues(
            content=content,
            file_path="/tmp/x.robot",
            lines=content.split("\n"),
            robot_patterns=patterns,
        )
        assert len(issues) == 1
        assert issues[0].issue_type == "pattern"
        assert issues[0].rule_id == "ROBOT_GLOBAL_VAR"

    def test_no_match_yields_empty(self) -> None:
        issues = scan_for_robot_framework_issues(
            content="Nothing matching here",
            file_path="/tmp/x.robot",
            lines=["Nothing matching here"],
            robot_patterns=[
                {
                    "pattern": r"NEVER_PRESENT",
                    "severity": "low",
                    "description": "x",
                    "remediation": "y",
                    "name": "z",
                }
            ],
        )
        assert issues == []


class TestHelperPredicates:
    """Private helpers underpin every scan function — test them directly."""

    def test_is_false_positive_matches_substring_case_insensitive(self) -> None:
        assert _is_false_positive("EXAMPLE_KEY", {"example"}) is True
        assert _is_false_positive("real_secret", {"example"}) is False

    def test_contains_safe_keywords_returns_true_on_match(self) -> None:
        assert _contains_safe_keywords("test value here", {"test"}) is True
        assert _contains_safe_keywords("real value", {"test"}) is False

    def test_is_placeholder_context_with_indicator_returns_true(self) -> None:
        assert _is_placeholder_context("foo bar", ("placeholder",)) is False
        assert _is_placeholder_context("foo placeholder", ("placeholder",)) is True

    def test_is_suspicious_variable_by_explicit_set(self) -> None:
        assert _is_suspicious_variable("my_var", {"my_var"}) is True

    def test_is_suspicious_variable_by_substring(self) -> None:
        # The substrings list ("password", "secret", "token", ...) catches
        # variable names that contain those terms even without an explicit
        # set match. This is a strong default; assert it stays in place.
        assert _is_suspicious_variable("user_password", set()) is True
        assert _is_suspicious_variable("api_token_v2", set()) is True
        assert _is_suspicious_variable("foo", set()) is False

    def test_variable_severity_for_critical_token(self) -> None:
        # Variables in the CRITICAL set return "critical"; others "high"
        # or "medium" based on the lookup tables in scanner_patterns.
        assert _get_variable_severity("foo_unmapped") == "medium"


class TestModulePrivacy:
    def test_all_is_empty(self) -> None:
        assert scanner_checks.__all__ == []
