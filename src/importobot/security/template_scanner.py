"""Template security scanner for `--robot-template` workflows.

Scans Robot Framework templates for leaked credentials, suspicious variables,
and other issues before they reach the converter.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from importobot.security.credential_patterns import get_credential_registry
from importobot.security.security_validator import SecurityValidator
from importobot.utils.logging import get_logger

logger = get_logger()


@dataclass
class SecurityIssue:
    """Represents a security issue found in a template file."""

    issue_type: str  # "credential", "suspicious_variable", "hardcoded_value", "pattern"
    severity: str  # "low", "medium", "high", "critical"
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
    """Comprehensive security report for template scanning."""

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


class TemplateSecurityScanner:
    """Security scanner for Robot Framework template files.

    Detects hard-coded credentials, suspicious variable names, insecure
    patterns, configuration issues, and authentication risks before conversion.
    """

    def __init__(self, security_validator: SecurityValidator | None = None):
        """Initialize the template security scanner.

        Args:
            security_validator: Optional security validator instance
        """
        self.credential_registry = get_credential_registry()
        self.security_validator = security_validator or SecurityValidator()
        self._suspicious_variables = self._load_suspicious_variables()
        self._hardcoded_patterns = self._load_hardcoded_patterns()
        self._safe_keywords = self._load_safe_keywords()

    def _load_suspicious_variables(self) -> set[str]:
        """Load suspicious variable names to detect.

        Returns:
            Set of suspicious variable names
        """
        suspicious_vars = {
            # Credential-related variables
            "password",
            "pwd",
            "passwd",
            "secret",
            "token",
            "key",
            "apikey",
            "api_key",
            "auth_token",
            "access_token",
            "refresh_token",
            "bearer_token",
            "client_secret",
            "client_id",
            "oauth_token",
            "jwt_secret",
            # Database-related
            "db_password",
            "db_user",
            "db_host",
            "database_password",
            "db_conn",
            "mysql_password",
            "postgres_password",
            "redis_password",
            # API-related
            "api_username",
            "api_password",
            "api_secret",
            "webhook_secret",
            "webhook_url",
            # Cloud service credentials
            "aws_key",
            "aws_secret",
            "aws_token",
            "azure_key",
            "gcp_key",
            "service_account_key",
            "subscription_key",
            # Security-related
            "encryption_key",
            "secret_key",
            "private_key",
            "public_key",
            "ssh_key",
            "ssl_certificate",
            "ssl_key",
            # Infrastructure
            "admin_password",
            "root_password",
            "sa_password",
        }

        # Add common variations and case-insensitive matches
        all_vars = set(suspicious_vars)
        for var in suspicious_vars:
            all_vars.add(var.upper())
            all_vars.add(var.lower())
            # Add variations with underscores and hyphens
            all_vars.add(var.replace("_", "-"))
            all_vars.add(var.replace("-", "_"))

        return all_vars

    def _load_hardcoded_patterns(self) -> list[dict[str, Any]]:
        """Load patterns for detecting hardcoded values.

        Returns:
            List of pattern dictionaries
        """
        return [
            {
                "name": "hardcoded_password",
                "pattern": (
                    r"(?i)\b(password|pwd|passwd)\s*[:=]\s*"
                    r'(?:"[^"\r\n]+?"|\'[^\']+\'|[^\s]+)'
                ),
                "severity": "critical",
                "description": "Hardcoded password detected",
                "remediation": "Use environment variables or credential manager",
            },
            {
                "name": "hardcoded_api_key",
                "pattern": (
                    r"(?i)\b(api[_-]?key|apikey)\s*[:=]\s*(?:['\"]?[a-zA-Z0-9_\-]{6,}['\"]?)"
                ),
                "severity": "high",
                "description": "Hardcoded API key detected",
                "remediation": "Use secure key management service",
            },
            {
                "name": "hardcoded_secret",
                "pattern": (
                    r"(?i)\b(secret|token|key)\s*[:=]\s*(?:['\"]?[a-zA-Z0-9_\-]{6,}['\"]?)"
                ),
                "severity": "high",
                "description": "Hardcoded secret/token detected",
                "remediation": "Use environment variables or secret manager",
            },
            {
                "name": "connection_string",
                "pattern": r"(?i)(?:mongodb|redis|postgres|mysql)://[^:]+:[^@]+@",
                "severity": "critical",
                "description": "Database connection string with credentials",
                "remediation": "Use separate credential management",
            },
            {
                "name": "jwt_token",
                "pattern": (
                    r"eyJ[a-zA-Z0-9_-]{6,}(?:\.[a-zA-Z0-9_-]{6,}){0,2}(?:\.\.\.)?"
                ),
                "severity": "high",
                "description": "Hardcoded JWT token detected",
                "remediation": "Use dynamic token retrieval",
            },
            {
                "name": "private_key",
                "pattern": r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
                "severity": "critical",
                "description": "Hardcoded private key detected",
                "remediation": "Move to HSM or key management service",
            },
        ]

    def _load_safe_keywords(self) -> set[str]:
        """Load keywords that indicate safe content.

        Returns:
            Set of safe keywords
        """
        return {
            "example",
            "test",
            "demo",
            "sample",
            "mock",
            "placeholder",
            "template",
            "dummy",
            "fake",
            "stub",
            "your",
            "xxx",
            "yyy",
            "zzz",
            "foo",
            "bar",
            "baz",
            "qux",
        }

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
            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            issues = self._scan_content(content, str(file_path))

            scan_duration = time.time() - start_time

            # Build report statistics
            issues_by_severity: dict[str, int] = {}
            issues_by_type: dict[str, int] = {}
            for issue in issues:
                issues_by_severity[issue.severity] = (
                    issues_by_severity.get(issue.severity, 0) + 1
                )
                issues_by_type[issue.issue_type] = (
                    issues_by_type.get(issue.issue_type, 0) + 1
                )

            # Determine if file is safe
            critical_high_count = issues_by_severity.get(
                "critical", 0
            ) + issues_by_severity.get("high", 0)
            credential_issues = issues_by_type.get("credential", 0)
            hardcoded_issues = issues_by_type.get("hardcoded_value", 0)
            is_safe = (
                critical_high_count == 0
                and credential_issues == 0
                and hardcoded_issues == 0
            )

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
        issues = []
        lines = content.split("\n")

        # 1. Scan for credential patterns
        credential_issues = self._scan_for_credentials(content, file_path)
        issues.extend(credential_issues)

        # 2. Scan for suspicious variables
        variable_issues = self._scan_for_suspicious_variables(content, file_path, lines)
        issues.extend(variable_issues)

        # 3. Scan for hardcoded patterns
        hardcoded_issues = self._scan_for_hardcoded_patterns(content, file_path, lines)
        issues.extend(hardcoded_issues)

        # 4. Scan for Robot Framework specific issues
        robot_issues = self._scan_for_robot_framework_issues(content, file_path, lines)
        issues.extend(robot_issues)

        # Remove duplicates and sort
        unique_issues = self._deduplicate_issues(issues)
        unique_issues.sort(key=lambda i: (i.line_number, i.column_number))

        return unique_issues

    def _scan_for_credentials(
        self, content: str, file_path: str
    ) -> list[SecurityIssue]:
        """Scan content for credential patterns.

        Args:
            content: Content to scan
            file_path: File being scanned

        Returns:
            List of SecurityIssue objects
        """
        issues = []
        matches = self.credential_registry.search_text(content, min_confidence=0.7)

        for match in matches:
            # Check if this is likely a false positive (safe keywords)
            if self._is_false_positive(match["match_text"]):
                continue

            credential_type = match["credential_type"].upper()
            base_severity = match.get("severity", "HIGH").upper()
            confidence = match["confidence"]

            # Adjust severity based on confidence (false positive reduction)
            if confidence < 0.4:
                adjusted_severity = "LOW"
            elif confidence < 0.6:
                adjusted_severity = "MEDIUM"
            else:
                adjusted_severity = base_severity

            issue = SecurityIssue(
                issue_type="credential",
                severity=adjusted_severity,
                file_path=file_path,
                line_number=match["line_number"],
                column_number=match["start_pos"]
                - content.rfind("\n", 0, match["start_pos"]),
                description=match["pattern"],
                match_text=match["match_text"],
                confidence=match["confidence"],
                remediation=match["remediation"],
                context=self._get_context(content, match["line_number"]),
                rule_id=f"CRED_{credential_type}_{adjusted_severity}",
            )
            issues.append(issue)

        return issues

    def _scan_for_suspicious_variables(
        self, content: str, file_path: str, lines: list[str]
    ) -> list[SecurityIssue]:
        """Scan for suspicious variable names.

        Args:
            content: Content to scan
            file_path: File being scanned
            lines: Lines of content

        Returns:
            List of SecurityIssue objects
        """
        issues = []

        # Robot Framework variable patterns
        variable_patterns = [
            r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}",  # ${VARIABLE}
            r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\s+",  # ${VARIABLE} with following content
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=",  # VARIABLE = value
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern in variable_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    var_name = match.group(1).lower()

                    # Check if variable name is suspicious
                    if self._is_suspicious_variable(var_name):
                        # Enhanced false positive reduction for variables
                        value_start = match.end()
                        remaining_line = line[value_start:]

                        # Check for false positive indicators in the context
                        # Use more limited context to avoid false positives from section
                        # headers
                        context_lines = []
                        # Add a few lines around, but avoid section headers
                        for i in range(max(0, line_num-1), min(len(lines), line_num+2)):
                            line_content = lines[i].strip()
                            # Skip section headers (lines that start and end with ***)
                            starts_with_stars = line_content.startswith('***')
                            ends_with_stars = line_content.endswith('***')
                            is_section_header = starts_with_stars and ends_with_stars
                            if not is_section_header:
                                context_lines.append(line_content)

                        limited_context = " ".join(context_lines)
                        if (
                            self._contains_safe_keywords(remaining_line)
                            or self._is_placeholder_context(limited_context)
                        ):
                            continue

                        severity = self._get_variable_severity(var_name)

                        # Reduce severity for likely placeholder variables
                        if self._is_placeholder_context(limited_context):
                            severity = "low"
                            confidence = 0.3
                        else:
                            confidence = 0.8

                        issue = SecurityIssue(
                            issue_type="suspicious_variable",
                            severity=severity,
                            file_path=file_path,
                            line_number=line_num,
                            column_number=match.start(),
                            description=f"Suspicious variable name: {var_name}",
                            match_text=match.group(0),
                            confidence=confidence,
                            remediation=(
                                "Use generic variable names or load from environment"
                            ),
                            context=line.strip(),
                            rule_id=f"SUSPICIOUS_VAR_{var_name.upper()}",
                        )
                        issues.append(issue)

        return issues

    def _scan_for_hardcoded_patterns(
        self, content: str, file_path: str, lines: list[str]
    ) -> list[SecurityIssue]:
        """Scan for hardcoded value patterns.

        Args:
            content: Content to scan
            file_path: File being scanned
            lines: Lines of content

        Returns:
            List of SecurityIssue objects
        """
        issues = []

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            comment_text = ""
            if "#" in line_lower:
                comment_text = line_lower.split("#", 1)[1]

            for pattern_config in self._hardcoded_patterns:
                matches = re.finditer(pattern_config["pattern"], line)
                for match in matches:
                    # Check if this is likely a false positive
                    if self._is_false_positive(match.group(0)):
                        continue
                    if comment_text and any(
                        keyword in comment_text for keyword in self._safe_keywords
                    ):
                        continue

                    issue = SecurityIssue(
                        issue_type="hardcoded_value",
                        severity=pattern_config["severity"],
                        file_path=file_path,
                        line_number=line_num,
                        column_number=match.start(),
                        description=pattern_config["description"],
                        match_text=match.group(0),
                        confidence=0.9,
                        remediation=pattern_config["remediation"],
                        context=line.strip(),
                        rule_id=f"HARDCODED_{pattern_config['name'].upper()}",
                    )
                    issues.append(issue)

        return issues

    def _scan_for_robot_framework_issues(
        self, content: str, file_path: str, lines: list[str]
    ) -> list[SecurityIssue]:
        """Scan for Robot Framework specific security issues.

        Args:
            content: Content to scan
            file_path: File being scanned
            lines: Lines of content

        Returns:
            List of SecurityIssue objects
        """
        issues = []

        robot_patterns = [
            {
                "name": "credentials_in_variables_section",
                "pattern": r"^\*\*\* Variables \*\*\*$",
                "severity": "medium",
                "description": (
                    "Credentials in Variables section - should use environment "
                    "variables"
                ),
                "remediation": (
                    "Move credentials to environment variables or secure storage"
                ),
            },
            {
                "name": "insecure_library_import",
                "pattern": r"(?i)Library\s+(?:SeleniumLibrary|RequestsLibrary).*",
                "severity": "low",
                "description": "Potentially insecure library import",
                "remediation": "Review library usage and ensure secure configuration",
            },
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern_config in robot_patterns:
                if re.search(pattern_config["pattern"], line):
                    issue = SecurityIssue(
                        issue_type="pattern",
                        severity=pattern_config["severity"],
                        file_path=file_path,
                        line_number=line_num,
                        column_number=0,
                        description=pattern_config["description"],
                        match_text=line.strip(),
                        confidence=0.7,
                        remediation=pattern_config["remediation"],
                        context=line.strip(),
                        rule_id=f"ROBOT_{pattern_config['name'].upper()}",
                    )
                    issues.append(issue)

        return issues

    def _is_false_positive(self, text: str) -> bool:
        """Check if a match is likely a false positive.

        Args:
            text: Text to check

        Returns:
            True if likely a false positive
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self._safe_keywords)

    def _contains_safe_keywords(self, text: str) -> bool:
        """Check if text contains safe keywords.

        Args:
            text: Text to check

        Returns:
            True if safe keywords are present
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self._safe_keywords)

    def _is_placeholder_context(self, context: str) -> bool:
        """Check if the context indicates placeholder/example content.

        Args:
            context: Text context around the match

        Returns:
            True if context suggests placeholder content
        """
        context_lower = context.lower()
        placeholder_indicators = (
            "example ",
            "example_",
            "example-",
            "sample ",
            "sample_",
            "sample-",
            "demo ",
            "demo_",
            "demo-",
            "test ",
            "test_",
            "test-",
            "fake ",
            "fake_",
            "fake-",
            "dummy ",
            "dummy_",
            "dummy-",
            "placeholder",
            "replace_with",
            "your_",
            "placeholder_key",
            "use_env_variable_for",
            "# example",
            "# test",
            "# demo",
            "example only",
            "replace_with_actual",
        )
        return any(indicator in context_lower for indicator in placeholder_indicators)

    def _is_suspicious_variable(self, var_name: str) -> bool:
        """Determine whether a variable name is suspicious."""
        substrings = (
            "password",
            "secret",
            "token",
            "apikey",
            "api_key",
            "credential",
            "key",
        )
        return var_name in self._suspicious_variables or any(
            substring in var_name for substring in substrings
        )

    def _get_variable_severity(self, var_name: str) -> str:
        """Get severity level for a suspicious variable.

        Args:
            var_name: Variable name to assess

        Returns:
            Severity level string
        """
        high_severity_vars = {
            "password",
            "pwd",
            "passwd",
            "secret",
            "token",
            "key",
            "db_password",
            "mysql_password",
            "postgres_password",
        }

        critical_severity_vars = {
            "aws_key",
            "aws_secret",
            "azure_key",
            "gcp_key",
            "private_key",
            "ssh_key",
            "ssl_certificate",
        }

        var_name_lower = var_name.lower()
        if var_name_lower in critical_severity_vars:
            return "critical"
        elif var_name_lower in high_severity_vars:
            return "high"
        else:
            return "medium"

    def _get_context(
        self, content: str, line_number: int, context_lines: int = 3
    ) -> str:
        """Get context around a match.

        Args:
            content: Full content
            line_number: Line number of the match
            context_lines: Number of lines before and after to include

        Returns:
            Context string
        """
        lines = content.split("\n")
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        context_lines_list = lines[start:end]
        return "\n".join(
            f"{i + start + 1:3d}: {line}" for i, line in enumerate(context_lines_list)
        )

    def _deduplicate_issues(self, issues: list[SecurityIssue]) -> list[SecurityIssue]:
        """Remove duplicate issues.

        Args:
            issues: List of issues to deduplicate

        Returns:
            Deduplicated list of issues
        """
        seen = set()
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

    def generate_summary_report(
        self, reports: list[TemplateSecurityReport]
    ) -> dict[str, Any]:
        """Generate a summary report from multiple scan reports.

        Args:
            reports: List of TemplateSecurityReport objects

        Returns:
            Summary report dictionary
        """
        total_files = len(reports)
        total_issues = sum(r.total_issues for r in reports)
        safe_files = sum(1 for r in reports if r.is_safe)
        unsafe_files = total_files - safe_files

        # Aggregate issues by severity and type
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

        # Find most critical issues
        critical_issues = []
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
            "critical_issues": critical_issues[:10],  # Top 10 most critical
            "recommendations": self._generate_recommendations(all_issues_by_type),
        }

    def _generate_recommendations(self, issues_by_type: dict[str, int]) -> list[str]:
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
                "Review and fix Robot Framework patterns that may lead to "
                "security issues"
            )

        if not recommendations:
            recommendations.append(
                "No major security issues detected - continue following "
                "security best practices"
            )

        return recommendations


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
