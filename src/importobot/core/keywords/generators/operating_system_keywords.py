"""Operating System keyword generation for Robot Framework."""

import re
from typing import Any

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.utils.pattern_extraction import extract_pattern
from importobot.utils.step_processing import extract_step_information


class OperatingSystemKeywordGenerator(BaseKeywordGenerator):
    """Generates OperatingSystem library Robot Framework keywords."""

    def generate_command_keyword(self, test_data: str) -> str:
        """Generate appropriate command execution keyword."""
        # First try to extract from "command:" or "cmd:" patterns
        command = extract_pattern(test_data, r"(?:command|cmd):\s*(.+)")

        # If no command pattern found, treat the entire test_data as the command
        if not command:
            # Clean up the test data and use it as the command
            command = test_data.strip()
            # Remove common prefixes that aren't part of the actual command
            command = re.sub(r"^(?:command|cmd):\s*", "", command, flags=re.IGNORECASE)

        # If still no command, use a placeholder
        if not command:
            command = "${command}"

        # Determine which library to use based on command characteristics
        return self._choose_command_library(command)

    def _choose_command_library(self, command: str) -> str:
        """Choose between OperatingSystem.Run and Run Process based on command needs."""
        command_lower = command.lower()

        # Check if the command is a known Robot Framework keyword
        known_keywords = [
            "should be equal",
            "should contain",
            "create file",
            "get file",
            "log",
            "input text",
            "input password",
            "click button",
            "page should contain",
        ]
        if any(command_lower.startswith(kw) for kw in known_keywords):
            return command

        # Special handling for network commands that should always use Run Process
        network_commands = ["curl", "wget"]
        first_word = command.split()[0] if command.split() else ""

        # If it's a network command, always use Run Process
        # and format arguments properly
        if any(first_word.startswith(net_cmd) for net_cmd in network_commands):
            # Split the command into arguments properly
            parts = command.split()
            if len(parts) > 1:
                # Format as "Run Process    cmd    arg1    arg2    ..."
                formatted_args = "    ".join(parts)
                return f"Run Process    {formatted_args}"
            return f"Run Process    {command}"

        # Check if it's a known simple command
        simple_commands = [
            "echo",
            "cat",
            "ls",
            "pwd",
            "whoami",
            "date",
            "uname",
            "hash",
            "md5sum",
            "sha1sum",
            "sha256sum",
            "sha512sum",
            "grep",
            "awk",
            "sed",
            "sort",
            "uniq",
            "wc",
            "head",
            "tail",
            "chmod",
            "chown",
            "mkdir",
            "rmdir",
            "touch",
            "cp",
            "mv",
            "rm",
            "ping",
            "netstat",
            "ps",
            "top",
            "df",
            "du",
        ]

        if any(first_word.startswith(simple_cmd) for simple_cmd in simple_commands):
            return f"Run    {command}"

        # Use Run Process for complex scenarios requiring process management
        process_scenarios = [
            # Long-running or interactive commands
            "&" in command,  # Background processes
            ">" in command and "|" in command,  # Complex piping/redirection
            "&&" in command or "||" in command,  # Command chaining
            command.count("|") > 1,  # Multiple pipes
            # Commands that typically require process interaction
            any(
                cmd in command_lower
                for cmd in [
                    "python",
                    "node",
                    "java",
                    "npm",
                    "yarn",
                    "docker",
                    "kubectl",
                ]
            ),
            # Commands with complex arguments (only for non-simple commands)
            len(command.split()) > 5,  # Many arguments might need careful handling
        ]

        if any(process_scenarios):
            return f"Run Process    {command}    shell=True"

        # Default to OperatingSystem.Run for unknown simple commands
        return f"Run    {command}"

    def generate_file_operation_keyword(self, description: str, test_data: str) -> str:
        """Generate file operation keywords."""
        desc_lower = description.lower()

        # File creation
        if "create" in desc_lower and "file" in desc_lower:
            return self.generate_create_file_keyword(test_data)

        # File reading
        if (
            any(word in desc_lower for word in ["read", "get", "cat", "view"])
            and "file" in desc_lower
        ):
            return self.generate_get_file_keyword(test_data)

        # File copying
        if "copy" in desc_lower and "file" in desc_lower:
            return self.generate_copy_file_keyword(test_data)

        # File removal
        if (
            any(word in desc_lower for word in ["remove", "delete", "rm"])
            and "file" in desc_lower
        ):
            return self.generate_remove_file_keyword(test_data)

        # Default to generic file operation
        return f"Run    {test_data}"

    def generate_create_file_keyword(self, test_data: str) -> str:
        """Generate Create File keyword."""
        # Extract file path and content
        path = extract_pattern(test_data, r"(?:file|path):\s*([^\s,]+)")
        content = extract_pattern(test_data, r"(?:content|text|data):\s*(.+)")

        if not path:
            path = "/tmp/test_file.txt"
        if not content:
            content = "Default content"

        return f"Create File    {path}    {content}"

    def generate_get_file_keyword(self, test_data: str) -> str:
        """Generate Get File keyword."""
        path = extract_pattern(test_data, r"(?:file|path):\s*([^\s,]+)")

        if not path:
            # Try to extract file path from the data
            path_match = re.search(
                r"([^\s]+\.txt|[^\s]+\.log|[^\s]+\.json|/[^\s]+)", test_data
            )
            if path_match:
                path = path_match.group(1)
            else:
                path = "/tmp/test_file.txt"

        return f"Get File    {path}"

    def generate_copy_file_keyword(self, test_data: str) -> str:
        """Generate Copy File keyword."""
        source = extract_pattern(test_data, r"(?:source|from):\s*([^\s,]+)")
        dest = extract_pattern(test_data, r"(?:dest|destination|to):\s*([^\s,]+)")

        if not source:
            source = "/tmp/source.txt"
        if not dest:
            dest = "/tmp/destination.txt"

        return f"Copy File    {source}    {dest}"

    def generate_remove_file_keyword(self, test_data: str) -> str:
        """Generate Remove File keyword."""
        path = extract_pattern(test_data, r"(?:file|path):\s*([^\s,]+)")

        if not path:
            # Try to extract file path from the data
            path_match = re.search(
                r"([^\s]+\.txt|[^\s]+\.log|[^\s]+\.json|/[^\s]+)", test_data
            )
            if path_match:
                path = path_match.group(1)
            else:
                path = "/tmp/test_file.txt"

        return f"Remove File    {path}"

    def generate_directory_operation_keyword(
        self, description: str, test_data: str
    ) -> str:
        """Generate directory operation keywords."""
        desc_lower = description.lower()

        # Directory creation
        if "create" in desc_lower and (
            "directory" in desc_lower or "dir" in desc_lower
        ):
            path = extract_pattern(test_data, r"(?:dir|directory|path):\s*([^\s,]+)")
            if not path:
                path = "/tmp/test_dir"
            return f"Create Directory    {path}"

        # Directory listing
        if "list" in desc_lower and ("directory" in desc_lower or "dir" in desc_lower):
            path = extract_pattern(test_data, r"(?:dir|directory|path):\s*([^\s,]+)")
            if not path:
                path = "/tmp"
            return f"List Directory    {path}"

        # Directory removal
        if any(word in desc_lower for word in ["remove", "delete"]) and (
            "directory" in desc_lower or "dir" in desc_lower
        ):
            path = extract_pattern(test_data, r"(?:dir|directory|path):\s*([^\s,]+)")
            if not path:
                path = "/tmp/test_dir"
            return f"Remove Directory    {path}"

        # Default
        return f"Run    {test_data}"

    def generate_environment_variable_keyword(
        self, description: str, test_data: str
    ) -> str:
        """Generate environment variable keywords."""
        desc_lower = description.lower()

        # Set environment variable
        if "set" in desc_lower and ("env" in desc_lower or "environment" in desc_lower):
            name = extract_pattern(test_data, r"(?:name|var|variable):\s*([^\s,=]+)")
            value = extract_pattern(test_data, r"(?:value|val):\s*(.+)")

            if not name:
                name = "TEST_VAR"
            if not value:
                value = "test_value"

            return f"Set Environment Variable    {name}    {value}"

        # Get environment variable
        if "get" in desc_lower and ("env" in desc_lower or "environment" in desc_lower):
            name = extract_pattern(test_data, r"(?:name|var|variable):\s*([^\s,=]+)")

            if not name:
                name = "PATH"

            return f"Get Environment Variable    {name}"

        # Default
        return f"Run    {test_data}"

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for an OperatingSystem step."""
        lines = []

        # Add standard step header comments
        lines.extend(self._generate_step_header_comments(step))

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)

        # Generate Robot keyword based on step content
        combined = f"{description} {test_data}".lower()

        # Determine the type of operation
        if any(
            file_op in combined
            for file_op in [
                "file",
                "create file",
                "read file",
                "copy file",
                "remove file",
            ]
        ):
            keyword = self.generate_file_operation_keyword(description, test_data)
        elif any(
            dir_op in combined
            for dir_op in ["directory", "dir", "create dir", "list dir"]
        ):
            keyword = self.generate_directory_operation_keyword(description, test_data)
        elif any(
            env_op in combined
            for env_op in ["environment", "env var", "set env", "get env"]
        ):
            keyword = self.generate_environment_variable_keyword(description, test_data)
        else:
            # Default to command execution
            keyword = self.generate_command_keyword(test_data)

        lines.append(keyword)
        return lines
