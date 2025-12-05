"""Security recommendations and guidelines.

Provides security guidelines for SSH, database, web operations,
and general test automation security.
"""

from typing import Any

from importobot.utils.string_cache import data_to_lower_cached

SSH_SECURITY_GUIDELINES = [
    "SSH Security Guidelines for Test Automation:",
    "• Use key-based authentication instead of passwords",
    "• Implement connection timeouts (default: 30 seconds)",
    "• Validate host key fingerprints in production",
    "• Use dedicated test environments, not production systems",
    "• Limit SSH user privileges to minimum required",
    "• Log all SSH operations for audit trails",
    "• Never hardcode credentials in test scripts",
    "• Use environment variables or secure vaults for secrets",
    "• Implement proper error handling to avoid information disclosure",
    "• Regular security audits of SSH configurations",
    "• Monitor for unusual SSH activity patterns",
    "• Implement continuous monitoring and alerting",
    "• Restrict network access to SSH services",
    "• Use strong encryption algorithms and key sizes",
]


def get_ssh_security_guidelines() -> list[str]:
    """Get SSH security guidelines for test automation.

    Returns:
        List of SSH security guideline strings
    """
    return [
        "SSH Security Guidelines:",
        "• Use key-based authentication instead of passwords",
        "• Implement connection timeouts (default: 30 seconds)",
        "• Validate host key fingerprints",
        "• Use dedicated test environments",
        "• Limit SSH user privileges to minimum required",
        "• Log all SSH operations for audit trails",
        "• Never hardcode credentials in test scripts",
        "• Use environment variables or secure vaults for secrets",
        "• Implement proper error handling to avoid information disclosure",
        "• Regular security audits of SSH configurations",
        "• Monitor for unusual SSH activity patterns",
        "• Implement continuous monitoring and alerting",
        "• Restrict network access to SSH services",
        "• Use strong encryption algorithms and key sizes",
    ]


def generate_security_recommendations(test_data: dict[str, Any]) -> list[str]:
    """Generate security recommendations for test case.

    Analyzes test data and generates relevant security recommendations
    based on detected operation types (SSH, database, web).

    Args:
        test_data: Dictionary containing test case data

    Returns:
        List of security recommendation strings
    """
    recommendations = []

    # Check for SSH usage
    if any(
        "ssh" in data_to_lower_cached(value) or "ssh" in key.lower()
        for key, value in test_data.items()
    ):
        recommendations.extend(
            [
                "Use key-based authentication instead of passwords for SSH",
                "Implement connection timeouts for SSH operations",
                "Use dedicated test environments, not production systems",
                "Validate host key fingerprints in automated tests",
            ]
        )

    # Check for database operations
    if any(
        "database" in data_to_lower_cached(value)
        or "sql" in data_to_lower_cached(value)
        or "select" in data_to_lower_cached(value)
        or "insert" in data_to_lower_cached(value)
        or "update" in data_to_lower_cached(value)
        or "delete" in data_to_lower_cached(value)
        or "database" in key.lower()
        or "query" in key.lower()
        for key, value in test_data.items()
    ):
        recommendations.extend(
            [
                "Use parameterized queries to prevent SQL injection",
                "Test with minimal database privileges",
                "Sanitize all user inputs in database tests",
            ]
        )

    # Check for web operations
    if any(
        "browser" in data_to_lower_cached(value)
        or "web" in data_to_lower_cached(value)
        or "browser" in key.lower()
        or "url" in key.lower()
        for key, value in test_data.items()
    ):
        recommendations.extend(
            [
                "TIP: Validate all form inputs for XSS prevention",
                "TIP: Test authentication and authorization flows",
                "TIP: Use secure test data, avoid production credentials",
            ]
        )

    return recommendations


def extract_security_warnings(keyword_info: dict[str, Any]) -> list[str]:
    """Extract security warnings from keyword information.

    Args:
        keyword_info: Dictionary containing keyword information

    Returns:
        List of security warnings and notes
    """
    warnings = []
    if "security_warning" in keyword_info:
        warnings.append(keyword_info["security_warning"])
    if "security_note" in keyword_info:
        warnings.append(keyword_info["security_note"])
    return warnings


# Internal utility - not part of public API
__all__: list[str] = []
