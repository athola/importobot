"""Template security scanner for `--robot-template` workflows.

Scans Robot Framework templates for leaked credentials, suspicious variables,
and other issues before they reach the converter.

This module provides the main TemplateSecurityScanner class that orchestrates
security scanning using specialized modules for pattern matching, checks,
and utilities.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from importobot.security.credential_patterns import (
    CredentialPatternRegistry,
    get_current_registry,
)
from importobot.security.scanner_checks import (
    scan_for_credentials,
    scan_for_hardcoded_patterns,
    scan_for_robot_framework_issues,
    scan_for_suspicious_variables,
)
from importobot.security.scanner_patterns import ScannerPatterns
from importobot.security.scanner_types import SecurityIssue, TemplateSecurityReport
from importobot.security.scanner_utils import (
    aggregate_reports,
    build_report_statistics,
    deduplicate_issues,
    determine_safety,
    generate_recommendations,
    get_context,
)
from importobot.security.security_validator import SecurityValidator
from importobot.utils.logging import get_logger

logger = get_logger()

# Re-exports for backwards compatibility
__all__ = [
    "SecurityIssue",
    "TemplateSecurityReport",
    "TemplateSecurityScanner",
    "scan_template_file_for_security",
]


class TemplateSecurityScanner:
    """Security scanner for Robot Framework template files.

    Detects hard-coded credentials, suspicious variable names, insecure
    patterns, configuration issues, and authentication risks before conversion.

    Features:
    - Pattern-based credential detection
    - Variable name security analysis
    - Template structure validation
    - Confidence scoring and prioritization
    - Detailed security recommendations
    - Configurable critical issue reporting limits

    All pattern sets are configurable. You can either:
    1. Pass custom patterns to the constructor
    2. Modify the module-level constants in scanner_patterns.py
    3. Subclass ScannerPatterns and override the class variables

    Attributes:
        credential_registry: Registry for credential patterns.
        security_validator: Validator for security checks.
        max_critical_issues: Maximum critical issues in summary reports.
    """

    def __init__(
        self,
        security_validator: SecurityValidator | None = None,
        credential_registry: CredentialPatternRegistry | None = None,
        max_critical_issues: int = 10,
        *,
        additional_suspicious_variables: set[str] | None = None,
        additional_hardcoded_patterns: list[dict[str, Any]] | None = None,
        additional_robot_patterns: list[dict[str, Any]] | None = None,
        additional_safe_keywords: set[str] | None = None,
    ):
        """Initialize the template security scanner.

        Args:
            security_validator: Optional security validator instance
            credential_registry: Optional credential pattern registry instance.
                If None, uses current thread-local registry.
            max_critical_issues: Maximum number of critical issues to include
                in summary reports (default: 10)
            additional_suspicious_variables: Extra variable names to add to
                the default suspicious variables set.
            additional_hardcoded_patterns: Extra patterns to add to the default
                hardcoded value patterns list.
            additional_robot_patterns: Extra patterns to add to the default
                Robot Framework patterns list.
            additional_safe_keywords: Extra keywords to add to the default
                safe keywords set for false positive reduction.

        Example:
            # Use defaults:
            scanner = TemplateSecurityScanner()

            # Extend defaults with additional patterns:
            scanner = TemplateSecurityScanner(
                additional_suspicious_variables={"my_secret_var"},
                additional_hardcoded_patterns=[
                    {
                        "name": "custom_token",
                        "pattern": r"CUSTOM_[A-Z0-9]{32}",
                        "severity": "high",
                        "description": "Custom token detected",
                        "remediation": "Use environment variables",
                    }
                ],
                additional_safe_keywords={"mycompany_test"},
            )
        """
        self.credential_registry = credential_registry or get_current_registry()
        self.security_validator = security_validator or SecurityValidator()
        self.max_critical_issues = max_critical_issues

        # Load configurable patterns
        self._suspicious_variables = ScannerPatterns.get_suspicious_variables(
            additional_suspicious_variables
        )
        self._hardcoded_patterns = ScannerPatterns.get_hardcoded_patterns(
            additional_hardcoded_patterns
        )
        self._robot_patterns = ScannerPatterns.get_robot_patterns(
            additional_robot_patterns
        )
        self._safe_keywords = ScannerPatterns.get_safe_keywords(
            additional_safe_keywords
        )
        self._placeholder_indicators = ScannerPatterns.PLACEHOLDER_INDICATORS

    def scan_template_file(
        self, file_path: Path | str, min_confidence: float = 0.7
    ) -> TemplateSecurityReport:
        """Scan a single template file for security issues.

        Args:
            file_path: Path to template file
            min_confidence: Minimum confidence threshold for pattern matching

        Returns:
            TemplateSecurityReport with all found issues
        """
        start_time = time.time()
        file_path = Path(file_path)

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            file_hash = hashlib.blake2b(
                content.encode("utf-8"), digest_size=32
            ).hexdigest()

            issues = self._scan_content(content, str(file_path))

            scan_duration = time.time() - start_time

            # Build report statistics
            issues_by_severity, issues_by_type = build_report_statistics(issues)

            # Determine if file is safe
            is_safe = determine_safety(issues_by_severity, issues_by_type)

            return TemplateSecurityReport(
                file_path=str(file_path),
                scan_timestamp=start_time,
                scan_duration=scan_duration,
                issues=issues,
                total_issues=len(issues),
                issues_by_severity=issues_by_severity,
                issues_by_type=issues_by_type,
                is_safe=is_safe,
                file_hash=file_hash,
                statistics={
                    "suspicious_variables_found": issues_by_type.get(
                        "suspicious_variable", 0
                    ),
                    "hardcoded_credentials_found": issues_by_type.get("credential", 0),
                    "patterns_detected": issues_by_type.get("pattern", 0),
                    "total_patterns_available": len(
                        self.credential_registry.get_all_patterns()
                    ),
                },
            )

        except Exception as exc:
            logger.error("Failed to scan template file %s: %s", file_path, exc)
            return TemplateSecurityReport(
                file_path=str(file_path),
                scan_timestamp=start_time,
                scan_duration=time.time() - start_time,
                issues=[],
                total_issues=0,
                issues_by_severity={},
                issues_by_type={},
                is_safe=False,
                file_hash="",
                statistics={"error": str(exc)},
            )

    def scan_template_directory(
        self,
        directory_path: Path | str,
        file_extensions: list[str] | None = None,
        min_confidence: float = 0.7,
    ) -> list[TemplateSecurityReport]:
        """Scan all template files in a directory.

        Args:
            directory_path: Path to directory containing templates
            file_extensions: List of file extensions to scan
            min_confidence: Minimum confidence threshold

        Returns:
            List of TemplateSecurityReport objects
        """
        directory_path = Path(directory_path)
        if file_extensions is None:
            file_extensions = [".robot", ".txt", ".template"]

        reports = []

        try:
            for file_path in directory_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                    report = self.scan_template_file(file_path, min_confidence)
                    reports.append(report)

        except Exception as exc:
            logger.error("Failed to scan directory %s: %s", directory_path, exc)

        return reports

    def _scan_content(self, content: str, file_path: str) -> list[SecurityIssue]:
        """Scan content for security issues.

        Args:
            content: File content to scan
            file_path: Path to the file being scanned

        Returns:
            List of SecurityIssue objects
        """
        issues: list[SecurityIssue] = []
        lines = content.split("\n")

        # 1. Scan for credential patterns
        credential_issues = scan_for_credentials(
            content,
            file_path,
            self.credential_registry,
            self._safe_keywords,
            get_context,
        )
        issues.extend(credential_issues)

        # 2. Scan for suspicious variables
        variable_issues = scan_for_suspicious_variables(
            content,
            file_path,
            lines,
            self._suspicious_variables,
            self._safe_keywords,
            self._placeholder_indicators,
        )
        issues.extend(variable_issues)

        # 3. Scan for hardcoded patterns
        hardcoded_issues = scan_for_hardcoded_patterns(
            content,
            file_path,
            lines,
            self._hardcoded_patterns,
            self._safe_keywords,
        )
        issues.extend(hardcoded_issues)

        # 4. Scan for Robot Framework specific issues
        robot_issues = scan_for_robot_framework_issues(
            content,
            file_path,
            lines,
            self._robot_patterns,
        )
        issues.extend(robot_issues)

        # Remove duplicates and sort
        unique_issues = deduplicate_issues(issues)
        unique_issues.sort(key=lambda i: (i.line_number, i.column_number))

        return unique_issues

    def generate_summary_report(
        self,
        reports: list[TemplateSecurityReport],
        max_critical_issues: int | None = None,
    ) -> dict[str, Any]:
        """Generate a summary report from multiple scan reports.

        Args:
            reports: List of TemplateSecurityReport objects
            max_critical_issues: Maximum number of critical issues to include
                in the report (default: uses instance max_critical_issues)

        Returns:
            Summary report dictionary
        """
        # Use provided parameter or fall back to instance setting
        limit = (
            max_critical_issues
            if max_critical_issues is not None
            else self.max_critical_issues
        )

        total_files = len(reports)
        total_issues = sum(r.total_issues for r in reports)
        safe_files = sum(1 for r in reports if r.is_safe)
        unsafe_files = total_files - safe_files

        # Aggregate issues by severity and type
        all_issues_by_severity, all_issues_by_type = aggregate_reports(reports)

        # Find most critical issues
        critical_issues: list[SecurityIssue] = []
        for report in reports:
            critical_issues.extend(
                [i for i in report.issues if i.severity == "critical"]
            )

        critical_issues.sort(key=lambda i: i.confidence, reverse=True)

        return {
            "scan_summary": {
                "total_files_scanned": total_files,
                "total_issues_found": total_issues,
                "safe_files": safe_files,
                "unsafe_files": unsafe_files,
                "scan_pass_rate": (safe_files / total_files * 100)
                if total_files > 0
                else 0,
            },
            "issue_summary": {
                "by_severity": all_issues_by_severity,
                "by_type": all_issues_by_type,
            },
            "critical_issues": critical_issues[:limit],  # Top X most critical
            "recommendations": generate_recommendations(all_issues_by_type),
        }


# Convenience helper for quick template scanning
def scan_template_file_for_security(
    file_path: Path | str, min_confidence: float = 0.7
) -> TemplateSecurityReport:
    """Scan a template file for security issues.

    Args:
        file_path: Path to template file
        min_confidence: Minimum confidence threshold

    Returns:
        TemplateSecurityReport with scan results
    """
    scanner = TemplateSecurityScanner()
    return scanner.scan_template_file(file_path, min_confidence)
