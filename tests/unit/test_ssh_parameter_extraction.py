"""Tests for SSH keyword parameter extraction and formatting."""

from typing import Any

import pytest

from importobot.core.keywords.generators.ssh_keywords import SSHKeywordGenerator
from importobot.utils.pattern_extraction import extract_pattern
from importobot.utils.validation import (
    convert_parameters_to_robot_variables,
    format_robot_framework_arguments,
    sanitize_robot_string,
)


class TestSSHParameterExtraction:
    """Tests for SSH parameter extraction and pattern matching."""

    @pytest.fixture
    def ssh_generator(self):
        """Return an SSHKeywordGenerator instance."""
        return SSHKeywordGenerator()

    def test_extract_pattern_case_insensitive(self):
        """Test that pattern extraction is case insensitive."""
        test_data = "HOST: example.com USERNAME: testuser PASSWORD: testpass"

        host = extract_pattern(test_data, r"(?:host|server):\s*([^,\s]+)")
        username = extract_pattern(test_data, r"username:\s*([^,\s]+)")
        password = extract_pattern(test_data, r"password:\s*([^,\s]+)")

        assert host == "example.com"
        assert username == "testuser"
        assert password == "testpass"

    def test_extract_pattern_with_different_separators(self):
        """Test pattern extraction with various separators."""
        test_cases: list[tuple[str, str]] = [
            ("host: example.com", "example.com"),
            ("host=example.com", ""),  # Should not match with = separator
            ("host : example.com", "example.com"),  # Extra spaces
            ("host:example.com", "example.com"),  # No space after colon
            ("host:\texample.com", "example.com"),  # Tab separator
        ]

        for test_data, expected in test_cases:
            result = extract_pattern(test_data, r"(?:host|server)\s*:\s*([^,\s]+)")
            assert result == expected, f"Failed for: {test_data}"

    def test_extract_pattern_with_special_characters(self):
        """Test pattern extraction with special characters in values."""
        test_cases: list[tuple[str, str]] = [
            ("host: example-server.com", "example-server.com"),
            ("host: 192.168.1.100", "192.168.1.100"),
            ("username: user_name", "user_name"),
            ("password: pass@word123", "pass@word123"),
            ("file: /path/to/file.txt", "/path/to/file.txt"),
            (
                "command: ls -la | grep test",
                "ls",
            ),  # Should stop at space for this pattern
        ]

        for test_data, expected in test_cases:
            if "file:" in test_data:
                result = extract_pattern(test_data, r"(?:file|path):\s*([^,\s]+)")
            elif "command:" in test_data:
                result = extract_pattern(test_data, r"(?:command|cmd):\s*([^,\s]+)")
            else:
                result = extract_pattern(
                    test_data, r"(?:host|server|username|password):\s*([^,\s]+)"
                )
            assert result == expected, f"Failed for: {test_data}"

    def test_extract_pattern_with_quoted_values(self):
        """Test pattern extraction with quoted values."""
        test_data = 'command: "ls -la ./user" file: "./path with spaces/file.txt"'

        # Current implementation may not handle quotes - testing actual behavior
        command = extract_pattern(test_data, r"(?:command|cmd):\s*(.+)")
        assert command == '"ls -la ./user" file: "./path with spaces/file.txt"'

    def test_extract_pattern_multiple_matches(self):
        """Test pattern extraction when multiple matches exist."""
        test_data = "host: first.com, host: second.com, server: third.com"

        # Should return the first match
        result = extract_pattern(test_data, r"(?:host|server):\s*([^,\s]+)")
        assert result == "first.com"

    def test_extract_pattern_no_match(self):
        """Test pattern extraction when no match is found."""
        test_data = "some random data without patterns"

        result = extract_pattern(test_data, r"(?:host|server):\s*([^,\s]+)")
        assert result == ""

    def test_extract_pattern_empty_input(self):
        """Test pattern extraction with empty input."""
        result = extract_pattern("", r"(?:host|server):\s*([^,\s]+)")
        assert result == ""

    def test_ssh_command_parsing(self, ssh_generator):
        """Test SSH command format parsing."""
        test_cases: list[tuple[str, str, str]] = [
            ("ssh user@host.com", "user", "host.com"),
            ("ssh admin@192.168.1.100", "admin", "192.168.1.100"),
            ("ssh deploy@prod-server.example.com", "deploy", "prod-server.example.com"),
            ("SSH testuser@test.local", "testuser", "test.local"),  # Case insensitive
        ]

        for test_data, expected_user, expected_host in test_cases:
            # Test the connection keyword generation which uses this parsing
            result = ssh_generator.generate_connect_keyword(test_data)
            expected = f"Open Connection    {expected_host}    {expected_user}"
            assert result == expected, f"Failed for: {test_data}"

    def test_file_path_extraction_patterns(self):
        """Test various file path extraction patterns."""
        test_cases: list[tuple[str, str]] = [
            # Different field names
            ("source: /local/file", "/local/file"),
            ("from: /local/file", "/local/file"),
            ("file: /local/file", "/local/file"),
            ("path: /local/file", "/local/file"),
            # Different path formats
            ("source: /absolute/path/file.txt", "/absolute/path/file.txt"),
            ("source: relative/path/file.txt", "relative/path/file.txt"),
            ("source: ./current/dir/file.txt", "./current/dir/file.txt"),
            ("source: ../parent/dir/file.txt", "../parent/dir/file.txt"),
            ("source: ~/home/user/file.txt", "~/home/user/file.txt"),
        ]

        for test_data, expected in test_cases:
            result = extract_pattern(
                test_data, r"(?:source|from|file|path):\s*([^,\s]+)"
            )
            assert result == expected, f"Failed for: {test_data}"

    def test_command_extraction_patterns(self):
        """Test command extraction patterns."""
        test_cases: list[tuple[str, str]] = [
            ("command: ls -la", "ls -la"),
            ("cmd: pwd", "pwd"),
            ("command: systemctl status nginx", "systemctl status nginx"),
            (
                "cmd: python3 /path/to/script.py --arg value",
                "python3 /path/to/script.py --arg value",
            ),
        ]

        for test_data, expected in test_cases:
            result = extract_pattern(test_data, r"(?:command|cmd):\s*(.+)")
            assert result == expected, f"Failed for: {test_data}"

    def test_complex_data_extraction(self):
        """Test extraction from complex multi-field data."""
        complex_data = """
        host: production.example.com
        username: deploy
        password: secure_password_123
        port: 2222
        source: /local/deployment/app.tar.gz
        destination: /opt/app/releases/
        command: tar -xzf app.tar.gz && systemctl restart app
        logfile: /var/log/deployment.log
        """

        extractions = [
            (r"(?:host|server):\s*([^,\s]+)", "production.example.com"),
            (r"username:\s*([^,\s]+)", "deploy"),
            (r"password:\s*([^,\s]+)", "secure_password_123"),
            (r"port:\s*([^,\s]+)", "2222"),
            (r"(?:source|from):\s*([^,\s]+)", "/local/deployment/app.tar.gz"),
            (r"(?:destination|dest|to):\s*([^,\s]+)", "/opt/app/releases/"),
            (
                r"(?:command|cmd):\s*(.+)",
                "tar -xzf app.tar.gz && systemctl restart app",
            ),
            (r"(?:logfile|log):\s*([^,\s]+)", "/var/log/deployment.log"),
        ]

        for pattern, expected in extractions:
            result = extract_pattern(complex_data, pattern)
            if "command" in pattern:
                # Command extraction gets everything after the pattern until end
                assert result.startswith(expected.split("        ", maxsplit=1)[0]), (
                    "Command extraction failed"
                )
            else:
                assert result == expected, f"Failed for pattern: {pattern}"


class TestSSHParameterFormatting:
    """Tests for SSH parameter formatting and Robot Framework argument generation."""

    def test_format_robot_framework_arguments_basic(self):
        """Test basic Robot Framework argument formatting."""
        result = format_robot_framework_arguments(
            "Open Connection", "host.com", "user", "pass"
        )
        expected = "Open Connection    host.com    user    pass"
        assert result == expected

    def test_format_robot_framework_arguments_single_arg(self):
        """Test Robot Framework formatting with single argument."""
        result = format_robot_framework_arguments("Close Connection")
        expected = "Close Connection"
        assert result == expected

    def test_format_robot_framework_arguments_empty_args(self):
        """Test Robot Framework formatting with empty arguments."""
        result = format_robot_framework_arguments("Read")
        expected = "Read"
        assert result == expected

    def test_format_robot_framework_arguments_with_special_chars(self):
        """Test Robot Framework formatting with special characters."""
        result = format_robot_framework_arguments(
            "Execute Command", "ls -la | grep test"
        )
        expected = "Execute Command    ls -la | grep test"
        assert result == expected

    def test_sanitize_robot_string_basic(self):
        """Test basic Robot Framework string sanitization."""
        test_cases: list[tuple[str, str]] = [
            ("normal_string", "normal_string"),
            ("string with spaces", "string with spaces"),
            ("string/with/slashes", "string/with/slashes"),
            ("string-with-dashes", "string-with-dashes"),
            ("string_with_underscores", "string_with_underscores"),
        ]

        for input_str, expected in test_cases:
            result = sanitize_robot_string(input_str)
            assert result == expected, f"Failed for: {input_str}"

    def test_sanitize_robot_string_with_variables(self):
        """Test Robot Framework string sanitization with variables."""
        test_cases: list[tuple[str, str]] = [
            ("${variable}", "${variable}"),
            ("string with ${variable}", "string with ${variable}"),
            ("${var1} and ${var2}", "${var1} and ${var2}"),
        ]

        for input_str, expected in test_cases:
            result = sanitize_robot_string(input_str)
            assert result == expected, f"Failed for: {input_str}"

    def test_convert_parameters_to_robot_variables(self):
        """Test conversion of parameters to Robot Framework variables."""
        # Test with string containing parameter placeholders
        text_with_params = "ssh {username}@{host} && {command}"

        result = convert_parameters_to_robot_variables(text_with_params)

        assert "${host}" in result
        assert "${username}" in result
        assert "${command}" in result
        assert result == "ssh ${username}@${host} && ${command}"

    def test_ssh_keyword_parameter_combinations(self):
        """Test SSH keyword generation with various parameter combinations."""
        ssh_generator = SSHKeywordGenerator()

        test_cases: list[dict[str, Any]] = [
            {
                "method": "generate_connect_keyword",
                "input": "host: server.com username: user",
                "expected": "Open Connection    server.com    user",
            },
            {
                "method": "generate_connect_keyword",
                "input": "host: server.com username: user password: pass",
                "expected": "Open Connection    server.com    user    pass",
            },
            {
                "method": "generate_file_transfer_keyword",
                "input": "source: /local destination: /remote",
                "operation": "upload",
                "expected": "Put File    /local    /remote",
            },
            {
                "method": "generate_file_verification_keyword",
                "input": "file: /path/to/file",
                "should_exist": True,
                "expected": "File Should Exist    /path/to/file",
            },
        ]

        for test_case in test_cases:
            method = getattr(ssh_generator, test_case["method"])

            if test_case["method"] == "generate_file_transfer_keyword":
                # pylint: disable=unexpected-keyword-arg
                result = method(test_case["input"], operation=test_case["operation"])
            elif test_case["method"] == "generate_file_verification_keyword":
                # pylint: disable=unexpected-keyword-arg
                result = method(
                    test_case["input"], should_exist=test_case["should_exist"]
                )
            else:
                result = method(test_case["input"])

            assert result == test_case["expected"], f"Failed for {test_case['method']}"

    def test_ssh_parameter_empty_input_handling(self):
        """Test SSH parameter generation with empty input data."""
        ssh_generator = SSHKeywordGenerator()

        # Test handling when parameters are missing from input
        empty_input_cases = [
            {
                "method": "generate_connect_keyword",
                "input": "",
                "expected": "Open Connection    ${HOST}",
            },
            {
                "method": "generate_execute_keyword",
                "input": "",
                "expected": "Execute Command    ${COMMAND}",
            },
            {
                "method": "generate_file_transfer_keyword",
                "input": "",
                "operation": "upload",
                "expected": "Put File    ${SOURCE_FILE}    ${DESTINATION_PATH}",
            },
        ]

        for case in empty_input_cases:
            method = getattr(ssh_generator, case["method"])

            if case["method"] == "generate_file_transfer_keyword":
                # pylint: disable=too-many-function-args
                result = method(case["input"], case["operation"])
            else:
                result = method(case["input"])

            assert result == case["expected"], (
                f"Empty input handling failed for {case['method']}"
            )

    def test_ssh_parameter_edge_cases(self):
        """Test SSH parameter extraction with edge cases."""

        edge_cases = [
            # Whitespace handling
            ("  host:   example.com  ", r"(?:host|server):\s*([^,\s]+)", "example.com"),
            ("host:\t\texample.com", r"(?:host|server):\s*([^,\s]+)", "example.com"),
            # Multiple colons
            (
                "host: example.com:8080",
                r"(?:host|server):\s*([^,\s]+)",
                "example.com:8080",
            ),
            # Numbers and special characters
            ("port: 2222", r"port:\s*([^,\s]+)", "2222"),
            ("timeout: 30s", r"timeout:\s*([^,\s]+)", "30s"),
            # Empty values
            ("host: ", r"(?:host|server):\s*([^,\s]+)", ""),
            ("username:", r"username:\s*([^,\s]+)", ""),
        ]

        for test_data, pattern, expected in edge_cases:
            result = extract_pattern(test_data, pattern)
            assert result == expected, f"Edge case failed: {test_data}"

    def test_ssh_parameter_security_considerations(self):
        """Test parameter extraction with security considerations."""
        ssh_generator = SSHKeywordGenerator()

        # Test that sensitive parameters are extracted but not exposed inappropriately
        sensitive_data = (
            "username: admin password: super_secret_password_123 "
            "keyfile: /path/to/secret.key"
        )

        username = extract_pattern(sensitive_data, r"username:\s*([^,\s]+)")
        password = extract_pattern(sensitive_data, r"password:\s*([^,\s]+)")
        keyfile = extract_pattern(sensitive_data, r"(?:key|keyfile):\s*([^,\s]+)")

        # Extraction should work
        assert username == "admin"
        assert password == "super_secret_password_123"
        assert keyfile == "/path/to/secret.key"

        # But generated keywords should use proper Robot Framework format
        connect_result = ssh_generator.generate_connect_keyword(sensitive_data)
        assert "admin" in connect_result
        assert "super_secret_password_123" in connect_result

    def test_ssh_parameter_validation_integration(self):
        """Test integration between parameter extraction and validation."""
        ssh_generator = SSHKeywordGenerator()

        # Test various parameter formats that should all work
        valid_formats = [
            "host: example.com username: user password: pass",
            "HOST: EXAMPLE.COM USERNAME: USER PASSWORD: PASS",
            "host : example.com , username : user , password : pass",
            "host:example.com username:user password:pass",
        ]

        for format_data in valid_formats:
            result = ssh_generator.generate_connect_keyword(format_data)
            # All should generate valid connection keywords
            assert result.startswith("Open Connection"), (
                f"Invalid result for: {format_data}"
            )
            assert "example.com" in result.lower() or "EXAMPLE.COM" in result
            assert "user" in result.lower() or "USER" in result
