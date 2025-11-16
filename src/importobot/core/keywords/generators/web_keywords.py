"""Web and browser keyword generation for Robot Framework."""

import re
from typing import Any

from importobot import config
from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.core.pattern_matcher import LibraryDetector, RobotFrameworkLibrary
from importobot.utils.step_processing import extract_step_information

# Compiled regex patterns for performance optimization
_URL_PATTERN = re.compile(r"https?://[^\s,]+")
_VALUE_PATTERN = re.compile(r"value:\s*([^,\s]+)")
_QUOTED_PATTERN = re.compile(r'"([^"]*)"')


class WebKeywordGenerator(BaseKeywordGenerator):
    """Generate web and browser-related Robot Framework keywords."""

    def generate_browser_keyword(self, test_data: str) -> str:
        """Generate browser or mobile app opening keyword with appropriate options."""
        # Detect if this is a mobile app context
        mobile_indicators = [
            "platformname",
            "devicename",
            "apppackage",
            "appactivity",
            "bundleid",
        ]
        is_mobile = any(
            indicator in test_data.lower() for indicator in mobile_indicators
        )

        if is_mobile:
            # Use AppiumLibrary Open Application for mobile apps
            _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
                "app_open"
            )
            return f"{keyword_name}    {test_data}"
        else:
            # Use SeleniumLibrary Open Browser for web
            _, keyword_name = RobotFrameworkKeywordRegistry.get_intent_keyword(
                "web_open"
            )
            url_match = _URL_PATTERN.search(test_data)
            url = url_match.group(0) if url_match else config.TEST_LOGIN_URL
            # Add Chrome options to prevent session conflicts in CI/testing environments
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
        """Generate input keyword with intelligent library selection."""
        # Detect which library should be used
        libraries = LibraryDetector.detect_libraries_from_text(
            f"input {field_type} {test_data}"
        )

        # Choose library: prefer AppiumLibrary if available, fallback to SeleniumLibrary
        if RobotFrameworkLibrary.APPIUM_LIBRARY in libraries:
            prefix = LibraryDetector.get_keyword_prefix_for_library(
                RobotFrameworkLibrary.APPIUM_LIBRARY
            )
        elif RobotFrameworkLibrary.SELENIUM_LIBRARY in libraries:
            # For simple username: format, keep backward compatibility
            if ":" in test_data and field_type in test_data:
                # This looks like test data (e.g., "username: testuser"), use simple
                prefix = ""
            else:
                # More complex case, use conflict detection
                prefix = LibraryDetector.get_keyword_prefix_for_library(
                    RobotFrameworkLibrary.SELENIUM_LIBRARY
                )
        else:
            # Default to no prefix (let Robot Framework resolve)
            prefix = ""

        value = self._extract_value_from_data(test_data)
        keyword_name = f"{prefix}.Input Text" if prefix else "Input Text"
        return (
            f"{keyword_name}    id={field_type}    {value}"
            if value
            else f"{keyword_name}    id={field_type}    test_value"
        )

    def generate_password_keyword(self, test_data: str) -> str:
        """Generate password input keyword with intelligent library selection."""
        # Detect which library should be used
        libraries = LibraryDetector.detect_libraries_from_text(f"password {test_data}")

        # Choose library: prefer AppiumLibrary if available, fallback to SeleniumLibrary
        if RobotFrameworkLibrary.APPIUM_LIBRARY in libraries:
            prefix = LibraryDetector.get_keyword_prefix_for_library(
                RobotFrameworkLibrary.APPIUM_LIBRARY
            )
        elif RobotFrameworkLibrary.SELENIUM_LIBRARY in libraries:
            # For simple password: format, keep backward compatibility
            if ":" in test_data:
                # This looks like test data (e.g., "password: testpass"), use simple
                prefix = ""
            else:
                # More complex case, use conflict detection
                prefix = LibraryDetector.get_keyword_prefix_for_library(
                    RobotFrameworkLibrary.SELENIUM_LIBRARY
                )
        else:
            # Default to no prefix (let Robot Framework resolve)
            prefix = ""

        value = self._extract_value_from_data(test_data)
        keyword_name = f"{prefix}.Input Password" if prefix else "Input Password"
        return (
            f"{keyword_name}    id=password    {value}"
            if value
            else f"{keyword_name}    id=password    test_password"
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

        if "submit" in desc_lower:
            if any(term in desc_lower for term in ["button", "form", "login"]):
                return "Click Button    id=submit_button"
            return "Click Element    id=submit_button"

        # If no locator is found, use original logic
        if "login" in desc_lower and "button" in desc_lower:
            return "Click Button    id=login_button"
        if "button" in desc_lower:
            return "Click Button    id=submit_button"
        return "Click Element    id=clickable_element"

    def _extract_verification_text(self, test_data: str, expected: str) -> str:
        """Extract text to verify from test_data or expected result.

        This is a helper method used by verification keyword generators to extract
        the actual text that needs to be verified from various input formats.

        Args:
            test_data: Test data string which may contain the text to verify
            expected: Expected result string as fallback

        Returns:
            The extracted text to verify, or "expected content" as default
        """
        if ":" in test_data:
            return test_data.split(":", 1)[1].strip()
        if expected:
            return expected
        # Try to extract from common patterns
        value_match = re.search(r"(?:text|message)[:\s=]+([^,\s]+)", test_data)
        return value_match.group(1) if value_match else "expected content"

    def generate_library_aware_page_verification_keyword(
        self, test_data: str, expected: str, library_context: set[Any]
    ) -> str:
        """Generate page verification keyword with library-aware selection.

        This method correctly chooses between SeleniumLibrary and AppiumLibrary
        based on the detected library context, ensuring the right verification
        keyword is used for web vs mobile testing.

        Args:
            test_data: Test data string containing text to verify
            expected: Expected result as fallback
            library_context: Set of RobotFrameworkLibrary enums detected from test

        Returns:
            Library-prefixed verification keyword appropriate for the context:
            - AppiumLibrary.Page Should Contain Text (for mobile)
            - SeleniumLibrary.Page Should Contain (for web)
            - Default to SeleniumLibrary if no proper match can be determined
        """
        text_to_verify = self._extract_verification_text(test_data, expected)

        # Use library context to determine verification method
        if RobotFrameworkLibrary.APPIUM_LIBRARY in library_context:
            return f"AppiumLibrary.Page Should Contain Text    {text_to_verify}"
        if RobotFrameworkLibrary.SELENIUM_LIBRARY in library_context:
            return f"SeleniumLibrary.Page Should Contain    {text_to_verify}"
        # Default to SeleniumLibrary if no proper match can be determined
        return f"SeleniumLibrary.Page Should Contain    {text_to_verify}"

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
