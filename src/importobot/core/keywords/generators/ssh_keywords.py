"""SSH keyword generation for Robot Framework."""

import re
from typing import Any

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.utils.pattern_extraction import extract_pattern
from importobot.utils.step_comments import generate_step_comments
from importobot.utils.step_processing import (
    extract_step_information,
)
from importobot.utils.validation import format_robot_framework_arguments


class SSHKeywordGenerator(BaseKeywordGenerator):
    """Generate SSH-related Robot Framework keywords."""

    def generate_connect_keyword(self, test_data: str) -> str:
        """Generate SSH connection keyword."""
        # Get keyword name from registry
        _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
            "ssh_connect"
        )

        # First try to parse ssh command format: ssh user@host
        ssh_match = re.search(r"ssh\s+(\w+)@([^\s]+)", test_data, re.IGNORECASE)
        if ssh_match:
            username = ssh_match.group(1)
            host = ssh_match.group(2)
            return format_robot_framework_arguments(keyword_name, host, username)

        # If ssh command format fails, try structured format
        host = extract_pattern(test_data, r"(?:host|server)\s*:\s*([^,\s]+)")
        username = extract_pattern(test_data, r"username\s*:\s*([^,\s]+)")
        password = extract_pattern(test_data, r"password\s*:\s*([^,\s]+)")

        args = [host] if host else []
        if username:
            args.append(username)
            if password:
                args.append(password)

        # Open Connection requires at least a host
        if args:
            return format_robot_framework_arguments(keyword_name, *args)
        return f"{keyword_name}    ${{HOST}}"

    def generate_execute_keyword(self, test_data: str) -> str:
        """Generate SSH Execute Command keyword."""
        # Get keyword name from registry
        _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
            "ssh_execute"
        )

        command = extract_pattern(test_data, r"(?:command|cmd):\s*(.*)")

        # Use parameterized placeholder for missing commands
        if not command or command.strip() == "":
            command = "${COMMAND}"

        return f"{keyword_name}    {command}"

    def generate_file_transfer_keyword(self, test_data: str, operation: str) -> str:
        """Generate SSH file transfer keywords."""
        # Get keyword names from registry
        if operation in ("upload", "put"):
            _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
                "ssh_file_upload"
            )
        elif operation in ("download", "get"):
            _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
                "ssh_file_download"
            )
        else:
            _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
                "ssh_put_file"
            )

        # Enhanced patterns for various file path formats
        source = extract_pattern(
            test_data, r"(?:Remote\s+File\s+Path|source|from):\s*([^,\s]+)"
        ) or extract_pattern(test_data, r"(?:source|from):\s*([^,\s]+)")
        destination = extract_pattern(
            test_data,
            r"(?:Local\s+Destination\s+Path|destination|dest|to):\s*([^,\s]+)",
        ) or extract_pattern(test_data, r"(?:destination|dest|to):\s*([^,\s]+)")

        if not source:
            source = "${SOURCE_FILE}"
        if not destination:
            destination = "${DESTINATION_PATH}"

        return format_robot_framework_arguments(keyword_name, source, destination)

    def generate_file_verification_keyword(
        self, test_data: str, should_exist: bool = True
    ) -> str:
        """Generate SSH file verification keywords."""
        file_path = extract_pattern(test_data, r"(?:file|path):\s*([^,\s]+)")

        if not file_path:
            file_path = "${FILE_PATH}"

        if should_exist:
            return format_robot_framework_arguments("File Should Exist", file_path)
        return format_robot_framework_arguments("File Should Not Exist", file_path)

    def generate_directory_operations_keyword(
        self, test_data: str, operation: str
    ) -> str:
        """Generate SSH directory operation keywords."""
        path = extract_pattern(test_data, r"(?:directory|dir|path):\s*([^,\s]+)")

        if not path:
            path = "${DIRECTORY_PATH}"

        if operation == "create":
            return format_robot_framework_arguments("Create Directory", path)
        if operation == "remove":
            return format_robot_framework_arguments("Remove Directory", path)
        if operation == "list":
            return format_robot_framework_arguments("List Directory", path)
        if operation == "verify_exists":
            return format_robot_framework_arguments("Directory Should Exist", path)
        if operation == "verify_not_exists":
            return format_robot_framework_arguments("Directory Should Not Exist", path)
        return format_robot_framework_arguments("List Directory", path)

    def generate_interactive_shell_keyword(self, test_data: str, operation: str) -> str:
        """Generate SSH interactive shell keywords."""
        if operation == "write":
            text = extract_pattern(test_data, r"(?:text|write|send):\s*(.+)")
            if not text:
                text = "${TEXT_TO_WRITE}"
            return format_robot_framework_arguments("Write", text)
        if operation == "read":
            return "Read"
        if operation == "read_until":
            expected = extract_pattern(test_data, r"(?:until|expected):\s*(.+)")
            if not expected:
                expected = "${EXPECTED_TEXT}"
            return format_robot_framework_arguments("Read Until", expected)
        if operation == "read_until_prompt":
            return "Read Until Prompt"
        return "Read"

    def _generate_connection_keywords(self, combined: str, test_data: str) -> str:
        """Generate connection management keywords."""
        # Check for specific connection operations first
        if "switch" in combined and "connection" in combined:
            return "Switch Connection    ${CONNECTION_ALIAS}"
        if "close all" in combined or (
            "close" in combined and "all" in combined and "connection" in combined
        ):
            return "Close All Connections"
        if "disconnect" in combined or (
            "close" in combined and ("connection" in combined or "ssh" in combined)
        ):
            return "Close Connection"
        if "connect" in combined or "open" in combined:
            return self.generate_connect_keyword(test_data)
        return ""

    def _generate_authentication_keywords(self, combined: str, test_data: str) -> str:
        """Generate authentication keywords."""
        if "login" in combined:
            if "key" in combined or "public" in combined:
                username = extract_pattern(test_data, r"username:\s*([^,\s]+)")
                keyfile = extract_pattern(test_data, r"(?:key|keyfile):\s*([^,\s]+)")
                if username and keyfile:
                    return format_robot_framework_arguments(
                        "Login With Public Key", username, keyfile
                    )
                return "Login With Public Key    ${USERNAME}    ${KEYFILE}"
            username = extract_pattern(test_data, r"username:\s*([^,\s]+)")
            password = extract_pattern(test_data, r"password:\s*([^,\s]+)")
            if username and password:
                return format_robot_framework_arguments("Login", username, password)
            return "Login    ${USERNAME}    ${PASSWORD}"
        return ""

    def _generate_configuration_keywords(self, combined: str, test_data: str) -> str:
        """Generate SSH configuration keywords."""
        if "set" in combined and ("configuration" in combined or "config" in combined):
            return self.generate_configuration_keyword(test_data, "client")
        if "set default configuration" in combined:
            return self.generate_configuration_keyword(test_data, "default")
        return ""

    def _generate_command_execution_keywords(
        self, combined: str, test_data: str
    ) -> str:
        """Generate command execution keywords."""
        if "start" in combined and (
            "command" in combined or "background" in combined or "process" in combined
        ):
            command = extract_pattern(test_data, r"(?:command|cmd):\s*(.+)")
            if command:
                return format_robot_framework_arguments("Start Command", command)
            return "Start Command    ${COMMAND}"
        if "read" in combined and "output" in combined:
            return "Read Command Output"
        if "execute" in combined or "command" in combined:
            return self.generate_execute_keyword(test_data)
        return ""

    def _generate_file_operation_keywords(self, combined: str, test_data: str) -> str:
        """Generate file operation keywords."""
        if any(op in combined for op in ["upload", "put", "send file"]):
            return self.generate_file_transfer_keyword(test_data, "upload")
        if any(op in combined for op in ["download", "get", "receive file"]):
            return self.generate_file_transfer_keyword(test_data, "download")
        if "file should exist" in combined or "verify file" in combined:
            return self.generate_file_verification_keyword(test_data, should_exist=True)
        if "file should not exist" in combined:
            return self.generate_file_verification_keyword(
                test_data, should_exist=False
            )
        if "create file" in combined:
            file_path = extract_pattern(test_data, r"(?:file|path):\s*([^,\s]+)")
            content = extract_pattern(test_data, r"(?:content|data):\s*(.+)")
            if file_path:
                if content:
                    return format_robot_framework_arguments(
                        "Create File", file_path, content
                    )
                return format_robot_framework_arguments("Create File", file_path)
            return "Create File    ${FILE_PATH}    ${CONTENT}"
        if "remove file" in combined or "delete file" in combined:
            file_path = extract_pattern(test_data, r"(?:file|path):\s*([^,\s]+)")
            if file_path:
                return format_robot_framework_arguments("Remove File", file_path)
            return "Remove File    ${FILE_PATH}"
        return ""

    def _generate_directory_keywords(self, combined: str, test_data: str) -> str:
        """Generate directory operation keywords."""
        if "create directory" in combined or "mkdir" in combined:
            return self.generate_directory_operations_keyword(test_data, "create")
        if "remove directory" in combined or "rmdir" in combined:
            return self.generate_directory_operations_keyword(test_data, "remove")
        if "list directory" in combined or "ls" in combined:
            return self.generate_directory_operations_keyword(test_data, "list")
        if "directory should exist" in combined:
            return self.generate_directory_operations_keyword(
                test_data, "verify_exists"
            )
        if "directory should not exist" in combined:
            return self.generate_directory_operations_keyword(
                test_data, "verify_not_exists"
            )
        return ""

    def _generate_shell_keywords(self, combined: str, test_data: str) -> str:
        """Generate interactive shell keywords."""
        # Check for write/send operations specifically for shell interaction
        if ("write" in combined and ("shell" in combined or "text" in test_data)) or (
            "send" in combined and "text" in test_data
        ):
            return self.generate_interactive_shell_keyword(test_data, "write")
        if "read until prompt" in combined:
            return self.generate_interactive_shell_keyword(
                test_data, "read_until_prompt"
            )
        if "read until" in combined:
            return self.generate_interactive_shell_keyword(test_data, "read_until")
        if "read" in combined and ("shell" in combined or "output" in combined):
            return self.generate_interactive_shell_keyword(test_data, "read")
        return ""

    def _generate_logging_keywords(self, combined: str, test_data: str) -> str:
        """Generate logging operation keywords."""
        if ("enable" in combined and "logging" in combined) or (
            "start" in combined and "logging" in combined
        ):
            logfile = extract_pattern(test_data, r"(?:logfile|log):\s*([^,\s]+)")
            if logfile:
                return format_robot_framework_arguments("Enable Ssh Logging", logfile)
            return "Enable Ssh Logging    ${LOGFILE}"
        if ("disable" in combined and "logging" in combined) or (
            "stop" in combined and "logging" in combined
        ):
            return "Disable Ssh Logging"
        return ""

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for an SSH-related step."""
        lines = []

        # Add traceability comments using shared utility, apply SSH indentation
        base_comments = generate_step_comments(step)
        for comment in base_comments:
            # SSH-specific indentation: Test Data comments get 4 spaces
            if comment.startswith("# Test Data:"):
                lines.append(f"    {comment}")
            else:
                lines.append(comment)

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)

        # Generate Robot keyword based on step content
        combined = f"{description} {test_data}".lower()

        # Try different keyword generation methods in priority order
        # More specific patterns first to avoid conflicts
        keyword = (
            self._generate_connection_keywords(combined, test_data)
            or self._generate_authentication_keywords(combined, test_data)
            or self._generate_configuration_keywords(combined, test_data)
            or self._generate_logging_keywords(combined, test_data)
            or self._generate_shell_keywords(combined, test_data)
            or self._generate_file_operation_keywords(combined, test_data)
            or self._generate_directory_keywords(combined, test_data)
            or self._generate_command_execution_keywords(combined, test_data)
            or "No Operation  # SSH operation not recognized"
        )

        lines.append(keyword)
        return lines

    def generate_configuration_keyword(self, test_data: str, config_type: str) -> str:
        """Generate SSH configuration keyword."""
        if config_type == "client":
            # Extract configuration parameters
            encoding = extract_pattern(test_data, r"encoding[:\s=]+([^,\s]+)")
            term_type = extract_pattern(test_data, r"term_type[:\s=]+([^,\s]+)")
            timeout = extract_pattern(test_data, r"timeout[:\s=]+([^,\s]+)")

            # Build Set Client Configuration with available parameters
            args = []
            if encoding:
                args.extend(["encoding", encoding])
            if term_type:
                args.extend(["term_type", term_type])
            if timeout:
                args.extend(["timeout", timeout])

            if args:
                return format_robot_framework_arguments(
                    "Set Client Configuration", *args
                )
            return "Set Client Configuration"

        if config_type == "default":
            # Extract default configuration parameters
            timeout = extract_pattern(test_data, r"timeout[:\s=]+([^,\s]+)")
            prompt = extract_pattern(test_data, r"prompt[:\s=]+([^,\s]+)")

            args = []
            if timeout:
                args.extend(["timeout", timeout])
            if prompt:
                args.extend(["prompt", prompt])

            if args:
                return format_robot_framework_arguments(
                    "Set Default Configuration", *args
                )
            return "Set Default Configuration"

        return "Set Client Configuration"

    def generate_logging_keyword(self, test_data: str, operation: str) -> str:
        """Generate SSH logging keyword."""
        logfile = extract_pattern(test_data, r"logfile[:\s=]+([^,\s]+)")

        if operation == "enable":
            if logfile:
                return format_robot_framework_arguments("Enable Ssh Logging", logfile)
            return "Enable Ssh Logging"
        if operation == "disable":
            return "Disable Ssh Logging"
        return "Enable Ssh Logging"
