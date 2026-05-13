"""Utility functions for template security scanning.

Helper functions for context extraction, issue deduplication,
and recommendation generation.
"""

from __future__ import annotations

from typing import Any

from importobot.security.scanner_types import SecurityIssue


def get_context(content: str, line_number: int, context_lines: int = 3) -> str:
    """Get context around a match.

    Args:
        content: Full content
        line_number: Line number of the match
        context_lines: Number of lines before and after to include

    Returns:
        Context string with line numbers
    """
    lines = content.split("\n")
    start = max(0, line_number - context_lines - 1)
    end = min(len(lines), line_number + context_lines)

    context_lines_list = lines[start:end]
    return "\n".join(
        f"{i + start + 1:3d}: {line}" for i, line in enumerate(context_lines_list)
    )


def deduplicate_issues(issues: list[SecurityIssue]) -> list[SecurityIssue]:
    """Remove duplicate issues.

    Args:
        issues: List of issues to deduplicate

    Returns:
        Deduplicated list of issues
    """
    seen: set[tuple[str, int, str, str]] = set()
    unique_issues = []

    for issue in issues:
        # Create a key for deduplication
        key = (
            issue.file_path,
            issue.line_number,
            issue.issue_type,
            issue.match_text,
        )

        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    return unique_issues


def generate_recommendations(issues_by_type: dict[str, int]) -> list[str]:
    """Generate recommendations based on issue types.

    Args:
        issues_by_type: Dictionary of issue types and counts

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if issues_by_type.get("credential", 0) > 0:
        recommendations.append(
            "Remove hard-coded credentials and use environment variables "
            "or a secret management system"
        )

    if issues_by_type.get("suspicious_variable", 0) > 0:
        recommendations.append(
            "Rename suspicious variables to use generic names and load "
            "values from secure sources"
        )

    if issues_by_type.get("hardcoded_value", 0) > 0:
        recommendations.append(
            "Replace hard-coded values with configuration from secure storage"
        )

    if issues_by_type.get("pattern", 0) > 0:
        recommendations.append(
            "Review and fix Robot Framework patterns that may lead to security issues"
        )

    if not recommendations:
        recommendations.append(
            "No major security issues detected - continue following "
            "security best practices"
        )

    return recommendations


def build_report_statistics(
    issues: list[SecurityIssue],
) -> tuple[dict[str, int], dict[str, int]]:
    """Build report statistics from issues.

    Args:
        issues: List of SecurityIssue objects

    Returns:
        Tuple of (issues_by_severity, issues_by_type) dictionaries
    """
    issues_by_severity: dict[str, int] = {}
    issues_by_type: dict[str, int] = {}

    for issue in issues:
        issues_by_severity[issue.severity] = (
            issues_by_severity.get(issue.severity, 0) + 1
        )
        issues_by_type[issue.issue_type] = issues_by_type.get(issue.issue_type, 0) + 1

    return issues_by_severity, issues_by_type


def determine_safety(
    issues_by_severity: dict[str, int], issues_by_type: dict[str, int]
) -> bool:
    """Determine if a file is safe based on issues.

    Args:
        issues_by_severity: Count of issues by severity
        issues_by_type: Count of issues by type

    Returns:
        True if the file is considered safe
    """
    critical_high_count = issues_by_severity.get(
        "critical", 0
    ) + issues_by_severity.get("high", 0)
    credential_issues = issues_by_type.get("credential", 0)
    hardcoded_issues = issues_by_type.get("hardcoded_value", 0)

    return critical_high_count == 0 and credential_issues == 0 and hardcoded_issues == 0


def aggregate_reports(
    reports: list[Any],
) -> tuple[dict[str, int], dict[str, int]]:
    """Aggregate issues from multiple reports.

    Args:
        reports: List of TemplateSecurityReport objects

    Returns:
        Tuple of (all_issues_by_severity, all_issues_by_type) dictionaries
    """
    all_issues_by_severity: dict[str, int] = {}
    all_issues_by_type: dict[str, int] = {}

    for report in reports:
        for severity, count in report.issues_by_severity.items():
            all_issues_by_severity[severity] = (
                all_issues_by_severity.get(severity, 0) + count
            )
        for issue_type, count in report.issues_by_type.items():
            all_issues_by_type[issue_type] = (
                all_issues_by_type.get(issue_type, 0) + count
            )

    return all_issues_by_severity, all_issues_by_type


# Internal utility - not part of public API
__all__: list[str] = []
