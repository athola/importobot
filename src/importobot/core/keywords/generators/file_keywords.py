"""File operation keyword generation for Robot Framework."""

import json
import os
import re
from typing import Any

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.utils.pattern_extraction import extract_pattern
from importobot.utils.step_processing import extract_step_information
from importobot.utils.validation import format_robot_framework_arguments

_SAFE_FILE_ROOT = os.path.join(os.path.expanduser("~"), "importobot", "files")


def _safe_file_path(name: str) -> str:
    """Return a predictable default path outside world-writable temp locations."""
    cleaned = name.lstrip("/\\")
    return os.path.join(_SAFE_FILE_ROOT, cleaned) if cleaned else _SAFE_FILE_ROOT


class FileKeywordGenerator(BaseKeywordGenerator):
    """Generate file operation-related Robot Framework keywords."""

    def generate_transfer_keyword(self, test_data: str) -> str:
        """Generate file transfer keyword."""
        # First try to parse scp command format: scp user@host:/remote/path local_path
        scp_match = re.search(r"scp\s+\w+@[^:]+:([^\s]+)\s+([^\s]+)", test_data)
        if scp_match:
            remote_path = scp_match.group(1)
            local_path = scp_match.group(2)
            return format_robot_framework_arguments("Get File", remote_path, local_path)

        # Default to structured format
        remote = extract_pattern(test_data, r"Remote File Path:\s*([^,\s]+)")
        local = extract_pattern(test_data, r"Local Destination Path:\s*([^,\s]+)")

        args = []
        if remote:
            args.append(remote)
        if local:
            args.append(local)

        # Get File requires at least a remote path
        if args:
            return format_robot_framework_arguments("Get File", *args)
        return (
            "Get File    "
            f"{_safe_file_path('remote.txt')}    {_safe_file_path('local.txt')}"
        )

    def generate_exists_keyword(self, test_data: str) -> str:
        """Generate file exists verification keyword."""
        # Look for explicit file paths
        path = extract_pattern(test_data, r"/[^\s,]+|[a-zA-Z]:\\[^\s,]+")
        if not path:
            # Try alternative patterns for file paths in test data
            path = extract_pattern(test_data, r"at\s+([^\s,]+)")
        if not path:
            # Look for file names with extensions
            path_match = re.search(
                r"([a-zA-Z0-9_.-]+\.txt|[a-zA-Z0-9_.-]+\.json|"
                r"[a-zA-Z0-9_.-]+\.[a-zA-Z]+)",
                test_data,
            )
            if path_match:
                path = path_match.group(1)
        # File Should Exist requires a path argument
        if path:
            return f"File Should Exist    {path}"
        return f"File Should Exist    {_safe_file_path('test.txt')}"

    def generate_remove_keyword(self, test_data: str) -> str:
        """Generate file removal keyword."""
        # First try to extract from "rm path" or "Command: rm path" patterns
        path = extract_pattern(test_data, r"rm\s+([^\s]+)")
        if not path:
            # Try generic file path extraction
            path = extract_pattern(test_data, r"/[^\s,]+|[a-zA-Z]:\\[^\s,]+")
        # Remove File requires a path argument
        return (
            f"Remove File    {path}"
            if path
            else f"Remove File    {_safe_file_path('test.txt')}"
        )

    def generate_create_keyword(self, description: str, test_data: str) -> str:
        """Generate file creation keyword."""
        # Extract variables from description or test data
        file_var = re.search(r"\$\{(\w+)\}", description)
        content_var = re.search(r"\$\{(\w+content\w*)\}", description, re.IGNORECASE)

        if file_var and content_var:
            file_param = file_var.group(1)
            content_param = content_var.group(1)
            return f"Create File    ${{{file_param}}}    ${{{content_param}}}"
        if file_var:
            file_param = file_var.group(1)
            return f"Create File    ${{{file_param}}}    Default content"
        # Try to extract from test data
        path = extract_pattern(test_data, r"fileName:\s*([^,\s]+)")
        content = extract_pattern(test_data, r"fileContent:\s*(.+)")
        if path and content:
            return f"Create File    {path}    {content}"
        return "Create File    test_file.txt    Test content"

    def generate_operation_keyword(self, description: str, test_data: str) -> str:
        """Generate general file operation keyword."""
        desc_lower = description.lower()
        if "read" in desc_lower or "cat" in desc_lower:
            file_var = re.search(r"\$\{(\w+)\}", description)
            if file_var:
                return f"Get File    ${{{file_var.group(1)}}}"
            path = extract_pattern(test_data, r"fileName:\s*([^,\s]+)")
            return f"Get File    {path}" if path else "Get File    test_file.txt"
        if "copy" in desc_lower:
            return self._extract_copy_move_arguments(
                "Copy File", description, test_data
            )
        if "move" in desc_lower:
            return self._extract_copy_move_arguments(
                "Move File", description, test_data
            )
        return "No Operation    # Generic file operation"

    def _extract_copy_move_arguments(
        self, operation: str, description: str, test_data: str
    ) -> str:
        """Extract arguments for copy/move operations."""
        # Extract source and destination from description or test data
        variables = re.findall(r"\$\{([^}]+)\}", description)

        if len(variables) == 2:
            return f"{operation}    ${{{variables[0]}}}    ${{{variables[1]}}}"

        # Try to extract from test data as JSON
        try:
            data = json.loads(test_data)
            source = data.get("sourceFile") or data.get("source")
            dest = data.get("destinationFile") or data.get("destination")
            if source and dest:
                return f"{operation}    {source}    {dest}"
        except (json.JSONDecodeError, AttributeError):
            # Not a JSON string or not a dict, try regex
            pass

        # Try to extract from test data with regex
        source = extract_pattern(test_data, r"(?:source|sourceFile)=([^,\s]+)")
        dest = extract_pattern(
            test_data, r"(?:dest|destination|destinationFile)=([^,\s]+)"
        )

        if source and dest:
            return f"{operation}    {source}    {dest}"

        return f"{operation}    ${{source_file}}    ${{destination_file}}"

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for a file operation step."""
        lines = []

        # Add standard step header comments
        lines.extend(self._generate_step_header_comments(step))

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)

        # Generate Robot keyword based on step content
        combined = f"{description} {test_data}".lower()

        if "transfer" in combined or "get file" in combined:
            keyword = self.generate_transfer_keyword(test_data)
        elif "exists" in combined or "verify" in combined:
            keyword = self.generate_exists_keyword(test_data)
        elif "remove" in combined or "delete" in combined:
            keyword = self.generate_remove_keyword(test_data)
        elif "create" in combined:
            keyword = self.generate_create_keyword(description, test_data)
        else:
            keyword = self.generate_operation_keyword(description, test_data)

        lines.append(keyword)
        return lines
