"""Comprehensive generative tests ensuring all 42 SSH keywords are covered."""

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from importobot.core.converter import convert_file
from importobot.utils.test_generation.ssh_generator import SSHKeywordTestGenerator
from tests.shared_ssh_test_data import (
    ALL_SSH_KEYWORDS,
    EXPECTED_SSH_KEYWORD_COUNT,
    EXPECTED_TOTAL_SSH_TESTS,
    get_basic_ssh_connection_keywords,
)

pytestmark = pytest.mark.slow


class TestSSHComprehensiveCoverage:
    """Comprehensive generative tests for all SSH keywords."""

    @pytest.fixture
    def ssh_generator(self):
        """Initialize SSH keyword test generator."""
        return SSHKeywordTestGenerator()

    @pytest.fixture
    def all_ssh_keywords(self):
        """List of all 42 SSH keywords that must be covered."""
        return ALL_SSH_KEYWORDS

    def test_ssh_keyword_count_completeness(self, all_ssh_keywords):
        """Verify we have all 42 SSH keywords defined."""
        assert len(all_ssh_keywords) == EXPECTED_SSH_KEYWORD_COUNT, (
            f"Expected {EXPECTED_SSH_KEYWORD_COUNT} SSH keywords, "
            f"got {len(all_ssh_keywords)}"
        )

    def test_ssh_generator_covers_all_keywords(self, ssh_generator, all_ssh_keywords):
        """Verify SSH generator can generate tests for all keywords."""
        covered_keywords = set(ssh_generator.keyword_generators.keys())
        expected_keywords = set(all_ssh_keywords)

        missing_keywords = expected_keywords - covered_keywords
        extra_keywords = covered_keywords - expected_keywords

        assert not missing_keywords, f"Missing keyword generators: {missing_keywords}"
        assert not extra_keywords, f"Extra keyword generators: {extra_keywords}"
        assert len(covered_keywords) == EXPECTED_SSH_KEYWORD_COUNT, (
            f"Expected {EXPECTED_SSH_KEYWORD_COUNT} generators, "
            f"got {len(covered_keywords)}"
        )

    @pytest.mark.parametrize(
        "keyword",
        [
            # Connection Management
            "Open Connection",
            "Close Connection",
            "Close All Connections",
            "Switch Connection",
            "Get Connection",
            "Get Connections",
            # Authentication
            "Login",
            "Login With Public Key",
            # Configuration
            "Set Default Configuration",
            "Set Client Configuration",
            # Command Execution
            "Execute Command",
            "Start Command",
            "Read Command Output",
            # File Operations
            "Put File",
            "Put Directory",
            "Get File",
            "Get Directory",
            "Create File",
            "Remove File",
            "Move File",
            "Get File Size",
            "Get File Permissions",
            "Set File Permissions",
            # Directory Operations
            "List Directory",
            "List Files In Directory",
            "List Directories In Directory",
            "Create Directory",
            "Remove Directory",
            "Move Directory",
            # File/Directory Verification
            "File Should Exist",
            "File Should Not Exist",
            "Directory Should Exist",
            "Directory Should Not Exist",
            # Interactive Shell
            "Write",
            "Write Bare",
            "Read",
            "Read Until",
            "Read Until Prompt",
            "Read Until Regexp",
            "Write Until Expected Output",
            # Logging
            "Enable Ssh Logging",
            "Disable Ssh Logging",
        ],
    )
    def test_generate_individual_ssh_keyword_test(self, ssh_generator, keyword):
        """Test generation of individual SSH keyword test cases."""
        # Generate test case for the specific keyword
        test_case = ssh_generator.generate_ssh_keyword_test(keyword)

        # Validate test case structure
        assert "test_case" in test_case
        assert "name" in test_case["test_case"]
        assert "description" in test_case["test_case"]
        assert "steps" in test_case["test_case"]
        assert len(test_case["test_case"]["steps"]) > 0

        # Validate step structure
        step = test_case["test_case"]["steps"][0]
        assert "step" in step
        assert "test_data" in step
        assert "expected" in step

        # Verify test case can be converted to Robot Framework
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(test_case, temp_file, indent=2)
            temp_file_path = temp_file.name

        try:
            robot_file_path = None
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".robot", delete=False
            ) as robot_file:
                robot_file_path = robot_file.name

            # Convert to Robot Framework
            convert_file(temp_file_path, robot_file_path)
            # Verify Robot file was created and has content
            robot_path = Path(robot_file_path)
            assert robot_path.exists(), f"Robot file not created for {keyword}"

            robot_content = robot_path.read_text(encoding="utf-8")
            assert len(robot_content) > 0, f"Robot file is empty for {keyword}"
            assert "SSHLibrary" in robot_content, (
                f"SSHLibrary not imported for {keyword}"
            )

        finally:
            # Cleanup
            Path(temp_file_path).unlink(missing_ok=True)
            if robot_file_path:
                Path(robot_file_path).unlink(missing_ok=True)

    def test_generate_all_ssh_keyword_tests(self, ssh_generator):
        """Test generation of all SSH keyword test cases in bulk."""
        all_tests = ssh_generator.generate_all_ssh_keyword_tests()

        # Should have 3 variations per keyword
        assert len(all_tests) == EXPECTED_TOTAL_SSH_TESTS, (
            f"Expected {EXPECTED_TOTAL_SSH_TESTS} test variations, got {len(all_tests)}"
        )

        # Verify all keywords are represented
        keywords_covered = set()
        for test in all_tests:
            assert "keyword_focus" in test
            keywords_covered.add(test["keyword_focus"])

        assert len(keywords_covered) == EXPECTED_SSH_KEYWORD_COUNT, (
            f"Expected 42 unique keywords, got {len(keywords_covered)}"
        )

    def test_ssh_keyword_test_data_realism(self, ssh_generator, all_ssh_keywords):
        """Verify that generated test data is realistic and varied."""
        # Generate multiple test cases for each keyword and check variety
        for keyword in all_ssh_keywords[:5]:  # Test first 5 keywords for performance
            test_cases = []
            for _ in range(5):
                test_case = ssh_generator.generate_ssh_keyword_test(keyword)
                test_cases.append(test_case)

            # Verify test cases have some variation
            test_data_strings = [
                test["test_case"]["steps"][0]["test_data"] for test in test_cases
            ]

            # Should have some variation in test data (not all identical)
            unique_data = set(test_data_strings)
            assert len(unique_data) > 1 or len(test_data_strings[0]) == 0, (
                f"No variation in test data for {keyword}: {test_data_strings}"
            )

    def test_ssh_connection_keywords_integration(self, ssh_generator):
        """Test that connection-related keywords work together."""
        connection_keywords = [
            "Open Connection",
            "Login",
            "Execute Command",
            "Close Connection",
        ]

        integrated_test_case: dict[str, Any] = {
            "test_case": {
                "name": "SSH Integration Test - Connection Workflow",
                "description": "Complete SSH connection workflow test",
                "steps": [],
            }
        }

        # Generate steps for each connection keyword
        for keyword in connection_keywords:
            individual_test = ssh_generator.generate_ssh_keyword_test(keyword)
            step = individual_test["test_case"]["steps"][0]
            integrated_test_case["test_case"]["steps"].append(step)

        # Verify integrated test case structure
        assert len(integrated_test_case["test_case"]["steps"]) == 4

        # Test conversion to Robot Framework
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(integrated_test_case, temp_file, indent=2)
            temp_file_path = temp_file.name

        try:
            robot_file_path = None
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".robot", delete=False
            ) as robot_file:
                robot_file_path = robot_file.name

            # convert_file raises exception on failure, returns None on success
            convert_file(temp_file_path, robot_file_path)

            robot_content = Path(robot_file_path).read_text(encoding="utf-8")

            # Verify all connection keywords are present
            assert "Open Connection" in robot_content
            assert "Login" in robot_content or "Execute Command" in robot_content
            assert "Close Connection" in robot_content

        finally:
            Path(temp_file_path).unlink(missing_ok=True)
            if robot_file_path:
                Path(robot_file_path).unlink(missing_ok=True)

    def test_ssh_file_operations_integration(self, ssh_generator):
        """Test that file operation keywords work together."""
        file_keywords = [
            "Put File",
            "File Should Exist",
            "Get File Permissions",
            "Remove File",
        ]

        file_workflow_test: dict[str, Any] = {
            "test_case": {
                "name": "SSH File Operations Workflow",
                "description": "Complete file operations workflow test",
                "steps": [],
            }
        }

        # Generate steps for file operations
        for keyword in file_keywords:
            individual_test = ssh_generator.generate_ssh_keyword_test(keyword)
            step = individual_test["test_case"]["steps"][0]
            file_workflow_test["test_case"]["steps"].append(step)

        # Test conversion
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(file_workflow_test, temp_file, indent=2)
            temp_file_path = temp_file.name

        try:
            robot_file_path = None
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".robot", delete=False
            ) as robot_file:
                robot_file_path = robot_file.name

            # convert_file raises exception on failure, returns None on success
            convert_file(temp_file_path, robot_file_path)

        finally:
            Path(temp_file_path).unlink(missing_ok=True)
            if robot_file_path:
                Path(robot_file_path).unlink(missing_ok=True)

    def test_ssh_interactive_shell_workflow(self, ssh_generator):
        """Test interactive shell operation sequence."""
        shell_keywords = [
            "Write",
            "Read Until Prompt",
            "Execute Command",
            "Read Command Output",
        ]

        shell_workflow_test: dict[str, Any] = {
            "test_case": {
                "name": "SSH Interactive Shell Workflow",
                "description": "Interactive shell operations workflow",
                "steps": [],
            }
        }

        for keyword in shell_keywords:
            individual_test = ssh_generator.generate_ssh_keyword_test(keyword)
            step = individual_test["test_case"]["steps"][0]
            shell_workflow_test["test_case"]["steps"].append(step)

        # Verify workflow makes sense
        steps = shell_workflow_test["test_case"]["steps"]
        assert len(steps) == 4
        assert "write" in steps[0]["step"].lower()
        assert "read" in steps[1]["step"].lower()

    def test_ssh_comprehensive_scenario_generation(self, ssh_generator):
        """Generate a comprehensive SSH scenario using multiple keyword categories."""
        # Select representative keywords from each category
        scenario_keywords = [
            "Open Connection",  # Connection
            "Login With Public Key",  # Authentication
            "Set Client Configuration",  # Configuration
            "Execute Command",  # Command execution
            "Put File",  # File operations
            "Create Directory",  # Directory operations
            "File Should Exist",  # Verification
            "Write",  # Interactive shell
            "Enable Ssh Logging",  # Logging
        ]

        comprehensive_scenario: dict[str, Any] = {
            "test_case": {
                "name": "SSH Comprehensive Deployment Scenario",
                "description": "Complete SSH deployment and verification scenario",
                "steps": [],
            }
        }

        # Generate realistic deployment scenario
        for keyword in scenario_keywords:
            individual_test = ssh_generator.generate_ssh_keyword_test(keyword)
            step = individual_test["test_case"]["steps"][0]
            comprehensive_scenario["test_case"]["steps"].append(step)

        # Verify comprehensive scenario
        assert len(comprehensive_scenario["test_case"]["steps"]) == 9

        # Test conversion to Robot Framework
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(comprehensive_scenario, temp_file, indent=2)
            temp_file_path = temp_file.name

        try:
            robot_file_path = None
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".robot", delete=False
            ) as robot_file:
                robot_file_path = robot_file.name

            # convert_file raises exception on failure, returns None on success
            convert_file(temp_file_path, robot_file_path)

            robot_content = Path(robot_file_path).read_text(encoding="utf-8")

            # Verify that SSH functionality is present in the Robot Framework output
            # The conversion engine may choose different libraries for the same
            # functionality
            required_functionality = [
                ("SSH Connection", ["Open Connection"]),
                ("SSH Authentication", ["Login With Public Key"]),
                ("SSH Configuration", ["Set Client Configuration"]),
                (
                    "Command Execution",
                    ["Execute Command", "Run Process"],
                ),  # May use either SSH or Process library
                ("File Transfer", ["Put File"]),
                ("Directory Creation", ["Create Directory"]),
                ("File Verification", ["File Should Exist"]),
                ("Shell Interaction", ["Write"]),
                (
                    "SSH Logging",
                    ["Enable Ssh Logging", "Enable SSH session logging"],
                ),
            ]

            missing_functionality = []
            for functionality_name, possible_keywords in required_functionality:
                found = any(keyword in robot_content for keyword in possible_keywords)
                if not found:
                    missing_functionality.append(
                        f"{functionality_name} (expected one of: {possible_keywords})"
                    )

            assert not missing_functionality, (
                f"Missing functionality: {missing_functionality}. "
                f"Robot content preview: {robot_content[:500]}..."
            )

        finally:
            Path(temp_file_path).unlink(missing_ok=True)
            if robot_file_path:
                Path(robot_file_path).unlink(missing_ok=True)

    def test_ssh_keyword_security_considerations(self, ssh_generator):
        """Test that security-sensitive keywords generate appropriate test data."""
        security_keywords = [
            "Login",
            "Login With Public Key",
            "Put File",
            "Execute Command",
        ]

        for keyword in security_keywords:
            test_case = ssh_generator.generate_ssh_keyword_test(keyword)
            step = test_case["test_case"]["steps"][0]
            test_data = step["test_data"]

            # Security checks based on keyword
            if keyword == "Login":
                assert "password:" in test_data.lower()
                # Password should not be obvious/weak
                assert "password123" not in test_data.lower()
                assert (
                    "admin" not in test_data.lower() or "root" not in test_data.lower()
                )

            elif keyword == "Login With Public Key":
                assert "keyfile:" in test_data.lower()
                # Should reference a key file path
                assert ".ssh" in test_data or "key" in test_data

            elif keyword == "Execute Command":
                assert "command:" in test_data.lower()
                # Should not contain obviously dangerous commands
                command_text = test_data.lower()
                dangerous_patterns = [
                    "rm -rf /",
                    "dd if=",
                    "format c:",
                    "> /etc/passwd",
                ]
                for pattern in dangerous_patterns:
                    assert pattern not in command_text, (
                        f"Dangerous command pattern found: {pattern}"
                    )

    def test_ssh_error_handling_keywords(self, ssh_generator):
        """Test keywords that might commonly fail or need error handling."""
        error_prone_keywords = get_basic_ssh_connection_keywords()

        for keyword in error_prone_keywords:
            test_case = ssh_generator.generate_ssh_keyword_test(keyword)

            # Verify test case has realistic expectations
            step = test_case["test_case"]["steps"][0]
            expected = step["expected"]

            # Expected results should be positive/success-oriented for generated tests
            success_indicators = [
                "success",
                "establish",
                "connect",
                "upload",
                "download",
                "execut",
            ]
            has_success_indicator = any(
                indicator in expected.lower() for indicator in success_indicators
            )

            assert has_success_indicator, (
                f"Generated test for {keyword} lacks positive expectation: {expected}"
            )

    def test_ssh_performance_and_scale(self, ssh_generator):
        """Test generation performance and ability to handle scale."""

        # Test generation time for all keywords
        start_time = time.time()
        all_tests = ssh_generator.generate_all_ssh_keyword_tests()
        generation_time = time.time() - start_time

        # Should generate expected tests in reasonable time
        assert len(all_tests) == EXPECTED_TOTAL_SSH_TESTS
        assert generation_time < 5.0, (
            f"Generation took too long: {generation_time:.2f}s"
        )

        # Test memory usage (rough check)
        total_size = sum(sys.getsizeof(test) for test in all_tests)
        assert total_size < 10 * 1024 * 1024, (
            f"Generated tests too large: {total_size} bytes"
        )
