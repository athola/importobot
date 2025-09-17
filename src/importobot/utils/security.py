"""Security utilities for test generation and Robot Framework operations."""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validates and sanitizes test parameters for security concerns."""

    # Dangerous command patterns that should be flagged
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"sudo\s+",
        r"chmod\s+777",
        r">\s*/dev/null",
        r"\|\s*sh",
        r"\|\s*bash",
        r"eval\s*\(",
        r"exec\s*\(",
        r"`[^`]*`",  # Command substitution
        r"\$\([^)]*\)",  # Command substitution
        r"&&\s*rm",
        r";\s*rm",
        r"curl.*\|\s*sh",
        r"wget.*\|\s*sh",
    ]

    # Sensitive path patterns
    SENSITIVE_PATHS = [
        r"/etc/passwd",
        r"/etc/shadow",
        r"/home/[^/]+/\.ssh",
        r"\.aws/credentials",
        r"\.ssh/id_rsa",
        r"/root/",
        r"C:\\Windows\\System32",
        r"%USERPROFILE%",
    ]

    def validate_ssh_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate SSH operation parameters for security issues."""
        warnings = []

        # Check for hardcoded credentials
        if "password" in parameters:
            warnings.append(
                "⚠️  SSH password found - consider using key-based authentication"
            )

        # Check for dangerous commands
        if "command" in parameters:
            command = str(parameters["command"])
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    warnings.append(
                        f"⚠️  Potentially dangerous command pattern detected: {pattern}"
                    )

        # Check for sensitive file paths
        for key, value in parameters.items():
            if isinstance(value, str):
                for pattern in self.SENSITIVE_PATHS:
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append(
                            f"⚠️  Sensitive path detected in {key}: {pattern}"
                        )

        # Check for production indicators
        if any(
            env in str(parameters).lower() for env in ["prod", "production", "live"]
        ):
            warnings.append(
                "⚠️  Production environment detected - ensure proper authorization"
            )

        return warnings

    def sanitize_command_parameters(self, command: str) -> str:
        """Sanitize command parameters to prevent injection attacks."""
        if not isinstance(command, str):
            return str(command)

        # Remove potentially dangerous characters and patterns
        sanitized = command

        # Escape shell metacharacters
        dangerous_chars = ["|", "&", ";", "$(", "`", ">", "<", "*", "?", "[", "]"]
        for char in dangerous_chars:
            if char in sanitized:
                logger.warning(
                    "Potentially dangerous character '%s' found in command, escaping",
                    char,
                )
                sanitized = sanitized.replace(char, f"\\{char}")

        return sanitized

    def validate_file_operations(self, file_path: str, operation: str) -> List[str]:
        """Validate file operations for security concerns."""
        warnings = []

        # Check for path traversal attempts
        if ".." in file_path or "//" in file_path:
            warnings.append("⚠️  Potential path traversal detected in file path")

        # Check for sensitive file access
        for pattern in self.SENSITIVE_PATHS:
            if re.search(pattern, file_path, re.IGNORECASE):
                warnings.append(f"⚠️  Sensitive file access detected: {file_path}")

        # Warn about destructive operations
        if operation.lower() in ["delete", "remove", "truncate", "drop"]:
            warnings.append(
                f"⚠️  Destructive operation '{operation}' - ensure proper safeguards"
            )

        return warnings

    def sanitize_error_message(self, error_msg: str) -> str:
        """Sanitize error messages to prevent information disclosure."""
        if not isinstance(error_msg, str):
            return str(error_msg)

        sanitized = error_msg

        # Remove sensitive path information
        sensitive_patterns = [
            (r"/home/[^/\s]+", "/home/[USER]"),
            (r"C:\\Users\\[^\\]+", "C:\\Users\\[USER]"),
            (r"/Users/[^/\s]+", "/Users/[USER]"),
            (r"(/[^/\s]*){3,}", "[PATH]"),  # Long absolute paths
            (r"[a-zA-Z]:\\[^\\]+\\[^\\]+\\[^\\]+", "[PATH]"),  # Long Windows paths
        ]

        for pattern, replacement in sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    def generate_security_recommendations(self, test_data: Dict[str, Any]) -> List[str]:
        """Generate security recommendations for test case."""
        recommendations = []

        # Check for SSH usage
        if any("ssh" in str(value).lower() for value in test_data.values()):
            recommendations.extend(
                [
                    "💡 Use key-based authentication instead of passwords for SSH",
                    "💡 Implement connection timeouts for SSH operations",
                    "💡 Use dedicated test environments, not production systems",
                    "💡 Validate host key fingerprints in automated tests",
                ]
            )

        # Check for database operations
        if any(
            "database" in str(value).lower() or "sql" in str(value).lower()
            for value in test_data.values()
        ):
            recommendations.extend(
                [
                    "💡 Use parameterized queries to prevent SQL injection",
                    "💡 Test with minimal database privileges",
                    "💡 Sanitize all user inputs in database tests",
                ]
            )

        # Check for web operations
        if any(
            "browser" in str(value).lower() or "web" in str(value).lower()
            for value in test_data.values()
        ):
            recommendations.extend(
                [
                    "💡 Validate all form inputs for XSS prevention",
                    "💡 Test authentication and authorization flows",
                    "💡 Use secure test data, avoid production credentials",
                ]
            )

        return recommendations


def validate_test_security(test_case: Dict[str, Any]) -> Dict[str, List[str]]:
    """Comprehensive security validation for test cases."""
    validator = SecurityValidator()
    results: Dict[str, List[str]] = {
        "warnings": [],
        "recommendations": [],
        "sanitized_errors": [],
    }

    # Validate SSH operations
    if "ssh" in str(test_case).lower():
        ssh_warnings = validator.validate_ssh_parameters(test_case)
        results["warnings"].extend(ssh_warnings)

    # Generate security recommendations
    recommendations = validator.generate_security_recommendations(test_case)
    results["recommendations"].extend(recommendations)

    # Log security analysis
    if results["warnings"]:
        logger.warning(
            "Security warnings for test case: %d issues found", len(results["warnings"])
        )

    return results


def get_ssh_security_guidelines() -> List[str]:
    """Get SSH security guidelines for test automation."""
    return [
        "🔒 SSH Security Guidelines:",
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
    ]


# Shared SSH security guidelines constant
SSH_SECURITY_GUIDELINES = [
    "🔒 SSH Security Guidelines for Test Automation:",
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
]


def extract_security_warnings(keyword_info: Dict[str, Any]) -> List[str]:
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
