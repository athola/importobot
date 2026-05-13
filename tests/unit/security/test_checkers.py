"""Tests for security checker functions.

Tests cover:
- Command sanitization with configurable dangerous characters
- Default and custom dangerous character handling
"""

from __future__ import annotations

import pytest

from importobot.security.checkers import sanitize_command_parameters
from importobot.security.patterns import (
    DEFAULT_DANGEROUS_CHARS,
    SecurityPatterns,
)


class TestSanitizeCommandParameters:
    """Test the sanitize_command_parameters function."""

    def test_sanitize_with_default_dangerous_chars(self) -> None:
        """Test that default dangerous characters are escaped."""
        command = "echo hello | grep world"
        result = sanitize_command_parameters(command)

        # Pipe should be escaped by default
        assert "\\|" in result
        assert "echo hello" in result

    def test_sanitize_with_custom_dangerous_chars(self) -> None:
        """Test that custom dangerous characters can be provided."""
        command = "echo hello | grep world"
        # Only escape pipes, not other chars
        custom_chars = ["|"]
        result = sanitize_command_parameters(command, dangerous_chars=custom_chars)

        assert "\\|" in result
        assert "echo hello" in result

    def test_sanitize_with_empty_dangerous_chars(self) -> None:
        """Test that empty dangerous_chars list disables escaping."""
        command = "echo hello | grep world"
        result = sanitize_command_parameters(command, dangerous_chars=[])

        # Nothing should be escaped
        assert result == command
        assert "\\|" not in result

    def test_sanitize_all_default_chars(self) -> None:
        """Test that all default dangerous chars are escaped."""
        # Command containing all default dangerous chars
        command = "cmd | arg & more ; $(sub) `tick` > out < in * ? [bracket]"
        result = sanitize_command_parameters(command)

        # All should be escaped
        for char in DEFAULT_DANGEROUS_CHARS:
            assert f"\\{char}" in result or char not in command

    def test_sanitize_non_string_input(self) -> None:
        """Test that non-string input is converted to string."""
        result = sanitize_command_parameters(123)
        assert result == "123"

    def test_sanitize_preserves_safe_content(self) -> None:
        """Test that safe content is preserved."""
        command = "ls -la /home/user"
        result = sanitize_command_parameters(command)

        assert result == command  # No dangerous chars, no changes


class TestDefaultDangerousChars:
    """Test the DEFAULT_DANGEROUS_CHARS constant."""

    def test_default_dangerous_chars_exists(self) -> None:
        """Test that DEFAULT_DANGEROUS_CHARS is defined."""
        assert DEFAULT_DANGEROUS_CHARS is not None
        assert isinstance(DEFAULT_DANGEROUS_CHARS, list)

    def test_default_dangerous_chars_contains_expected(self) -> None:
        """Test that expected dangerous characters are in defaults."""
        expected = ["|", "&", ";", "$(", "`", ">", "<", "*", "?", "[", "]"]
        for char in expected:
            assert char in DEFAULT_DANGEROUS_CHARS

    def test_default_dangerous_chars_immutable_pattern(self) -> None:
        """Test that the default list follows the immutable pattern."""
        # The module-level constant should be a list
        assert isinstance(DEFAULT_DANGEROUS_CHARS, list)


class TestSecurityPatternsGetDangerousChars:
    """Test the SecurityPatterns.get_dangerous_chars method."""

    def test_get_dangerous_chars_returns_defaults(self) -> None:
        """Test that get_dangerous_chars returns defaults when no custom provided."""
        chars = SecurityPatterns.get_dangerous_chars()
        assert chars == DEFAULT_DANGEROUS_CHARS

    def test_get_dangerous_chars_with_custom(self) -> None:
        """Test that get_dangerous_chars accepts custom list."""
        custom = ["|", "&"]
        chars = SecurityPatterns.get_dangerous_chars(custom_chars=custom)
        assert chars == custom

    def test_get_dangerous_chars_with_additional(self) -> None:
        """Test that get_dangerous_chars can extend defaults."""
        additional = ["@", "#"]
        chars = SecurityPatterns.get_dangerous_chars(additional_chars=additional)

        # Should contain defaults plus additional
        for char in DEFAULT_DANGEROUS_CHARS:
            assert char in chars
        for char in additional:
            assert char in chars


if __name__ == "__main__":
    pytest.main([__file__])
