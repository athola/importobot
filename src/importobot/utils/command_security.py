"""Robust command security validation and sanitization utilities.

This module provides enterprise-grade security for command execution with:
- Whitelist-based command validation
- Parameter validation and sanitization
- Context-aware security levels
- Comprehensive audit logging
- Built-in security policies for different environments
"""

from __future__ import annotations

import re
import shlex
import subprocess
from enum import Enum
from typing import Any, ClassVar

from importobot.services.security_types import SecurityLevel, SecurityPolicy
from importobot.utils.logging import get_logger

logger = get_logger(__name__)


class CommandValidationResult(Enum):
    """Result of command security validation."""

    ALLOWED = "allowed"
    """Command is safe to execute."""

    REJECTED = "rejected"
    """Command is dangerous and must be blocked."""

    MODIFIED = "modified"
    """Command was sanitized and can be executed with caution."""


class CommandWhitelist:
    """Whitelist of allowed commands and patterns by security level."""

    # Default safe commands for all environments
    UNIVERSALLY_SAFE_COMMANDS: ClassVar[set[str]] = {
        # Basic file operations
        "ls",
        "dir",
        "cd",
        "pwd",
        # File information
        "file",
        "stat",
        "wc",
        "head",
        "tail",
        # Text processing
        "cat",
        "grep",
        "sed",
        "awk",
        "sort",
        "uniq",
        "cut",
        # Compression
        "tar",
        "gzip",
        "gunzip",
        "zip",
        "unzip",
        # Network diagnostics (read-only)
        "ping",
        "traceroute",
        "nslookup",
        "dig",
        # System information (read-only)
        "uname",
        "whoami",
        "id",
        "date",
        "uptime",
    }

    # Development environment commands
    DEVELOPMENT_COMMANDS: ClassVar[set[str]] = {
        # Build tools
        "make",
        "cmake",
        "gcc",
        "g++",
        "python",
        "python3",
        "node",
        "npm",
        # Version control
        "git",
        "svn",
        "hg",
        # Testing
        "pytest",
        "jest",
        "mocha",
        "cargo test",
        # Development utilities
        "curl",
        "wget",
        "ssh",
        "scp",
        "rsync",
    }

    # Production environment commands (restricted)
    PRODUCTION_COMMANDS: ClassVar[set[str]] = {
        # System monitoring (read-only)
        "ps",
        "top",
        "htop",
        "df",
        "du",
        "free",
        "netstat",
        # Service status (read-only)
        "systemctl status",
        "service status",
    }

    # Dangerous command patterns to always block
    BLOCKED_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        # File system destruction
        re.compile(r"rm\s+-rf\s+/"),
        re.compile(r"dd\s+if=/dev/zero"),
        re.compile(r"mkfs\."),
        re.compile(r"fdisk\s"),
        # System compromise
        re.compile(r":\(\)\{.*:\|:&.*\}:"),  # Fork bomb
        re.compile(r"chmod\s+777\s+/"),
        re.compile(r"chown\s+.*\s+/"),
        # Information disclosure
        re.compile(r"cat\s+/etc/(shadow|passwd|master\.passwd)"),
        re.compile(r"cat\s+/proc/(version|cpuinfo|meminfo)"),
        # Network attacks
        re.compile(r"nc\s+-l\s+-p"),  # Netcat listener
        re.compile(r"iptables\s+-F"),  # Flush firewall rules
        # Command injection patterns
        re.compile(r"\$\([^)]*\)"),  # Command substitution
        re.compile(r"`[^`]*`"),  # Backtick substitution
        re.compile(r"\|\s*sh"),
        re.compile(r"\|\s*bash"),
        re.compile(r"&&\s*(rm|dd|mkfs|chmod\s+777)"),
        re.compile(r"&&"),
    ]

    # Suspicious parameter keywords and ports
    SENSITIVE_PARAM_PREFIXES: ClassVar[tuple[str, ...]] = ("password", "pwd", "pass")
    CREDENTIAL_PARAM_PREFIXES: ClassVar[tuple[str, ...]] = (
        "api_key",
        "apikey",
        "token",
        "secret",
    )
    SUSPICIOUS_PORTS: ClassVar[tuple[str, ...]] = (
        "4444",
        "5555",
        "6666",
        "7777",
        "8888",
        "9999",
        "1337",
        "31337",
    )

    @classmethod
    def get_allowed_commands(cls, security_level: SecurityLevel) -> set[str]:
        """Get allowed commands based on security level."""
        base_commands = cls.UNIVERSALLY_SAFE_COMMANDS.copy()
        base_commands.update(cls.PRODUCTION_COMMANDS)

        if security_level == SecurityLevel.PERMISSIVE:
            base_commands.update(cls.DEVELOPMENT_COMMANDS)
        elif security_level == SecurityLevel.STANDARD:
            base_commands.update(
                {"git", "curl", "wget", "python", "python3", "make", "cmake"}
            )
        # STRICT uses base + production only

        return base_commands

    @classmethod
    def is_command_allowed(cls, command: str, security_level: SecurityLevel) -> bool:
        """Check if a command is in the allowed list."""
        # Extract base command (first word)
        base_command = command.split()[0] if command.split() else ""

        # Check against allowed commands
        allowed_commands = cls.get_allowed_commands(security_level)
        return base_command in allowed_commands

    @classmethod
    def has_blocked_pattern(cls, command: str) -> tuple[bool, re.Pattern[str] | None]:
        """Check if command contains blocked patterns."""
        for pattern in cls.BLOCKED_PATTERNS:
            if pattern.search(command):
                return True, pattern
        return False, None

    @classmethod
    def has_suspicious_params(cls, command: str) -> list[str]:
        """Check if command has suspicious parameters."""
        findings: list[str] = []
        lowered = command.lower()

        findings.extend(
            f"{prefix} parameter"
            for prefix in cls.SENSITIVE_PARAM_PREFIXES
            if f"{prefix}=" in lowered
        )

        if any(f"{prefix}=" in lowered for prefix in cls.CREDENTIAL_PARAM_PREFIXES):
            findings.append("credential parameter")

        if "../" in command:
            findings.append("path traversal sequence")

        if "/etc/" in lowered and any(symbol in command for symbol in (";", "|", "&")):
            findings.append("sensitive path chained execution")

        if "/proc/" in lowered and any(symbol in command for symbol in ("|", "&")):
            findings.append("/proc access with piping")

        for port in cls.SUSPICIOUS_PORTS:
            if f":{port}" in lowered or f" {port}" in lowered:
                findings.append(f"suspicious port {port}")
                break

        return findings


class CommandValidator:
    """Enterprise-grade command security validator."""

    def __init__(
        self,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
        policy: SecurityPolicy = SecurityPolicy.BLOCK,
        custom_whitelist: set[str] | None = None,
        enable_audit_logging: bool = True,
    ):
        """Initialize command validator.

        Args:
            security_level: Security level determining validation strictness
            policy: Security policy for handling dangerous commands
            custom_whitelist: Additional allowed commands beyond defaults
            enable_audit_logging: Enable detailed audit logging
        """
        self.security_level = security_level
        self.policy = policy
        self.custom_whitelist = custom_whitelist or set()
        self.enable_audit_logging = enable_audit_logging

        # Initialize whitelist
        self.allowed_commands = CommandWhitelist.get_allowed_commands(security_level)
        self.allowed_commands.update(self.custom_whitelist)

    def validate_command(
        self, command: str | Any, context: dict[str, Any] | None = None
    ) -> tuple[CommandValidationResult, str, list[str]]:
        """Validate a command for security issues.

        Args:
            command: Command string to validate
            context: Additional context for validation (e.g., user, purpose)

        Returns:
            Tuple of (validation_result, processed_command, warnings)
        """
        if not isinstance(command, str):
            return CommandValidationResult.ALLOWED, str(command), []

        warnings: list[str] = []
        processed_command = command.strip()

        # Empty commands are allowed
        if not processed_command:
            return CommandValidationResult.ALLOWED, "", []

        # Log validation start
        if self.enable_audit_logging:
            logger.info(
                "Validating command with security_level=%s, policy=%s: %s",
                self.security_level.value,
                self.policy.value,
                (
                    processed_command[:100] + "..."
                    if len(processed_command) > 100
                    else processed_command
                ),
            )

        blocked_result = self._process_blocked_patterns(
            processed_command, warnings, context
        )
        if blocked_result is not None:
            return blocked_result

        self._record_suspicious_params(processed_command, warnings)

        # Check against whitelist
        whitelist_result = self._process_whitelist(processed_command, warnings, context)
        if whitelist_result is not None:
            return whitelist_result

        # Apply security policy
        if warnings:
            return self._apply_security_policy(processed_command, warnings)

        if self.policy == SecurityPolicy.ESCAPE:
            escaped_command = self._escape_dangerous_chars(processed_command)
            if escaped_command != processed_command:
                warnings.append("Dangerous characters escaped (policy=ESCAPE)")
            return CommandValidationResult.ALLOWED, escaped_command, warnings

        # If we get here, command is considered safe
        return CommandValidationResult.ALLOWED, processed_command, warnings

    def _handle_blocked_pattern(
        self,
        processed_command: str,
        blocked_pattern: re.Pattern[str],
        warnings: list[str],
        context: dict[str, Any] | None,
    ) -> tuple[CommandValidationResult, str, list[str]] | None:
        """Handle commands that match blocked patterns."""
        error_msg = f"Command contains dangerous pattern: {blocked_pattern.pattern}"
        warnings.append(error_msg)
        if self.policy == SecurityPolicy.BLOCK:
            self._log_security_event(
                "COMMAND_BLOCKED",
                {
                    "command": processed_command[:200],
                    "reason": "dangerous_pattern",
                    "pattern": blocked_pattern.pattern,
                    "context": context or {},
                },
            )
            return CommandValidationResult.REJECTED, "", warnings
        if self.policy == SecurityPolicy.ESCAPE:
            processed_command = self._escape_dangerous_chars(processed_command)
            warnings.append("Dangerous characters escaped (legacy behavior)")
            return CommandValidationResult.ALLOWED, processed_command, warnings
        return None

    def _handle_not_whitelisted(
        self,
        processed_command: str,
        base_command: str,
        warnings: list[str],
        context: dict[str, Any] | None,
    ) -> tuple[CommandValidationResult, str, list[str]] | None:
        """Handle commands that are not whitelisted."""
        warnings.append(f"Command '{base_command}' not in allowed commands list")
        if self.policy == SecurityPolicy.BLOCK:
            self._log_security_event(
                "COMMAND_BLOCKED",
                {
                    "command": processed_command[:200],
                    "reason": "not_whitelisted",
                    "base_command": base_command,
                    "context": context or {},
                },
            )
            return CommandValidationResult.REJECTED, "", warnings
        if self.policy == SecurityPolicy.ESCAPE:
            processed_command = self._escape_dangerous_chars(processed_command)
            warnings.append("Dangerous characters escaped (legacy behavior)")
            return CommandValidationResult.ALLOWED, processed_command, warnings
        return None

    def _process_blocked_patterns(
        self,
        processed_command: str,
        warnings: list[str],
        context: dict[str, Any] | None,
    ) -> tuple[CommandValidationResult, str, list[str]] | None:
        has_blocked, blocked_pattern = CommandWhitelist.has_blocked_pattern(
            processed_command
        )
        if has_blocked and blocked_pattern is not None:
            return self._handle_blocked_pattern(
                processed_command, blocked_pattern, warnings, context
            )
        if has_blocked:
            warnings.append("Blocked pattern detected but pattern was unavailable")
            return CommandValidationResult.REJECTED, processed_command, warnings
        return None

    def _record_suspicious_params(
        self, processed_command: str, warnings: list[str]
    ) -> None:
        suspicious_patterns = CommandWhitelist.has_suspicious_params(processed_command)
        if suspicious_patterns:
            warnings.extend(
                f"Suspicious parameter detected: {pattern}"
                for pattern in suspicious_patterns
            )

    def _process_whitelist(
        self,
        processed_command: str,
        warnings: list[str],
        context: dict[str, Any] | None,
    ) -> tuple[CommandValidationResult, str, list[str]] | None:
        base_command = (
            processed_command.split()[0] if processed_command.split() else "unknown"
        )
        if (
            self.policy == SecurityPolicy.BLOCK
            and base_command in CommandWhitelist.DEVELOPMENT_COMMANDS
            and self.security_level != SecurityLevel.PERMISSIVE
        ):
            warnings.append(f"Command '{base_command}' not in allowed commands list")

        if base_command not in self.allowed_commands:
            return self._handle_not_whitelisted(
                processed_command, base_command, warnings, context
            )
        return None

    def _apply_security_policy(
        self, processed_command: str, warnings: list[str]
    ) -> tuple[CommandValidationResult, str, list[str]]:
        """Apply security policy based on warnings."""
        if self.policy == SecurityPolicy.SANITIZE:
            processed_command = self._sanitize_command(processed_command)
            warnings.append("Command sanitized for safety")
            return CommandValidationResult.MODIFIED, processed_command, warnings
        if self.policy == SecurityPolicy.WARN:
            warnings.append("Command allowed with warnings (policy=WARN)")
            return CommandValidationResult.ALLOWED, processed_command, warnings
        if self.policy == SecurityPolicy.ESCAPE:
            escaped_command = self._escape_dangerous_chars(processed_command)
            if escaped_command != processed_command:
                warnings.append("Dangerous characters escaped (policy=ESCAPE)")
            return CommandValidationResult.ALLOWED, escaped_command, warnings
        return CommandValidationResult.ALLOWED, processed_command, warnings

    def validate_command_args(
        self, command: str, args: list[str] | tuple[str, ...]
    ) -> tuple[CommandValidationResult, str, list[str]]:
        """Validate command with separate arguments (safer approach).

        Args:
            command: Base command to execute
            args: List of arguments to pass to the command

        Returns:
            Tuple of (validation_result, full_command, warnings)
        """
        warnings = []

        # Validate base command
        base_result, _, base_warnings = self.validate_command(command, {"args": args})
        warnings.extend(base_warnings)

        if base_result == CommandValidationResult.REJECTED:
            return CommandValidationResult.REJECTED, "", warnings

        # Validate each argument
        validated_args = []
        for i, arg in enumerate(args):
            arg_warnings = self._validate_argument(arg, i)
            warnings.extend(arg_warnings)

            if arg_warnings and self.policy == SecurityPolicy.BLOCK:
                return CommandValidationResult.REJECTED, "", warnings

            # Sanitize argument if needed
            if self.policy == SecurityPolicy.SANITIZE:
                sanitized_arg = self._sanitize_argument(arg)
            else:
                sanitized_arg = arg

            validated_args.append(sanitized_arg)

        # Construct safe command
        try:
            # Use shlex.quote for proper shell escaping
            full_command = (
                command + " " + " ".join(shlex.quote(arg) for arg in validated_args)
            )
            return CommandValidationResult.ALLOWED, full_command, warnings
        except Exception as exc:
            error_msg = f"Failed to construct safe command: {exc}"
            warnings.append(error_msg)
            return CommandValidationResult.REJECTED, "", warnings

    def create_safe_process(
        self, command: str, args: list[str] | None = None, **kwargs: Any
    ) -> tuple[bool, subprocess.Popen[str] | None, list[str]]:
        """Create a safe subprocess.Popen with validation.

        Args:
            command: Command to execute
            args: Command arguments (safer than passing command string)
            **kwargs: Additional arguments for subprocess.Popen

        Returns:
            Tuple of (success, process, warnings)
        """
        warnings: list[str] = []

        if args is not None:
            # Use argument-based validation (safer)
            result, full_command, cmd_warnings = self.validate_command_args(
                command, args
            )
        else:
            # Fallback to string validation
            result, full_command, cmd_warnings = self.validate_command(command)

        warnings.extend(cmd_warnings)

        if result == CommandValidationResult.REJECTED:
            return False, None, warnings

        try:
            # Set safe defaults
            safe_kwargs: dict[str, Any] = {
                "shell": False,  # Never use shell with argument lists
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if kwargs:
                warnings.append(
                    "Custom subprocess options are not supported; ignoring overrides"
                )

            # Create process with validated command
            process: subprocess.Popen[str]
            if args is not None:
                process = subprocess.Popen([command, *args], **safe_kwargs)
            else:
                # For string commands, use safe parsing
                parsed_args = shlex.split(full_command)
                process = subprocess.Popen(parsed_args, **safe_kwargs)

            self._log_security_event(
                "PROCESS_CREATED",
                {
                    "command": full_command[:200],
                    "pid": process.pid,
                    "security_level": self.security_level.value,
                },
            )

            return True, process, warnings

        except Exception as exc:
            error_msg = f"Failed to create process: {exc}"
            warnings.append(error_msg)
            self._log_security_event(
                "PROCESS_CREATION_FAILED",
                {
                    "command": full_command[:200],
                    "error": str(exc),
                    "security_level": self.security_level.value,
                },
            )
            return False, None, warnings

    def _validate_argument(self, arg: str, position: int) -> list[str]:
        """Validate a single command argument."""
        warnings: list[str] = []

        # Check for injection patterns in argument
        injection_patterns = [";", "&", "|", "`", "$(", "${", ">", "<", "*"]
        warnings.extend(
            f"Argument {position} contains injection character: {pattern}"
            for pattern in injection_patterns
            if pattern in arg
        )

        # Check for path traversal
        if "../" in arg or "..\\" in arg:
            warnings.append(f"Argument {position} contains path traversal: {arg[:50]}")

        # Check for suspicious file paths
        dangerous_paths = ["/etc/", "/proc/", "/sys/", "/dev/", "C:\\Windows\\System32"]
        warnings.extend(
            f"Argument {position} accesses dangerous path: {path}"
            for path in dangerous_paths
            if path in arg.lower()
        )

        return warnings

    def _sanitize_command(self, command: str) -> str:
        """Sanitize a command string."""
        # Remove dangerous patterns entirely
        sanitized = command

        # Remove command substitution
        sanitized = re.sub(r"\$\([^)]*\)", "", sanitized)
        sanitized = re.sub(r"`[^`]*`", "", sanitized)

        # Remove dangerous operators
        sanitized = re.sub(r"&&.*$", "", sanitized)
        sanitized = re.sub(r"\|\|.*$", "", sanitized)

        # Remove pipe redirects to shells
        sanitized = re.sub(
            r"\|\s*(sh|bash|cmd|powershell)", "", sanitized, flags=re.IGNORECASE
        )

        return sanitized.strip()

    def _sanitize_argument(self, arg: str) -> str:
        """Sanitize a command argument."""
        # Remove dangerous characters
        dangerous_chars = [";", "&", "|", "`", "$", "<", ">", "*"]
        sanitized = arg

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        return sanitized

    def _escape_dangerous_chars(self, command: str) -> str:
        """Escape dangerous characters (legacy behavior)."""
        dangerous_chars = ["|", "&", ";", "$(", "`", ">", "<", "*", "?", "[", "]"]
        escaped = command

        for char in dangerous_chars:
            if char in escaped:
                escaped = escaped.replace(char, f"\\{char}")

        return escaped

    def _log_security_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Log security event for audit purposes."""
        if not self.enable_audit_logging:
            return

        logger.warning(
            "Security Event: %s - %s",
            event_type,
            " | ".join(f"{k}={v}" for k, v in details.items()),
        )


# Convenience functions for backward compatibility
def create_command_validator(
    security_level: SecurityLevel = SecurityLevel.STANDARD,
    policy: SecurityPolicy = SecurityPolicy.BLOCK,
    **kwargs: Any,
) -> CommandValidator:
    """Create a CommandValidator with sensible defaults."""
    return CommandValidator(security_level=security_level, policy=policy, **kwargs)


def validate_command_safely(
    command: str,
    security_level: SecurityLevel = SecurityLevel.STANDARD,
    policy: SecurityPolicy = SecurityPolicy.BLOCK,
    context: dict[str, Any] | None = None,
) -> tuple[bool, str, list[str]]:
    """Validate a command using default settings.

    Args:
        command: Command to validate
        security_level: Security validation level
        policy: Security policy for handling issues
        context: Additional context

    Returns:
        Tuple of (is_safe, processed_command, warnings)
    """
    validator = CommandValidator(security_level=security_level, policy=policy)
    result, processed_command, warnings = validator.validate_command(command, context)

    is_safe = result in [
        CommandValidationResult.ALLOWED,
        CommandValidationResult.MODIFIED,
    ]
    return is_safe, processed_command, warnings


def get_safe_execution_allowed_commands(security_level: SecurityLevel) -> set[str]:
    """Get the list of commands allowed for safe execution."""
    return CommandWhitelist.get_allowed_commands(security_level)


# Export main classes and functions
__all__ = [
    "CommandValidationResult",
    "CommandValidator",
    "CommandWhitelist",
    "SecurityPolicy",
    "create_command_validator",
    "get_safe_execution_allowed_commands",
    "validate_command_safely",
]
