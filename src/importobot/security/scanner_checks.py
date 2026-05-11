"""Scan functions for template security scanning.

Individual scan functions for detecting credentials, suspicious variables,
hardcoded patterns, and Robot Framework-specific security issues.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from importobot.security.scanner_types import SecurityIssue

if TYPE_CHECKING:
    from importobot.security.credential_patterns import CredentialPatternRegistry


def scan_for_credentials(
    content: str,
    file_path: str,
    credential_registry: CredentialPatternRegistry,
    safe_keywords: set[str],
    get_context_fn: Any,
) -> list[SecurityIssue]:
    """Scan content for credential patterns.

    Args:
        content: Content to scan
        file_path: File being scanned
        credential_registry: Registry of credential patterns
        safe_keywords: Set of keywords indicating safe content
        get_context_fn: Function to get context around a match

    Returns:
        List of SecurityIssue objects
    """
    issues = []
    matches = credential_registry.search_text(content, min_confidence=0.7)

    for match in matches:
        # Check if this is likely a false positive (safe keywords)
        if _is_false_positive(match["match_text"], safe_keywords):
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
            context=get_context_fn(content, match["line_number"]),
            rule_id=f"CRED_{credential_type}_{adjusted_severity}",
        )
        issues.append(issue)

    return issues


def scan_for_suspicious_variables(
    content: str,
    file_path: str,
    lines: list[str],
    suspicious_variables: set[str],
    safe_keywords: set[str],
    placeholder_indicators: tuple[str, ...],
) -> list[SecurityIssue]:
    """Scan for suspicious variable names.

    Args:
        content: Content to scan
        file_path: File being scanned
        lines: Lines of content
        suspicious_variables: Set of suspicious variable names
        safe_keywords: Set of keywords indicating safe content
        placeholder_indicators: Tuple of strings indicating placeholder content

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
                if _is_suspicious_variable(var_name, suspicious_variables):
                    # Enhanced false positive reduction for variables
                    value_start = match.end()
                    remaining_line = line[value_start:]

                    # Check for false positive indicators in the context
                    # Use more limited context to avoid false positives from section
                    # headers
                    context_lines = []
                    # Add a few lines around, but avoid section headers
                    for i in range(max(0, line_num - 1), min(len(lines), line_num + 2)):
                        line_content = lines[i].strip()
                        # Skip section headers (lines that start and end with ***)
                        starts_with_stars = line_content.startswith("***")
                        ends_with_stars = line_content.endswith("***")
                        is_section_header = starts_with_stars and ends_with_stars
                        if not is_section_header:
                            context_lines.append(line_content)

                    limited_context = " ".join(context_lines)
                    is_safe_remaining = _contains_safe_keywords(
                        remaining_line, safe_keywords
                    )
                    is_placeholder = _is_placeholder_context(
                        limited_context, placeholder_indicators
                    )
                    if is_safe_remaining or is_placeholder:
                        continue

                    severity = _get_variable_severity(var_name)

                    # Reduce severity for likely placeholder variables
                    if _is_placeholder_context(limited_context, placeholder_indicators):
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


def scan_for_hardcoded_patterns(
    content: str,
    file_path: str,
    lines: list[str],
    hardcoded_patterns: list[dict[str, Any]],
    safe_keywords: set[str],
) -> list[SecurityIssue]:
    """Scan for hardcoded value patterns.

    Args:
        content: Content to scan
        file_path: File being scanned
        lines: Lines of content
        hardcoded_patterns: List of pattern dictionaries
        safe_keywords: Set of keywords indicating safe content

    Returns:
        List of SecurityIssue objects
    """
    issues = []

    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()
        comment_text = ""
        if "#" in line_lower:
            comment_text = line_lower.split("#", 1)[1]

        for pattern_config in hardcoded_patterns:
            matches = re.finditer(pattern_config["pattern"], line)
            for match in matches:
                # Check if this is likely a false positive
                if _is_false_positive(match.group(0), safe_keywords):
                    continue
                if comment_text and any(
                    keyword in comment_text for keyword in safe_keywords
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


def scan_for_robot_framework_issues(
    content: str,
    file_path: str,
    lines: list[str],
    robot_patterns: list[dict[str, Any]],
) -> list[SecurityIssue]:
    """Scan for Robot Framework specific security issues.

    Args:
        content: Content to scan
        file_path: File being scanned
        lines: Lines of content
        robot_patterns: List of Robot Framework-specific pattern dictionaries

    Returns:
        List of SecurityIssue objects
    """
    issues = []

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


# =============================================================================
# HELPER FUNCTIONS (used internally by scan functions)
# =============================================================================


def _is_false_positive(text: str, safe_keywords: set[str]) -> bool:
    """Check if a match is likely a false positive.

    Args:
        text: Text to check
        safe_keywords: Set of safe keywords

    Returns:
        True if likely a false positive
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in safe_keywords)


def _contains_safe_keywords(text: str, safe_keywords: set[str]) -> bool:
    """Check if text contains safe keywords.

    Args:
        text: Text to check
        safe_keywords: Set of safe keywords

    Returns:
        True if safe keywords are present
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in safe_keywords)


def _is_placeholder_context(
    context: str, placeholder_indicators: tuple[str, ...]
) -> bool:
    """Check if the context indicates placeholder/example content.

    Args:
        context: Text context around the match
        placeholder_indicators: Tuple of strings indicating placeholder content

    Returns:
        True if context suggests placeholder content
    """
    context_lower = context.lower()
    return any(indicator in context_lower for indicator in placeholder_indicators)


def _is_suspicious_variable(var_name: str, suspicious_variables: set[str]) -> bool:
    """Determine whether a variable name is suspicious.

    Args:
        var_name: Variable name to check
        suspicious_variables: Set of suspicious variable names

    Returns:
        True if the variable name is suspicious
    """
    substrings = (
        "password",
        "secret",
        "token",
        "apikey",
        "api_key",
        "credential",
        "key",
    )
    return var_name in suspicious_variables or any(
        substring in var_name for substring in substrings
    )


def _get_variable_severity(var_name: str) -> str:
    """Get severity level for a suspicious variable.

    Args:
        var_name: Variable name to assess

    Returns:
        Severity level string ("low", "medium", "high", "critical")
    """
    # Import here to avoid circular dependency
    from importobot.security.scanner_patterns import (  # noqa: PLC0415
        CRITICAL_SEVERITY_VARIABLES,
        HIGH_SEVERITY_VARIABLES,
    )

    var_name_lower = var_name.lower()
    if var_name_lower in CRITICAL_SEVERITY_VARIABLES:
        return "critical"
    elif var_name_lower in HIGH_SEVERITY_VARIABLES:
        return "high"
    else:
        return "medium"


# Internal utility - not part of public API
__all__: list[str] = []
