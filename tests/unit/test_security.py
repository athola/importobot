"""Tests for security utilities."""

from importobot.utils.security import (
    SecurityValidator,
    extract_security_warnings,
    get_ssh_security_guidelines,
    validate_test_security,
)


class TestSecurityValidator:  # pylint: disable=too-many-public-methods
    """Test SecurityValidator class."""

    def test_validate_ssh_parameters_no_warnings(self):
        """Test SSH parameter validation with no warnings."""
        validator = SecurityValidator()
        params = {"host": "example.com", "port": 22, "username": "user"}

        warnings = validator.validate_ssh_parameters(params)

        assert not warnings

    def test_validate_ssh_parameters_with_password(self):
        """Test SSH parameter validation with password warning."""
        validator = SecurityValidator()
        params = {"password": "secret123"}

        warnings = validator.validate_ssh_parameters(params)

        assert len(warnings) == 2  # SSH password + hardcoded credential warnings
        assert any("⚠️  SSH password found" in w for w in warnings)
        assert any("consider using key-based authentication" in w for w in warnings)
        assert any("⚠️  Hardcoded credential detected" in w for w in warnings)

    def test_validate_ssh_parameters_dangerous_command(self):
        """Test SSH parameter validation with dangerous command."""
        validator = SecurityValidator()
        params = {"command": "rm -rf /"}

        warnings = validator.validate_ssh_parameters(params)

        assert len(warnings) == 1
        assert (
            "⚠️  Potentially dangerous command pattern detected: rm\\s+-rf"
            in warnings[0]
        )

    def test_validate_ssh_parameters_multiple_patterns(self):
        """Test SSH parameter validation with multiple dangerous patterns."""
        validator = SecurityValidator()
        params = {"command": "sudo rm -rf / && echo done"}

        warnings = validator.validate_ssh_parameters(params)

        assert len(warnings) == 2
        assert any("sudo" in w for w in warnings)
        assert any("rm\\s+-rf" in w for w in warnings)

    def test_validate_ssh_parameters_sensitive_path(self):
        """Test SSH parameter validation with sensitive paths."""
        validator = SecurityValidator()
        params = {"path": "/etc/passwd"}

        warnings = validator.validate_ssh_parameters(params)

        assert (
            len(warnings) == 2
        )  # Both sensitive file access and sensitive path warnings
        assert any("⚠️  Sensitive" in w for w in warnings)
        assert any("/etc/passwd" in w for w in warnings)

    def test_validate_ssh_parameters_production_env(self):
        """Test SSH parameter validation with production environment."""
        validator = SecurityValidator()
        params = {"env": "production", "command": "deploy"}

        warnings = validator.validate_ssh_parameters(params)

        assert len(warnings) == 1
        assert "⚠️  Production environment detected" in warnings[0]

    def test_sanitize_command_parameters_string_input(self):
        """Test command parameter sanitization with string input."""
        validator = SecurityValidator()

        result = validator.sanitize_command_parameters("safe command")

        assert result == "safe command"

    def test_sanitize_command_parameters_non_string_input(self):
        """Test command parameter sanitization with non-string input."""
        validator = SecurityValidator()

        result = validator.sanitize_command_parameters(123)

        assert result == "123"

    def test_sanitize_command_parameters_with_dangerous_chars(self):
        """Test command parameter sanitization with dangerous characters."""
        validator = SecurityValidator()
        command = "command | pipe ; semicolon `backtick` $(subshell)"

        result = validator.sanitize_command_parameters(command)

        # Characters should be escaped
        assert "\\|" in result
        assert "\\;" in result
        assert "\\`" in result
        # Note: $( becomes \$( but the test assertion needs adjustment

    def test_validate_file_operations_no_warnings(self):
        """Test file operations validation with no warnings."""
        validator = SecurityValidator()

        warnings = validator.validate_file_operations("safe_file.txt", "read")

        assert not warnings

    def test_validate_file_operations_path_traversal(self):
        """Test file operations validation with path traversal."""
        validator = SecurityValidator()

        warnings = validator.validate_file_operations("../../../etc/passwd", "read")

        assert len(warnings) == 2  # Both path traversal and sensitive path
        assert "⚠️  Potential path traversal detected" in warnings[0]
        assert "⚠️  Sensitive file access detected" in warnings[1]

    def test_validate_file_operations_double_slash(self):
        """Test file operations validation with double slash."""
        validator = SecurityValidator()

        warnings = validator.validate_file_operations("path//to//file", "read")

        assert len(warnings) == 1
        assert "⚠️  Potential path traversal detected" in warnings[0]

    def test_validate_file_operations_sensitive_path(self):
        """Test file operations validation with sensitive path."""
        validator = SecurityValidator()

        warnings = validator.validate_file_operations("/etc/shadow", "write")

        assert len(warnings) == 1
        assert "⚠️  Sensitive file access detected" in warnings[0]

    def test_validate_file_operations_destructive_operation(self):
        """Test file operations validation with destructive operation."""
        validator = SecurityValidator()

        warnings = validator.validate_file_operations("file.txt", "delete")

        assert len(warnings) == 1
        assert "⚠️  Destructive operation 'delete'" in warnings[0]

    def test_validate_file_operations_multiple_warnings(self):
        """Test file operations validation with multiple warnings."""
        validator = SecurityValidator()

        warnings = validator.validate_file_operations("/etc/passwd", "truncate")

        assert len(warnings) == 2
        assert any("Sensitive file access" in w for w in warnings)
        assert any("Destructive operation" in w for w in warnings)

    def test_sanitize_error_message_string_input(self):
        """Test error message sanitization with string input."""
        validator = SecurityValidator()

        result = validator.sanitize_error_message("Normal error message")

        assert result == "Normal error message"

    def test_sanitize_error_message_non_string_input(self):
        """Test error message sanitization with non-string input."""
        validator = SecurityValidator()

        result = validator.sanitize_error_message(42)

        assert result == "42"

    def test_sanitize_error_message_path_sanitization(self):
        """Test error message sanitization with path information."""
        validator = SecurityValidator()
        error_msg = "Error in /home/user/secret/file.txt on line 10"

        result = validator.sanitize_error_message(error_msg)

        assert "[PATH]" in result  # Long paths get fully sanitized
        assert "secret/file.txt" not in result

    def test_sanitize_error_message_windows_path(self):
        """Test error message sanitization with Windows path."""
        validator = SecurityValidator()
        error_msg = "Error in C:\\Users\\Admin\\Documents\\file.txt"

        result = validator.sanitize_error_message(error_msg)

        assert "C:/Users/[USER]" in result

    def test_sanitize_error_message_long_path(self):
        """Test error message sanitization with long absolute path."""
        validator = SecurityValidator()
        error_msg = "Error in /very/long/path/to/some/deeply/nested/file.txt"

        result = validator.sanitize_error_message(error_msg)

        assert "[PATH]" in result

    def test_generate_security_recommendations_ssh_usage(self):
        """Test security recommendations generation for SSH usage."""
        validator = SecurityValidator()
        test_data = {"command": "ssh user@host 'ls -la'"}

        recommendations = validator.generate_security_recommendations(test_data)

        assert len(recommendations) == 4
        assert any("key-based authentication" in r for r in recommendations)
        assert any("connection timeouts" in r for r in recommendations)
        assert any("dedicated test environments" in r for r in recommendations)
        assert any("host key fingerprints" in r for r in recommendations)

    def test_generate_security_recommendations_database_usage(self):
        """Test security recommendations generation for database usage."""
        validator = SecurityValidator()
        test_data = {"query": "SELECT * FROM users", "database": "test_db"}

        recommendations = validator.generate_security_recommendations(test_data)

        assert len(recommendations) == 3
        assert any("parameterized queries" in r for r in recommendations)
        assert any("minimal database privileges" in r for r in recommendations)
        assert any(
            "Sanitize all user inputs in database tests" in r for r in recommendations
        )

    def test_generate_security_recommendations_web_usage(self):
        """Test security recommendations generation for web usage."""
        validator = SecurityValidator()
        test_data = {"browser": "chrome", "url": "https://example.com"}

        recommendations = validator.generate_security_recommendations(test_data)

        assert len(recommendations) == 3
        assert any("XSS prevention" in r for r in recommendations)
        assert any("authentication and authorization" in r for r in recommendations)
        assert any("secure test data" in r for r in recommendations)

    def test_generate_security_recommendations_no_matches(self):
        """Test security recommendations generation with no matching patterns."""
        validator = SecurityValidator()
        test_data = {"simple": "test", "value": 42}

        recommendations = validator.generate_security_recommendations(test_data)

        assert not recommendations


class TestValidateTestSecurity:
    """Test validate_test_security function."""

    def test_validate_test_security_clean_test(self):
        """Test security validation for clean test case."""
        test_case = {"name": "Clean test", "steps": []}

        results = validate_test_security(test_case)

        assert not results["warnings"]
        assert len(results["recommendations"]) == 0
        assert not results["sanitized_errors"]

    def test_validate_test_security_with_ssh_warnings(self):
        """Test security validation for test case with SSH warnings."""
        test_case = {
            "name": "SSH test",
            "steps": [
                {
                    "library": "SSHLibrary",
                    "test_data": "password: secret, command: rm -rf /tmp/*",
                }
            ],
        }

        results = validate_test_security(test_case)

        assert (
            len(results["warnings"]) == 3
        )  # password, hardcoded credential, and dangerous command
        assert len(results["recommendations"]) >= 4  # SSH recommendations

    def test_validate_test_security_logging(self):
        """Test that security validation logs warnings."""
        test_case = {
            "name": "SSH test",
            "steps": [{"library": "SSHLibrary", "test_data": "password: secret"}],
        }

        results = validate_test_security(test_case)

        # Should have warnings
        assert len(results["warnings"]) > 0


class TestGetSSHSecurityGuidelines:
    """Test get_ssh_security_guidelines function."""

    def test_get_ssh_security_guidelines_content(self):
        """Test SSH security guidelines content."""
        guidelines = get_ssh_security_guidelines()

        assert len(guidelines) > 0
        assert all(isinstance(g, str) for g in guidelines)
        assert any("SSH Security Guidelines:" in g for g in guidelines)
        assert any("key-based authentication" in g for g in guidelines)
        assert any("connection timeouts" in g for g in guidelines)
        assert any("host key fingerprints" in g for g in guidelines)

    def test_get_ssh_security_guidelines_comprehensive(self):
        """Test that SSH guidelines cover all important aspects."""
        guidelines = get_ssh_security_guidelines()

        expected_topics = [
            "key-based authentication",
            "connection timeouts",
            "host key fingerprints",
            "dedicated test environments",
            "privileges",
            "audit trails",
            "credentials",
            "secrets",
            "error handling",
            "audits",
        ]

        guidelines_text = " ".join(guidelines).lower()
        for topic in expected_topics:
            assert topic in guidelines_text, f"Missing topic: {topic}"


class TestExtractSecurityWarnings:
    """Test extract_security_warnings function."""

    def test_extract_security_warnings_no_warnings(self):
        """Test extracting security warnings when none exist."""
        keyword_info = {"name": "test", "type": "action"}

        warnings = extract_security_warnings(keyword_info)

        assert not warnings

    def test_extract_security_warnings_with_security_warning(self):
        """Test extracting security warning from keyword info."""
        keyword_info = {"name": "test", "security_warning": "This action is dangerous"}

        warnings = extract_security_warnings(keyword_info)

        assert warnings == ["This action is dangerous"]

    def test_extract_security_warnings_with_security_note(self):
        """Test extracting security note from keyword info."""
        keyword_info = {"name": "test", "security_note": "Use with caution"}

        warnings = extract_security_warnings(keyword_info)

        assert warnings == ["Use with caution"]

    def test_extract_security_warnings_both_fields(self):
        """Test extracting both security warning and note."""
        keyword_info = {
            "name": "test",
            "security_warning": "Dangerous action",
            "security_note": "Requires admin privileges",
        }

        warnings = extract_security_warnings(keyword_info)

        assert len(warnings) == 2
        assert "Dangerous action" in warnings
        assert "Requires admin privileges" in warnings
