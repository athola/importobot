"""Tests ensuring code follows project automation philosophy from CLAUDE.md."""

import re

from importobot.core.keywords.generators.api_keywords import APIKeywordGenerator
from importobot.core.keywords.generators.ssh_keywords import SSHKeywordGenerator
from importobot.core.keywords.generators.web_keywords import WebKeywordGenerator


def _var_message(prefix: str, suffix: str, result: str) -> str:
    """Build an assertion helper message for variable validation."""
    return f"{prefix} {suffix} {result}"


class TestAutomationPhilosophyCompliance:
    """Verify code follows automation principles from CLAUDE.md."""

    def test_no_hardcoded_infrastructure_in_ssh_output(self):
        """SSH generators must not hardcode infrastructure details."""
        ssh_gen = SSHKeywordGenerator()

        # Test various empty/minimal inputs
        test_cases = ["", "empty", "no data", "test"]

        for test_data in test_cases:
            connect_result = ssh_gen.generate_connect_keyword(test_data)
            execute_result = ssh_gen.generate_execute_keyword(test_data)

            # Must not contain hardcoded infrastructure
            assert "localhost" not in connect_result
            assert "127.0.0.1" not in connect_result
            assert "admin" not in connect_result
            assert "testuser" not in connect_result
            assert "example.com" not in connect_result

            # Must not contain hardcoded commands
            assert "ls -la" not in execute_result
            assert "pwd" not in execute_result

            # Should use parameterized placeholders
            assert "${" in connect_result or "Open Connection" in connect_result
            assert "${" in execute_result

    def test_no_hardcoded_domains_in_web_output(self):
        """Web generators must not hardcode example domains."""
        web_gen = WebKeywordGenerator()

        test_cases = ["", "navigate", "go to", "test"]

        for test_data in test_cases:
            result = web_gen.generate_url_keyword(test_data)

            # Must not contain hardcoded domains
            assert "example.com" not in result
            assert "localhost" not in result
            assert "127.0.0.1" not in result

            # Should use parameterized URL
            assert "${URL}" in result

    def test_no_hardcoded_apis_in_api_output(self):
        """API generators must not hardcode API endpoints."""
        api_gen = APIKeywordGenerator()

        test_cases = ["", "session", "api call", "test"]

        for test_data in test_cases:
            result = api_gen.generate_session_keyword(test_data)

            # Must not contain hardcoded API domains
            assert "example.com" not in result
            assert "api.example.com" not in result
            assert "localhost" not in result

            # Should use parameterized API URL
            assert "${API_BASE_URL}" in result

    def test_generated_output_is_immediately_executable(self):
        """Generated Robot Framework output must be immediately executable."""
        ssh_gen = SSHKeywordGenerator()

        # Test that generated output contains only valid RF syntax
        connect_result = ssh_gen.generate_connect_keyword("")
        execute_result = ssh_gen.generate_execute_keyword("")

        # Valid Robot Framework syntax patterns
        rf_keyword_pattern = r"^[A-Za-z][A-Za-z0-9 ]*(?:\s+.*)?$"

        # Should be valid RF syntax
        assert re.match(rf_keyword_pattern, connect_result.strip())
        assert re.match(rf_keyword_pattern, execute_result.strip())

        # Should not contain placeholder text that requires manual editing
        assert "TODO" not in connect_result
        assert "FIXME" not in connect_result
        assert "CHANGE_ME" not in connect_result
        assert "UPDATE_THIS" not in connect_result

    def test_parameterized_variables_follow_rf_conventions(self):
        """Parameterized variables must follow Robot Framework conventions."""
        generators = [
            SSHKeywordGenerator(),
            WebKeywordGenerator(),
            APIKeywordGenerator(),
        ]

        test_cases = ["", "empty input", "minimal data"]

        for generator in generators:  # pylint: disable=too-many-nested-blocks
            for method_name in dir(generator):
                if method_name.startswith("generate_") and callable(
                    getattr(generator, method_name)
                ):
                    method = getattr(generator, method_name)

                    # Skip methods that require specific parameters
                    # or special signatures
                    if method_name in [
                        "generate_file_transfer_keyword",
                        "generate_directory_operations_keyword",
                    ]:
                        continue

                    # Handle methods that expect dictionary input differently
                    if method_name == "generate_step_keywords":
                        # This method expects a dictionary, not a string
                        for test_data in test_cases:
                            try:
                                # Use a sample dictionary matching expected step format
                                step_dict = {
                                    "description": test_data,
                                    "test_data": test_data,
                                }
                                result = method(step_dict)

                                variables = re.findall(r"\$\{([^}]+)\}", result)

                                for var in variables:
                                    message_prefix = f"Variable ${{{var}}}"
                                    upper_error = _var_message(
                                        message_prefix,
                                        "should be uppercase in",
                                        result,
                                    )
                                    no_space_error = _var_message(
                                        message_prefix,
                                        "should not contain spaces in",
                                        result,
                                    )
                                    descriptive_error = _var_message(
                                        message_prefix,
                                        "should be descriptive in",
                                        result,
                                    )

                                    assert var.isupper(), upper_error
                                    assert " " not in var, no_space_error
                                    assert len(var) > 1, descriptive_error

                            except TypeError:
                                # Skip methods with different signatures
                                continue
                        continue  # Skip to next method after handling this special case

                    for test_data in test_cases:
                        try:
                            if "file_transfer" in method_name:
                                result = method(test_data, "upload")
                            elif "directory" in method_name:
                                result = method(test_data, "create")
                            else:
                                result = method(test_data)

                            # Find all variable references
                            variables = re.findall(r"\$\{([^}]+)\}", result)

                            for var in variables:
                                # Must be uppercase Robot Framework convention
                                assert var.isupper(), (
                                    f"Variable ${{{var}}} should be uppercase in "
                                    f"{result}"
                                )
                                # Must not contain spaces
                                assert " " not in var, (
                                    f"Variable ${{{var}}} should not contain spaces "
                                    f"in {result}"
                                )
                                # Must be descriptive
                                assert len(var) > 1, (
                                    f"Variable ${{{var}}} should be descriptive in "
                                    f"{result}"
                                )

                        except TypeError:
                            # Skip methods with different signatures
                            continue

    def test_no_business_logic_assumptions_in_generators(self):
        """Generators must not make domain-specific business assumptions."""
        ssh_gen = SSHKeywordGenerator()

        # Test that generators don't assume specific business contexts
        test_data = "connect to database server"
        result = ssh_gen.generate_connect_keyword(test_data)

        # Should not inject business-specific assumptions
        assert "database" not in result  # Should not carry over business context
        assert "server" not in result  # Should extract only the technical parameters

        # Should focus only on SSH connection parameters
        assert "Open Connection" in result
        assert "${HOST}" in result or "Open Connection" in result

    def test_conversion_produces_consistent_output_format(self):
        """All generators must produce consistent Robot Framework format."""
        generators = [
            (SSHKeywordGenerator(), "generate_connect_keyword"),
            (WebKeywordGenerator(), "generate_url_keyword"),
            (APIKeywordGenerator(), "generate_session_keyword"),
        ]

        for generator, method_name in generators:
            method = getattr(generator, method_name)
            result = method("")

            # Must follow "Keyword    Arguments" format
            parts = result.split()
            assert len(parts) >= 1, f"Invalid format in {result}"

            # First part should be the keyword name
            keyword = parts[0]
            assert keyword[0].isupper(), (
                f"Keyword should start with uppercase: {keyword}"
            )

            # Should not end with unnecessary whitespace
            assert result == result.strip(), (
                f"Result should not have trailing whitespace: '{result}'"
            )
