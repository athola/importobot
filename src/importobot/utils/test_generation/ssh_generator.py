"""SSH keyword test case generator for comprehensive testing coverage."""

import os
import random
from typing import Any

from importobot.core.keywords.generators.ssh_keywords import SSHKeywordGenerator

from .ssh_authentication_tests import SSHAuthenticationTestGenerator
from .ssh_connection_tests import SSHConnectionTestGenerator

_SAFE_LOCAL_ROOT = os.path.join(os.path.expanduser("~"), "importobot", "local")
_SAFE_REMOTE_ROOT = os.path.join(os.path.expanduser("~"), "importobot", "remote")


def _local_path(name: str) -> str:
    cleaned = name.lstrip("/\\")
    return os.path.join(_SAFE_LOCAL_ROOT, cleaned) if cleaned else _SAFE_LOCAL_ROOT


def _remote_path(name: str) -> str:
    cleaned = name.lstrip("/\\")
    return os.path.join(_SAFE_REMOTE_ROOT, cleaned) if cleaned else _SAFE_REMOTE_ROOT


class SSHKeywordTestGenerator:
    """Generate comprehensive test cases for SSH keyword coverage."""

    def __init__(self) -> None:
        """Initialize SSH keyword test generator."""
        self.ssh_generator = SSHKeywordGenerator()
        self.connection_gen = SSHConnectionTestGenerator()
        self.auth_gen = SSHAuthenticationTestGenerator()
        self._keyword_generators = self._build_keyword_generators()

    @property
    def keyword_generators(self) -> dict[str, Any]:
        """Return mapping of SSH keywords to their generators."""
        return self._keyword_generators

    def _build_keyword_generators(self) -> dict[str, Any]:
        """Build mapping of SSH keywords to test data generators."""
        return {
            # Connection Management (6)
            "Open Connection": self.connection_gen.generate_open_connection_test,
            "Close Connection": self.connection_gen.generate_close_connection_test,
            "Close All Connections": (
                self.connection_gen.generate_close_all_connections_test
            ),
            "Switch Connection": self.connection_gen.generate_switch_connection_test,
            "Get Connection": self.connection_gen.generate_get_connection_test,
            "Get Connections": self.connection_gen.generate_get_connections_test,
            # Authentication (2)
            "Login": self.auth_gen.generate_login_test,
            "Login With Public Key": (
                self.auth_gen.generate_login_with_public_key_test
            ),
            # Configuration (2)
            "Set Default Configuration": self._generate_set_default_configuration_test,
            "Set Client Configuration": self._generate_set_client_configuration_test,
            # Command Execution (3)
            "Execute Command": self._generate_execute_command_test,
            "Start Command": self._generate_start_command_test,
            "Read Command Output": self._generate_read_command_output_test,
            # File Operations (12)
            "Put File": self._generate_put_file_test,
            "Put Directory": self._generate_put_directory_test,
            "Get File": self._generate_get_file_test,
            "Get Directory": self._generate_get_directory_test,
            "Create File": self._generate_create_file_test,
            "Remove File": self._generate_remove_file_test,
            "Move File": self._generate_move_file_test,
            "Get File Size": self._generate_get_file_size_test,
            "Get File Permissions": self._generate_get_file_permissions_test,
            "Set File Permissions": self._generate_set_file_permissions_test,
            "File Should Exist": self._generate_file_should_exist_test,
            "File Should Not Exist": self._generate_file_should_not_exist_test,
            # Directory Operations (10)
            "Create Directory": self._generate_create_directory_test,
            "List Directory": self._generate_list_directory_test,
            "List Files In Directory": (self._generate_list_files_in_directory_test),
            "List Directories In Directory": (
                self._generate_list_directories_in_directory_test
            ),
            "Directory Should Exist": self._generate_directory_should_exist_test,
            "Directory Should Not Exist": (
                self._generate_directory_should_not_exist_test
            ),
            "Remove Directory": self._generate_remove_directory_test,
            "Move Directory": self._generate_move_directory_test,
            # Interactive Shell (6)
            "Write": self._generate_write_test,
            "Write Bare": self._generate_write_bare_test,
            "Read": self._generate_read_test,
            "Read Until": self._generate_read_until_test,
            "Read Until Prompt": self._generate_read_until_prompt_test,
            "Read Until Regexp": self._generate_read_until_regexp_test,
            "Write Until Expected Output": (
                self._generate_write_until_expected_output_test
            ),
            # Logging (2)
            "Enable Ssh Logging": self._generate_enable_ssh_logging_test,
            "Disable Ssh Logging": self._generate_disable_ssh_logging_test,
        }

    def generate_ssh_keyword_test(self, keyword: str) -> dict[str, Any]:
        """Generate a test case for a specific SSH keyword."""
        generator = self._keyword_generators.get(keyword)
        if generator:
            result = generator()
            return (
                result
                if isinstance(result, dict)
                else self._generate_generic_test(keyword)
            )
        return self._generate_generic_test(keyword)

    def generate_all_ssh_keyword_tests(self) -> list[dict[str, Any]]:
        """Generate test cases for all SSH keywords."""
        tests = []
        for keyword in self._keyword_generators:
            # Generate 3 variations per keyword
            for variation in range(3):
                test_case = self.generate_ssh_keyword_test(keyword)
                # Add variation info to the test case
                test_case["keyword_focus"] = keyword
                test_case["variation"] = variation + 1
                tests.append(test_case)
        return tests

    # Simplified placeholder methods for remaining categories
    def _generate_set_default_configuration_test(self) -> dict[str, Any]:
        """Generate test for Set Default Configuration keyword."""
        return self._create_simple_test(
            name="SSH Set Default Configuration Test",
            description="Test setting SSH default configuration parameters",
            step="Set default SSH configuration",
            test_data="timeout: 30s prompt: $",
            expected="Default configuration set successfully",
        )

    def _generate_set_client_configuration_test(self) -> dict[str, Any]:
        """Generate test for Set Client Configuration keyword."""
        return self._create_simple_test(
            name="SSH Set Client Configuration Test",
            description="Test setting SSH client configuration",
            step="Set SSH client configuration",
            test_data="encoding: UTF-8 term_type: xterm",
            expected="Client configuration set successfully",
        )

    def _generate_execute_command_test(self) -> dict[str, Any]:
        """Generate test for Execute Command keyword."""
        commands = ["ls -la", "pwd", "whoami", "df -h"]
        return self._create_simple_test(
            name="SSH Execute Command Test",
            description="Test SSH command execution",
            step="Execute SSH command",
            test_data=f"command: {random.choice(commands)}",
            expected="Command executed successfully",
        )

    def _generate_start_command_test(self) -> dict[str, Any]:
        """Generate test for Start Command keyword."""
        return self._create_simple_test(
            name="SSH Start Command Test",
            description="Test starting SSH background command",
            step="Start SSH background command",
            test_data="command: ping localhost",
            expected="Background command started",
        )

    def _generate_read_command_output_test(self) -> dict[str, Any]:
        """Generate test for Read Command Output keyword."""
        return self._create_simple_test(
            name="SSH Read Command Output Test",
            description="Test reading SSH command output",
            step="Read SSH command output",
            test_data="",
            expected="Command output read successfully",
        )

    # Additional placeholder methods for other categories would go here...
    # For brevity, I'll implement a few key ones and use generic test for the rest

    def _generate_put_file_test(self) -> dict[str, Any]:
        """Generate test for Put File keyword."""
        # Generate varied file names and paths
        source_files = [
            _local_path("file.txt"),
            _local_path("data.csv"),
            "/home/user/config.json",
            "/var/log/app.log",
            "/opt/scripts/deploy.sh",
        ]
        dest_files = [
            _remote_path("file.txt"),
            _remote_path("data.csv"),
            "/home/user/config.json",
            "/var/log/app.log",
            "/opt/scripts/deploy.sh",
        ]

        # Randomly select different source and destination files
        source_file = random.choice(source_files)
        dest_file = random.choice(dest_files)

        return self._create_simple_test(
            name="SSH Put File Test",
            description="Test uploading file via SSH",
            step="Upload file to SSH server",
            test_data=f"source: {source_file} destination: {dest_file}",
            expected="File uploaded successfully",
        )

    def _generate_get_file_test(self) -> dict[str, Any]:
        """Generate test for Get File keyword."""
        return self._create_simple_test(
            name="SSH Get File Test",
            description="Test downloading file via SSH",
            step="Download file from SSH server",
            test_data="source: /remote/file.txt destination: /local/file.txt",
            expected="File downloaded successfully",
        )

    def _generate_create_file_test(self) -> dict[str, Any]:
        """Generate test for Create File keyword."""
        return self._create_simple_test(
            name="SSH Create File Test",
            description="Test creating file on SSH server",
            step="Create file on SSH server",
            test_data=f"path: {_remote_path('test.txt')} content: test content",
            expected="File created successfully",
        )

    def _generate_remove_file_test(self) -> dict[str, Any]:
        """Generate test for Remove File keyword."""
        return self._create_simple_test(
            name="SSH Remove File Test",
            description="Test removing file from SSH server",
            step="Remove file from SSH server",
            test_data=f"path: {_remote_path('test.txt')}",
            expected="File removed successfully",
        )

    def _generate_move_file_test(self) -> dict[str, Any]:
        """Generate test for Move File keyword."""
        return self._create_simple_test(
            name="SSH Move File Test",
            description="Test moving file on SSH server",
            step="Move file on SSH server",
            test_data=(
                f"source: {_remote_path('old.txt')} "
                f"destination: {_remote_path('new.txt')}"
            ),
            expected="File moved successfully",
        )

    def _generate_file_should_exist_test(self) -> dict[str, Any]:
        """Generate test for File Should Exist keyword."""
        return self._create_simple_test(
            name="SSH File Should Exist Test",
            description="Test verifying file exists on SSH server",
            step="Verify file exists on SSH server",
            test_data="path: /etc/hosts",
            expected="File exists verification passed",
        )

    def _generate_file_should_not_exist_test(self) -> dict[str, Any]:
        """Generate test for File Should Not Exist keyword."""
        return self._create_simple_test(
            name="SSH File Should Not Exist Test",
            description="Test verifying file does not exist on SSH server",
            step="Verify file does not exist on SSH server",
            test_data=f"path: {_remote_path('nonexistent.txt')}",
            expected="File non-existence verification passed",
        )

    def _generate_change_file_permissions_test(self) -> dict[str, Any]:
        """Generate test for Change File Permissions keyword."""
        return self._create_simple_test(
            name="SSH Change File Permissions Test",
            description="Test changing file permissions on SSH server",
            step="Change file permissions on SSH server",
            test_data=f"path: {_remote_path('test.txt')} permissions: 755",
            expected="File permissions changed successfully",
        )

    def _generate_get_file_size_test(self) -> dict[str, Any]:
        """Generate test for Get File Size keyword."""
        return self._create_simple_test(
            name="SSH Get File Size Test",
            description="Test getting file size on SSH server",
            step="Get file size on SSH server",
            test_data=f"path: {_remote_path('test.txt')}",
            expected="File size retrieved successfully",
        )

    def _generate_get_file_permissions_test(self) -> dict[str, Any]:
        """Generate test for Get File Permissions keyword."""
        return self._create_simple_test(
            name="SSH Get File Permissions Test",
            description="Test getting file permissions on SSH server",
            step="Get file permissions on SSH server",
            test_data=f"path: {_remote_path('test.txt')}",
            expected="File permissions retrieved successfully",
        )

    def _generate_set_file_permissions_test(self) -> dict[str, Any]:
        """Generate test for Set File Permissions keyword."""
        return self._create_simple_test(
            name="SSH Set File Permissions Test",
            description="Test setting file permissions on SSH server",
            step="Set file permissions on SSH server",
            test_data=f"path: {_remote_path('test.txt')} permissions: 644",
            expected="File permissions set successfully",
        )

    def _generate_create_directory_test(self) -> dict[str, Any]:
        """Generate test for Create Directory keyword."""
        # Generate varied directory paths
        directory_paths = [
            _remote_path("testdir"),
            "/var/log/app",
            "/home/user/data",
            "/opt/backups",
            "/usr/local/config",
        ]

        return self._create_simple_test(
            name="SSH Create Directory Test",
            description="Test creating directory on SSH server",
            step="Create directory on SSH server",
            test_data=f"path: {random.choice(directory_paths)}",
            expected="Directory created successfully",
        )

    def _generate_list_directory_test(self) -> dict[str, Any]:
        """Generate test for List Directory keyword."""
        return self._create_simple_test(
            name="SSH List Directory Test",
            description="Test listing directory contents on SSH server",
            step="List directory contents on SSH server",
            test_data=f"path: {_remote_path('')}",
            expected="Directory contents listed successfully",
        )

    def _generate_directory_should_exist_test(self) -> dict[str, Any]:
        """Generate test for Directory Should Exist keyword."""
        return self._create_simple_test(
            name="SSH Directory Should Exist Test",
            description="Test verifying directory exists on SSH server",
            step="Verify directory exists on SSH server",
            test_data="path: /etc",
            expected="Directory exists verification passed",
        )

    def _generate_directory_should_not_exist_test(self) -> dict[str, Any]:
        """Generate test for Directory Should Not Exist keyword."""
        return self._create_simple_test(
            name="SSH Directory Should Not Exist Test",
            description="Test verifying directory does not exist on SSH server",
            step="Verify directory does not exist on SSH server",
            test_data=f"path: {_remote_path('nonexistent')}",
            expected="Directory non-existence verification passed",
        )

    def _generate_remove_directory_test(self) -> dict[str, Any]:
        """Generate test for Remove Directory keyword."""
        return self._create_simple_test(
            name="SSH Remove Directory Test",
            description="Test removing directory from SSH server",
            step="Remove directory from SSH server",
            test_data=f"path: {_remote_path('testdir')}",
            expected="Directory removed successfully",
        )

    def _generate_move_directory_test(self) -> dict[str, Any]:
        """Generate test for Move Directory keyword."""
        return self._create_simple_test(
            name="SSH Move Directory Test",
            description="Test moving directory on SSH server",
            step="Move directory on SSH server",
            test_data=(
                f"source: {_remote_path('olddir')} "
                f"destination: {_remote_path('newdir')}"
            ),
            expected="Directory moved successfully",
        )

    def _generate_list_files_in_directory_test(self) -> dict[str, Any]:
        """Generate test for List Files In Directory keyword."""
        return self._create_simple_test(
            name="SSH List Files In Directory Test",
            description="Test listing files in directory on SSH server",
            step="List files in directory on SSH server",
            test_data=f"path: {_remote_path('')}",
            expected="Files in directory listed successfully",
        )

    def _generate_list_directories_in_directory_test(self) -> dict[str, Any]:
        """Generate test for List Directories In Directory keyword."""
        return self._create_simple_test(
            name="SSH List Directories In Directory Test",
            description="Test listing directories in directory on SSH server",
            step="List directories in directory on SSH server",
            test_data=f"path: {_remote_path('')}",
            expected="Directories in directory listed successfully",
        )

    def _generate_write_test(self) -> dict[str, Any]:
        """Generate test for Write keyword."""
        return self._create_simple_test(
            name="SSH Write Test",
            description="Test writing to SSH interactive shell",
            step="Write to SSH interactive shell",
            test_data="text: ls -la",
            expected="Text written to shell successfully",
        )

    def _generate_read_test(self) -> dict[str, Any]:
        """Generate test for Read keyword."""
        return self._create_simple_test(
            name="SSH Read Test",
            description="Test reading from SSH interactive shell",
            step="Read from SSH interactive shell",
            test_data="",
            expected="Shell output read successfully",
        )

    def _generate_read_until_test(self) -> dict[str, Any]:
        """Generate test for Read Until keyword."""
        return self._create_simple_test(
            name="SSH Read Until Test",
            description="Test reading until specific text appears",
            step="Read until specific text appears",
            test_data="expected: $",
            expected="Read until condition met",
        )

    def _generate_read_until_prompt_test(self) -> dict[str, Any]:
        """Generate test for Read Until Prompt keyword."""
        return self._create_simple_test(
            name="SSH Read Until Prompt Test",
            description="Test reading until shell prompt appears",
            step="Read until shell prompt appears",
            test_data="",
            expected="Shell prompt detected successfully",
        )

    def _generate_set_prompt_test(self) -> dict[str, Any]:
        """Generate test for Set Prompt keyword."""
        return self._create_simple_test(
            name="SSH Set Prompt Test",
            description="Test setting shell prompt pattern",
            step="Set shell prompt pattern",
            test_data="prompt: $",
            expected="Shell prompt pattern set successfully",
        )

    def _generate_write_bare_test(self) -> dict[str, Any]:
        """Generate test for Write Bare keyword."""
        return self._create_simple_test(
            name="SSH Write Bare Test",
            description="Test writing bare text to SSH interactive shell",
            step="Write bare text to SSH interactive shell",
            test_data="text: echo hello",
            expected="Bare text written to shell successfully",
        )

    def _generate_read_until_regexp_test(self) -> dict[str, Any]:
        """Generate test for Read Until Regexp keyword."""
        return self._create_simple_test(
            name="SSH Read Until Regexp Test",
            description="Test reading until regular expression matches",
            step="Read until regular expression matches",
            test_data="pattern: [\\$#]",
            expected="Read until regexp condition met",
        )

    def _generate_write_until_expected_output_test(self) -> dict[str, Any]:
        """Generate test for Write Until Expected Output keyword."""
        return self._create_simple_test(
            name="SSH Write Until Expected Output Test",
            description="Test writing until expected output appears",
            step="Write until expected output appears",
            test_data="text: ls expected: total",
            expected="Write until expected output condition met",
        )

    def _generate_enable_ssh_logging_test(self) -> dict[str, Any]:
        """Generate test for Enable Ssh Logging keyword."""
        return self._create_simple_test(
            name="SSH Enable Logging Test",
            description="Test enabling SSH session logging",
            step="Enable SSH session logging",
            test_data=f"logfile: {_remote_path('logs/ssh.log')}",
            expected="SSH logging enabled successfully",
        )

    def _generate_disable_ssh_logging_test(self) -> dict[str, Any]:
        """Generate test for Disable Ssh Logging keyword."""
        return self._create_simple_test(
            name="SSH Disable Logging Test",
            description="Test disabling SSH session logging",
            step="Disable SSH session logging",
            test_data="",
            expected="SSH logging disabled successfully",
        )

    def _generate_put_directory_test(self) -> dict[str, Any]:
        """Generate test for Put Directory keyword."""
        return self._create_simple_test(
            name="SSH Put Directory Test",
            description="Test uploading directory via SSH",
            step="Upload directory to SSH server",
            test_data="source: /local/dir destination: /remote/dir",
            expected="Directory uploaded successfully",
        )

    def _generate_get_directory_test(self) -> dict[str, Any]:
        """Generate test for Get Directory keyword."""
        return self._create_simple_test(
            name="SSH Get Directory Test",
            description="Test downloading directory via SSH",
            step="Download directory from SSH server",
            test_data="source: /remote/dir destination: /local/dir",
            expected="Directory downloaded successfully",
        )

    def _create_simple_test(
        self, *, name: str, description: str, step: str, test_data: str, expected: str
    ) -> dict[str, Any]:
        """Create a simple test case structure."""
        return {
            "test_case": {
                "name": name,
                "description": description,
                "steps": [
                    {
                        "step": step,
                        "test_data": test_data,
                        "expected": expected,
                    }
                ],
            }
        }

    def _generate_generic_test(self, keyword: str) -> dict[str, Any]:
        """Generate a generic test case for unknown keywords."""
        return self._create_simple_test(
            name=f"SSH {keyword} Test",
            description=f"Test {keyword} SSH keyword functionality",
            step=f"Execute {keyword} SSH operation",
            test_data="Generic test data for SSH operation",
            expected=f"{keyword} operation completed successfully",
        )
