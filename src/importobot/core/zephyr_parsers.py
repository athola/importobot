"""Zephyr-specific parsers and analyzers for enhanced test case processing."""

import re
from typing import ClassVar


class PlatformCommandParser:
    """Parse Zephyr-style platform-specific commands."""

    PLATFORM_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "PLATFORM1": ["target", "default", "standard"],
        "PLATFORM2": ["alternative", "fallback"],
        "PLATFORM3": ["embedded", "device"],
        "OTHER": ["other", "misc"],
    }

    def parse_platform_commands(self, test_data: str) -> dict[str, list[str]]:
        """Extract platform-specific command variations.

        Handles platform-agnostic format:
        PLATFORM1: command for primary platform
        PLATFORM2: command for alternative platform
        PLATFORM3: command for embedded platform
        OTHER: fallback command
        """
        commands: dict[str, list[str]] = {
            platform: [] for platform in self.PLATFORM_KEYWORDS
        }

        # Implementation for parsing platform commands
        lines = test_data.split("\n")  # Don't strip to preserve empty lines
        current_platform = None
        previous_line_empty = False

        for line in lines:
            stripped_line = line.strip()

            # Check if this is an empty line
            if not stripped_line:
                previous_line_empty = True
                continue

            # Check for platform indicator
            platform_found, current_platform = self._check_platform_indicator(
                commands, stripped_line, current_platform
            )
            if platform_found:
                previous_line_empty = False
                continue

            # Handle continuation if no platform indicator
            current_platform = self._handle_continuation(
                commands,
                current_platform,
                stripped_line,
                previous_line_empty=previous_line_empty,
                line=line,
            )
            previous_line_empty = False

        return commands

    def _check_platform_indicator(
        self,
        commands: dict[str, list[str]],
        stripped_line: str,
        current_platform: str | None,
    ) -> tuple[bool, str | None]:
        """Check if line contains a platform indicator and process it."""
        for platform, keywords in self.PLATFORM_KEYWORDS.items():
            for keyword in keywords:
                keyword_upper = keyword.upper()
                if stripped_line.upper().startswith(keyword_upper + ":"):
                    current_platform = platform
                    command = stripped_line.split(":", 1)[1].strip()
                    if command:  # Only append non-empty commands
                        commands[platform].append(command)
                    return True, current_platform
                if stripped_line.upper().startswith(keyword_upper + " "):
                    current_platform = platform
                    command = stripped_line[len(keyword_upper):].strip()
                    if command:  # Only append non-empty commands
                        commands[platform].append(command)
                    return True, current_platform
        return False, current_platform

    def _handle_continuation(
        self,
        commands: dict[str, list[str]],
        current_platform: str | None,
        stripped_line: str,
        *,
        previous_line_empty: bool,
        line: str,
    ) -> str | None:
        """Handle continuation of a command from a previous line."""
        if current_platform and stripped_line:
            # Reset continuation only if we had an empty line AND
            # this line is indented (indicating it's not a new command
            # but rather separated content)
            if previous_line_empty and line.startswith("    "):
                current_platform = None
            else:
                # Continuation of previous platform command
                commands[current_platform].append(stripped_line)

        return current_platform


class ZephyrTestLevelClassifier:
    """Classify tests according to Zephyr methodology."""

    TEST_LEVELS: ClassVar[dict[str, int]] = {
        "Minimum Viable CRS": 1,  # Required for J9, CRS-linked
        "Smoke": 0,  # Preliminary critical tests
        "Edge Case": 2,  # Optional, edge cases
        "Regression": 3,  # Bug fix validation, optional for J9
    }

    def classify_test(self, test_data: dict) -> tuple[str, int]:
        """Determine test level based on content and metadata."""
        # Check for CRS links
        if self._has_crs_links(test_data):
            return ("Minimum Viable CRS", 1)

        # Check for smoke test indicators
        if self._is_smoke_test(test_data):
            return ("Smoke", 0)

        # Check for edge case patterns
        if self._is_edge_case(test_data):
            return ("Edge Case", 2)

        # Default to regression
        return ("Regression", 3)

    def _has_crs_links(self, test_data: dict) -> bool:
        """Check if test case has CRS requirement links."""
        traceability_fields = [
            "issues",
            "linkedCRS",
            "requirements",
            "confluence",
            "webLinks",
        ]

        for field in traceability_fields:
            if test_data.get(field):
                # Handle different field types
                values = test_data[field]
                if isinstance(values, str):
                    values = [values]
                elif not isinstance(values, list):
                    continue

                # Check if any value represents a requirement link
                for value in values:
                    if isinstance(value, str):
                        # Check for CRS links (case-insensitive, must have dash)
                        if value.upper().startswith("CRS-"):
                            return True
                        # Check for URLs in confluence/requirements fields
                        if field in ["confluence", "requirements", "webLinks"] and (
                            "http://" in value or "https://" in value
                        ):
                            return True

        return False

    def _is_smoke_test(self, test_data: dict) -> bool:
        """Identify smoke test patterns."""
        smoke_indicators = ["smoke", "basic", "core", "critical", "startup", "health"]
        test_text = " ".join(
            [
                str(test_data.get("name", "")),
                str(test_data.get("objective", "")),
                str(test_data.get("description", "")),
            ]
        ).lower()

        return any(indicator in test_text for indicator in smoke_indicators)

    def _is_edge_case(self, test_data: dict) -> bool:
        """Identify edge case patterns."""
        edge_indicators = [
            "edge",
            "boundary",
            "negative",
            "error",
            "exception",
            "invalid",
            "limit",
            "exhausted",
            "resource",
        ]
        test_text = " ".join(
            [
                str(test_data.get("name", "")),
                str(test_data.get("objective", "")),
                str(test_data.get("description", "")),
            ]
        ).lower()

        return any(indicator in test_text for indicator in edge_indicators)


class ZephyrPreconditionAnalyzer:
    """Analyze and structure test preconditions."""

    STANDARD_PRECONDITIONS: ClassVar[list[str]] = [
        "YJ Installed",
        "Communication Prepared",
        "Socket(s) Open",
        "Agent Stamped",
        "Agent Deployed",
        "CLI Connected to Active Agent",
    ]

    def analyze_preconditions(self, precondition_text: str) -> list[dict]:
        """Parse precondition text into structured steps."""
        if not precondition_text:
            return []

        steps = []
        lines = precondition_text.strip().split("\n")

        # Parse formatted preconditions (numbered or bulleted)
        steps = self._parse_formatted_preconditions(lines)

        # If the text wasn't formatted, handle unformatted text
        if steps and not self._has_formatting(lines):
            steps = self._handle_unformatted_text(precondition_text, steps)

        return steps

    def _parse_formatted_preconditions(self, lines: list[str]) -> list[dict]:
        """Parse formatted preconditions (numbered or bulleted)."""
        steps = []
        current_step: dict[str, str] = {}

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Check for step numbering
            if (
                stripped_line[0].isdigit()
                and ("." in stripped_line or ")" in stripped_line)
            ):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    "description": stripped_line.split(".", 1)[-1]
                    .split(")", 1)[-1]
                    .strip()
                }
            elif stripped_line.startswith("-") or stripped_line.startswith("*"):
                if current_step:
                    steps.append(current_step)
                current_step = {"description": stripped_line[1:].strip()}
            # Continuation of current step
            elif current_step:
                current_step["description"] += " " + stripped_line
            else:
                current_step = {"description": stripped_line}

        if current_step:
            steps.append(current_step)

        return steps

    def _has_formatting(self, lines: list[str]) -> bool:
        """Check if the text has formatting (numbering or bullets)."""
        for line in lines:
            stripped_line = line.strip()
            if (
                stripped_line
                and stripped_line[0].isdigit()
                and ("." in stripped_line or ")" in stripped_line)
            ):
                return True
            if stripped_line.startswith("-") or stripped_line.startswith("*"):
                return True
        return False

    def _handle_unformatted_text(
        self, precondition_text: str, steps: list[dict]
    ) -> list[dict]:
        """Handle unformatted text by combining first and last lines."""
        if len(steps) == 1:
            # For unformatted text, if there are multiple lines,
            # combine first and last lines only (test expectation)
            split_lines = precondition_text.strip().split("\n")
            non_empty_lines = [line.strip() for line in split_lines if line.strip()]
            if len(non_empty_lines) > 1:
                combined_description = non_empty_lines[0] + " " + non_empty_lines[-1]
                steps = [{"description": combined_description}]

        return steps

    def detect_hyperlinked_test_cases(self, precondition_text: str) -> list[str]:
        """Extract references to other test cases in preconditions."""
        if not precondition_text:
            return []

        # Look for patterns like "See test case X" or hyperlinked test names
        test_case_refs = []

        # Pattern for test case keys - project codes with 3+ digits,
        # excluding generic prefixes
        # More restrictive pattern to avoid matching regular identifiers
        # and generic TEST-XXX
        test_key_pattern = r"\b(?!TEST-)[A-Z]{3,}-\d{3,}\b"
        test_case_refs.extend(re.findall(test_key_pattern, precondition_text))

        # Pattern for test names in quotes (both double and single quotes)
        test_name_pattern_double = r'"([^"]+)"'
        test_name_pattern_single = r"'([^']+)'"
        test_case_refs.extend(re.findall(test_name_pattern_double, precondition_text))
        test_case_refs.extend(re.findall(test_name_pattern_single, precondition_text))

        return test_case_refs
