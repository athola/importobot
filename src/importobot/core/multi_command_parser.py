"""Multi-command parsing module for Robot Framework conversion.

This module handles the conversion of single JSON test steps into multiple
Robot Framework commands, enabling more sophisticated test automation scenarios.
"""

import re
import shlex


class MultiCommandParser:
    """Parser generating multiple Robot Framework commands from a single JSON step.

    This parser handles the conversion of single JSON test steps into multiple
    Robot Framework commands, enabling more sophisticated test automation scenarios.
    """

    def parse_test_data(self, test_data: str) -> dict[str, str]:
        """Parse test data string into key-value pairs."""
        if not test_data:
            return {}

        parsed = {}

        # Handle comma-separated key:value pairs
        if ":" in test_data and "," in test_data:
            pairs = test_data.split(",")
            for pair in pairs:
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    parsed[key.strip()] = value.strip()
        # Handle single key:value pair or space-separated pairs (no commas)
        elif ":" in test_data:
            # First try to parse as single key:value pair
            if test_data.count(":") == 1:
                key, value = test_data.split(":", 1)
                parsed[key.strip()] = value.strip()
            else:
                # Multiple colons, try space-separated parsing
                parts = test_data.split()
                for part in parts:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        parsed[key.strip()] = value.strip()

        return parsed

    def should_generate_multiple_commands(
        self, description: str, parsed_data: dict[str, str]
    ) -> bool:
        """Determine if multiple commands should be generated from parsed data."""
        # Check for form filling scenarios
        form_indicators = ["fill", "enter", "input", "form", "details", "credentials"]
        if any(indicator in description.lower() for indicator in form_indicators):
            # Check for multiple input fields with flexible matching
            input_fields = ["email", "password", "username", "name", "phone", "address"]
            field_count = 0

            for field_name in parsed_data:
                field_lower = field_name.lower()
                # Check for flexible matching including variations
                # with underscores, etc.
                if any(inp in field_lower for inp in input_fields) or any(
                    variation in field_lower
                    for variation in [
                        "mail",
                        "pass",
                        "user",
                        "login",
                        "username",
                        "phone",
                        "tel",
                        "addr",
                    ]
                ):
                    field_count += 1

            if field_count >= 2:
                return True

        # Check for database scenarios with multiple operations
        if "query" in description.lower() and "verify" in description.lower():
            return True

        # Check for API scenarios with request and validation
        if "api" in description.lower() or (
            "request" in description.lower() and "validate" in description.lower()
        ):
            return True

        # Check for file operations with verification
        if "upload" in description.lower() and "verify" in description.lower():
            return True

        # Detect hash comparison style operations
        return self._is_hash_comparison_operation(description, parsed_data)

    def generate_multiple_robot_keywords(
        self, description: str, parsed_data: dict[str, str], expected: str
    ) -> list[str]:
        """Generate multiple Robot Framework keywords from parsed data."""
        keywords = []

        # Detect the type of operations needed
        if self._is_form_filling_operation(description, parsed_data):
            keywords.extend(self._generate_form_filling_keywords(parsed_data))
        elif self._is_database_operation(description):
            keywords.extend(
                self._generate_database_keywords(description, parsed_data, expected)
            )
        elif self._is_api_operation(description):
            keywords.extend(
                self._generate_api_keywords(description, parsed_data, expected)
            )
        elif self._is_file_upload_operation(description):
            keywords.extend(self._generate_file_upload_keywords(parsed_data, expected))
        elif self._is_hash_comparison_operation(description, parsed_data):
            keywords.extend(self._generate_command_comparison_keywords(parsed_data))
        else:
            # Fall back to generic processing
            keywords.extend(self._generate_generic_keywords(parsed_data))

        return keywords

    def _is_form_filling_operation(
        self, description: str, parsed_data: dict[str, str]
    ) -> bool:
        """Check if this is a form filling operation."""
        # parsed_data parameter is kept for interface consistency
        # but not used in this implementation
        _ = parsed_data  # Mark as intentionally unused
        form_indicators = ["fill", "enter", "input", "form", "details", "credentials"]
        return any(indicator in description.lower() for indicator in form_indicators)

    def _is_database_operation(self, description: str) -> bool:
        """Check if this is a database operation."""
        return "query" in description.lower() and "verify" in description.lower()

    def _is_api_operation(self, description: str) -> bool:
        """Check if this is an API operation."""
        return "api" in description.lower() or (
            "request" in description.lower() and "validate" in description.lower()
        )

    def _is_file_upload_operation(self, description: str) -> bool:
        """Check if this is a file upload operation."""
        return "upload" in description.lower() and "verify" in description.lower()

    def _is_hash_comparison_operation(
        self, description: str, parsed_data: dict[str, str]
    ) -> bool:
        """Detect whether the step represents a hash comparison workflow."""
        if not parsed_data:
            return False
        keys = {key.lower() for key in parsed_data}
        if {"command_1", "command_2"}.issubset(keys):
            return True
        if {"source_command", "target_command"}.issubset(keys):
            return True
        description_lower = description.lower() if description else ""
        keywords = ["hash", "checksum", "digest", "compare", "diff"]
        return any(token in description_lower for token in keywords)

    def _generate_command_comparison_keywords(
        self, parsed_data: dict[str, str]
    ) -> list[str]:
        """Generate commands to compare outputs of two hash commands."""
        source_command = (
            parsed_data.get("command_1")
            or parsed_data.get("source_command")
            or parsed_data.get("source")
        )
        target_command = (
            parsed_data.get("command_2")
            or parsed_data.get("target_command")
            or parsed_data.get("target")
        )

        if not source_command or not target_command:
            return []

        source_tokens = self._split_command(source_command)
        target_tokens = self._split_command(target_command)
        if not source_tokens or not target_tokens:
            return []

        commands: list[str] = []
        commands.append(self._format_run_process_command(source_tokens, "hash_source"))
        commands.append(self._format_run_process_command(target_tokens, "hash_target"))
        commands.append(
            "Should Be Equal As Strings    ${hash_source}    ${hash_target}"
        )
        return commands

    def _split_command(self, command: str) -> list[str]:
        """Split a shell command into Robot Framework arguments."""
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        return [token for token in tokens if token]

    def _format_run_process_command(self, tokens: list[str], var_name: str) -> str:
        """Format a Run Process command capturing stdout into a variable."""
        if not tokens:
            return "Run Process"
        command = tokens[0]
        arguments = "    ".join(tokens[1:])
        stdout_capture = f"stdout=${{{var_name}}}"
        if arguments:
            return f"Run Process    {command}    {arguments}    {stdout_capture}"
        return f"Run Process    {command}    {stdout_capture}"

    def _generate_form_filling_keywords(self, parsed_data: dict[str, str]) -> list[str]:
        """Generate form filling keywords from parsed data."""
        keywords = []

        for field, value in parsed_data.items():
            field_lower = field.lower()
            if "password" in field_lower or "pass" in field_lower:
                keywords.append(f"Input Password    id={field}    {value}")
            elif any(
                field_type in field_lower
                for field_type in [
                    "email",
                    "mail",
                    "username",
                    "user",
                    "name",
                    "phone",
                    "tel",
                    "address",
                    "addr",
                ]
            ):
                keywords.append(f"Input Text    id={field}    {value}")
            elif field_lower in ["remember", "active", "agree"]:
                if value.lower() in ["true", "yes", "1"]:
                    keywords.append(f"Select Checkbox    id={field}")
                else:
                    keywords.append(f"Unselect Checkbox    id={field}")
            else:
                # Default to text input
                keywords.append(f"Input Text    id={field}    {value}")

        return keywords

    def _generate_database_keywords(
        self, description: str, parsed_data: dict[str, str], expected: str
    ) -> list[str]:
        """Generate database operation keywords."""
        # description parameter is kept for interface consistency
        # but not used in this implementation
        _ = description  # Mark as intentionally unused
        keywords = []

        # Extract SQL query if present
        sql_query = None
        for value in parsed_data.values():
            if any(
                keyword in value.upper()
                for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE"]
            ):
                sql_query = value
                break

        if sql_query:
            keywords.append(f"Query    {sql_query}")

            # Add verification based on expected result
            if expected and "returns" in expected.lower():
                # Extract row count if mentioned
                count_match = re.search(r"(\d+)", expected)
                if count_match:
                    count = count_match.group(1)
                    keywords.append(f"Row Count Should Be Equal To    {count}")

        return keywords

    def _generate_api_keywords(
        self, description: str, parsed_data: dict[str, str], expected: str
    ) -> list[str]:
        """Generate API operation keywords."""
        # description parameter is kept for interface consistency
        # but not used in this implementation
        _ = description  # Mark as intentionally unused
        keywords = []

        # Look for HTTP method and endpoint
        endpoint = None
        method = "GET"  # default

        for value in parsed_data.values():
            if value.startswith(("GET ", "POST ", "PUT ", "DELETE ")):
                parts = value.split(" ", 1)
                method = parts[0]
                if len(parts) > 1:
                    endpoint = parts[1]
            elif value.startswith("/"):
                endpoint = value

        if endpoint:
            keywords.append(f"{method}    {endpoint}")

            # Add validations based on expected result
            if expected:
                if "status 200" in expected.lower():
                    keywords.append("Status Should Be    200")
                if "contains" in expected.lower():
                    # Extract what it should contain
                    contains_match = re.search(r"contains (.+)", expected.lower())
                    if contains_match:
                        content = contains_match.group(1)
                        keywords.append(f"Response Should Contain    {content}")

        return keywords

    def _generate_file_upload_keywords(
        self, parsed_data: dict[str, str], expected: str
    ) -> list[str]:
        """Generate file upload keywords."""
        keywords = []

        file_path = parsed_data.get("file", "")
        if file_path:
            keywords.append(f"Choose File    id=fileInput    {file_path}")
            keywords.append("Click Button    id=uploadBtn")

            # Add verification
            if expected and "successfully" in expected.lower():
                keywords.append(f"Page Should Contain    {expected}")

        return keywords

    def _generate_generic_keywords(self, parsed_data: dict[str, str]) -> list[str]:
        """Generate generic keywords for unrecognized patterns."""
        keywords = []

        for field, value in parsed_data.items():
            # Default behavior - treat as text input
            keywords.append(f"Input Text    id={field}    {value}")

        return keywords

    def detect_field_types(self, parsed_data: dict[str, str]) -> dict[str, str]:
        """Detect input field types from parsed data."""
        field_types = {}

        for field in parsed_data:
            field_lower = field.lower()

            if "password" in field_lower or "pass" in field_lower:
                field_types[field] = "password"
            elif "email" in field_lower:
                field_types[field] = "text"
            elif field_lower in ["remember", "active", "agree", "accept"]:
                field_types[field] = "checkbox"
            elif field_lower in ["age", "count", "number"]:
                field_types[field] = "text"
            else:
                field_types[field] = "text"

        return field_types

    def generate_robot_commands(
        self, parsed_data: dict[str, str], field_types: dict[str, str]
    ) -> list[str]:
        """Generate Robot Framework commands from parsed data and field types."""
        commands = []

        for field, value in parsed_data.items():
            field_type = field_types.get(field, "text")

            if field_type == "password":
                commands.append(f"Input Password    id={field}    {value}")
            elif field_type == "checkbox":
                if value.lower() in ["true", "yes", "1"]:
                    commands.append(f"Select Checkbox    id={field}")
                else:
                    commands.append(f"Unselect Checkbox    id={field}")
            else:  # text and other types
                commands.append(f"Input Text    id={field}    {value}")

        return commands
