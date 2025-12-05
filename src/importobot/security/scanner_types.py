"""Data types for template security scanning.

Provides dataclasses for representing security issues and scan reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SecurityIssue:
    """Represents a security issue found in a template file.

    Attributes:
        issue_type: Category of issue ("credential", "suspicious_variable",
            "hardcoded_value", "pattern")
        severity: Severity level ("low", "medium", "high", "critical")
        file_path: Path to the file containing the issue
        line_number: Line number where issue was found
        column_number: Column number where issue starts
        description: Human-readable description of the issue
        match_text: The actual text that matched the security pattern
        confidence: Confidence score (0.0 to 1.0) for this detection
        remediation: Suggested fix for the issue
        context: Surrounding code context for the issue
        rule_id: Optional identifier for the security rule that triggered
    """

    issue_type: str
    severity: str
    file_path: str
    line_number: int
    column_number: int
    description: str
    match_text: str
    confidence: float
    remediation: str
    context: str
    rule_id: str | None = None


@dataclass
class TemplateSecurityReport:
    """Comprehensive security report for template scanning.

    Attributes:
        file_path: Path to the scanned file
        scan_timestamp: Unix timestamp when scan started
        scan_duration: Duration of scan in seconds
        issues: List of SecurityIssue objects found
        total_issues: Total count of issues
        issues_by_severity: Count of issues grouped by severity
        issues_by_type: Count of issues grouped by type
        is_safe: Whether the file passed security checks
        file_hash: Blake2b hash of file contents
        statistics: Additional scan statistics
    """

    file_path: str
    scan_timestamp: float
    scan_duration: float
    issues: list[SecurityIssue]
    total_issues: int
    issues_by_severity: dict[str, int]
    issues_by_type: dict[str, int]
    is_safe: bool
    file_hash: str
    statistics: dict[str, Any]


# Internal utility - not part of public API
__all__: list[str] = []
