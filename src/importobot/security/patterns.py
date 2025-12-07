"""Security pattern constants and management.

Provides dangerous command patterns and sensitive path patterns that
vary based on security level (strict, standard, permissive).

All pattern lists are user-configurable. The defaults below represent
common security concerns but can be customized for your environment.
"""

from typing import ClassVar

from importobot.services.security_types import SecurityLevel

# =============================================================================
# DEFAULT DANGEROUS COMMAND PATTERNS
# =============================================================================
# These patterns detect potentially dangerous shell commands.
# Customize by passing your own list to SecurityValidator or SecurityPatterns.
#
# Each pattern is a Python regex string. Examples:
#   r"rm\s+-rf"          - Matches "rm -rf" (recursive force delete)
#   r"sudo\s+"           - Matches "sudo " (privilege escalation)
#   r"`[^`]*`"           - Matches backtick command substitution
#
# To add custom patterns, create a list and pass to SecurityValidator:
#   my_patterns = SecurityPatterns.DEFAULT_DANGEROUS_PATTERNS + [
#       r"my_dangerous_cmd",
#   ]
#   validator = SecurityValidator(dangerous_patterns=my_patterns)
# =============================================================================

DEFAULT_DANGEROUS_PATTERNS: list[str] = [
    # Shell deletion commands
    r"rm\s+-rf",  # Recursive force delete
    r"&&\s*rm",  # Chained rm command
    r";\s*rm",  # Sequential rm command
    # Privilege escalation
    r"sudo\s+",  # Sudo command
    r"chmod\s+777",  # World-writable permissions
    # Shell piping dangers
    r">\s*/dev/null",  # Output redirection (can hide errors)
    r"\|\s*sh",  # Pipe to shell
    r"\|\s*bash",  # Pipe to bash
    r"curl.*\|\s*sh",  # Download and execute
    r"wget.*\|\s*sh",  # Download and execute
    # Code execution
    r"eval\s*\(",  # Eval function
    r"exec\s*\(",  # Exec function
    r"`[^`]*`",  # Backtick command substitution
    r"\$\([^)]*\)",  # $() command substitution
    # Disk operations
    r"dd\s+if=.*of=/dev/",  # Disk dump to device
    r"mkfs\.",  # Format filesystem
    r"fdisk\s",  # Disk partitioning
    r"/dev/sda",  # Direct disk access
    r"/dev/hda",  # Direct disk access (legacy)
    # System file access
    r"cat\s+/etc/shadow",  # Reading shadow file
    r">\s*/etc/passwd",  # Overwriting passwd
    # Fork bomb
    r":\(\)\{.*:\|:&.*\};:",  # Classic fork bomb pattern
]

# =============================================================================
# DEFAULT SENSITIVE PATH PATTERNS
# =============================================================================
# These patterns identify access to sensitive file locations.
# Customize for your environment's specific sensitive paths.
#
# Example customization:
#   my_paths = SecurityPatterns.DEFAULT_SENSITIVE_PATHS + [
#       r"/opt/myapp/secrets/",
#       r"\.myapp/credentials",
#   ]
#   validator = SecurityValidator(sensitive_paths=my_paths)
# =============================================================================

DEFAULT_SENSITIVE_PATHS: list[str] = [
    # Unix system files
    r"/etc/passwd",  # User database
    r"/etc/shadow",  # Password hashes
    r"/root/",  # Root home directory
    # SSH credentials
    r"/home/[^/]+/\.ssh",  # User SSH directories
    r"\.ssh/id_rsa",  # SSH private key
    # Cloud credentials
    r"\.aws/credentials",  # AWS credentials file
    # Windows system paths
    r"C:\\Windows\\System32",  # Windows system directory
    r"%USERPROFILE%",  # Windows user profile variable
]

# =============================================================================
# STRICT MODE ADDITIONS
# =============================================================================
# Additional patterns applied when security_level=STRICT.
# These are our assumed reasonable defaults for production environments.
#
# Customize as needed: comment out patterns that cause false positives
# in your environment, or add additional patterns for your requirements.
# =============================================================================

STRICT_DANGEROUS_PATTERN_ADDITIONS: list[str] = [
    # System information gathering (reasonable defaults for production)
    r"cat\s+/proc/",  # Reading proc filesystem
    r"netstat\s",  # Network enumeration
    r"ps\s+aux",  # Process enumeration
    r"whoami",  # User enumeration
    r"id\s",  # User ID enumeration
    # Network requests (may cause false positives in API-heavy environments)
    r"curl\s+",  # External network requests
    r"wget\s+",  # External network requests
    # Additional patterns you may want to enable:
    # r"nmap\s",           # Port scanning
    # r"tcpdump\s",        # Packet capture
    # r"strace\s",         # System call tracing
    # r"ltrace\s",         # Library call tracing
]

STRICT_SENSITIVE_PATH_ADDITIONS: list[str] = [
    # Linux system directories (reasonable defaults for production)
    r"/proc/",  # Process information
    r"/sys/",  # Kernel/device information
    r"/var/log/",  # System logs
    # Container/orchestration configs
    r"\.kube/config",  # Kubernetes config
    r"\.docker/config\.json",  # Docker config
    # Windows
    r"C:\\ProgramData",  # Windows program data
    # Additional paths you may want to enable:
    # r"/etc/sudoers",     # Sudo configuration
    # r"\.gnupg/",         # GPG keys
    # r"\.npmrc",          # NPM credentials
    # r"\.pypirc",         # PyPI credentials
    # r"\.netrc",          # FTP/HTTP credentials
]

# =============================================================================
# PERMISSIVE MODE REMOVALS
# =============================================================================
# Patterns removed from defaults when security_level=PERMISSIVE.
# These are commonly used in legitimate development workflows.
# =============================================================================

PERMISSIVE_PATTERN_REMOVALS: set[str] = {
    r"curl\s+",  # Often needed for API testing
    r"wget\s+",  # Often needed for downloads
    r">\s*/dev/null",  # Common in scripts
    # Uncomment to allow more in permissive mode:
    # r"sudo\s+",          # If sudo is routinely needed
}

# =============================================================================
# INJECTION DETECTION PATTERNS
# =============================================================================
# Patterns for detecting command/SQL/code injection attempts.
# These are reasonable defaults - extend with additional_injection_patterns.
#
# Note: These patterns aim to catch obvious injection attempts while minimizing
# false positives. For high-security environments, consider enabling the
# commented patterns or adding domain-specific patterns.
# =============================================================================

INJECTION_PATTERNS: list[str] = [
    # --- Command Injection (Shell) ---
    r";.*rm\s",  # Semicolon followed by rm
    r"`[^`]*`",  # Backtick command substitution
    r"\$\([^)]*\)",  # $() command substitution
    r"\|\s*sh",  # Pipe to sh
    r"\|\s*bash",  # Pipe to bash
    r"&&.*rm\s",  # AND-chained rm
    r"\|\|.*rm\s",  # OR-chained rm
    # --- Download & Execute ---
    r"curl.*\|\s*sh",  # Curl pipe to shell
    r"wget.*\|\s*sh",  # Wget pipe to shell
    r"curl.*\|\s*bash",  # Curl pipe to bash
    r"wget.*\|\s*bash",  # Wget pipe to bash
    r"&&.*wget",  # Chained download
    r"&&.*curl",  # Chained curl
    # --- System File Access ---
    r"cat\s+/etc/",  # Reading system files
    r"head\s+/etc/",  # Reading system files
    r"tail\s+/etc/",  # Reading system files
    r"less\s+/etc/",  # Reading system files
    # --- Code Execution ---
    r"eval\s*\(",  # Eval function
    r"exec\s*\(",  # Exec function
    # --- SQL Injection (basic indicators) ---
    r"'\s*OR\s+'",  # OR-based SQL injection
    r"\"\s*OR\s+\"",  # OR-based SQL injection (double quotes)
    r"'\s*OR\s+1\s*=\s*1",  # Classic 1=1 injection
    r";\s*--",  # Statement terminator + comment
    # Additional patterns you may want to enable:
    # r"UNION\s+SELECT",   # SQL UNION injection
    # r";\s*DROP\s",       # SQL DROP injection
    # r"INTO\s+OUTFILE",   # SQL file write
    # r"LOAD_FILE\s*\(",   # SQL file read
    # r"<script",          # XSS script tag
    # r"javascript:",      # XSS javascript protocol
    # r"onerror\s*=",      # XSS event handler
    # r"onload\s*=",       # XSS event handler
    # r"\.\./",            # Path traversal
    # r"\.\.\\",           # Path traversal (Windows)
]

# =============================================================================
# DEFAULT DANGEROUS CHARACTERS FOR COMMAND SANITIZATION
# =============================================================================
# Characters that may enable shell injection when passed to command execution.
# Used by sanitize_command_parameters to escape potentially dangerous chars.
#
# These are the characters that are escaped in command strings:
#   |    - Pipe (command chaining)
#   &    - Background execution / AND operator
#   ;    - Command separator
#   $(   - Command substitution start
#   `    - Backtick command substitution
#   >    - Output redirection
#   <    - Input redirection
#   *    - Glob wildcard
#   ?    - Single char wildcard
#   [    - Character class start
#   ]    - Character class end
#
# To customize, pass your own list to sanitize_command_parameters:
#   custom_chars = ["|", "&", ";"]  # Only escape these
#   sanitize_command_parameters(cmd, dangerous_chars=custom_chars)
# =============================================================================

DEFAULT_DANGEROUS_CHARS: list[str] = [
    "|",  # Pipe - command chaining
    "&",  # Background execution / AND operator
    ";",  # Command separator
    "$(",  # Command substitution start
    "`",  # Backtick command substitution
    ">",  # Output redirection
    "<",  # Input redirection
    "*",  # Glob wildcard
    "?",  # Single char wildcard
    "[",  # Character class start
    "]",  # Character class end
]

# =============================================================================
# ERROR MESSAGE SANITIZATION PATTERNS
# =============================================================================
# Patterns for redacting sensitive information from error messages.
# Each tuple is (regex_pattern, replacement_text).
# These are reasonable defaults - extend with additional_sanitization_patterns.
# =============================================================================

ERROR_SANITIZATION_PATTERNS: list[tuple[str, str]] = [
    # User home directories (prevents username disclosure)
    (r"/home/[^/\s]+", "/home/[USER]"),  # Linux
    (r"/Users/[^/\s]+", "/Users/[USER]"),  # macOS
    (r"C:\\Users\\[^\\]+", "C:\\\\Users\\\\[USER]"),  # Windows (escaped for re.sub)
    # Deep paths (prevents directory structure disclosure)
    (r"(/[^/\s]*){3,}", "[PATH]"),  # Unix paths 3+ deep
    (r"[a-zA-Z]:\\[^\\]+\\[^\\]+\\[^\\]+", "[PATH]"),  # Windows paths 3+ deep
    # Additional patterns you may want to enable:
    # (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]"),  # IP addresses
    # (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),  # Emails
    # (r"/var/log/[^\s]+", "[LOGFILE]"),           # Log file paths
    # (r"port\s*[=:]\s*\d+", "port=[PORT]"),       # Port numbers
]


class SecurityPatterns:
    """Manages dangerous patterns and sensitive paths by security level.

    All pattern lists are exposed as class variables for easy customization.
    You can either:
    1. Pass custom patterns to SecurityValidator constructor
    2. Modify the module-level constants before creating validators
    3. Subclass SecurityPatterns and override the class variables

    Security Levels:
        strict: Maximum security for production environments.
            - Adds STRICT_DANGEROUS_PATTERN_ADDITIONS
            - Adds STRICT_SENSITIVE_PATH_ADDITIONS
            - Recommended for: Production, compliance environments

        standard: Balanced security for general development and testing.
            - Uses DEFAULT_DANGEROUS_PATTERNS
            - Uses DEFAULT_SENSITIVE_PATHS
            - Recommended for: Development, CI/CD pipelines

        permissive: Relaxed security for trusted environments.
            - Removes PERMISSIVE_PATTERN_REMOVALS from defaults
            - Recommended for: Local development, trusted environments

    Example:
        >>> # Use defaults
        >>> validator = SecurityValidator()
        >>>
        >>> # Custom patterns
        >>> my_patterns = DEFAULT_DANGEROUS_PATTERNS + [r"my_cmd"]
        >>> validator = SecurityValidator(dangerous_patterns=my_patterns)
    """

    # Class variables reference module-level defaults for easy override
    DEFAULT_DANGEROUS_PATTERNS: ClassVar[list[str]] = DEFAULT_DANGEROUS_PATTERNS
    DEFAULT_SENSITIVE_PATHS: ClassVar[list[str]] = DEFAULT_SENSITIVE_PATHS
    DEFAULT_DANGEROUS_CHARS: ClassVar[list[str]] = DEFAULT_DANGEROUS_CHARS
    STRICT_PATTERN_ADDITIONS: ClassVar[list[str]] = STRICT_DANGEROUS_PATTERN_ADDITIONS
    STRICT_PATH_ADDITIONS: ClassVar[list[str]] = STRICT_SENSITIVE_PATH_ADDITIONS
    ERROR_SANITIZATION_PATTERNS: ClassVar[list[tuple[str, str]]] = (
        ERROR_SANITIZATION_PATTERNS
    )
    PERMISSIVE_REMOVALS: ClassVar[set[str]] = PERMISSIVE_PATTERN_REMOVALS
    INJECTION_PATTERNS: ClassVar[list[str]] = INJECTION_PATTERNS

    @classmethod
    def get_dangerous_patterns(
        cls,
        custom_patterns: list[str] | None,
        level: SecurityLevel,
        additional_patterns: list[str] | None = None,
    ) -> list[str]:
        """Get dangerous patterns based on security level.

        Args:
            custom_patterns: Custom patterns to use instead of defaults.
                If provided, these completely replace the defaults.
            level: Security level ('strict', 'standard', 'permissive')
            additional_patterns: Extra patterns to append to the result.
                Use this to extend defaults without replacing them.

        Returns:
            List of dangerous command patterns for the specified security level
        """
        base_patterns = (
            custom_patterns
            if custom_patterns is not None
            else list(cls.DEFAULT_DANGEROUS_PATTERNS)
        )

        if level == SecurityLevel.STRICT:
            result = base_patterns + list(cls.STRICT_PATTERN_ADDITIONS)
        elif level == SecurityLevel.PERMISSIVE:
            result = [p for p in base_patterns if p not in cls.PERMISSIVE_REMOVALS]
        else:
            result = base_patterns

        # Append any additional user-provided patterns
        if additional_patterns:
            result = result + list(additional_patterns)

        return result

    @classmethod
    def get_sensitive_paths(
        cls,
        custom_paths: list[str] | None,
        level: SecurityLevel,
        additional_paths: list[str] | None = None,
    ) -> list[str]:
        """Get sensitive paths based on security level.

        Args:
            custom_paths: Custom paths to use instead of defaults.
                If provided, these completely replace the defaults.
            level: Security level ('strict', 'standard', 'permissive')
            additional_paths: Extra paths to append to the result.
                Use this to extend defaults without replacing them.

        Returns:
            List of sensitive file path patterns for the specified security level
        """
        base_paths = (
            custom_paths
            if custom_paths is not None
            else list(cls.DEFAULT_SENSITIVE_PATHS)
        )

        if level == SecurityLevel.STRICT:
            result = base_paths + list(cls.STRICT_PATH_ADDITIONS)
        else:
            result = base_paths

        # Append any additional user-provided paths
        if additional_paths:
            result = result + list(additional_paths)

        return result

    @classmethod
    def get_injection_patterns(
        cls,
        additional_patterns: list[str] | None = None,
    ) -> list[str]:
        """Get injection detection patterns.

        Args:
            additional_patterns: Extra patterns to append to the defaults.
                Use this to extend the injection detection coverage.

        Returns:
            List of patterns for detecting injection attempts
        """
        result = list(cls.INJECTION_PATTERNS)
        if additional_patterns:
            result = result + list(additional_patterns)
        return result

    @classmethod
    def get_sanitization_patterns(
        cls,
        additional_patterns: list[tuple[str, str]] | None = None,
    ) -> list[tuple[str, str]]:
        """Get error message sanitization patterns.

        Args:
            additional_patterns: Extra (pattern, replacement) tuples to append.
                Use this to extend the sanitization coverage.

        Returns:
            List of (pattern, replacement) tuples for sanitizing error messages
        """
        result = list(cls.ERROR_SANITIZATION_PATTERNS)
        if additional_patterns:
            result = result + list(additional_patterns)
        return result

    @classmethod
    def get_dangerous_chars(
        cls,
        custom_chars: list[str] | None = None,
        additional_chars: list[str] | None = None,
    ) -> list[str]:
        """Get dangerous characters for command sanitization.

        Args:
            custom_chars: Custom characters to use instead of defaults.
                If provided, these completely replace the defaults.
            additional_chars: Extra characters to append to the result.
                Use this to extend defaults without replacing them.

        Returns:
            List of dangerous characters to escape in commands

        Example:
            >>> # Use defaults
            >>> chars = SecurityPatterns.get_dangerous_chars()
            >>>
            >>> # Custom chars only
            >>> chars = SecurityPatterns.get_dangerous_chars(custom_chars=["|", "&"])
            >>>
            >>> # Extend defaults
            >>> chars = SecurityPatterns.get_dangerous_chars(additional_chars=["@"])
        """
        base_chars = (
            custom_chars
            if custom_chars is not None
            else list(cls.DEFAULT_DANGEROUS_CHARS)
        )

        return base_chars + list(additional_chars) if additional_chars else base_chars


# Export module-level constants for direct import
__all__ = [
    "DEFAULT_DANGEROUS_CHARS",
    "DEFAULT_DANGEROUS_PATTERNS",
    "DEFAULT_SENSITIVE_PATHS",
    "ERROR_SANITIZATION_PATTERNS",
    "INJECTION_PATTERNS",
    "PERMISSIVE_PATTERN_REMOVALS",
    "STRICT_DANGEROUS_PATTERN_ADDITIONS",
    "STRICT_SENSITIVE_PATH_ADDITIONS",
    "SecurityPatterns",
]
