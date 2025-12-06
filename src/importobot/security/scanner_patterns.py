"""Pattern definitions for template security scanning.

Provides configurable patterns for detecting suspicious variables,
hardcoded credentials, and safe keywords for false positive reduction.
"""

from __future__ import annotations

from typing import Any, ClassVar

# =============================================================================
# SUSPICIOUS VARIABLE NAMES
# =============================================================================
# Variable names that suggest credential or secret storage.
# These are reasonable defaults - extend with additional_suspicious_variables.
# =============================================================================

SUSPICIOUS_VARIABLE_NAMES: set[str] = {
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

# =============================================================================
# HARDCODED VALUE PATTERNS
# =============================================================================
# Patterns for detecting hardcoded credentials in template files.
# Each pattern has: name, regex pattern, severity, description, remediation.
# =============================================================================

HARDCODED_VALUE_PATTERNS: list[dict[str, Any]] = [
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
            r"(?i)\b(api[_-]?key|apikey)\s*[:=]\s*"
            r"(?:['\"]?[a-zA-Z0-9_\-]{6,}['\"]?)"
        ),
        "severity": "high",
        "description": "Hardcoded API key detected",
        "remediation": "Use secure key management service",
    },
    {
        "name": "hardcoded_secret",
        "pattern": (
            r"(?i)\b(secret|token|key)\s*[:=]\s*"
            r"(?:['\"]?[a-zA-Z0-9_\-]{6,}['\"]?)"
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
        "pattern": r"eyJ[a-zA-Z0-9_-]{6,}(?:\.[a-zA-Z0-9_-]{6,}){0,2}(?:\.\.\.)?",
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
    # Additional patterns you may want to enable:
    # {
    #     "name": "aws_access_key",
    #     "pattern": r"AKIA[0-9A-Z]{16}",
    #     "severity": "critical",
    #     "description": "AWS Access Key ID detected",
    #     "remediation": "Use IAM roles or AWS Secrets Manager",
    # },
    # {
    #     "name": "github_token",
    #     "pattern": r"gh[pousr]_[A-Za-z0-9_]{36,}",
    #     "severity": "critical",
    #     "description": "GitHub token detected",
    #     "remediation": "Use GitHub Actions secrets or environment variables",
    # },
]

# =============================================================================
# ROBOT FRAMEWORK SPECIFIC PATTERNS
# =============================================================================
# Patterns for detecting Robot Framework-specific security issues.
# =============================================================================

ROBOT_FRAMEWORK_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "credentials_in_variables_section",
        "pattern": r"^\*\*\* Variables \*\*\*$",
        "severity": "medium",
        "description": (
            "Credentials in Variables section - should use environment variables"
        ),
        "remediation": ("Move credentials to environment variables or secure storage"),
    },
    {
        "name": "insecure_library_import",
        "pattern": r"(?i)Library\s+(?:SeleniumLibrary|RequestsLibrary).*",
        "severity": "low",
        "description": "Potentially insecure library import",
        "remediation": "Review library usage and ensure secure configuration",
    },
    # Additional patterns you may want to enable:
    # {
    #     "name": "hardcoded_url",
    #     "pattern": r"(?i)https?://[^\s]+",
    #     "severity": "low",
    #     "description": "Hardcoded URL detected",
    #     "remediation": "Consider using variables for URLs",
    # },
]

# =============================================================================
# SAFE KEYWORDS (False Positive Reduction)
# =============================================================================
# Keywords that indicate safe/example content, used to reduce false positives.
# =============================================================================

SAFE_KEYWORDS: set[str] = {
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

# =============================================================================
# PLACEHOLDER CONTEXT INDICATORS
# =============================================================================
# Indicators that suggest content is placeholder/example data.
# =============================================================================

PLACEHOLDER_INDICATORS: tuple[str, ...] = (
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

# =============================================================================
# SEVERITY CLASSIFICATION
# =============================================================================
# Variable names classified by severity level.
# =============================================================================

HIGH_SEVERITY_VARIABLES: set[str] = {
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

CRITICAL_SEVERITY_VARIABLES: set[str] = {
    "aws_key",
    "aws_secret",
    "azure_key",
    "gcp_key",
    "private_key",
    "ssh_key",
    "ssl_certificate",
}


class ScannerPatterns:
    """Manages patterns for template security scanning.

    All pattern sets are exposed as class variables for easy customization.
    You can either:
    1. Pass custom patterns to TemplateSecurityScanner constructor
    2. Modify the module-level constants before creating scanners
    3. Subclass ScannerPatterns and override the class variables
    """

    SUSPICIOUS_VARIABLES: ClassVar[set[str]] = SUSPICIOUS_VARIABLE_NAMES
    HARDCODED_PATTERNS: ClassVar[list[dict[str, Any]]] = HARDCODED_VALUE_PATTERNS
    ROBOT_PATTERNS: ClassVar[list[dict[str, Any]]] = ROBOT_FRAMEWORK_PATTERNS
    SAFE_KEYWORDS: ClassVar[set[str]] = SAFE_KEYWORDS
    PLACEHOLDER_INDICATORS: ClassVar[tuple[str, ...]] = PLACEHOLDER_INDICATORS
    HIGH_SEVERITY_VARS: ClassVar[set[str]] = HIGH_SEVERITY_VARIABLES
    CRITICAL_SEVERITY_VARS: ClassVar[set[str]] = CRITICAL_SEVERITY_VARIABLES

    @classmethod
    def get_suspicious_variables(
        cls, additional_variables: set[str] | None = None
    ) -> set[str]:
        """Get suspicious variable names with variations.

        Args:
            additional_variables: Extra variable names to add.

        Returns:
            Set of suspicious variable names with case variations.
        """
        base_vars = set(cls.SUSPICIOUS_VARIABLES)
        if additional_variables:
            base_vars.update(additional_variables)

        # Add common variations
        all_vars = set(base_vars)
        for var in base_vars:
            all_vars.add(var.upper())
            all_vars.add(var.lower())
            all_vars.add(var.replace("_", "-"))
            all_vars.add(var.replace("-", "_"))

        return all_vars

    @classmethod
    def get_hardcoded_patterns(
        cls, additional_patterns: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Get hardcoded value patterns.

        Args:
            additional_patterns: Extra patterns to add.

        Returns:
            List of pattern dictionaries.
        """
        result = list(cls.HARDCODED_PATTERNS)
        if additional_patterns:
            result.extend(additional_patterns)
        return result

    @classmethod
    def get_robot_patterns(
        cls, additional_patterns: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Get Robot Framework-specific patterns.

        Args:
            additional_patterns: Extra patterns to add.

        Returns:
            List of pattern dictionaries.
        """
        result = list(cls.ROBOT_PATTERNS)
        if additional_patterns:
            result.extend(additional_patterns)
        return result

    @classmethod
    def get_safe_keywords(cls, additional_keywords: set[str] | None = None) -> set[str]:
        """Get safe keywords for false positive reduction.

        Args:
            additional_keywords: Extra keywords to add.

        Returns:
            Set of safe keywords.
        """
        result = set(cls.SAFE_KEYWORDS)
        if additional_keywords:
            result.update(additional_keywords)
        return result

    @classmethod
    def get_variable_severity(cls, var_name: str) -> str:
        """Get severity level for a suspicious variable.

        Args:
            var_name: Variable name to assess.

        Returns:
            Severity level string ("low", "medium", "high", "critical").
        """
        var_name_lower = var_name.lower()
        if var_name_lower in cls.CRITICAL_SEVERITY_VARS:
            return "critical"
        elif var_name_lower in cls.HIGH_SEVERITY_VARS:
            return "high"
        else:
            return "medium"


# Export module-level constants for direct import
__all__ = [
    "CRITICAL_SEVERITY_VARIABLES",
    "HARDCODED_VALUE_PATTERNS",
    "HIGH_SEVERITY_VARIABLES",
    "PLACEHOLDER_INDICATORS",
    "ROBOT_FRAMEWORK_PATTERNS",
    "SAFE_KEYWORDS",
    "SUSPICIOUS_VARIABLE_NAMES",
    "ScannerPatterns",
]
