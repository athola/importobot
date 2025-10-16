"""Context analyzer for cross-step analysis and intelligent suggestions.

This module analyzes multiple test steps to identify patterns and suggest
missing setup, cleanup, or verification steps.
"""

from collections.abc import Callable
from typing import Any

from importobot.utils.field_extraction import extract_field
from importobot.utils.ssh_patterns import (
    SSH_FILE_PATH_INDICATORS,
    SSH_STRONG_INDICATORS,
)


class ContextAnalyzer:
    """Analyzer for detecting patterns and missing steps across multiple test steps."""

    def __init__(self) -> None:
        """Initialize the context analyzer."""

    def analyze_step_context(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze context across multiple steps for intelligent suggestions."""
        suggestions: list[dict[str, Any]] = []

        # Check for various patterns
        suggestions.extend(self.detect_missing_setup(steps))
        suggestions.extend(self.detect_missing_cleanup(steps))
        suggestions.extend(self.detect_missing_verification(steps))
        suggestions.extend(self.detect_transaction_patterns(steps))

        return suggestions

    def detect_missing_setup(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect missing setup steps."""
        suggestions: list[dict[str, Any]] = []

        # Check for SSH operations without connection
        ssh_operations = []
        ssh_connection_found = False

        for i, step in enumerate(steps):
            description = self._extract_field(step, ["step", "description", "action"])
            test_data = self._extract_field(step, ["testData", "data"])

            if self._is_ssh_context(description, test_data):
                if "connect" in description.lower():
                    ssh_connection_found = True
                else:
                    ssh_operations.append(i)

        if ssh_operations and not ssh_connection_found:
            suggestions.append(
                {
                    "type": "missing_setup",
                    "description": "SSH connection not established",
                    "suggested_step": {
                        "description": "Connect to SSH server",
                        "testData": (
                            "host: server.com, username: ${username}, "
                            "password: ${password}"
                        ),
                        "expectedResult": "Connected successfully",
                    },
                    "position": "before_step_1",
                }
            )

        # Check for database operations without connection
        db_operations = []
        db_connection_found = False

        for i, step in enumerate(steps):
            description = self._extract_field(step, ["step", "description", "action"])
            test_data = self._extract_field(step, ["testData", "data"])

            if self._is_database_context(description, test_data):
                if "connect" in description.lower():
                    db_connection_found = True
                else:
                    db_operations.append(i)

        if db_operations and not db_connection_found:
            suggestions.append(
                {
                    "type": "database_connection",
                    "description": "Database connection required before queries",
                    "position": "before_step_1",
                }
            )

        return suggestions

    def detect_missing_cleanup(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect missing cleanup steps."""
        suggestions: list[dict[str, Any]] = []

        # Check for SSH connection without disconnect
        self._check_connection_cleanup(
            steps=steps,
            context_check_func=self._is_ssh_context,
            suggestion_type="missing_cleanup",
            description="SSH connection not closed",
            suggested_step={
                "description": "Close SSH connection",
                "testData": "",
                "expectedResult": "Connection closed",
            },
            suggestions=suggestions,
        )

        # Check for database connection without disconnect
        self._check_connection_cleanup(
            steps=steps,
            context_check_func=self._is_database_context,
            suggestion_type="database_disconnect",
            description="Database connection should be closed",
            suggested_step=None,
            suggestions=suggestions,
        )

        return suggestions

    def _check_connection_cleanup(
        self,
        *,
        steps: list[dict[str, Any]],
        context_check_func: Callable[[str, str], bool],
        suggestion_type: str,
        description: str,
        suggested_step: dict[str, Any] | None,
        suggestions: list[dict[str, Any]],
    ) -> None:
        """Check for connection cleanup issues."""
        connection_found = False
        disconnect_found = False

        for step in steps:
            step_description = self._extract_field(
                step, ["step", "description", "action"]
            )
            test_data = self._extract_field(step, ["testData", "data"])

            if context_check_func(step_description, test_data):
                if "connect" in step_description.lower():
                    connection_found = True
                elif (
                    "disconnect" in step_description.lower()
                    or "close" in step_description.lower()
                ):
                    disconnect_found = True

        if connection_found and not disconnect_found:
            suggestion: dict[str, Any] = {
                "type": suggestion_type,
                "description": description,
                "position": "after_last_step",
            }
            if suggested_step:
                suggestion["suggested_step"] = suggested_step
            suggestions.append(suggestion)

    def detect_missing_verification(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect missing verification steps."""
        suggestions: list[dict[str, Any]] = []

        # Check for hash calculation patterns
        hash_steps = []
        for i, step in enumerate(steps):
            description = self._extract_field(step, ["step", "description", "action"])
            if "hash" in description.lower() and "calculate" in description.lower():
                hash_steps.append((i, step))

        if len(hash_steps) >= 2:
            suggestions.append(
                {
                    "type": "hash_comparison",
                    "description": "Hash values should be compared",
                    "position": "after_step_2",
                }
            )

        # Check for form submission without validation
        form_submit_found = False
        validation_found = False

        for step in steps:
            description = self._extract_field(step, ["step", "description", "action"])
            if "submit" in description.lower() and (
                "form" in description.lower() or "button" in description.lower()
            ):
                form_submit_found = True
            elif (
                "verify" in description.lower()
                or "validate" in description.lower()
                or "success" in description.lower()
            ):
                validation_found = True

        if form_submit_found and not validation_found:
            suggestions.append(
                {
                    "type": "missing_validation",
                    "description": "Consider adding form validation step",
                    "suggested_step": {
                        "description": "Verify form submission success",
                        "testData": "message: Success",
                        "expectedResult": "Success message displayed",
                    },
                    "position": "after_last_step",
                }
            )

        return suggestions

    def detect_transaction_patterns(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect database transaction patterns."""
        suggestions: list[dict[str, Any]] = []

        # Check for multiple database modification operations
        modification_steps = []
        transaction_found = False

        for i, step in enumerate(steps):
            description = self._extract_field(step, ["step", "description", "action"])
            test_data = self._extract_field(step, ["testData", "data"])

            if self._is_database_modification(description, test_data):
                modification_steps.append(i)
            elif (
                "transaction" in description.lower()
                or "begin" in test_data.upper()
                or "commit" in test_data.upper()
            ):
                transaction_found = True

        if len(modification_steps) > 1 and not transaction_found:
            suggestions.append(
                {
                    "type": "missing_transaction",
                    "description": "Database operations should be wrapped in "
                    "transaction",
                    "suggested_steps": [
                        {
                            "description": "Begin transaction",
                            "testData": "BEGIN",
                            "expectedResult": "Transaction started",
                            "position": "before_step_1",
                        },
                        {
                            "description": "Commit transaction",
                            "testData": "COMMIT",
                            "expectedResult": "Transaction committed",
                            "position": "after_last_step",
                        },
                    ],
                }
            )

        return suggestions

    def _extract_field(self, data: dict[str, Any], field_names: list[str]) -> str:
        """Extract value from first matching field name."""
        return extract_field(data, field_names)

    def _is_ssh_context(self, description: str, test_data: str) -> bool:
        """Check if the operation is in SSH context."""
        combined = f"{description} {test_data}".lower()

        # Check for strong indicators first
        if any(indicator in combined for indicator in SSH_STRONG_INDICATORS):
            return True

        # Check for remote operations
        if "remote" in description.lower() and (
            "command" in description.lower() or "execute" in description.lower()
        ):
            return True

        # Check for file paths combined with upload/download context
        return bool(
            any(path in combined for path in SSH_FILE_PATH_INDICATORS)
            and any(
                word in description.lower()
                for word in ["upload", "download", "transfer", "copy"]
            )
        )

    def _is_database_context(self, description: str, test_data: str) -> bool:
        """Check if the operation is in database context."""
        combined = f"{description} {test_data}".lower()
        db_indicators = [
            "database",
            "query",
            "select",
            "insert",
            "update",
            "delete",
            "sql",
            "db",
            "connect",
            "connection",
            "execute",
        ]
        return any(indicator in combined for indicator in db_indicators)

    def _is_database_modification(self, description: str, test_data: str) -> bool:
        """Check if the operation modifies database data."""
        combined = f"{description} {test_data}".upper()
        modification_indicators = ["INSERT", "UPDATE", "DELETE"]
        return any(indicator in combined for indicator in modification_indicators)
