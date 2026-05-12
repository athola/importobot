"""Tests for scanner utility helpers.

Covers the pure-function helpers in ``importobot.security.scanner_utils``
that downstream scanners use to format context, deduplicate findings,
and aggregate statistics. These functions are leaf-level — testing them
directly catches regressions before they propagate into reports.
"""

from __future__ import annotations

import pytest

from importobot.security import scanner_utils
from importobot.security.scanner_types import (
    SecurityIssue,
    TemplateSecurityReport,
)
from importobot.security.scanner_utils import (
    aggregate_reports,
    build_report_statistics,
    deduplicate_issues,
    determine_safety,
    generate_recommendations,
    get_context,
)


def _make_issue(**overrides: object) -> SecurityIssue:
    defaults: dict[str, object] = {
        "issue_type": "credential",
        "severity": "high",
        "file_path": "/tmp/x.robot",
        "line_number": 1,
        "column_number": 1,
        "description": "...",
        "match_text": "abc",
        "confidence": 0.9,
        "remediation": "...",
        "context": "...",
    }
    defaults.update(overrides)
    return SecurityIssue(**defaults)  # type: ignore[arg-type]


class TestGetContext:
    """Context extraction around a target line."""

    @pytest.fixture
    def content(self) -> str:
        return "\n".join(f"line {n}" for n in range(1, 11))

    def test_middle_line_with_default_context_returns_seven_lines(
        self, content: str
    ) -> None:
        # Default context_lines=3 -> 3 before + the line + 3 after.
        out = get_context(content, line_number=5)
        lines = out.split("\n")
        assert len(lines) == 7
        assert lines[0].startswith("  2:")
        assert lines[-1].startswith("  8:")

    def test_top_line_clips_at_start(self, content: str) -> None:
        out = get_context(content, line_number=1, context_lines=3)
        lines = out.split("\n")
        # Cannot go before line 1, so window is [1, 4].
        assert lines[0].startswith("  1:")
        assert lines[-1].startswith("  4:")

    def test_bottom_line_clips_at_end(self, content: str) -> None:
        out = get_context(content, line_number=10, context_lines=3)
        lines = out.split("\n")
        # Cannot go past line 10.
        assert lines[-1].startswith(" 10:")

    def test_zero_context_returns_only_target_line(self, content: str) -> None:
        out = get_context(content, line_number=5, context_lines=0)
        # With context_lines=0 the slice [4:5] yields just line 5.
        assert out == "  5: line 5"

    def test_empty_content_yields_empty_string(self) -> None:
        # The split of "" produces [""] so we get a single padded line.
        # Lock the current behaviour so future refactors notice.
        out = get_context("", line_number=1, context_lines=3)
        assert out == "  1: "


class TestDeduplicateIssues:
    """Deduplication keyed on (file_path, line_number, issue_type, match_text)."""

    def test_empty_list_returns_empty(self) -> None:
        assert deduplicate_issues([]) == []

    def test_identical_issues_collapse_to_one(self) -> None:
        a = _make_issue()
        b = _make_issue()
        result = deduplicate_issues([a, b])
        assert len(result) == 1
        # Preserves the first occurrence.
        assert result[0] is a

    def test_differing_line_numbers_are_kept_separate(self) -> None:
        a = _make_issue(line_number=1)
        b = _make_issue(line_number=2)
        result = deduplicate_issues([a, b])
        assert len(result) == 2

    def test_description_differs_but_dedup_key_same_collapses(self) -> None:
        # Description is intentionally NOT part of the dedup key; encoding
        # this lets future refactors notice if dedup gets stricter.
        a = _make_issue(description="A")
        b = _make_issue(description="B")
        result = deduplicate_issues([a, b])
        assert len(result) == 1


class TestGenerateRecommendations:
    """Type-driven recommendation builder with fallback."""

    def test_no_issues_returns_fallback(self) -> None:
        recs = generate_recommendations({})
        assert len(recs) == 1
        assert "no major security issues" in recs[0].lower()

    def test_credential_yields_secret_storage_advice(self) -> None:
        recs = generate_recommendations({"credential": 2})
        assert any("environment variables" in r for r in recs)

    def test_suspicious_variable_yields_rename_advice(self) -> None:
        recs = generate_recommendations({"suspicious_variable": 1})
        assert any("rename" in r.lower() for r in recs)

    def test_hardcoded_value_yields_config_advice(self) -> None:
        recs = generate_recommendations({"hardcoded_value": 3})
        assert any("secure storage" in r.lower() for r in recs)

    def test_pattern_yields_robot_advice(self) -> None:
        recs = generate_recommendations({"pattern": 1})
        assert any("robot framework" in r.lower() for r in recs)

    def test_multiple_types_yield_multiple_recommendations(self) -> None:
        recs = generate_recommendations(
            {"credential": 1, "suspicious_variable": 1, "hardcoded_value": 1}
        )
        # Three distinct categories, three distinct recommendations.
        assert len(recs) == 3

    def test_zero_counts_treated_as_absent(self) -> None:
        recs = generate_recommendations({"credential": 0, "pattern": 0})
        # Both counts are zero, so the fallback must fire.
        assert len(recs) == 1
        assert "no major" in recs[0].lower()


class TestBuildReportStatistics:
    """Severity and type tallies."""

    def test_empty_issues_yield_empty_dicts(self) -> None:
        by_sev, by_type = build_report_statistics([])
        assert by_sev == {}
        assert by_type == {}

    def test_counts_multiple_severities_and_types(self) -> None:
        issues = [
            _make_issue(severity="high", issue_type="credential"),
            _make_issue(severity="high", issue_type="pattern"),
            _make_issue(severity="medium", issue_type="credential"),
        ]
        by_sev, by_type = build_report_statistics(issues)
        assert by_sev == {"high": 2, "medium": 1}
        assert by_type == {"credential": 2, "pattern": 1}


class TestDetermineSafety:
    """The boolean safety verdict has three failure dimensions."""

    def test_empty_stats_is_safe(self) -> None:
        assert determine_safety({}, {}) is True

    def test_critical_severity_marks_unsafe(self) -> None:
        assert determine_safety({"critical": 1}, {}) is False

    def test_high_severity_marks_unsafe(self) -> None:
        assert determine_safety({"high": 1}, {}) is False

    def test_credential_issue_marks_unsafe_regardless_of_severity(self) -> None:
        # Even if every credential is low-severity, the file is unsafe.
        assert determine_safety({"low": 5}, {"credential": 1}) is False

    def test_hardcoded_value_marks_unsafe(self) -> None:
        assert determine_safety({"low": 1}, {"hardcoded_value": 1}) is False

    def test_only_medium_pattern_issues_still_safe(self) -> None:
        # Lower severities with non-credential/non-hardcoded types do not
        # flip the verdict — the function's three-axis check must remain
        # exact for any compliance reporting downstream.
        assert determine_safety({"medium": 5}, {"pattern": 3}) is True


class TestAggregateReports:
    """Aggregation across multiple reports."""

    def _make_report(
        self,
        sev: dict[str, int] | None = None,
        types: dict[str, int] | None = None,
    ) -> TemplateSecurityReport:
        return TemplateSecurityReport(
            file_path="/x",
            scan_timestamp=0.0,
            scan_duration=0.0,
            issues=[],
            total_issues=0,
            issues_by_severity=sev or {},
            issues_by_type=types or {},
            is_safe=True,
            file_hash="",
            statistics={},
        )

    def test_no_reports_returns_empty(self) -> None:
        by_sev, by_type = aggregate_reports([])
        assert by_sev == {}
        assert by_type == {}

    def test_two_reports_sum_counts(self) -> None:
        r1 = self._make_report(sev={"high": 1, "low": 2}, types={"credential": 1})
        r2 = self._make_report(
            sev={"high": 2, "medium": 1}, types={"credential": 1, "pattern": 1}
        )
        by_sev, by_type = aggregate_reports([r1, r2])
        assert by_sev == {"high": 3, "low": 2, "medium": 1}
        assert by_type == {"credential": 2, "pattern": 1}


class TestModulePrivacy:
    def test_all_is_empty(self) -> None:
        assert scanner_utils.__all__ == []
