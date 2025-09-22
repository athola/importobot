"""Web and browser keyword generation for Robot Framework."""

import re
from typing import Any

from importobot import config
from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.utils.step_processing import extract_step_information

# Compiled regex patterns for performance optimization
_URL_PATTERN = re.compile(r"https?://[^\s,]+")
_VALUE_PATTERN = re.compile(r"value:\s*([^,\s]+)")
_QUOTED_PATTERN = re.compile(r'"([^"]*)"')


class WebKeywordGenerator(BaseKeywordGenerator):
    """Generates web and browser-related Robot Framework keywords."""

    def generate_browser_keyword(self, test_data: str) -> str:
        """Generate browser opening keyword with Chrome options for CI/headless."""
        # Get keyword name from registry
        _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword("web_open")

        url_match = _URL_PATTERN.search(test_data)
        url = url_match.group(0) if url_match else config.TEST_LOGIN_URL
        # Add Chrome options to prevent session conflicts in CI/testing environments
        # Using the correct format for SeleniumLibrary Chrome options
        chrome_options = "; ".join(
            f"add_argument('{option}')" for option in config.CHROME_OPTIONS
        )
        return f"{keyword_name}    {url}    chrome    options={chrome_options}"

    def generate_url_keyword(self, test_data: str) -> str:
        """Generate URL navigation keyword."""
        url_match = _URL_PATTERN.search(test_data)
        if url_match:
            return f"Go To    {url_match.group(0)}"
        # Go To requires a URL
        return "Go To    ${URL}"

    def generate_navigation_keyword(self, test_data: str) -> str:
        """Generate URL navigation keyword (alias for generate_url_keyword)."""
        return self.generate_url_keyword(test_data)

    def generate_input_keyword(self, field_type: str, test_data: str) -> str:
        """Generate input keyword."""
        value = self._extract_value_from_data(test_data)
        return (
            f"Input Text    id={field_type}    {value}"
            if value
            else f"Input Text    id={field_type}    test_value"
        )

    def generate_password_keyword(self, test_data: str) -> str:
        """Generate password input keyword."""
        value = self._extract_value_from_data(test_data)
        return (
            f"Input Password    id=password    {value}"
            if value
            else "Input Password    id=password    test_password"
        )

    def generate_click_keyword(self, description: str, test_data: str = "") -> str:
        """Generate click keyword."""
        desc_lower = description.lower()
        f"{description} {test_data}".lower()

        # Extract locator from test_data if available
        locator_match = re.search(r"(?:locator|id|xpath|css):\s*([^,\s]+)", test_data)
        if locator_match:
            locator = locator_match.group(1)
            # When we have a specific locator, prefer Click Element for flexibility
            return f"Click Element    {locator}"

        # Fallback to original logic if no locator found
        if "login" in desc_lower and "button" in desc_lower:
            return "Click Button    id=login_button"
        if "button" in desc_lower:
            return "Click Button    id=submit_button"
        return "Click Element    id=clickable_element"

    def generate_page_verification_keyword(self, test_data: str, expected: str) -> str:
        """Generate page verification keyword."""
        # Extract text to verify from test_data
        text_to_verify = ""
        if ":" in test_data:
            text_to_verify = test_data.split(":", 1)[1].strip()
        elif expected:
            text_to_verify = expected
        else:
            # Try to extract from common patterns
            value_match = re.search(r"(?:text|message)[:\s=]+([^,\s]+)", test_data)
            if value_match:
                text_to_verify = value_match.group(1)
            else:
                text_to_verify = "expected content"

        return f"Page Should Contain    {text_to_verify}"

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for a web-related step."""
        lines = []

        # Add standard step header comments
        lines.extend(self._generate_step_header_comments(step))

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)

        # Generate Robot keyword based on step content
        combined = f"{description} {test_data}".lower()

        if "browser" in combined or "open" in combined:
            keyword = self.generate_browser_keyword(test_data)
        elif "navigate" in combined or "url" in combined:
            keyword = self.generate_url_keyword(test_data)
        elif "username" in combined or "user" in combined:
            keyword = self.generate_input_keyword("username", test_data)
        elif "password" in combined:
            keyword = self.generate_password_keyword(test_data)
        elif "click" in combined or "button" in combined:
            keyword = self.generate_click_keyword(description)
        else:
            keyword = "No Operation  # Web operation not recognized"

        lines.append(keyword)
        return lines

    def _extract_value_from_data(self, test_data: str) -> str:
        """Extract value from test data string."""
        # Look for common value patterns
        value_match = _VALUE_PATTERN.search(test_data)
        if value_match:
            return value_match.group(1)

        # Look for quoted strings
        quote_match = _QUOTED_PATTERN.search(test_data)
        if quote_match:
            return quote_match.group(1)

        return ""
