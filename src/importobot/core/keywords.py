"""Implementation of keyword generation components."""

import re
from typing import Any, Callable, Dict, List, Set

from importobot import config
from importobot.core.constants import EXPECTED_RESULT_FIELD_NAMES, TEST_DATA_FIELD_NAMES
from importobot.core.interfaces import KeywordGenerator
from importobot.core.keywords_registry import IntentRecognitionEngine, LibraryDetector
from importobot.core.parsers import GenericTestFileParser
from importobot.utils.logging import setup_logger
from importobot.utils.validation import sanitize_robot_string

logger = setup_logger(__name__)


class GenericKeywordGenerator(KeywordGenerator):
    """Generic keyword generator for Robot Framework conversion."""

    def __init__(self) -> None:
        """Initialize the generator with intent patterns."""
        self._intent_patterns = self._build_intent_patterns()

    def generate_test_case(self, test_data: Dict[str, Any]) -> List[str]:
        """Generate Robot Framework test case."""
        lines = []

        # Test name
        name = self._extract_field(test_data, ["name", "title", "testname", "summary"])
        lines.append(sanitize_robot_string(name or "Unnamed Test"))

        # Documentation
        doc = self._extract_field(
            test_data, ["description", "objective", "documentation"]
        )
        if doc:
            lines.append(f"    [Documentation]    {sanitize_robot_string(doc)}")

        # Steps
        parser = self._get_parser()
        steps = parser.find_steps(test_data)
        if not steps:
            lines.append("    No Operation  # Placeholder for missing steps")
        else:
            for step in steps:
                lines.extend(self.generate_step_keywords(step))

        lines.append("")
        return lines

    def generate_step_keywords(self, step: Dict[str, Any]) -> List[str]:
        """Generate Robot Framework keywords for a step."""
        lines = []

        # Extract step information
        description = self._extract_field(
            step, ["step", "description", "action", "instruction"]
        )
        test_data = self._extract_field(step, TEST_DATA_FIELD_NAMES)
        expected = self._extract_field(step, EXPECTED_RESULT_FIELD_NAMES)

        # Add traceability comments
        if description:
            lines.append(f"    # Step: {description}")
        if test_data:
            lines.extend(self._format_test_data_comment(test_data))
        if expected:
            lines.append(f"    # Expected Result: {expected}")

        # Generate Robot keyword
        keyword_line = self._determine_robot_keyword(description, test_data, expected)
        lines.append(f"    {keyword_line}")

        return lines

    def detect_libraries(self, steps: List[Dict[str, Any]]) -> Set[str]:
        """Detect required Robot Framework libraries from step content."""
        return LibraryDetector.detect_libraries_from_steps(steps)

    def _get_parser(self) -> GenericTestFileParser:
        """Get parser instance."""
        return GenericTestFileParser()

    def _extract_field(self, data: Dict[str, Any], field_names: List[str]) -> str:
        """Extract value from first matching field name."""
        for field in field_names:
            if field in data and data[field]:
                return str(data[field])
        return ""

    def _format_test_data_comment(self, test_data: str) -> List[str]:
        """Format test data comment, splitting long lines as needed."""
        comment = f"    # Test Data: {test_data}"
        if len(comment) <= 88:
            return [comment]

        # Split long test data comments across multiple lines
        split_points = [", ", "; ", " "]
        best_split = None

        for split_char in split_points:
            # Look for split point that keeps first line under 88 chars
            for i in range(len(test_data)):
                end_idx = i + len(split_char)
                if test_data[i:end_idx] == split_char:
                    first_part = (
                        f"    # Test Data: {test_data[: i + len(split_char) - 1]}"
                    )
                    if len(first_part) <= 88:
                        best_split = i + len(split_char) - 1
                    else:
                        break
            if best_split:
                break

        if best_split:
            first_part = test_data[:best_split].rstrip()
            second_part = test_data[best_split:].lstrip()
            return [
                f"    # Test Data: {first_part}",
                f"    # Test Data (cont.): {second_part}",
            ]

        # Fallback: split at 75 chars to leave room for prefix
        split_point = 75 - len("    # Test Data: ")
        first_part = test_data[:split_point].rstrip()
        second_part = test_data[split_point:].lstrip()
        return [
            f"    # Test Data: {first_part}",
            f"    # Test Data (cont.): {second_part}",
        ]

    def _determine_robot_keyword(
        self, description: str, test_data: str, expected: str
    ) -> str:
        """Determine Robot Framework keyword based on step content."""
        combined = f"{description} {test_data}".lower()
        intent = IntentRecognitionEngine.recognize_intent(combined)

        # Switch-like pattern for intent-based keyword generation
        intent_handlers = {
            "command_execution": lambda: self._command_keyword(test_data),
            "file_verification": lambda: self._file_exists_keyword(test_data),
            "file_removal": lambda: self._remove_file_keyword(test_data),
            "file_transfer": lambda: self._file_transfer_keyword(test_data),
            "ssh_connect": lambda: self._ssh_connect_keyword(test_data),
            "ssh_disconnect": lambda: "Close Connection",
            "web_navigation": lambda: self._browser_keyword(test_data),
            "web_input_username": lambda: self._input_keyword("username", test_data),
            "web_input_password": lambda: self._password_keyword(test_data),
            "web_click": lambda: self._click_keyword(description),
            "assertion_contains": lambda: self._assert_contains_keyword(
                test_data, expected
            ),
            "content_verification": lambda: self._verify_keyword(expected or test_data),
            "db_connect": lambda: self._database_connect_keyword(test_data),
            "db_execute": lambda: self._database_query_keyword(test_data),
            "db_disconnect": lambda: "Disconnect From Database",
            "db_modify": lambda: self._database_modify_keyword(test_data),
            "db_row_count": lambda: self._database_row_count_keyword(test_data),
            "api_request": lambda: self._api_request_keyword(test_data),
            "api_session": lambda: self._api_session_keyword(test_data),
            "api_response": lambda: self._api_response_keyword(test_data),
        }

        # Execute handler if intent is recognized
        if intent in intent_handlers:
            return intent_handlers[intent]()

        # Fallback to original patterns for compatibility
        for pattern, keyword_func in self._intent_patterns.items():
            if re.search(pattern, combined):
                return keyword_func(description, test_data, expected)

        return "No Operation"

    def _build_intent_patterns(self) -> Dict[str, Callable[[str, str, str], str]]:
        """Build intent pattern to keyword function mapping."""
        return {
            # Command execution (check first for curl/wget)
            r"\b(?:initiate.*download|execute.*curl|run.*wget|curl|wget)\b": lambda d,
            td,
            e: self._command_keyword(td),
            # General command execution (for echo, hash, etc.)
            r"\b(?:echo|hash|sha256sum)\b": lambda d, td, e: self._command_keyword(td),
            # File operations (most specific patterns first)
            r"\b(?:verify|check|ensure).*file.*exists?\b": lambda d,
            td,
            e: self._file_exists_keyword(td),
            r"\b(?:remove|delete|clean).*file\b": lambda d,
            td,
            e: self._remove_file_keyword(td),
            r"\b(?:get|retrieve).*file\b": lambda d, td, e: self._file_transfer_keyword(
                td
            ),
            r"\btransfer.*file\b": lambda d, td, e: self._file_transfer_keyword(td),
            # SSH operations
            r"\b(?:open|establish|create).*(?:ssh|connection|remote)\b": lambda d,
            td,
            e: self._ssh_connect_keyword(td),
            r"\b(?:close|disconnect|terminate).*(?:connection|ssh)\b": lambda d,
            td,
            e: "Close Connection",
            # Browser operations
            r"\b(?:open|navigate|visit).*(?:browser|page|url|application)\b": lambda d,
            td,
            e: self._browser_keyword(td),
            r"\b(?:go to|navigate to)\b.*\b(?:url|page|site)\b": lambda d,
            td,
            e: self._url_keyword(td),
            r"\b(?:enter|input|type|fill).*username\b": lambda d,
            td,
            e: self._input_keyword("username", td),
            r"\b(?:enter|input|type|fill).*password\b": lambda d,
            td,
            e: self._password_keyword(td),
            r"\b(?:click|press|tap).*(?:button|element)\b": lambda d,
            td,
            e: self._click_keyword(d),
            # Specific patterns for builtin assertions
            r"\bassert.*contains?\b": (
                lambda d, td, e: self._assert_contains_keyword(td, e)
            ),
            # Content verification
            r"\b(?:verify|check|ensure|assert).*(?:content|contains|displays)\b": (
                lambda d, td, e: self._verify_keyword(e or td)
            ),
            # Database operations
            r"\b(?:connect|establish|open).*(?:database|db connection)\b": lambda d,
            td,
            e: self._database_connect_keyword(td),
            r"\b(?:execute|run).*(?:sql|query)\b": lambda d,
            td,
            e: self._database_query_keyword(td),
            r"\b(?:disconnect|close|terminate).*(?:database|db)\b": lambda d,
            td,
            e: "Disconnect From Database",
            r"\b(?:insert|update|delete).*(?:record|row)\b": lambda d,
            td,
            e: self._database_modify_keyword(td),
            r"\b(?:verify|check|validate).*(?:row|record).*count\b": (
                lambda d, td, e: self._database_row_count_keyword(td)
            ),
            # API operations
            r"\b(?:make|send|perform).*(?:get|post|put|delete).*(?:request|api)\b": (
                lambda d, td, e: self._api_request_keyword(td)
            ),
            r"\b(?:create|establish).*(?:session|api connection)\b": lambda d,
            td,
            e: self._api_session_keyword(td),
            r"\b(?:verify|check|validate).*(?:response|status)\b": lambda d,
            td,
            e: self._api_response_keyword(td),
        }

    def _browser_keyword(self, test_data: str) -> str:
        """Generate browser opening keyword with Chrome options for CI/headless."""
        url_match = re.search(r"https?://[^\s,]+", test_data)
        url = url_match.group(0) if url_match else config.TEST_LOGIN_URL
        # Add Chrome options to prevent session conflicts in CI/testing environments
        # Using the correct format for SeleniumLibrary Chrome options
        chrome_options = "; ".join(
            f"add_argument('{option}')" for option in config.CHROME_OPTIONS
        )
        return f"Open Browser    {url}    chrome    options={chrome_options}"

    def _url_keyword(self, test_data: str) -> str:
        """Generate URL navigation keyword."""
        url_match = re.search(r"https?://[^\s,]+", test_data)
        if url_match:
            return f"Go To    {url_match.group(0)}"
        # Go To requires a URL
        return "Go To    https://example.com"

    def _input_keyword(self, field_type: str, test_data: str) -> str:
        """Generate input keyword."""
        value = self._extract_value_from_data(test_data)
        return (
            f"Input Text    id={field_type}    {value}"
            if value
            else f"Input Text    id={field_type}    test_value"
        )

    def _password_keyword(self, test_data: str) -> str:
        """Generate password input keyword."""
        value = self._extract_value_from_data(test_data)
        return (
            f"Input Password    id=password    {value}"
            if value
            else "Input Password    id=password    test_password"
        )

    def _database_connect_keyword(self, test_data: str) -> str:
        """Generate database connection keyword."""
        # Extract database connection parameters
        module = self._extract_pattern(test_data, r"(?:module|driver):\s*([^,\s]+)")
        database = self._extract_pattern(
            test_data, r"(?:database|db|dbname):\s*([^,\s]+)"
        )
        username = self._extract_pattern(test_data, r"(?:username|user):\s*([^,\s]+)")
        password = self._extract_pattern(test_data, r"(?:password|pass):\s*([^,\s]+)")
        host = self._extract_pattern(test_data, r"(?:host|server):\s*([^,\s]+)")

        args = []
        if module:
            args.append(module)
        if database:
            args.append(database)
        if username:
            args.append(username)
        if password:
            args.append(password)
        if host:
            args.append(host)

        return (
            f"Connect To Database    {'    '.join(args)}"
            if args
            else "Connect To Database    sqlite3    test.db"
        )

    def _database_query_keyword(self, test_data: str) -> str:
        """Generate database query keyword."""
        # Extract SQL query
        sql_match = re.search(
            r"(?:sql|query|statement):\s*(.+?)(?:\s*(?:\n|$))",
            test_data,
            re.IGNORECASE | re.DOTALL,
        )
        if sql_match:
            sql = sql_match.group(1).strip()
            return f"Execute Sql String    {sql}"

        # Try to extract just the SQL part
        sql_patterns = [
            r"(SELECT\s+.+?);?",
            r"(INSERT\s+.+?);?",
            r"(UPDATE\s+.+?);?",
            r"(DELETE\s+.+?);?",
        ]

        for pattern in sql_patterns:
            sql_match = re.search(pattern, test_data, re.IGNORECASE | re.DOTALL)
            if sql_match:
                sql = sql_match.group(1).strip()
                return f"Execute Sql String    {sql}"

        # Execute Sql String requires at least one argument
        return "Execute Sql String    SELECT 1"

    def _database_modify_keyword(self, test_data: str) -> str:
        """Generate database modification keyword."""
        # Extract SQL modification statement
        sql_match = re.search(
            r"(?:sql|query|statement):\s*(.+?)(?:\s*(?:\n|$))",
            test_data,
            re.IGNORECASE | re.DOTALL,
        )
        if sql_match:
            sql = sql_match.group(1).strip()
            return f"Execute Sql String    {sql}"
        # Execute Sql String requires at least one argument
        return "Execute Sql String    SELECT 1"

    def _database_row_count_keyword(self, test_data: str) -> str:
        """Generate database row count verification keyword."""
        # Extract table name if present
        table_name = self._extract_pattern(test_data, r"(?:table|from):\s*([^\s,]+)")

        # Use Query keyword for row count verification since Row Count Should Be
        # is not a standard DatabaseLibrary keyword
        if not table_name:
            table_name = "users"  # Default table name

        # Query returns results, so we use SELECT COUNT(*) for row count
        select_statement = f"SELECT COUNT(*) FROM {table_name}"

        return f"Query    {select_statement}"

    def _api_request_keyword(self, test_data: str) -> str:
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

    def _api_session_keyword(self, test_data: str) -> str:
        """Generate API session keyword."""
        alias = (
            self._extract_pattern(test_data, r"(?:alias|name):\s*([^,\s]+)")
            or "default_session"
        )
        url = self._extract_pattern(test_data, r"(?:url|base.*url):\s*([^,\s]+)")

        if url:
            return f"Create Session    {alias}    {url}"
        # Create Session requires both alias and URL
        return f"Create Session    {alias}    https://api.example.com"

    def _api_response_keyword(self, test_data: str) -> str:
        """Generate API response verification keyword."""
        expected_status = self._extract_pattern(test_data, r"(?:status|code):\s*(\d+)")
        if expected_status:
            return f"Status Should Be    {expected_status}"
        return "Status Should Be    200"

    def _click_keyword(self, description: str) -> str:
        """Generate click keyword."""
        desc_lower = description.lower()
        if "login" in desc_lower and "button" in desc_lower:
            return "Click Button    id=login_button"
        if "button" in desc_lower:
            return "Click Button    id=submit_button"
        return "Click Element    id=clickable_element"

    def _ssh_connect_keyword(self, test_data: str) -> str:
        """Generate SSH connection keyword."""
        host = self._extract_pattern(test_data, r"(?:host|server):\s*([^,\s]+)")
        username = self._extract_pattern(test_data, r"username:\s*([^,\s]+)")
        password = self._extract_pattern(test_data, r"password:\s*([^,\s]+)")

        args = [host] if host else []
        if username and password:
            args.extend([username, password])

        # Open Connection requires at least a host
        if args:
            return f"Open Connection    {'    '.join(args)}"
        return "Open Connection    localhost"

    def _file_transfer_keyword(self, test_data: str) -> str:
        """Generate file transfer keyword."""
        remote = self._extract_pattern(test_data, r"Remote File Path:\s*([^,\s]+)")
        local = self._extract_pattern(test_data, r"Local Destination Path:\s*([^,\s]+)")

        args = []
        if remote:
            args.append(remote)
        if local:
            args.append(local)

        # Get File requires at least a remote path
        if args:
            return f"Get File    {'    '.join(args)}"
        return "Get File    /tmp/remote.txt    /tmp/local.txt"

    def _file_exists_keyword(self, test_data: str) -> str:
        """Generate file exists verification keyword."""
        # Look for explicit file paths
        path = self._extract_pattern(test_data, r"/[^\s,]+|[a-zA-Z]:\\[^\s,]+")
        if not path:
            # Try alternative patterns for file paths in test data
            path = self._extract_pattern(test_data, r"at\s+([^\s,]+)")
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
        return "File Should Exist    /tmp/test.txt"

    def _remove_file_keyword(self, test_data: str) -> str:
        """Generate file removal keyword."""
        # First try to extract from "rm path" or "Command: rm path" patterns
        path = self._extract_pattern(test_data, r"rm\s+([^\s]+)")
        if not path:
            # Try generic file path extraction
            path = self._extract_pattern(test_data, r"/[^\s,]+|[a-zA-Z]:\\[^\s,]+")
        # Remove File requires a path argument
        return f"Remove File    {path}" if path else "Remove File    /tmp/test.txt"

    def _command_keyword(self, test_data: str) -> str:
        """Generate command execution keyword."""
        command = self._extract_pattern(test_data, r"command:\s*(.+)")
        if command:
            cmd_parts = command.strip().split()
            parts = "    ".join(cmd_parts)
            return f"Run Process    {parts}"

        # For direct command execution (echo, hash, etc.), use test_data directly
        if test_data and test_data.strip():
            # Split the command into parts
            cmd_parts = test_data.strip().split()
            return f"Run Process    {'    '.join(cmd_parts)}"
        # Run Process requires at least a command
        return "Run Process    echo    test"

    def _assert_contains_keyword(self, test_data: str, expected: str) -> str:
        """Generate builtin Should Contain keyword."""
        # Extract container and item from test data
        container = "title"  # Default container
        item = expected or test_data or "test"

        # Try to extract more specific values
        if test_data:
            # Look for patterns like "Container: ${text}, Item: 'expected_text'"
            container_match = re.search(
                r"container[^\w]+(\S+)", test_data, re.IGNORECASE
            )
            item_match = re.search(r"item[^\w]+(\S+)", test_data, re.IGNORECASE)

            if container_match:
                container = container_match.group(1)
            if item_match:
                item = item_match.group(1)
            elif not expected:
                # Use the test data as the item if no expected result
                item = test_data

        return f"Should Contain    {container}    {item}"

    def _verify_keyword(self, content: str) -> str:
        """Generate content verification keyword."""
        if content and content not in ["N/A", "n/a"]:
            return f"Page Should Contain    {content}"
        # Page Should Contain requires text to verify
        return "Page Should Contain    test"

    def _extract_value_from_data(self, test_data: str) -> str:
        """Extract value from test data."""
        if ":" in test_data:
            return test_data.split(":", 1)[1].strip()
        return test_data.strip() if test_data else ""

    def _extract_pattern(self, text: str, pattern: str) -> str:
        """Extract first match from regex pattern."""
        if not text:
            return ""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match and match.lastindex else ""
