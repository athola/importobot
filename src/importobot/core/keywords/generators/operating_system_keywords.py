"""Operating System keyword generation for Robot Framework."""

import os
import re
from typing import Any, ClassVar

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.utils.pattern_extraction import extract_pattern
from importobot.utils.step_processing import extract_step_information

_SAFE_DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), "importobot")


def _safe_home_path(name: str) -> str:
    """Return a predictable, non-world-writable default path."""
    cleaned = name.lstrip("/\\")
    return os.path.join(_SAFE_DEFAULT_ROOT, cleaned) if cleaned else _SAFE_DEFAULT_ROOT


class OperatingSystemKeywordGenerator(BaseKeywordGenerator):
    """Generate OperatingSystem library Robot Framework keywords."""

    BINARY_EXTENSIONS: ClassVar[set[str]] = {
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".tif",
        ".tiff",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".exe",
        ".dll",
        ".so",
        ".o",
        ".class",
        ".jar",
        ".war",
        ".ear",
        ".pyc",
        ".db",
        ".sqlite",
        ".mdb",
        ".iso",
        ".img",
        ".bin",
        ".dat",
    }

    COMMAND_TO_KEYWORD: ClassVar[dict[str, str]] = {
        "cat": "Get File",
        "ls": "List Directory",
        "mkdir": "Create Directory",
        "rmdir": "Remove Directory",
        "touch": "Create File",
        "cp": "Copy File",
        "mv": "Move File",
        "rm": "Remove File",
    }

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

    def _check_known_keywords(self, command_lower: str) -> str | None:
        """Check if the command is a known Robot Framework keyword."""
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
            return command_lower
        return None

    def _handle_simple_command_mapping(
        self, command: str, parts: list[str], first_word: str
    ) -> str | None:
        """Handle mapping of simple commands to specific keywords."""
        if first_word not in self.COMMAND_TO_KEYWORD:
            return None

        keyword = self.COMMAND_TO_KEYWORD[first_word]
        args = parts[1:]

        # Handle different keywords with dedicated methods
        if keyword == "Get File":
            return self._handle_get_file_command(command, args)
        if keyword == "Copy File":
            return self._handle_copy_file_command(command, args)
        if keyword == "Move File":
            return self._handle_move_file_command(command, args)
        if keyword == "Create File":
            if not args:
                return f"{keyword}    {_safe_home_path('new_file')}"
            return f"{keyword}    {'    '.join(args)}"
        if args:
            return f"{keyword}    {'    '.join(args)}"
        # For commands that need a path, default to current dir
        if keyword in (
            "Get File",
            "List Directory",
            "Remove File",
            "Create Directory",
            "Remove Directory",
        ):
            return f"{keyword}    ."
        return f"Run    {command}"

    def _handle_get_file_command(self, command: str, args: list[str]) -> str:
        """Handle Get File command."""
        if len(args) == 1:
            filepath = args[0]
            ext = os.path.splitext(filepath)[1].lower()
            if ext in self.BINARY_EXTENSIONS:
                return f"Get Binary File    {filepath}"
            return f"Get File    {filepath}"
        return f"Run    {command}"

    def _handle_copy_file_command(self, command: str, args: list[str]) -> str:
        """Handle Copy File command."""
        if len(args) > 1:
            sources = args[:-1]
            destination = args[-1]
            if len(sources) == 1:
                return f"Copy File    {sources[0]}    {destination}"
            return f"Copy Files    {'    '.join(sources)}    {destination}"
        return f"Run    {command}"

    def _handle_move_file_command(self, command: str, args: list[str]) -> str:
        """Handle Move File command."""
        if len(args) > 1:
            sources = args[:-1]
            destination = args[-1]
            if len(sources) == 1:
                return f"Move File    {sources[0]}    {destination}"
            return f"Move Files    {'    '.join(sources)}    {destination}"
        return f"Run    {command}"

    def _handle_network_commands(
        self, command: str, parts: list[str], first_word: str
    ) -> str | None:
        """Handle special network commands that should use Run Process."""
        network_commands = ["curl", "wget"]
        if any(first_word.startswith(net_cmd) for net_cmd in network_commands):
            # Split the command into arguments properly
            if len(parts) > 1:
                # Format as "Run Process    cmd    arg1    arg2    ..."
                formatted_args = "    ".join(parts)
                return f"Run Process    {formatted_args}"
            return f"Run Process    {command}"
        return None

    def _handle_simple_commands(self, command: str, first_word: str) -> str | None:
        """Check if it's a known simple command."""
        simple_commands = [
            "echo",
            "pwd",
            "whoami",
            "date",
            "uname",
            "hash",
            "md5sum",
            "sha1sum",
            "blake2bsum",
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
            "ping",
            "netstat",
            "ps",
            "top",
            "df",
            "du",
        ]

        if any(first_word.startswith(simple_cmd) for simple_cmd in simple_commands):
            return f"Run    {command}"
        return None

    def _handle_complex_commands(self, command: str, command_lower: str) -> str | None:
        """Use Run Process for complex scenarios requiring process management."""
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
        return None

    def _choose_command_library(self, command: str) -> str:
        """Choose between OperatingSystem.Run and Run Process based on command needs."""
        command_lower = command.lower()
        parts = command.split()
        first_word = parts[0].lower() if parts else ""

        # Check if the command is a known Robot Framework keyword
        known_result = self._check_known_keywords(command_lower)
        if known_result is not None:
            return known_result

        # Handle simple command mappings
        mapped_result = self._handle_simple_command_mapping(command, parts, first_word)
        if mapped_result is not None:
            return mapped_result

        # Handle network commands
        network_result = self._handle_network_commands(command, parts, first_word)
        if network_result is not None:
            return network_result

        # Handle simple commands
        simple_result = self._handle_simple_commands(command, first_word)
        if simple_result is not None:
            return simple_result

        # Handle complex commands
        complex_result = self._handle_complex_commands(command, command_lower)
        if complex_result is not None:
            return complex_result

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
            path = _safe_home_path("test_file.txt")
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
                path = _safe_home_path("test_file.txt")

        return f"Get File    {path}"

    def generate_copy_file_keyword(self, test_data: str) -> str:
        """Generate Copy File keyword."""
        source = extract_pattern(test_data, r"(?:source|from):\s*([^\s,]+)")
        dest = extract_pattern(test_data, r"(?:dest|destination|to):\s*([^\s,]+)")

        if not source:
            source = _safe_home_path("source.txt")
        if not dest:
            dest = _safe_home_path("destination.txt")

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
                path = _safe_home_path("test_file.txt")

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
                path = _safe_home_path("test_dir")
            return f"Create Directory    {path}"

        # Directory listing
        if "list" in desc_lower and ("directory" in desc_lower or "dir" in desc_lower):
            path = extract_pattern(test_data, r"(?:dir|directory|path):\s*([^\s,]+)")
            if not path:
                path = _SAFE_DEFAULT_ROOT
            return f"List Directory    {path}"

        # Directory removal
        if any(word in desc_lower for word in ["remove", "delete"]) and (
            "directory" in desc_lower or "dir" in desc_lower
        ):
            path = extract_pattern(test_data, r"(?:dir|directory|path):\s*([^\s,]+)")
            if not path:
                path = _safe_home_path("test_dir")
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
