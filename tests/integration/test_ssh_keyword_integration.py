"""Integration tests for SSH keyword generation workflows."""

import json
import time

import pytest

from importobot.core.converter import convert_file
from importobot.core.engine import GenericConversionEngine
from importobot.core.parsers import GenericTestFileParser
from importobot.core.pattern_matcher import LibraryDetector
from importobot.utils.file_operations import load_json_file as load_json


class TestSSHKeywordIntegration:
    """Integration tests for complete SSH keyword generation workflows."""

    @pytest.fixture
    def ssh_test_data(self, tmp_path):
        """Create test SSH JSON data."""
        ssh_data = {
            "test_case": {
                "name": "SSH Server Configuration Test",
                "description": "Test SSH server setup and file operations",
                "steps": [
                    {
                        "step": "Connect to SSH server",
                        "test_data": (
                            "host: production-server.example.com "
                            "username: deploy password: deploy123"
                        ),
                        "expected": "Connection established successfully",
                    },
                    {
                        "step": "Upload configuration file",
                        "test_data": (
                            "source: /local/config/nginx.conf "
                            "destination: /etc/nginx/nginx.conf"
                        ),
                        "expected": "File uploaded successfully",
                    },
                    {
                        "step": "Execute reload command",
                        "test_data": "command: sudo systemctl reload nginx",
                        "expected": "Service reloaded",
                    },
                    {
                        "step": "Verify configuration file exists",
                        "test_data": "file: /etc/nginx/nginx.conf",
                        "expected": "File exists on server",
                    },
                    {
                        "step": "Read service status",
                        "test_data": "until: active (running)",
                        "expected": "Service is running",
                    },
                    {
                        "step": "Create backup directory",
                        "test_data": "directory: /backup/nginx",
                        "expected": "Directory created",
                    },
                    {
                        "step": "Enable SSH logging for audit",
                        "test_data": "logfile: /var/log/ssh-audit.log",
                        "expected": "Logging enabled",
                    },
                    {
                        "step": "Close SSH connection",
                        "test_data": "",
                        "expected": "Connection closed",
                    },
                ],
            }
        }

        test_file = tmp_path / "ssh_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(ssh_data, f, indent=2)

        return test_file

    @pytest.fixture
    def ssh_library_detection_data(self, tmp_path):
        """Create test data that should trigger SSH library detection."""
        ssh_data = {
            "test_case": {
                "name": "SSH Operations Test",
                "steps": [
                    {"step": "Connect via SSH", "test_data": "ssh admin@server.com"},
                    {
                        "step": "Upload file via SFTP",
                        "test_data": "sftp put /local/file /remote/file",
                    },
                    {
                        "step": "Execute remote command",
                        "test_data": "ssh_command: ls -la /home",
                    },
                ],
            }
        }

        test_file = tmp_path / "ssh_library_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(ssh_data, f, indent=2)

        return test_file

    def test_end_to_end_ssh_keyword_conversion(self, ssh_test_data):
        """Test complete end-to-end SSH keyword conversion workflow."""
        # Load JSON data
        json_data = load_json(str(ssh_test_data))

        # Parse the test file
        parser = GenericTestFileParser()
        parser.find_tests(json_data)

        # Generate keywords using the conversion engine
        engine = GenericConversionEngine()
        robot_content = engine.convert(json_data)

        # Verify SSH-specific content
        assert "SSHLibrary" in robot_content
        assert (
            "Open Connection    production-server.example.com    deploy    deploy123"
            in robot_content
        )
        assert (
            "Put File    /local/config/nginx.conf    /etc/nginx/nginx.conf"
            in robot_content
        )
        assert "Execute Command    sudo systemctl reload nginx" in robot_content
        assert "File Should Exist    /etc/nginx/nginx.conf" in robot_content
        assert "Read Until    active (running)" in robot_content
        assert "Create Directory    /backup/nginx" in robot_content
        assert "Enable Ssh Logging    /var/log/ssh-audit.log" in robot_content
        assert "Close Connection" in robot_content

        # Verify Robot Framework structure
        assert "*** Settings ***" in robot_content
        assert "*** Test Cases ***" in robot_content
        assert "Library    SSHLibrary" in robot_content

    def test_ssh_library_detection_integration(self, ssh_library_detection_data):
        """Test that SSH library is correctly detected and used."""
        # Load JSON data
        json_data = load_json(str(ssh_library_detection_data))

        # Parse the test file
        parser = GenericTestFileParser()
        tests = parser.find_tests(json_data)

        # Extract all steps for library detection
        all_steps = []
        for test in tests:
            all_steps.extend(parser.find_steps(test))

        # Detect libraries
        libraries = LibraryDetector.detect_libraries_from_steps(all_steps)

        # SSH library should be detected
        assert "SSHLibrary" in libraries

        # Generate keywords using the conversion engine
        engine = GenericConversionEngine()
        robot_content = engine.convert(json_data)

        # Verify SSH library is imported
        assert "Library    SSHLibrary" in robot_content

    def test_ssh_keyword_security_warnings_integration(self, ssh_test_data):
        """Test that security warnings are properly integrated in conversion."""
        # Load JSON data and convert
        json_data = load_json(str(ssh_test_data))

        engine = GenericConversionEngine()
        robot_content = engine.convert(json_data)

        # Check that security comments are included for password usage
        lines = robot_content.split("\n")
        password_line_found = False
        security_warning_found = False

        for i, line in enumerate(lines):
            # Check if password is used in Robot Framework command
            if "deploy123" in line and "Open Connection" in line:
                password_line_found = True
                # Look for security warning in nearby lines
                for j in range(max(0, i - 3), min(len(lines), i + 3)):
                    if "⚠️" in lines[j] and "password" in lines[j].lower():
                        security_warning_found = True
                        break

        assert password_line_found, (
            "Password usage should be detected in Robot Framework command"
        )
        assert security_warning_found, (
            "Security warning should be present near password usage"
        )
        # Note: Security warnings are part of the JSON data,
        # not necessarily in generated Robot code

    def test_ssh_parameter_extraction_integration(self, ssh_test_data):
        """Test that SSH parameters are correctly extracted and formatted."""
        # Load JSON data and convert
        json_data = load_json(str(ssh_test_data))

        engine = GenericConversionEngine()
        robot_content = engine.convert(json_data)

        # Verify parameter extraction worked correctly
        assert "production-server.example.com" in robot_content  # Host extracted
        assert "deploy" in robot_content  # Username extracted
        assert "/local/config/nginx.conf" in robot_content  # Source path extracted
        assert "/etc/nginx/nginx.conf" in robot_content  # Destination path extracted
        assert "sudo systemctl reload nginx" in robot_content  # Command extracted
        assert "/backup/nginx" in robot_content  # Directory path extracted
        assert "/var/log/ssh-audit.log" in robot_content  # Log file path extracted

    def test_ssh_comprehensive_workflow_with_conversion_engine(
        self, ssh_test_data, tmp_path
    ):
        """Test SSH keyword generation through the complete conversion engine."""
        output_file = tmp_path / "ssh_test.robot"

        # Use the converter function
        convert_file(str(ssh_test_data), str(output_file))
        assert output_file.exists()

        # Read and verify the generated Robot file
        robot_content = output_file.read_text(encoding="utf-8")

        # Verify SSH library and keywords
        assert "Library    SSHLibrary" in robot_content
        assert "Open Connection" in robot_content
        assert "Put File" in robot_content
        assert "Execute Command" in robot_content
        assert "File Should Exist" in robot_content
        assert "Create Directory" in robot_content
        assert "Enable Ssh Logging" in robot_content
        assert "Close Connection" in robot_content

    def test_ssh_mixed_library_integration(self, tmp_path):
        """Test SSH keywords integration with other libraries."""
        mixed_data = {
            "test_case": {
                "name": "Mixed Library Test",
                "steps": [
                    {
                        "step": "Open browser to admin panel",
                        "test_data": "url: https://admin.example.com browser: Chrome",
                    },
                    {
                        "step": "Connect to server via SSH",
                        "test_data": "host: server.example.com username: admin",
                    },
                    {
                        "step": "Click login button",
                        "test_data": "locator: id=login-btn",
                    },
                    {
                        "step": "Execute server command",
                        "test_data": "command: tail -f /var/log/application.log",
                    },
                    {
                        "step": "Verify page contains text",
                        "test_data": "text: Dashboard",
                    },
                    {
                        "step": "Upload log file",
                        "test_data": (
                            "source: /var/log/app.log destination: /backup/app.log"
                        ),
                    },
                ],
            }
        }

        test_file = tmp_path / "mixed_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(mixed_data, f, indent=2)

        # Load JSON data and parse
        json_data = load_json(str(test_file))
        parser = GenericTestFileParser()
        tests = parser.find_tests(json_data)

        # Extract all steps for library detection
        all_steps = []
        for test in tests:
            all_steps.extend(parser.find_steps(test))

        # Detect libraries
        libraries = LibraryDetector.detect_libraries_from_steps(all_steps)

        # Both libraries should be detected
        assert "SSHLibrary" in libraries
        assert "SeleniumLibrary" in libraries

        # Generate keywords using the conversion engine
        engine = GenericConversionEngine()
        robot_content = engine.convert(json_data)

        # Verify both libraries are imported
        assert "Library    SSHLibrary" in robot_content
        assert "Library    SeleniumLibrary" in robot_content

        # Verify mixed keywords are generated
        assert "Open Browser" in robot_content  # Selenium
        assert "Open Connection" in robot_content  # SSH
        assert "Click Element" in robot_content  # Selenium
        assert "Execute Command" in robot_content  # SSH
        assert "Page Should Contain" in robot_content  # Selenium
        assert "Put File" in robot_content  # SSH

    def test_ssh_complex_scenario_integration(self, tmp_path):
        """Test complex SSH scenario with multiple operations."""
        complex_data = {
            "test_case": {
                "name": "Complex SSH Deployment Test",
                "steps": [
                    {
                        "step": "Connect to staging server",
                        "test_data": "host: staging.example.com username: deploy",
                    },
                    {
                        "step": "Login with SSH key",
                        "test_data": (
                            "username: deploy keyfile: /home/deploy/.ssh/id_rsa"
                        ),
                    },
                    {
                        "step": "Create deployment directory",
                        "test_data": "directory: /opt/myapp/releases/v1.2.3",
                    },
                    {
                        "step": "Upload application archive",
                        "test_data": (
                            "source: dist/myapp-1.2.3.tar.gz "
                            "destination: /tmp/myapp-1.2.3.tar.gz"
                        ),
                    },
                    {
                        "step": "Start extraction in background",
                        "test_data": (
                            "command: tar -xzf /tmp/myapp-1.2.3.tar.gz "
                            "-C /opt/myapp/releases/v1.2.3"
                        ),
                    },
                    {
                        "step": "Wait for extraction completion",
                        "test_data": "until: Extraction completed",
                    },
                    {
                        "step": "Write deployment script",
                        "test_data": "text: ./deploy.sh --version=1.2.3",
                    },
                    {"step": "Read deployment output", "test_data": ""},
                    {
                        "step": "Verify application file exists",
                        "test_data": "file: /opt/myapp/releases/v1.2.3/app.py",
                    },
                    {
                        "step": "List deployment contents",
                        "test_data": "directory: /opt/myapp/releases/v1.2.3",
                    },
                    {"step": "Switch to production connection", "test_data": ""},
                    {"step": "Close all SSH connections", "test_data": ""},
                ],
            }
        }

        test_file = tmp_path / "complex_ssh_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(complex_data, f, indent=2)

        # Convert through the converter function
        output_file = tmp_path / "complex_ssh_test.robot"
        convert_file(str(test_file), str(output_file))

        assert output_file.exists()
        robot_content = output_file.read_text(encoding="utf-8")

        # Verify all SSH operations are properly converted
        expected_keywords = [
            "Open Connection    staging.example.com    deploy",
            "Login With Public Key    deploy    /home/deploy/.ssh/id_rsa",
            "Create Directory    /opt/myapp/releases/v1.2.3",
            "Put File    dist/myapp-1.2.3.tar.gz    /tmp/myapp-1.2.3.tar.gz",
            (
                "Start Command    tar -xzf /tmp/myapp-1.2.3.tar.gz "
                "-C /opt/myapp/releases/v1.2.3"
            ),
            "Read Until    Extraction completed",
            "Write    ./deploy.sh --version=1.2.3",
            "Read",
            "File Should Exist    /opt/myapp/releases/v1.2.3/app.py",
            "List Directory    /opt/myapp/releases/v1.2.3",
            "Switch Connection    ${connection_alias}",
            "Close All Connections",
        ]

        for keyword in expected_keywords:
            assert keyword in robot_content, f"Missing expected keyword: {keyword}"

    def test_ssh_error_handling_integration(self, tmp_path):
        """Test SSH keyword generation with malformed or edge case data."""
        edge_case_data = {
            "test_case": {
                "name": "SSH Edge Cases Test",
                "steps": [
                    {"step": "Connect with minimal data", "test_data": ""},
                    {"step": "Execute empty command", "test_data": "command: "},
                    {"step": "Upload file with missing paths", "test_data": "source: "},
                    {
                        "step": "Unknown SSH operation",
                        "test_data": "some_unknown_field: value",
                    },
                ],
            }
        }

        test_file = tmp_path / "edge_case_ssh_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(edge_case_data, f, indent=2)

        # Should not crash and should generate fallback keywords
        output_file = tmp_path / "edge_case_ssh_test.robot"
        convert_file(str(test_file), str(output_file))

        assert output_file.exists()
        robot_content = output_file.read_text(encoding="utf-8")

        # Verify fallback behavior
        assert "Open Connection    ${HOST}" in robot_content  # Parameterized connection
        assert "Execute Command    ${COMMAND}" in robot_content  # Fallback command
        assert (
            "Put File    ${SOURCE_FILE}    ${DESTINATION_PATH}" in robot_content
        )  # Fallback file transfer
        assert (
            "No Operation  # SSH operation not recognized" in robot_content
        )  # Unrecognized operation

    def test_ssh_keyword_generation_performance(self, tmp_path):
        """Test SSH keyword generation performance with large datasets."""
        # Create a large SSH test case
        large_steps = []
        for i in range(100):
            large_steps.extend(
                [
                    {
                        "step": f"Connect to server {i}",
                        "test_data": (f"host: server{i}.example.com username: user{i}"),
                    },
                    {
                        "step": f"Upload file {i}",
                        "test_data": (
                            f"source: /local/file{i} destination: /remote/file{i}"
                        ),
                    },
                    {
                        "step": f"Execute command {i}",
                        "test_data": f"command: process_file_{i}.sh",
                    },
                    {"step": f"Close connection {i}", "test_data": ""},
                ]
            )

        large_data = {
            "test_case": {"name": "Large SSH Performance Test", "steps": large_steps}
        }

        test_file = tmp_path / "large_ssh_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(large_data, f, indent=2)

        # Measure conversion time
        start_time = time.time()

        output_file = tmp_path / "large_ssh_test.robot"
        convert_file(str(test_file), str(output_file))

        end_time = time.time()
        conversion_time = end_time - start_time

        assert output_file.exists()

        # Performance should be reasonable (less than 10 seconds for 400 steps)
        assert conversion_time < 10.0, (
            f"Conversion took too long: {conversion_time:.2f} seconds"
        )

        # Verify content was generated correctly
        robot_content = output_file.read_text(encoding="utf-8")
        assert robot_content.count("Open Connection") == 100
        assert robot_content.count("Put File") == 100
        assert robot_content.count("Execute Command") == 100
        assert robot_content.count("Close Connection") == 100
