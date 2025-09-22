"""Security utilities for test generation and Robot Framework operations."""

import logging
import re
from typing import Any

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
        # Additional dangerous patterns
        r"dd\s+if=.*of=/dev/",  # Disk dump operations
        r"mkfs\.",  # Format filesystem
        r"fdisk\s",  # Disk partitioning
        r":\(\)\{.*:\|:&.*\};:",  # Fork bomb pattern
        r"cat\s+/etc/shadow",  # Reading shadow file
        r">\s*/etc/passwd",  # Overwriting passwd
        r"/dev/sda",  # Direct disk access
        r"/dev/hda",  # Direct disk access
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

    def validate_ssh_parameters(self, parameters: dict[str, Any]) -> list[str]:
        """Validate SSH operation parameters for security issues."""
        warnings = []

        # Check for hardcoded credentials
        warnings.extend(self._check_hardcoded_credentials(parameters))

        # Check for exposed credential patterns in parameter values
        warnings.extend(self._check_credential_patterns(parameters))

        # Check for dangerous commands
        warnings.extend(self._check_dangerous_commands(parameters))

        # Check for injection patterns in all parameter values
        warnings.extend(self._check_injection_patterns(parameters))

        # Check for sensitive file paths and path traversal
        warnings.extend(self._check_sensitive_paths(parameters))

        # Check for production indicators
        warnings.extend(self._check_production_indicators(parameters))

        return warnings

    def _check_hardcoded_credentials(self, parameters: dict[str, Any]) -> list[str]:
        """Check for hardcoded credentials in parameters."""
        warnings = []

        if "password" in parameters:
            warnings.append(
                "⚠️  SSH password found - consider using key-based authentication"
            )
            # Also flag as credential exposure
            if (
                isinstance(parameters.get("password"), str)
                and len(parameters["password"]) > 1
            ):
                warnings.append(
                    "⚠️  Hardcoded credential detected - avoid exposing "
                    "secrets in test data"
                )

        return warnings

    def _check_credential_patterns(self, parameters: dict[str, Any]) -> list[str]:
        """Check for exposed credential patterns in parameter values."""
        warnings = []
        credential_patterns = [
            r"password.*[:\s]+\w{6,}",  # password: something
            r"secret.*[:\s]+\w{6,}",  # secret: something
            r"token.*[:\s]+\w{10,}",  # token: something
            r"key.*[:\s]+[\w/]{10,}",  # key: something
            r"hardcoded.*secret",  # hardcoded_secret_123
        ]

        for key, value in parameters.items():
            if isinstance(value, str):
                for pattern in credential_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append(
                            f"⚠️  Potential hardcoded credential exposure "
                            f"detected in {key}"
                        )
                        break

        return warnings

    def _check_dangerous_commands(self, parameters: dict[str, Any]) -> list[str]:
        """Check for dangerous command patterns."""
        warnings = []

        if "command" in parameters:
            command = str(parameters["command"])
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    warnings.append(
                        f"⚠️  Potentially dangerous command pattern detected: {pattern}"
                    )

        return warnings

    def _check_injection_patterns(self, parameters: dict[str, Any]) -> list[str]:
        """Check for injection patterns in parameter values."""
        warnings = []
        injection_patterns = [
            r";.*rm\s",
            r"`[^`]*`",
            r"\$\([^)]*\)",
            r"&&.*wget",
            r"\|\s*sh",
            r"'.*OR.*'",
            r"\".*OR.*\"",
            r"cat\s+/etc/",
            r"curl.*\|",
            r"wget.*\|",
            r"eval\s*\(",
            r"exec\s*\(",
        ]

        for key, value in parameters.items():
            if isinstance(value, str):
                for pattern in injection_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append(
                            f"⚠️  Potential injection pattern detected in {key}: "
                            f"suspicious command sequence"
                        )
                        break

        return warnings

    def _check_sensitive_paths(self, parameters: dict[str, Any]) -> list[str]:
        """Check for sensitive file paths and path traversal."""
        warnings = []

        for key, value in parameters.items():
            if isinstance(value, str) and (
                "path" in key.lower() or key in ["source_path", "destination_path"]
            ):
                # Check for path traversal using validate_file_operations
                file_warnings = self.validate_file_operations(value, "access")
                warnings.extend(file_warnings)

            if isinstance(value, str):
                for pattern in self.SENSITIVE_PATHS:
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append(
                            f"⚠️  Sensitive path detected in {key}: {pattern}"
                        )

        return warnings

    def _check_production_indicators(self, parameters: dict[str, Any]) -> list[str]:
        """Check for production environment indicators."""
        warnings = []

        if any(
            env in str(parameters).lower() for env in ["prod", "production", "live"]
        ):
            warnings.append(
                "⚠️  Production environment detected - ensure proper authorization"
            )

        return warnings

    def sanitize_command_parameters(self, command: Any) -> str:
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

    def validate_file_operations(self, file_path: str, operation: str) -> list[str]:
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

    def sanitize_error_message(self, error_msg: Any) -> str:
        """Sanitize error messages to prevent information disclosure."""
        if not isinstance(error_msg, str):
            return str(error_msg)

        sanitized = error_msg

        # Remove sensitive path information
        sensitive_patterns = [
            (r"/home/[^/\s]+", "/home/[USER]"),
            (r"C:\\Users\\[^\\]+", "C:/Users/[USER]"),
            (r"/Users/[^/\s]+", "/Users/[USER]"),
            (
                r"(/[^/\s]*){3,}",
                "[PATH]",
            ),  # Long absolute paths (must come after specific patterns)
            (r"[a-zA-Z]:\\[^\\]+\\[^\\]+\\[^\\]+", "[PATH]"),  # Long Windows paths
        ]

        for pattern, replacement in sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    def generate_security_recommendations(self, test_data: dict[str, Any]) -> list[str]:
        """Generate security recommendations for test case."""
        recommendations = []

        # Check for SSH usage
        if any(
            "ssh" in str(value).lower() or "ssh" in key.lower()
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
            "database" in str(value).lower()
            or "sql" in str(value).lower()
            or "select" in str(value).lower()
            or "insert" in str(value).lower()
            or "update" in str(value).lower()
            or "delete" in str(value).lower()
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
            "browser" in str(value).lower()
            or "web" in str(value).lower()
            or "browser" in key.lower()
            or "url" in key.lower()
            for key, value in test_data.items()
        ):
            recommendations.extend(
                [
                    "💡 Validate all form inputs for XSS prevention",
                    "💡 Test authentication and authorization flows",
                    "💡 Use secure test data, avoid production credentials",
                ]
            )

        return recommendations

    def validate_test_security(self, test_case: dict[str, Any]) -> dict[str, list[str]]:
        """Comprehensive security validation for test cases."""
        return validate_test_security(test_case)


def validate_test_security(test_case: dict[str, Any]) -> dict[str, list[str]]:
    """Comprehensive security validation for test cases."""
    validator = SecurityValidator()
    results: dict[str, list[str]] = {
        "warnings": [],
        "recommendations": [],
        "sanitized_errors": [],
    }

    # Validate SSH operations
    if "ssh" in str(test_case).lower():
        # Extract SSH parameters from test case steps
        for step in test_case.get("steps", []):
            if "ssh" in str(step).lower() or step.get("library") == "SSHLibrary":
                # Parse test_data for SSH parameters
                test_data = step.get("test_data", "")
                ssh_params = {}

                # Extract various SSH parameters using comprehensive patterns
                parameter_patterns = {
                    "password": r"password:\s*([^,\n\s]+)",
                    "username": r"username:\s*([^,\n\s]+)",
                    "keyfile": r"keyfile:\s*([^,\n\s]+)",
                    "command": r"command:\s*([^,\n]+)",
                    "host": r"host:\s*([^,\n\s]+)",
                    "source_path": r"source:\s*([^,\n]+)",
                    "destination_path": r"destination:\s*([^,\n]+)",
                    # Also extract parameters without colons for generic patterns
                    "parameter": r"parameter:\s*([^,\n]+)",
                }

                for param_name, pattern in parameter_patterns.items():
                    match = re.search(pattern, test_data)
                    if match:
                        ssh_params[param_name] = match.group(1).strip()

                # Additional processing: ensure password detection includes the value
                # for pattern matching
                if "password:" in test_data and "password" not in ssh_params:
                    ssh_params["password"] = True

                ssh_warnings = validator.validate_ssh_parameters(ssh_params)
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


def get_ssh_security_guidelines() -> list[str]:
    """Get SSH security guidelines for test automation."""
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


# Shared SSH security guidelines constant
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
