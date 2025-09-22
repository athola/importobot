"""Comprehensive tests for SSH keyword generation following TDD principles."""

from typing import Any

import pytest

from importobot.core.keywords.generators.ssh_keywords import SSHKeywordGenerator

# pylint: disable=redefined-outer-name


@pytest.fixture
def ssh_generator():
    """Return an SSHKeywordGenerator instance."""
    return SSHKeywordGenerator()


class TestSSHKeywordGenerator:
    """Tests for the SSHKeywordGenerator class."""

    def test_generate_connect_keyword_ssh_format(self, ssh_generator):
        """Test SSH connection keyword generation from ssh command format."""
        test_data = "ssh testuser@example.com"
        result = ssh_generator.generate_connect_keyword(test_data)
        assert result == "Open Connection    example.com    testuser"

    def test_generate_connect_keyword_structured_format(self, ssh_generator):
        """Test SSH connection keyword generation from structured format."""
        test_data = "host: example.com username: testuser password: testpass"
        result = ssh_generator.generate_connect_keyword(test_data)
        assert result == "Open Connection    example.com    testuser    testpass"

    def test_generate_connect_keyword_with_host_only(self, ssh_generator):
        """Test SSH connection keyword generation with host only."""
        test_data = "host: example.com"
        result = ssh_generator.generate_connect_keyword(test_data)
        assert result == "Open Connection    example.com"

    def test_generate_connect_keyword_with_empty_input(self, ssh_generator):
        """Test SSH connection keyword generation with empty input data."""
        test_data = ""
        result = ssh_generator.generate_connect_keyword(test_data)
        assert result == "Open Connection    ${HOST}"

    def test_generate_execute_keyword_with_command(self, ssh_generator):
        """Test SSH execute command keyword generation."""
        test_data = "command: ls -la"
        result = ssh_generator.generate_execute_keyword(test_data)
        assert result == "Execute Command    ls -la"

    def test_generate_execute_keyword_with_cmd_alias(self, ssh_generator):
        """Test SSH execute command keyword generation with cmd alias."""
        test_data = "cmd: pwd"
        result = ssh_generator.generate_execute_keyword(test_data)
        assert result == "Execute Command    pwd"

    def test_generate_execute_keyword_with_empty_input(self, ssh_generator):
        """Test SSH execute command keyword generation with empty input data."""
        test_data = ""
        result = ssh_generator.generate_execute_keyword(test_data)
        assert result == "Execute Command    ${COMMAND}"

    def test_generate_execute_keyword_with_generic_data(self, ssh_generator):
        """Test SSH execute command keyword generation with generic test data."""
        test_data = "localhost testuser"
        result = ssh_generator.generate_execute_keyword(test_data)
        assert result == "Execute Command    ${COMMAND}"


class TestSSHFileTransferKeywords:
    """Tests for SSH file transfer keyword generation."""

    def test_generate_file_transfer_keyword_upload(self, ssh_generator):
        """Test SSH file upload keyword generation."""
        test_data = "source: /local/file destination: /remote/file"
        result = ssh_generator.generate_file_transfer_keyword(test_data, "upload")
        assert result == "Put File    /local/file    /remote/file"

    def test_generate_file_transfer_keyword_download(self, ssh_generator):
        """Test SSH file download keyword generation."""
        test_data = "source: /remote/file destination: /local/file"
        result = ssh_generator.generate_file_transfer_keyword(test_data, "download")
        assert result == "Get File    /remote/file    /local/file"

    def test_generate_file_transfer_keyword_put_alias(self, ssh_generator):
        """Test SSH file transfer with put operation."""
        test_data = "from: /local/file to: /remote/file"
        result = ssh_generator.generate_file_transfer_keyword(test_data, "put")
        assert result == "Put File    /local/file    /remote/file"

    def test_generate_file_transfer_keyword_get_alias(self, ssh_generator):
        """Test SSH file transfer with get operation."""
        test_data = "from: /remote/file to: /local/file"
        result = ssh_generator.generate_file_transfer_keyword(test_data, "get")
        assert result == "Get File    /remote/file    /local/file"

    def test_generate_file_transfer_keyword_with_missing_data(self, ssh_generator):
        """Test SSH file transfer keyword generation with missing data."""
        test_data = ""
        result = ssh_generator.generate_file_transfer_keyword(test_data, "upload")
        assert result == "Put File    ${SOURCE_FILE}    ${DESTINATION_PATH}"

    def test_generate_file_transfer_keyword_default_operation(self, ssh_generator):
        """Test SSH file transfer keyword with unknown operation defaults to upload."""
        test_data = "source: /local/file destination: /remote/file"
        result = ssh_generator.generate_file_transfer_keyword(test_data, "unknown")
        assert result == "Put File    /local/file    /remote/file"


class TestSSHFileVerificationKeywords:
    """Tests for SSH file verification keyword generation."""

    def test_generate_file_verification_keyword_should_exist(self, ssh_generator):
        """Test SSH file verification keyword for existence."""
        test_data = "file: /path/to/file"
        result = ssh_generator.generate_file_verification_keyword(
            test_data, should_exist=True
        )
        assert result == "File Should Exist    /path/to/file"

    def test_generate_file_verification_keyword_should_not_exist(self, ssh_generator):
        """Test SSH file verification keyword for non-existence."""
        test_data = "path: /path/to/file"
        result = ssh_generator.generate_file_verification_keyword(
            test_data, should_exist=False
        )
        assert result == "File Should Not Exist    /path/to/file"

    def test_generate_file_verification_keyword_with_empty_input(self, ssh_generator):
        """Test SSH file verification keyword generation with empty input data."""
        test_data = ""
        result = ssh_generator.generate_file_verification_keyword(
            test_data, should_exist=True
        )
        assert result == "File Should Exist    ${FILE_PATH}"


class TestSSHDirectoryOperationKeywords:
    """Tests for SSH directory operation keyword generation."""

    def test_generate_directory_operations_keyword_create(self, ssh_generator):
        """Test SSH directory creation keyword generation."""
        test_data = "directory: /path/to/dir"
        result = ssh_generator.generate_directory_operations_keyword(
            test_data, "create"
        )
        assert result == "Create Directory    /path/to/dir"

    def test_generate_directory_operations_keyword_remove(self, ssh_generator):
        """Test SSH directory removal keyword generation."""
        test_data = "dir: /path/to/dir"
        result = ssh_generator.generate_directory_operations_keyword(
            test_data, "remove"
        )
        assert result == "Remove Directory    /path/to/dir"

    def test_generate_directory_operations_keyword_list(self, ssh_generator):
        """Test SSH directory listing keyword generation."""
        test_data = "path: /home/user"
        result = ssh_generator.generate_directory_operations_keyword(test_data, "list")
        assert result == "List Directory    /home/user"

    def test_generate_directory_operations_keyword_verify_exists(self, ssh_generator):
        """Test SSH directory existence verification keyword generation."""
        test_data = "directory: /path/to/dir"
        result = ssh_generator.generate_directory_operations_keyword(
            test_data, "verify_exists"
        )
        assert result == "Directory Should Exist    /path/to/dir"

    def test_generate_directory_operations_keyword_verify_not_exists(
        self, ssh_generator
    ):
        """Test SSH directory non-existence verification keyword generation."""
        test_data = "directory: /path/to/dir"
        result = ssh_generator.generate_directory_operations_keyword(
            test_data, "verify_not_exists"
        )
        assert result == "Directory Should Not Exist    /path/to/dir"

    def test_generate_directory_operations_keyword_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH directory operations keyword generation with empty input data."""
        test_data = ""
        result = ssh_generator.generate_directory_operations_keyword(
            test_data, "create"
        )
        assert result == "Create Directory    ${DIRECTORY_PATH}"

    def test_generate_directory_operations_keyword_default_operation(
        self, ssh_generator
    ):
        """Test SSH directory operations keyword with unknown operation defaults to
        list."""
        test_data = "directory: /home/user"
        result = ssh_generator.generate_directory_operations_keyword(
            test_data, "unknown"
        )
        assert result == "List Directory    /home/user"


class TestSSHInteractiveShellKeywords:
    """Tests for SSH interactive shell keyword generation."""

    def test_generate_interactive_shell_keyword_write(self, ssh_generator):
        """Test SSH interactive shell write keyword generation."""
        test_data = "text: echo hello"
        result = ssh_generator.generate_interactive_shell_keyword(test_data, "write")
        assert result == "Write    echo hello"

    def test_generate_interactive_shell_keyword_write_with_send_alias(
        self, ssh_generator
    ):
        """Test SSH interactive shell write keyword with send alias."""
        test_data = "send: sudo su"
        result = ssh_generator.generate_interactive_shell_keyword(test_data, "write")
        assert result == "Write    sudo su"

    def test_generate_interactive_shell_keyword_read(self, ssh_generator):
        """Test SSH interactive shell read keyword generation."""
        test_data = ""
        result = ssh_generator.generate_interactive_shell_keyword(test_data, "read")
        assert result == "Read"

    def test_generate_interactive_shell_keyword_read_until(self, ssh_generator):
        """Test SSH interactive shell read until keyword generation."""
        test_data = "until: $ expected: prompt"
        result = ssh_generator.generate_interactive_shell_keyword(
            test_data, "read_until"
        )
        assert result == "Read Until    $ expected: prompt"

    def test_generate_interactive_shell_keyword_read_until_prompt(self, ssh_generator):
        """Test SSH interactive shell read until prompt keyword generation."""
        test_data = ""
        result = ssh_generator.generate_interactive_shell_keyword(
            test_data, "read_until_prompt"
        )
        assert result == "Read Until Prompt"

    def test_generate_interactive_shell_keyword_write_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH interactive shell write keyword generation with empty input data."""
        test_data = ""
        result = ssh_generator.generate_interactive_shell_keyword(test_data, "write")
        assert result == "Write    ${TEXT_TO_WRITE}"

    def test_generate_interactive_shell_keyword_read_until_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH interactive shell read until keyword generation with empty input
        data."""
        test_data = ""
        result = ssh_generator.generate_interactive_shell_keyword(
            test_data, "read_until"
        )
        assert result == "Read Until    ${EXPECTED_TEXT}"

    def test_generate_interactive_shell_keyword_unknown_operation(self, ssh_generator):
        """Test SSH interactive shell keyword with unknown operation defaults to
        read."""
        test_data = ""
        result = ssh_generator.generate_interactive_shell_keyword(test_data, "unknown")
        assert result == "Read"


class TestSSHConnectionKeywords:
    """Tests for SSH connection management keyword generation."""

    # pylint: disable=protected-access

    def test_generate_connection_keywords_open(self, ssh_generator):
        """Test SSH connection keywords for opening connections."""
        combined = "connect to server"
        test_data = "host: example.com username: user"
        result = ssh_generator._generate_connection_keywords(combined, test_data)
        assert result == "Open Connection    example.com    user"

    def test_generate_connection_keywords_close(self, ssh_generator):
        """Test SSH connection keywords for closing connections."""
        combined = "disconnect from server"
        test_data = ""
        result = ssh_generator._generate_connection_keywords(combined, test_data)
        assert result == "Close Connection"

    def test_generate_connection_keywords_close_all(self, ssh_generator):
        """Test SSH connection keywords for closing all connections."""
        combined = "close all connections"
        test_data = ""
        result = ssh_generator._generate_connection_keywords(combined, test_data)
        assert result == "Close All Connections"

    def test_generate_connection_keywords_switch(self, ssh_generator):
        """Test SSH connection keywords for switching connections."""
        combined = "switch connection to another server"
        test_data = ""
        result = ssh_generator._generate_connection_keywords(combined, test_data)
        assert result == "Switch Connection    ${CONNECTION_ALIAS}"

    def test_generate_connection_keywords_no_match(self, ssh_generator):
        """Test SSH connection keywords when no pattern matches."""
        combined = "unrelated operation"
        test_data = ""
        result = ssh_generator._generate_connection_keywords(combined, test_data)
        assert result == ""


class TestSSHAuthenticationKeywords:
    """Tests for SSH authentication keyword generation."""

    # pylint: disable=protected-access

    def test_generate_authentication_keywords_login_password(self, ssh_generator):
        """Test SSH authentication keywords for password login."""
        combined = "login to server"
        test_data = "username: testuser password: testpass"
        result = ssh_generator._generate_authentication_keywords(combined, test_data)
        assert result == "Login    testuser    testpass"

    def test_generate_authentication_keywords_login_key(self, ssh_generator):
        """Test SSH authentication keywords for key-based login."""
        combined = "login with public key"
        test_data = "username: testuser keyfile: /path/to/key"
        result = ssh_generator._generate_authentication_keywords(combined, test_data)
        assert result == "Login With Public Key    testuser    /path/to/key"

    def test_generate_authentication_keywords_login_password_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH authentication keywords for password login with empty input data."""
        combined = "login to server"
        test_data = ""
        result = ssh_generator._generate_authentication_keywords(combined, test_data)
        assert result == "Login    ${USERNAME}    ${PASSWORD}"

    def test_generate_authentication_keywords_login_key_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH authentication keywords for key login with empty input data."""
        combined = "login with key authentication"
        test_data = ""
        result = ssh_generator._generate_authentication_keywords(combined, test_data)
        assert result == "Login With Public Key    ${USERNAME}    ${KEYFILE}"

    def test_generate_authentication_keywords_no_match(self, ssh_generator):
        """Test SSH authentication keywords when no pattern matches."""
        combined = "unrelated operation"
        test_data = ""
        result = ssh_generator._generate_authentication_keywords(combined, test_data)
        assert result == ""


class TestSSHCommandExecutionKeywords:
    """Tests for SSH command execution keyword generation."""

    # pylint: disable=protected-access

    def test_generate_command_execution_keywords_execute(self, ssh_generator):
        """Test SSH command execution keywords for regular execution."""
        combined = "execute command on server"
        test_data = "command: ls -la"
        result = ssh_generator._generate_command_execution_keywords(combined, test_data)
        assert result == "Execute Command    ls -la"

    def test_generate_command_execution_keywords_start_background(self, ssh_generator):
        """Test SSH command execution keywords for background execution."""
        combined = "start command in background"
        test_data = "command: python script.py"
        result = ssh_generator._generate_command_execution_keywords(combined, test_data)
        assert result == "Start Command    python script.py"

    def test_generate_command_execution_keywords_read_output(self, ssh_generator):
        """Test SSH command execution keywords for reading output."""
        combined = "read command output"
        test_data = ""
        result = ssh_generator._generate_command_execution_keywords(combined, test_data)
        assert result == "Read Command Output"

    def test_generate_command_execution_keywords_start_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH command execution keywords for start command with empty input
        data."""
        combined = "start background process"
        test_data = ""
        result = ssh_generator._generate_command_execution_keywords(combined, test_data)
        assert result == "Start Command    ${COMMAND}"

    def test_generate_command_execution_keywords_no_match(self, ssh_generator):
        """Test SSH command execution keywords when no pattern matches."""
        combined = "unrelated operation"
        test_data = ""
        result = ssh_generator._generate_command_execution_keywords(combined, test_data)
        assert result == ""


class TestSSHFileOperationKeywords:
    """Tests for SSH file operation keyword generation."""

    # pylint: disable=protected-access

    def test_generate_file_operation_keywords_upload(self, ssh_generator):
        """Test SSH file operation keywords for upload."""
        combined = "upload file to server"
        test_data = "source: /local/file destination: /remote/file"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Put File    /local/file    /remote/file"

    def test_generate_file_operation_keywords_download(self, ssh_generator):
        """Test SSH file operation keywords for download."""
        combined = "download file from server"
        test_data = "source: /remote/file destination: /local/file"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Get File    /remote/file    /local/file"

    def test_generate_file_operation_keywords_verify_exists(self, ssh_generator):
        """Test SSH file operation keywords for file existence verification."""
        combined = "verify file exists"
        test_data = "file: /path/to/file"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "File Should Exist    /path/to/file"

    def test_generate_file_operation_keywords_verify_not_exists(self, ssh_generator):
        """Test SSH file operation keywords for file non-existence verification."""
        combined = "file should not exist"
        test_data = "file: /path/to/file"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "File Should Not Exist    /path/to/file"

    def test_generate_file_operation_keywords_create_file(self, ssh_generator):
        """Test SSH file operation keywords for file creation."""
        combined = "create file on server"
        test_data = "file: /path/to/file content: hello world"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Create File    /path/to/file    hello world"

    def test_generate_file_operation_keywords_create_file_no_content(
        self, ssh_generator
    ):
        """Test SSH file operation keywords for file creation without content."""
        combined = "create file on server"
        test_data = "file: /path/to/file"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Create File    /path/to/file"

    def test_generate_file_operation_keywords_create_file_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH file operation keywords for file creation with empty input data."""
        combined = "create file on server"
        test_data = ""
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Create File    ${FILE_PATH}    ${CONTENT}"

    def test_generate_file_operation_keywords_remove_file(self, ssh_generator):
        """Test SSH file operation keywords for file removal."""
        combined = "remove file from server"
        test_data = "file: /path/to/file"
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Remove File    /path/to/file"

    def test_generate_file_operation_keywords_remove_file_with_empty_input(
        self, ssh_generator
    ):
        """Test SSH file operation keywords for file removal with empty input data."""
        combined = "delete file from server"
        test_data = ""
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == "Remove File    ${FILE_PATH}"

    def test_generate_file_operation_keywords_no_match(self, ssh_generator):
        """Test SSH file operation keywords when no pattern matches."""
        combined = "unrelated operation"
        test_data = ""
        result = ssh_generator._generate_file_operation_keywords(combined, test_data)
        assert result == ""


class TestSSHStepKeywords:
    """Tests for complete SSH step keyword generation."""

    def test_generate_step_keywords_connection_scenario(self, ssh_generator):
        """Test SSH step keyword generation for connection scenario."""
        step = {
            "step": "Connect to SSH server",
            "test_data": "host: example.com username: testuser",
            "expected": "Connection established",
        }
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 4
        assert result[0] == "# Step: Connect to SSH server"
        assert result[1] == "    # Test Data: host: example.com username: testuser"
        assert result[2] == "# Expected Result: Connection established"
        assert result[3] == "Open Connection    example.com    testuser"

    def test_generate_step_keywords_file_transfer_scenario(self, ssh_generator):
        """Test SSH step keyword generation for file transfer scenario."""
        step = {
            "description": "Upload configuration file",
            "test_data": "source: config.txt destination: /etc/config.txt",
        }
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 3
        assert result[0] == "# Step: Upload configuration file"
        assert (
            result[1]
            == "    # Test Data: source: config.txt destination: /etc/config.txt"
        )
        assert result[2] == "Put File    config.txt    /etc/config.txt"

    def test_generate_step_keywords_command_execution_scenario(self, ssh_generator):
        """Test SSH step keyword generation for command execution scenario."""
        step = {
            "action": "Execute system command",
            "test_data": "command: systemctl status nginx",
        }
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 3
        assert result[0] == "# Step: Execute system command"
        assert result[1] == "    # Test Data: command: systemctl status nginx"
        assert result[2] == "Execute Command    systemctl status nginx"

    def test_generate_step_keywords_unrecognized_operation(self, ssh_generator):
        """Test SSH step keyword generation for unrecognized operation."""
        step = {
            "instruction": "Perform unknown operation",
            "test_data": "some unknown data",
        }
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 3
        assert result[0] == "# Step: Perform unknown operation"
        assert result[1] == "    # Test Data: some unknown data"
        assert result[2] == "No Operation  # SSH operation not recognized"

    def test_generate_step_keywords_minimal_step(self, ssh_generator):
        """Test SSH step keyword generation with minimal step data."""
        step: dict[str, Any] = {}
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 1
        assert result[0] == "No Operation  # SSH operation not recognized"

    def test_generate_step_keywords_directory_operations(self, ssh_generator):
        """Test SSH step keyword generation for directory operations."""
        step = {
            "step": "Create directory for logs",
            "test_data": "directory: /var/log/myapp",
        }
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 3
        assert result[0] == "# Step: Create directory for logs"
        assert result[1] == "    # Test Data: directory: /var/log/myapp"
        assert result[2] == "Create Directory    /var/log/myapp"

    def test_generate_step_keywords_interactive_shell(self, ssh_generator):
        """Test SSH step keyword generation for interactive shell operations."""
        step = {"step": "Write command to shell", "test_data": "text: sudo apt update"}
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 3
        assert result[0] == "# Step: Write command to shell"
        assert result[1] == "    # Test Data: text: sudo apt update"
        assert result[2] == "Write    sudo apt update"

    def test_generate_step_keywords_logging_operations(self, ssh_generator):
        """Test SSH step keyword generation for logging operations."""
        step = {
            "step": "Enable SSH logging",
            "test_data": "logfile: /tmp/ssh_debug.log",
        }
        result = ssh_generator.generate_step_keywords(step)

        assert len(result) == 3
        assert result[0] == "# Step: Enable SSH logging"
        assert result[1] == "    # Test Data: logfile: /tmp/ssh_debug.log"
        assert result[2] == "Enable Ssh Logging    /tmp/ssh_debug.log"
