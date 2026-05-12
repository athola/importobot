"""Tests for security scanner data types.

Covers the SecurityIssue and TemplateSecurityReport dataclasses defined in
``importobot.security.scanner_types``. These types are internal but every
scanner downstream depends on their field shape, so regressions here would
cascade silently into reports.
"""

from __future__ import annotations

import pytest

from importobot.security import scanner_types
from importobot.security.scanner_types import (
    SecurityIssue,
    TemplateSecurityReport,
)


class TestSecurityIssue:
    """SecurityIssue dataclass behaviour."""

    def _make_issue(self, **overrides: object) -> SecurityIssue:
        defaults: dict[str, object] = {
            "issue_type": "credential",
            "severity": "high",
            "file_path": "/tmp/example.robot",
            "line_number": 12,
            "column_number": 4,
            "description": "Hardcoded API key",
            "match_text": "api_key=ABCDEF",
            "confidence": 0.9,
            "remediation": "Move to environment variable",
            "context": "*** Variables ***",
        }
        defaults.update(overrides)
        return SecurityIssue(**defaults)  # type: ignore[arg-type]

    def test_construction_with_required_fields_succeeds(self) -> None:
        issue = self._make_issue()
        assert issue.issue_type == "credential"
        assert issue.severity == "high"
        assert issue.line_number == 12
        assert issue.confidence == pytest.approx(0.9)

    def test_rule_id_defaults_to_none(self) -> None:
        issue = self._make_issue()
        assert issue.rule_id is None

    def test_rule_id_accepts_explicit_value(self) -> None:
        issue = self._make_issue(rule_id="CRED-001")
        assert issue.rule_id == "CRED-001"

    def test_equality_compares_by_field_value(self) -> None:
        a = self._make_issue()
        b = self._make_issue()
        c = self._make_issue(line_number=99)
        assert a == b
        assert a != c

    def test_missing_required_field_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            # Omit file_path on purpose to verify it is required.
            SecurityIssue(  # type: ignore[call-arg]
                issue_type="credential",
                severity="low",
                line_number=1,
                column_number=1,
                description="x",
                match_text="y",
                confidence=0.1,
                remediation="z",
                context="",
            )


class TestTemplateSecurityReport:
    """TemplateSecurityReport dataclass behaviour."""

    def _make_report(self, **overrides: object) -> TemplateSecurityReport:
        defaults: dict[str, object] = {
            "file_path": "/tmp/example.robot",
            "scan_timestamp": 1_700_000_000.0,
            "scan_duration": 0.42,
            "issues": [],
            "total_issues": 0,
            "issues_by_severity": {},
            "issues_by_type": {},
            "is_safe": True,
            "file_hash": "blake2b-deadbeef",
            "statistics": {},
        }
        defaults.update(overrides)
        return TemplateSecurityReport(**defaults)  # type: ignore[arg-type]

    def test_empty_report_is_safe_with_zero_issues(self) -> None:
        report = self._make_report()
        assert report.total_issues == 0
        assert report.is_safe is True
        assert report.issues == []

    def test_report_with_issues_reflects_counts(self) -> None:
        issue = SecurityIssue(
            issue_type="credential",
            severity="high",
            file_path="/tmp/example.robot",
            line_number=5,
            column_number=2,
            description="...",
            match_text="...",
            confidence=0.8,
            remediation="...",
            context="...",
        )
        report = self._make_report(
            issues=[issue],
            total_issues=1,
            issues_by_severity={"high": 1},
            issues_by_type={"credential": 1},
            is_safe=False,
        )
        assert report.total_issues == 1
        assert report.is_safe is False
        assert report.issues_by_severity["high"] == 1
        assert report.issues_by_type["credential"] == 1

    def test_statistics_accepts_arbitrary_metadata(self) -> None:
        # statistics is a free-form dict[str, Any]; downstream callers stash
        # scanner-specific metadata here, so it must not constrain the value
        # type at construction time.
        report = self._make_report(
            statistics={"lines": 100, "patterns_evaluated": 27, "skipped": False}
        )
        assert report.statistics["lines"] == 100
        assert report.statistics["skipped"] is False

    def test_all_is_intentionally_empty(self) -> None:
        # Encodes the invariant that scanner_types is internal: a refactor
        # promoting these to public API should be a conscious decision, not
        # a drift from someone exporting them silently.
        assert scanner_types.__all__ == []
