"""API keyword generation for Robot Framework."""

import re
from typing import Any

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.utils.step_processing import extract_step_information

# Compiled regex patterns for performance optimization
_METHOD_PATTERN = re.compile(r"(?:method|type):\s*([^,\s]+)", re.IGNORECASE)
_SESSION_PATTERN = re.compile(r"(?:session|alias):\s*([^,\s]+)", re.IGNORECASE)
_URL_PATTERN = re.compile(r"(?:url|endpoint):\s*([^,\s]+)", re.IGNORECASE)
_DATA_PATTERN = re.compile(r"(?:data|payload):\s*(.+?)(?:\s*$)", re.IGNORECASE)
_ALIAS_PATTERN = re.compile(r"(?:alias|name):\s*([^,\s]+)", re.IGNORECASE)
_BASE_URL_PATTERN = re.compile(r"(?:url|base.*url):\s*([^,\s]+)", re.IGNORECASE)
_STATUS_PATTERN = re.compile(r"(?:status|code):\s*(\d+)", re.IGNORECASE)


class APIKeywordGenerator(BaseKeywordGenerator):
    """Generate API/HTTP-related Robot Framework keywords."""

    def generate_request_keyword(self, test_data: str) -> str:
        """Generate API request keyword."""
        # Extract API request parameters
        method = (
            self._extract_pattern(test_data, r"(?:method|type):\s*([^,\s]+)") or "GET"
        )
        session = (
            self._extract_pattern(test_data, r"(?:session|alias):\s*([^,\s]+)")
            or "default_session"
        )
        url = self._extract_pattern(test_data, r"(?:url|endpoint):\s*([^,\s]+)")
        data = self._extract_pattern(test_data, r"(?:data|payload):\s*(.+?)(?:\s*$)")

        method = method.upper()

        if method == "POST":
            if url and data:
                return f"POST On Session    {session}    {url}    {data}"
            if url:
                return f"POST On Session    {session}    {url}"
            # POST On Session requires at least session and URL
            return f"POST On Session    {session}    /api/test"
        if method == "PUT":
            if url and data:
                return f"PUT On Session    {session}    {url}    {data}"
            if url:
                return f"PUT On Session    {session}    {url}"
            # PUT On Session requires at least session and URL
            return f"PUT On Session    {session}    /api/test"
        if method == "DELETE":
            if url:
                return f"DELETE On Session    {session}    {url}"
            # DELETE On Session requires at least session and URL
            return f"DELETE On Session    {session}    /api/test"
        # GET
        if url:
            return f"GET On Session    {session}    {url}"
        # GET On Session requires at least session and URL
        return f"GET On Session    {session}    /api/test"

    def generate_session_keyword(self, test_data: str) -> str:
        """Generate API session keyword."""
        alias = (
            self._extract_pattern(test_data, r"(?:alias|name):\s*([^,\s]+)")
            or "default_session"
        )
        url = self._extract_pattern(test_data, r"(?:url|base.*url):\s*([^,\s]+)")

        if url:
            return f"Create Session    {alias}    {url}"
        # Create Session requires both alias and URL
        return f"Create Session    {alias}    ${{API_BASE_URL}}"

    def generate_response_keyword(self, test_data: str) -> str:
        """Generate API response verification keyword."""
        expected_status = self._extract_pattern(test_data, r"(?:status|code):\s*(\d+)")
        if expected_status:
            return f"Status Should Be    {expected_status}"
        return "Status Should Be    200"

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for an API-related step."""
        lines = []

        # Add standard step header comments
        lines.extend(self._generate_step_header_comments(step))

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)

        # Generate Robot keyword based on step content
        combined = f"{description} {test_data}".lower()

        if "session" in combined or "create" in combined:
            keyword = self.generate_session_keyword(test_data)
        elif (
            "request" in combined
            or "post" in combined
            or "get" in combined
            or "put" in combined
            or "delete" in combined
        ):
            keyword = self.generate_request_keyword(test_data)
        elif "response" in combined or "status" in combined:
            keyword = self.generate_response_keyword(test_data)
        else:
            keyword = "No Operation  # API operation not recognized"

        lines.append(keyword)
        return lines

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""
