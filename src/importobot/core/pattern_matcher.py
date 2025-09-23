"""Pattern matching engine for intent-based keyword generation."""

import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from re import Pattern
from typing import Any, Dict, List, Set

from importobot.utils.defaults import PROGRESS_CONFIG
from importobot.utils.step_processing import combine_step_text


class IntentType(Enum):
    """Types of intents that can be detected in test steps."""

    COMMAND_EXECUTION = "command"
    FILE_EXISTS = "file_exists"
    FILE_REMOVE = "file_remove"
    FILE_TRANSFER = "file_transfer"
    FILE_VERIFICATION = "file_verification"
    FILE_REMOVAL = "file_removal"
    FILE_CREATION = "file_creation"
    SSH_CONNECT = "ssh_connect"
    SSH_DISCONNECT = "ssh_disconnect"
    SSH_CONFIGURATION = "ssh_configuration"
    SSH_DIRECTORY_CREATE = "ssh_directory_create"
    SSH_DIRECTORY_LIST = "ssh_directory_list"
    SSH_FILE_UPLOAD = "ssh_file_upload"
    SSH_FILE_DOWNLOAD = "ssh_file_download"
    SSH_EXECUTE = "ssh_execute"
    SSH_LOGIN = "ssh_login"
    SSH_WRITE = "ssh_write"
    SSH_ENABLE_LOGGING = "ssh_enable_logging"
    SSH_READ_UNTIL = "ssh_read_until"
    SSH_SWITCH_CONNECTION = "ssh_switch_connection"
    BROWSER_OPEN = "browser_open"
    BROWSER_NAVIGATE = "browser_navigate"
    INPUT_USERNAME = "input_username"
    INPUT_PASSWORD = "input_password"
    CLICK_ACTION = "click"
    VERIFY_CONTENT = "web_verify_text"
    ELEMENT_VERIFICATION = "element_verification"
    CONTENT_VERIFICATION = "content_verification"
    DATABASE_CONNECT = "db_connect"
    DATABASE_EXECUTE = "db_query"
    DATABASE_DISCONNECT = "db_disconnect"
    DATABASE_MODIFY = "db_modify"
    DATABASE_ROW_COUNT = "db_row_count"
    API_REQUEST = "api_request"
    API_SESSION = "api_session"
    API_RESPONSE = "api_response"
    ASSERTION_CONTAINS = "assertion_contains"
    PERFORMANCE_MONITORING = "performance_monitoring"
    PERFORMANCE_TESTING = "performance_testing"
    SECURITY_TESTING = "security_testing"
    SECURITY_SCANNING = "security_scanning"
    # BuiltIn conversion operations
    CONVERT_TO_INTEGER = "convert_to_integer"
    CONVERT_TO_STRING = "convert_to_string"
    CONVERT_TO_BOOLEAN = "convert_to_boolean"
    CONVERT_TO_NUMBER = "convert_to_number"
    # BuiltIn variable operations
    SET_VARIABLE = "set_variable"
    GET_VARIABLE = "get_variable"
    # BuiltIn collection operations
    CREATE_LIST = "create_list"
    CREATE_DICTIONARY = "create_dictionary"
    GET_LENGTH = "get_length"
    LENGTH_SHOULD_BE = "length_should_be"
    SHOULD_START_WITH = "should_start_with"
    SHOULD_END_WITH = "should_end_with"
    SHOULD_MATCH = "should_match"
    # BuiltIn evaluation and control flow
    EVALUATE_EXPRESSION = "evaluate_expression"
    RUN_KEYWORD_IF = "run_keyword_if"
    REPEAT_KEYWORD = "repeat_keyword"
    FAIL_TEST = "fail_test"
    GET_COUNT = "get_count"
    # BuiltIn logging
    LOG_MESSAGE = "log_message"


@dataclass(frozen=True)
class IntentPattern:
    """Represents a pattern for detecting an intent."""

    intent_type: IntentType
    pattern: str
    priority: int = 0  # Higher priority patterns are checked first

    # Dynamically created compiled pattern cache
    _compiled: Pattern | None = None

    def compiled_pattern(self) -> Pattern:
        """Get compiled regex pattern."""
        # Initialize cache if needed
        # Using instance-level caching without lru_cache decorator
        if not hasattr(self, "_compiled") or self._compiled is None:
            compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
            object.__setattr__(self, "_compiled", compiled_pattern)
        assert self._compiled is not None  # mypy type narrowing
        return self._compiled

    def matches(self, text: str) -> bool:
        """Check if pattern matches text."""
        return bool(self.compiled_pattern().search(text))


class PatternMatcher:
    """Efficient pattern matching for intent detection."""

    def __init__(self) -> None:
        """Initialize with intent patterns sorted by priority."""
        self.patterns = self._build_patterns()
        # Sort by priority (descending) for more specific patterns first
        self.patterns.sort(key=lambda p: p.priority, reverse=True)
        self._pattern_cache: dict[str, Pattern] = {}
        self._intent_cache: dict[str, IntentType | None] = {}

    def _build_patterns(self) -> list[IntentPattern]:
        """Build list of intent patterns."""
        return [
            # Command execution (highest priority for specific commands)
            IntentPattern(
                IntentType.COMMAND_EXECUTION,
                r"\b(?:initiate.*download|execute.*curl|run.*wget|curl|wget)\b",
                priority=10,
            ),
            IntentPattern(
                IntentType.COMMAND_EXECUTION, r"\b(?:echo|hash|sha256sum)\b", priority=9
            ),
            # File operations (most specific patterns first)
            IntentPattern(
                IntentType.FILE_EXISTS,
                r"\b(?:verify|check|ensure).*file.*exists?\b",
                priority=8,
            ),
            IntentPattern(
                IntentType.FILE_REMOVE, r"\b(?:remove|delete|clean).*file\b", priority=7
            ),
            IntentPattern(
                IntentType.FILE_TRANSFER,
                r"\b(?:get|retrieve|transfer).*file\b",
                priority=7,
            ),
            IntentPattern(
                IntentType.FILE_CREATION,
                r"\b(?:create|write).*file\b",
                priority=7,
            ),
            IntentPattern(
                IntentType.FILE_TRANSFER,
                r"\b(?:copy|move).*file\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.FILE_EXISTS,
                r"\b(?:file.*should.*exist|file.*exists)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.FILE_REMOVE,
                r"\b(?:file.*should.*not.*exist|remove.*file)\b",
                priority=6,
            ),
            # Database operations (more specific patterns first)
            IntentPattern(
                IntentType.DATABASE_CONNECT,
                r"\b(?:connect|establish|open).*(?:database|db connection)\b",
                priority=8,
            ),
            IntentPattern(
                IntentType.DATABASE_EXECUTE,
                r"\b(?:execute|run).*(?:sql|query)\b",
                priority=7,
            ),
            IntentPattern(
                IntentType.DATABASE_DISCONNECT,
                r"\b(?:disconnect|close|terminate).*(?:database|db)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.DATABASE_MODIFY,
                r"\b(?:insert|update|delete).*(?:record|row)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.DATABASE_ROW_COUNT,
                r"\b(?:verify|check|validate).*(?:row|record).*count\b",
                priority=5,
            ),
            # SSH operations
            IntentPattern(
                IntentType.SSH_CONNECT,
                r"\b(?:open|establish|create|connect).*"
                r"(?:ssh|connection|remote|server)\b",
                priority=7,
            ),
            IntentPattern(
                IntentType.SSH_CONNECT, r"\bconnect.*to.*server\b", priority=7
            ),
            IntentPattern(
                IntentType.SSH_CONNECT, r"\bconnect.*to.*staging\b", priority=7
            ),
            IntentPattern(
                IntentType.SSH_CONNECT, r"\bconnect.*to.*production\b", priority=7
            ),
            IntentPattern(IntentType.SSH_CONNECT, r"\bconnect\b", priority=6),
            IntentPattern(
                IntentType.SSH_DISCONNECT,
                r"\b(?:close|disconnect|terminate).*(?:connection|ssh|remote)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.SSH_EXECUTE,
                r"\b(?:execute|run).*(?:command|ssh)\b",
                priority=7,
            ),
            IntentPattern(IntentType.SSH_EXECUTE, r"\bstart.*extraction\b", priority=7),
            IntentPattern(IntentType.SSH_EXECUTE, r"\bstart.*command\b", priority=7),
            IntentPattern(IntentType.SSH_LOGIN, r"\blogin.*ssh\b", priority=7),
            IntentPattern(IntentType.SSH_LOGIN, r"\bssh.*login\b", priority=7),
            IntentPattern(IntentType.SSH_LOGIN, r"\blogin.*with.*key\b", priority=7),
            IntentPattern(
                IntentType.SSH_LOGIN, r"\blogin.*with.*public.*key\b", priority=7
            ),
            IntentPattern(
                IntentType.SSH_CONFIGURATION,
                r"\bset.*ssh.*client.*configuration\b",
                priority=7,
            ),
            IntentPattern(IntentType.SSH_FILE_UPLOAD, r"\bupload.*file\b", priority=7),
            IntentPattern(IntentType.SSH_FILE_UPLOAD, r"\bput.*file\b", priority=7),
            IntentPattern(
                IntentType.SSH_FILE_DOWNLOAD, r"\bdownload.*file\b", priority=7
            ),
            IntentPattern(IntentType.SSH_FILE_DOWNLOAD, r"\bget.*file\b", priority=7),
            IntentPattern(
                IntentType.SSH_DIRECTORY_CREATE, r"\bcreate.*directory\b", priority=8
            ),
            IntentPattern(
                IntentType.SSH_DIRECTORY_LIST, r"\blist.*directory\b", priority=7
            ),
            IntentPattern(IntentType.SSH_READ_UNTIL, r"\bread.*until\b", priority=7),
            IntentPattern(IntentType.SSH_WRITE, r"\bwrite\b", priority=7),
            IntentPattern(
                IntentType.SSH_ENABLE_LOGGING, r"\benable.*logging\b", priority=7
            ),
            IntentPattern(
                IntentType.SSH_SWITCH_CONNECTION, r"\bswitch.*connection\b", priority=7
            ),
            # More flexible SSH patterns that don't explicitly contain "ssh"
            IntentPattern(
                IntentType.SSH_FILE_UPLOAD,
                r"\bupload.*configuration.*file\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.SSH_FILE_UPLOAD,
                r"\bupload.*application.*archive\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.SSH_READ_UNTIL, r"\bwait.*for.*extraction\b", priority=6
            ),
            IntentPattern(
                IntentType.SSH_READ_UNTIL, r"\bwait.*for.*completion\b", priority=6
            ),
            IntentPattern(
                IntentType.SSH_WRITE, r"\bwrite.*deployment.*script\b", priority=6
            ),
            IntentPattern(
                IntentType.SSH_READ_UNTIL, r"\bread.*deployment.*output\b", priority=6
            ),
            IntentPattern(
                IntentType.FILE_VERIFICATION, r"\bverify.*file.*exists\b", priority=6
            ),
            IntentPattern(
                IntentType.SSH_DIRECTORY_CREATE,
                r"\blist.*deployment.*contents\b",
                priority=6,
            ),
            # Browser operations
            IntentPattern(
                IntentType.BROWSER_OPEN,
                r"\b(?:open|navigate|visit).*(?:browser|page|url|application)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.BROWSER_NAVIGATE,
                r"\b(?:go to|navigate to)\b.*\b(?:url|page|site)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.INPUT_USERNAME,
                r"\b(?:enter|input|type|fill).*username\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.INPUT_PASSWORD,
                r"\b(?:enter|input|type|fill).*password\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.CLICK_ACTION,
                r"\b(?:click|press|tap).*(?:button|element)\b",
                priority=4,
            ),
            # Specific patterns for builtin assertions
            IntentPattern(
                IntentType.VERIFY_CONTENT,
                r"\bassert.*page.*contains?\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.ASSERTION_CONTAINS,
                r"\bassert.*contains?\b",
                priority=4,
            ),
            # Content verification
            IntentPattern(
                IntentType.CONTENT_VERIFICATION,
                r"\b(?:verify|check|ensure|assert).*(?:content|contains|displays)\b",
                priority=3,
            ),
            # Specific verification format
            IntentPattern(
                IntentType.CONTENT_VERIFICATION,
                r"verify\s*:",
                priority=3,
            ),
            # Element verification format
            IntentPattern(
                IntentType.ELEMENT_VERIFICATION,
                r"element\s*:",
                priority=3,
            ),
            # API operations
            IntentPattern(
                IntentType.API_REQUEST,
                r"\b(?:make|send|perform).*(?:get|post|put|delete).*(?:request|api)\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.API_SESSION,
                r"\b(?:create|establish).*(?:session|api connection)\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.API_RESPONSE,
                r"\b(?:verify|check|validate).*(?:response|status)\b",
                priority=3,
            ),
            # Monitoring and performance
            IntentPattern(
                IntentType.PERFORMANCE_MONITORING,
                r"\b(?:monitor|measure|track).*(?:performance|metrics|load)\b",
                priority=3,
            ),
            IntentPattern(
                IntentType.PERFORMANCE_TESTING,
                r"\b(?:test|execute).*(?:performance|load|stress)\b",
                priority=3,
            ),
            # Security operations
            IntentPattern(
                IntentType.SECURITY_TESTING,
                r"\b(?:security|authenticate|authorization|vulnerability)\b",
                priority=3,
            ),
            IntentPattern(
                IntentType.SECURITY_SCANNING,
                r"\b(?:scan|penetration|security.*test)\b",
                priority=3,
            ),
            # BuiltIn conversion operations
            IntentPattern(
                IntentType.CONVERT_TO_INTEGER,
                r"\bconvert.*to.*integer\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.CONVERT_TO_STRING,
                r"\bconvert.*to.*string\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.CONVERT_TO_BOOLEAN,
                r"\bconvert.*to.*boolean\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.CONVERT_TO_NUMBER,
                r"\bconvert.*to.*number\b",
                priority=4,
            ),
            # BuiltIn variable operations
            IntentPattern(
                IntentType.SET_VARIABLE,
                r"\bset.*variable\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.GET_VARIABLE,
                r"\bget.*variable\b",
                priority=4,
            ),
            # BuiltIn collection operations
            IntentPattern(
                IntentType.CREATE_LIST,
                r"\bcreate.*list\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.CREATE_DICTIONARY,
                r"\bcreate.*dictionary\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.GET_LENGTH,
                r"\bget.*length\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.LENGTH_SHOULD_BE,
                r"\blength.*should.*be\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.LENGTH_SHOULD_BE,
                r"\bcheck.*length.*of.*collection\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.SHOULD_START_WITH,
                r"\bshould.*start.*with\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.SHOULD_END_WITH,
                r"\bshould.*end.*with\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.SHOULD_MATCH,
                r"\bshould.*match\b",
                priority=4,
            ),
            # BuiltIn evaluation and control flow
            IntentPattern(
                IntentType.EVALUATE_EXPRESSION,
                r"\bevaluate\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.RUN_KEYWORD_IF,
                r"\brun.*keyword.*if\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.RUN_KEYWORD_IF,
                r"\brun.*keyword.*conditionally\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.REPEAT_KEYWORD,
                r"\brepeat.*keyword\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.FAIL_TEST,
                r"\bfail\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.GET_COUNT,
                r"\bget.*count\b",
                priority=4,
            ),
            # BuiltIn logging
            IntentPattern(
                IntentType.LOG_MESSAGE,
                r"\blog.*message\b",
                priority=4,
            ),
            # BuiltIn string operations
            IntentPattern(
                IntentType.SHOULD_START_WITH,
                r"\bverify.*string.*starts.*with\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.SHOULD_MATCH,
                r"\bcheck.*string.*matches.*pattern\b",
                priority=4,
            ),
        ]

    def detect_intent(self, text: str) -> IntentType | None:
        """Detect the primary intent from text."""
        # Simple cache to avoid re-processing the same text
        if text in self._intent_cache:
            return self._intent_cache[text]

        text_lower = text.lower()

        result = None
        for pattern in self.patterns:
            if pattern.matches(text_lower):
                result = pattern.intent_type
                break

        # Use configurable cache limits
        if len(self._intent_cache) < PROGRESS_CONFIG.intent_cache_limit:
            self._intent_cache[text] = result
        elif len(self._intent_cache) >= PROGRESS_CONFIG.intent_cache_cleanup_threshold:
            # Clear half the cache when it gets too large
            keys_to_remove = list(self._intent_cache.keys())[
                : PROGRESS_CONFIG.intent_cache_limit
            ]
            for key in keys_to_remove:
                del self._intent_cache[key]

        return result

    def detect_all_intents(self, text: str) -> list[IntentType]:
        """Detect all matching intents from text."""
        text_lower = text.lower()
        intents = []

        for pattern in self.patterns:
            if pattern.matches(text_lower) and pattern.intent_type not in intents:
                intents.append(pattern.intent_type)

        return intents


class DataExtractor:
    """Extract data from test strings based on patterns."""

    @staticmethod
    @lru_cache(maxsize=128)
    def extract_pattern(text: str, pattern: str) -> str:
        """Extract first match from regex pattern."""
        if not text:
            return ""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match and match.lastindex else ""

    @staticmethod
    def extract_url(text: str) -> str:
        """Extract URL from text."""
        url_match = re.search(r"https?://[^\s,]+", text)
        return url_match.group(0) if url_match else ""

    @staticmethod
    def extract_file_path(text: str) -> str:
        """Extract file path from text."""
        # Look for explicit file paths
        # Handle Windows paths with spaces by looking for complete path patterns
        windows_path_match = re.search(r"[a-zA-Z]:\\[^,\n]+", text)
        if windows_path_match:
            return windows_path_match.group(0).strip()

        # Look for Unix paths
        unix_path_match = re.search(r"/[^\s,]+", text)
        if unix_path_match:
            return unix_path_match.group(0).strip()

        # Try alternative patterns for file paths in test data
        path = DataExtractor.extract_pattern(text, r"at\s+([^\s,]+)")
        if path:
            return path

        # Look for file names with extensions
        path_match = re.search(
            r"([a-zA-Z0-9_.-]+\.[a-zA-Z]+)",
            text,
        )
        if path_match:
            return path_match.group(1)

        return ""

    @staticmethod
    def extract_credentials(text: str) -> tuple[str, str]:
        """Extract username and password from text."""
        username = DataExtractor.extract_pattern(
            text, r"(?:username|user):\s*([^,\s]+)"
        )
        password = DataExtractor.extract_pattern(
            text, r"(?:password|pass|pwd):\s*([^,\s]+)"
        )
        return username, password

    @staticmethod
    def extract_database_params(text: str) -> dict[str, str]:
        """Extract database connection parameters."""
        return {
            "module": DataExtractor.extract_pattern(
                text, r"(?:module|driver):\s*([^,\s]+)"
            ),
            "database": DataExtractor.extract_pattern(
                text, r"(?:database|db|dbname):\s*([^,\s]+)"
            ),
            "username": DataExtractor.extract_pattern(
                text, r"(?:username|user):\s*([^,\s]+)"
            ),
            "password": DataExtractor.extract_pattern(
                text, r"(?:password|pass):\s*([^,\s]+)"
            ),
            "host": DataExtractor.extract_pattern(
                text, r"(?:host|server):\s*([^,\s]+)"
            ),
        }

    @staticmethod
    def extract_sql_query(text: str) -> str:
        """Extract SQL query from text."""
        # Try to extract SQL with label first
        sql_match = re.search(
            r"(?:sql|query|statement):\s*(.+?)(?:\s*(?:\n|$))",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if sql_match:
            return sql_match.group(1).strip()

        # Single combined pattern for all SQL statements (more efficient)
        combined_sql_pattern = r"((?:SELECT|INSERT|UPDATE|DELETE)\s+.+?)(?:;|$)"
        sql_match = re.search(combined_sql_pattern, text, re.IGNORECASE | re.DOTALL)
        return sql_match.group(1).strip() if sql_match else ""

    @staticmethod
    def extract_api_params(text: str) -> dict[str, str]:
        """Extract API request parameters."""
        return {
            "method": DataExtractor.extract_pattern(
                text, r"(?:method|type):\s*([^,\s]+)"
            )
            or "GET",
            "session": DataExtractor.extract_pattern(
                text, r"(?:session|alias):\s*([^,\s]+)"
            )
            or "default_session",
            "url": DataExtractor.extract_pattern(
                text, r"(?:url|endpoint):\s*([^,\s]+)"
            ),
            "data": DataExtractor.extract_pattern(
                text, r"(?:data|payload):\s*(.+?)(?:\s*$)"
            ),
        }


class LibraryDetector:
    """Unified library detection based on text patterns."""

    # Library detection patterns consolidated from keywords_registry
    LIBRARY_PATTERNS = {
        "SeleniumLibrary": (
            r"\b(?:browser|navigate|click|input|page|web|url|login|button|element"
            r"|selenium|page.*should.*contain|should.*contain.*page|verify.*content"
            r"|check.*content|ensure.*content|page.*contains|contains.*page"
            r"|verify.*text|check.*text|ensure.*text|title.*should|"
            r"location.*should)\b"
        ),
        "SSHLibrary": (
            r"\b(?:ssh|remote|connection|host|server|ssh.*connect|ssh.*disconnect|"
            r"execute.*command|open.*connection|close.*connection|connect.*ssh)\b"
        ),
        "Process": (
            r"\b(?:command|execute|run|curl|wget|bash|process|run.*process"
            r"|start.*process|terminate.*process|wait.*for.*process)\b"
        ),
        "OperatingSystem": (
            r"\b(?:file|directory|exists|remove|delete|filesystem|create.*file"
            r"|copy.*file|move.*file|file.*should.*exist|create.*directory"
            r"|remove.*directory|list.*directory|get.*file)\b"
        ),
        "DatabaseLibrary": (
            r"\b(?:database|sql|query|table|connect.*database|db_|execute.*sql"
            r"|row.*count|insert.*into|update.*table|delete.*from|select.*from"
            r"|database.*connection|db.*query|db.*execute|table.*exist"
            r"|row.*count|verify.*row|check.*database|"
            r"disconnect.*from.*database)\b"
        ),
        "RequestsLibrary": (
            r"\b(?:api|rest|request|response|session|get.*request|post.*request"
            r"|put.*request|delete.*request|http|create.*session|make.*request"
            r"|send.*request|api.*call|rest.*api|http.*request|verify.*response"
            r"|check.*status|get.*response|status.*should.*be)\b"
        ),
        "Collections": (
            r"\b(?:list|dictionary|collection|append|get.*from.*list"
            r"|get.*from.*dict|create.*list|create.*dictionary|dictionary.*key"
            r"|list.*item|collections|dict.*update|append.*to.*list)\b"
        ),
        "String": (
            r"\b(?:string|uppercase|lowercase|replace.*string|split.*string|strip"
            r"|string.*operation|string.*manipulation|convert.*case"
            r"|format.*string|convert.*to.*uppercase|convert.*to.*lowercase)\b"
        ),
    }

    @classmethod
    def detect_libraries_from_text(cls, text: str) -> Set[str]:
        """Detect required Robot Framework libraries from text content."""
        if not text:
            return set()
        libraries = set()
        text_lower = text.lower()
        for library, pattern in cls.LIBRARY_PATTERNS.items():
            if re.search(pattern, text_lower):
                libraries.add(library)
        return libraries

    @classmethod
    def detect_libraries_from_steps(cls, steps: List[Dict[str, Any]]) -> Set[str]:
        """Detect required libraries from step content."""
        combined_text = combine_step_text(steps)
        return cls.detect_libraries_from_text(combined_text)
