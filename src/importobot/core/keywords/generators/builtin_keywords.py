"""BuiltIn Robot Framework keyword generation."""

import re
from typing import Any

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.core.pattern_matcher import LibraryDetector, RobotFrameworkLibrary
from importobot.utils.step_comments import generate_step_comments
from importobot.utils.step_processing import extract_step_information


class ConversionKeywordsMixin:
    """Mixin for type conversion keywords."""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def generate_convert_to_integer_keyword(self, test_data: str) -> str:
        """Generate Convert To Integer keyword."""
        value = self._extract_pattern(
            test_data, r"(?:value|item|number)[:\s=]+([^,\s]+)"
        )
        if not value:
            value = "${value}"
        return f"Convert To Integer    {value}"

    def generate_convert_to_string_keyword(self, test_data: str) -> str:
        """Generate Convert To String keyword."""
        value = self._extract_pattern(test_data, r"(?:value|item)[:\s=]+([^,\s]+)")
        if not value:
            value = "${value}"
        return f"Convert To String    {value}"

    def generate_convert_to_boolean_keyword(self, test_data: str) -> str:
        """Generate Convert To Boolean keyword."""
        value = self._extract_pattern(test_data, r"(?:value|item)[:\s=]+([^,\s]+)")
        if not value:
            value = "${value}"
        return f"Convert To Boolean    {value}"

    def generate_convert_to_number_keyword(self, test_data: str) -> str:
        """Generate Convert To Number keyword."""
        # Check if test_data is malformed
        if test_data.startswith("test_data_for_") and "# builtin" in test_data:
            return (
                "# Convert To Number requires structured test data. "
                "Example: value: 123 or item: ${variable}"
            )

        value = self._extract_pattern(
            test_data, r"(?:value|item|number)[:\s=]+([^,\s]+)"
        )
        if not value:
            value = "${value}"
        return f"Convert To Number    {value}"


class VariableKeywordsMixin:
    """Mixin for variable manipulation keywords."""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def generate_log_keyword(self, test_data: str) -> str:
        """Generate Log keyword."""
        message = self._extract_pattern(test_data, r"(?:message|text)[:\s=]+(.+)")
        level = self._extract_pattern(test_data, r"(?:level)[:\s=]+([^,\s]+)")

        if not message:
            message = "Test message"

        if level and level.upper() in ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"]:
            return f"Log    {message}    {level.upper()}"
        return f"Log    {message}"

    def generate_set_variable_keyword(self, test_data: str) -> str:
        """Generate Set Variable keyword."""
        name = self._extract_pattern(
            test_data, r"(?:name|var|variable)[:\s=]+([^,\s]+)"
        )
        value = self._extract_pattern(test_data, r"(?:value|val)[:\s=]+(.+)")
        scope = self._extract_pattern(test_data, r"(?:scope)[:\s=]+([^,\s]+)")

        if not name:
            name = "${variable_name}"
        if not value:
            value = "default_value"

        if scope and scope.lower() in ["global", "suite", "test", "local"]:
            keyword_name = f"Set {scope.title()} Variable"
        else:
            keyword_name = "Set Variable"

        return f"{keyword_name}    {name}    {value}"

    def generate_get_variable_keyword(self, test_data: str) -> str:
        """Generate Get Variable Value keyword."""
        name = self._extract_pattern(
            test_data, r"(?:name|var|variable)[:\s=]+([^,\s]+)"
        )
        default = self._extract_pattern(test_data, r"(?:default)[:\s=]+(.+)")

        if not name:
            name = "${variable_name}"

        if default:
            return f"Get Variable Value    {name}    {default}"
        return f"Get Variable Value    {name}"

    def generate_get_length_keyword(self, test_data: str) -> str:
        """Generate Get Length keyword."""
        item = (
            self._extract_pattern(test_data, r"(?:item|list|string)[:\s=]+([^,\s]+)")
            or test_data.strip()
            or "${ITEM}"
        )
        return f"Get Length    {item}"


class AssertionKeywordsMixin:
    """Mixin for assertion and verification keywords."""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def generate_length_should_be_keyword(self, test_data: str, expected: str) -> str:
        """Generate Length Should Be keyword."""
        item = (
            self._extract_pattern(test_data, r"(?:item|list|string)[:\s=]+([^,\s]+)")
            or test_data.strip()
            or "${ITEM}"
        )
        length = expected.strip() or "${LENGTH}"
        return f"Length Should Be    {item}    {length}"

    def generate_should_start_with_keyword(self, test_data: str, expected: str) -> str:
        """Generate Should Start With keyword."""
        string = (
            self._extract_pattern(test_data, r"(?:string|text)[:\s=]+([^,\s]+)")
            or test_data.strip()
            or "${STRING}"
        )
        prefix = expected.strip() or "${PREFIX}"
        return f"Should Start With    {string}    {prefix}"

    def generate_should_end_with_keyword(self, test_data: str, expected: str) -> str:
        """Generate Should End With keyword."""
        string = (
            self._extract_pattern(test_data, r"(?:string|text)[:\s=]+([^,\s]+)")
            or test_data.strip()
            or "${STRING}"
        )
        suffix = expected.strip() or "${SUFFIX}"
        return f"Should End With    {string}    {suffix}"

    def generate_should_match_keyword(self, test_data: str, expected: str) -> str:
        """Generate Should Match keyword."""
        string = (
            self._extract_pattern(test_data, r"(?:string|text)[:\s=]+([^,\s]+)")
            or test_data.strip()
            or "${STRING}"
        )
        pattern = expected.strip() or "${PATTERN}"
        return f"Should Match    {string}    {pattern}"

    def generate_assert_contains_keyword(self, test_data: str, expected: str) -> str:
        """Generate Should Contain keyword."""
        container = (
            self._extract_pattern(
                test_data, r"(?:container|list|string)[:\s=]+([^,\s]+)"
            )
            or test_data.strip()
            or "${CONTAINER}"
        )
        item = expected.strip() or "${ITEM}"
        return f"Should Contain    {container}    {item}"

    def generate_verification_keyword(
        self, description: str, test_data: str, expected: str
    ) -> str:
        """Generate verification keyword based on description."""
        if "equal" in description.lower():
            return f"Should Be Equal    {test_data}    {expected}"
        if "contain" in description.lower():
            return f"Should Contain    {test_data}    {expected}"
        return f"Should Be Equal    {test_data}    {expected}"

    def generate_verify_keyword(self, expected: str) -> str:
        """Generate verification keyword."""
        return f"Should Be True    {expected}"


class ControlFlowKeywordsMixin:
    """Mixin for control flow keywords."""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def generate_evaluate_keyword(self, test_data: str) -> str:
        """Generate Evaluate keyword."""
        expression = (
            self._extract_pattern(test_data, r"(?:expression|eval)[:\s=]+(.+)")
            or test_data.strip()
            or "${EXPRESSION}"
        )
        return f"Evaluate    {expression}"

    def generate_run_keyword_if_keyword(self, test_data: str) -> str:
        """Generate Run Keyword If keyword."""
        condition = (
            self._extract_pattern(test_data, r"(?:condition|if)[:\s=]+([^,]+)")
            or "${CONDITION}"
        )
        keyword = (
            self._extract_pattern(test_data, r"(?:keyword|then)[:\s=]+([^,]+)")
            or "${KEYWORD}"
        )
        args = self._extract_pattern(test_data, r"(?:args|arguments)[:\s=]+(.+)") or ""

        if args:
            return f"Run Keyword If    {condition}    {keyword}    {args}"
        return f"Run Keyword If    {condition}    {keyword}"

    def generate_repeat_keyword_keyword(self, test_data: str) -> str:
        """Generate Repeat Keyword keyword."""
        times = (
            self._extract_pattern(test_data, r"(?:times|repeat)[:\s=]+([^,\s]+)")
            or "${TIMES}"
        )
        keyword = (
            self._extract_pattern(test_data, r"(?:keyword|action)[:\s=]+([^,]+)")
            or "${KEYWORD}"
        )
        args = self._extract_pattern(test_data, r"(?:args|arguments)[:\s=]+(.+)") or ""

        if args:
            return f"Repeat Keyword    {times}    {keyword}    {args}"
        return f"Repeat Keyword    {times}    {keyword}"

    def generate_fail_keyword(self, test_data: str) -> str:
        """Generate Fail keyword."""
        message = (
            self._extract_pattern(test_data, r"(?:message|reason)[:\s=]+(.+)")
            or test_data.strip()
            or "Test failed"
        )
        return f"Fail    {message}"


class DataStructureKeywordsMixin:
    """Mixin for data structure keywords."""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def generate_get_count_keyword(self, test_data: str, expected: str) -> str:
        """Generate Get Count keyword."""
        container = (
            self._extract_pattern(test_data, r"(?:container|list)[:\s=]+([^,\s]+)")
            or test_data.strip()
            or "${CONTAINER}"
        )
        item = expected.strip() or "${ITEM}"
        return f"Get Count    {container}    {item}"

    def generate_create_list_keyword(self, test_data: str) -> str:
        """Generate Create List keyword."""
        items = (
            self._extract_pattern(test_data, r"(?:items|elements)[:\s=]+(.+)")
            or test_data.strip()
            or "${ITEMS}"
        )
        return f"Create List    {items}"

    def generate_create_dictionary_keyword(self, test_data: str) -> str:
        """Generate Create Dictionary keyword."""
        pairs = (
            self._extract_pattern(test_data, r"(?:pairs|items)[:\s=]+(.+)")
            or test_data.strip()
            or "${KEY}=${VALUE}"
        )
        return f"Create Dictionary    {pairs}"

    def generate_comparison_keyword(self, description: str, test_data: str) -> str:
        """Generate comparison keyword based on description."""
        if "greater" in description.lower():
            return f"Should Be True    {test_data}"
        if "less" in description.lower():
            return f"Should Be True    {test_data}"
        return f"Should Be Equal    {test_data}    ${{EXPECTED}}"


class BuiltInKeywordGenerator(
    ConversionKeywordsMixin,
    VariableKeywordsMixin,
    AssertionKeywordsMixin,
    ControlFlowKeywordsMixin,
    DataStructureKeywordsMixin,
    BaseKeywordGenerator,
):
    """Generate BuiltIn Robot Framework keywords for core functionality."""

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for a BuiltIn step."""
        lines = []

        # Add traceability comments
        lines.extend(generate_step_comments(step))

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)
        expected = self._get_expected_result_fields(step)

        # Check if test_data is malformed and provide helpful guidance
        if test_data and not self._is_valid_test_data(test_data, description):
            # Add helpful parameter guidance comment
            guidance_comment = self._generate_parameter_guidance(description, test_data)
            lines.append(f"    {guidance_comment}")
            return lines

        # Generate Robot keyword based on step content
        keyword = self._generate_builtin_keyword(description, test_data, expected)
        lines.append(keyword)
        return lines

    def _generate_builtin_keyword(
        self, description: str, test_data: str, expected: str
    ) -> str:
        """Generate the appropriate BuiltIn keyword based on content."""
        combined = f"{description} {test_data}".lower()

        # Define keyword generation patterns
        keyword_patterns = {
            ("log",): self.generate_log_keyword,
            ("convert", "integer"): self.generate_convert_to_integer_keyword,
            ("convert", "string"): self.generate_convert_to_string_keyword,
            ("convert", "boolean"): self.generate_convert_to_boolean_keyword,
            ("convert", "number"): self.generate_convert_to_number_keyword,
            ("set", "variable"): self.generate_set_variable_keyword,
            ("get", "variable"): self.generate_get_variable_keyword,
            ("length",): self.generate_get_length_keyword,
            ("evaluate",): self.generate_evaluate_keyword,
            ("fail",): self.generate_fail_keyword,
            ("run", "keyword", "if"): self.generate_run_keyword_if_keyword,
            ("run", "keyword", "unless"): self.generate_run_keyword_if_keyword,
            ("repeat", "keyword"): self.generate_repeat_keyword_keyword,
        }

        # Check for matching patterns
        for pattern, method in keyword_patterns.items():
            if all(term in combined for term in pattern):
                return method(test_data)

        # Special handling for contains
        if "contains" in combined:
            return self.generate_assert_contains_keyword(
                test_data, expected or "expected_value"
            )

        # Default case
        return "No Operation  # BuiltIn operation not recognized"

    # Helper methods for the main class
    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract pattern from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def _is_valid_test_data(self, test_data: str, description: str) -> bool:
        """Check if test_data contains valid structured data for given description.

        Validate whether the provided test_data contains meaningful structured data
        that is appropriate for the given description context.
        """
        if not test_data:
            return False

        # Check if test_data looks like placeholder text
        # (e.g., "test_data_for_convert_to_number # builtin")
        if test_data.startswith("test_data_for_") and "# builtin" in test_data:
            return False

        # Check for basic structure based on description
        desc_lower = description.lower()

        if "convert" in desc_lower:
            # Should contain value: or similar
            return any(
                pattern in test_data.lower()
                for pattern in ["value:", "item:", "number:"]
            )

        if "run keyword if" in desc_lower:
            # Should contain condition: and keyword:
            return any(
                pattern in test_data.lower() for pattern in ["condition:", "if:"]
            )

        if "repeat keyword" in desc_lower:
            # Should contain times: and keyword:
            return any(
                pattern in test_data.lower() for pattern in ["times:", "repeat:"]
            )

        if "set variable" in desc_lower:
            # Should contain name: and value:
            return any(
                pattern in test_data.lower()
                for pattern in ["name:", "var:", "variable:"]
            )

        # For other cases, assume it's valid if it contains some structure
        return ":" in test_data or "=" in test_data

    def _generate_parameter_guidance(self, description: str, test_data: str) -> str:
        """Generate helpful parameter guidance comments for malformed test data."""
        _ = test_data  # Unused parameter, kept for interface consistency
        desc_lower = description.lower()

        if "convert to number" in desc_lower:
            return (
                "# Convert To Number requires structured test data. "
                "Example: value: 123 or item: ${variable}"
            )

        if "convert to integer" in desc_lower:
            return (
                "# Convert To Integer requires structured test data. "
                "Example: value: 123 or item: ${variable}"
            )

        if "convert to string" in desc_lower:
            return (
                "# Convert To String requires structured test data. "
                "Example: value: hello or item: ${variable}"
            )

        if "convert to boolean" in desc_lower:
            return (
                "# Convert To Boolean requires structured test data. "
                "Example: value: True or item: ${variable}"
            )

        if "run keyword if" in desc_lower or "run keyword conditionally" in desc_lower:
            return (
                "# Run Keyword If requires structured test data. "
                "Example: condition: ${var} == 'expected', "
                "keyword: Log, args: Success"
            )

        if (
            "repeat keyword" in desc_lower
            or "repeat keyword multiple times" in desc_lower
        ):
            return (
                "# Repeat Keyword requires structured test data. "
                "Example: times: 3, keyword: Log, "
                "args: Iteration complete"
            )

        if "set variable" in desc_lower or "set variable with value" in desc_lower:
            return (
                "# Set Variable requires structured test data. "
                "Example: name: test_var, value: test_value"
            )

        # Generic guidance
        return (
            "# BuiltIn keyword requires structured test data. "
            "Please provide proper parameters."
        )

    def _extract_value_from_data(self, test_data: str) -> str:
        """Extract value from test data string."""
        # Look for common value patterns
        value_match = re.search(r"value:\s*([^,\s]+)", test_data)
        if value_match:
            return value_match.group(1)

        # Look for quoted strings
        quote_match = re.search(r'"([^"]*)"', test_data)
        if quote_match:
            return quote_match.group(1)

        return ""

    def generate_verification_keyword(
        self, description: str, test_data: str, expected: str
    ) -> str:
        """Generate verification keyword based on description."""
        desc_lower = description.lower()
        test_data_lower = test_data.lower()
        combined = f"{desc_lower} {test_data_lower}"

        # Try element verification first
        element_result = self._try_element_verification(test_data_lower, test_data)
        if element_result:
            return element_result

        # Try web page verification
        web_result = self._try_web_page_verification(combined, test_data, expected)
        if web_result:
            return web_result

        # Try specific verification patterns
        pattern_result = self._try_pattern_verification(desc_lower, test_data, expected)
        if pattern_result:
            return pattern_result

        # Default web verification
        return self.generate_verify_keyword(expected or test_data)

    def _try_element_verification(
        self, test_data_lower: str, test_data: str
    ) -> str | None:
        """Try to generate element verification keyword."""
        if "element" not in test_data_lower:
            return None

        # Try element= format
        element_match = re.search(r"element=([^,]+)", test_data_lower)
        text_match = re.search(r"text=([^,]+)", test_data)  # Use original case for text
        if element_match and text_match:
            return (
                f"Element Should Contain    {element_match.group(1)}    "
                f"{text_match.group(1)}"
            )

        # Try element: format
        element_match = re.search(r"element:\s*([^,]+)", test_data_lower)
        expected_match = re.search(
            r"expected:\s*(.+)", test_data
        )  # Use original case for expected text
        if element_match and expected_match:
            return (
                f"Element Should Contain    {element_match.group(1)}    "
                f"{expected_match.group(1)}"
            )

        return None

    def _try_web_page_verification(
        self, combined: str, test_data: str, expected: str
    ) -> str | None:
        """Try to generate web page verification keyword."""
        web_terms = ["page", "message", "display", "welcome", "verify:", "check:"]

        if not any(web_term in combined for web_term in web_terms):
            return None

        # Extract message text from test_data
        if ":" in test_data:
            message_part = test_data.split(":", 1)[1].strip()
            if message_part:
                return self._generate_library_aware_page_verification(message_part)

        # Fall back to expected result
        if expected and any(
            web_term in expected.lower()
            for web_term in ["message", "text", "display", "show", "welcome", "success"]
        ):
            return self._generate_library_aware_page_verification(expected)

        return None

    def _generate_library_aware_page_verification(
        self, content: str, full_test_context: str = ""
    ) -> str:
        """
        Generate library-aware page verification keywords.

        Uses appropriate verification keyword based on detected library context.
        """
        # Detect which library should be used - prioritize test context if available
        context_to_check = (
            full_test_context if full_test_context else f"verify {content}"
        )
        libraries = LibraryDetector.detect_libraries_from_text(context_to_check)

        if RobotFrameworkLibrary.APPIUM_LIBRARY in libraries:
            # AppiumLibrary uses different verification keywords
            return (
                f"AppiumLibrary.Page Should Contain Element    "
                f"xpath=//*[contains(text(), '{content}')]"
            )
        elif RobotFrameworkLibrary.SELENIUM_LIBRARY in libraries:
            return f"SeleniumLibrary.Page Should Contain    {content}"
        else:
            # Default to SeleniumLibrary for backward compatibility
            return f"SeleniumLibrary.Page Should Contain    {content}"

    def _try_pattern_verification(
        self, desc_lower: str, test_data: str, expected: str
    ) -> str | None:
        """Try to generate pattern-based verification keyword."""
        pattern_methods = {
            "contains": self.generate_assert_contains_keyword,
            "length": self.generate_length_should_be_keyword,
            "start": self.generate_should_start_with_keyword,
            "end": self.generate_should_end_with_keyword,
            "match": self.generate_should_match_keyword,
        }

        for pattern, method in pattern_methods.items():
            if pattern in desc_lower:
                return method(test_data, expected)

        return None

    def generate_verify_keyword(self, expected: str) -> str:
        """Generate context-aware verification keyword."""
        if not expected:
            return self._generate_library_aware_page_verification("Expected content")

        # For web-related content (message, text, page content), use SeleniumLibrary
        web_indicators = [
            "message",
            "text",
            "page",
            "display",
            "show",
            "appear",
            "welcome",
            "error",
            "success",
            "confirm",
        ]
        expected_lower = expected.lower()

        if any(indicator in expected_lower for indicator in web_indicators):
            # Extract the actual message text to verify
            message_text = expected.strip()
            # Remove common prefixes that aren't part of the actual text
            message_text = re.sub(
                r"^(.*?(?:message|text|content|page)\s*"
                r"(?:displayed?|shown?|appears?)?[\s:]*)",
                "",
                message_text,
                flags=re.IGNORECASE,
            ).strip()

            if message_text:
                return self._generate_library_aware_page_verification(message_text)
            return self._generate_library_aware_page_verification(expected)

        # For non-web content, use generic assertion
        return f"Should Be Equal    ${{actual}}    {expected}"
