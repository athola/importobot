"""Pattern matching engine for intent-based keyword generation."""

import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from re import Pattern
from typing import Any, ClassVar

from importobot.medallion.bronze.evidence_accumulator import EvidenceItem
from importobot.medallion.bronze.format_models import EvidenceWeight
from importobot.medallion.interfaces.enums import EvidenceSource
from importobot.utils.defaults import PROGRESS_CONFIG
from importobot.utils.step_processing import combine_step_text


class RobotFrameworkLibrary(str, Enum):
    """Robot Framework library enumeration for extensible library management."""

    # Web automation libraries
    SELENIUM_LIBRARY = "SeleniumLibrary"
    APPIUM_LIBRARY = "AppiumLibrary"

    # API and database libraries
    REQUESTS_LIBRARY = "RequestsLibrary"
    DATABASE_LIBRARY = "DatabaseLibrary"
    MONGODB_LIBRARY = "RobotMongoDBLibrary"

    # System and SSH libraries
    SSH_LIBRARY = "SSHLibrary"
    OPERATING_SYSTEM = "OperatingSystem"
    PROCESS = "Process"

    # Utility libraries
    COLLECTIONS = "Collections"
    STRING = "String"
    TELNET = "Telnet"

    # FTP and messaging libraries
    FTP_LIBRARY = "FtpLibrary"
    MQTT_LIBRARY = "MQTTLibrary"
    REDIS_LIBRARY = "RedisLibrary"

    # Built-in library (always available)
    BUILTIN = "builtin"

    @classmethod
    def get_conflict_groups(cls) -> dict[str, set["RobotFrameworkLibrary"]]:
        """
        Get groups of libraries that have keyword conflicts.

        Returns:
            Dictionary mapping conflict group names to sets of conflicting libraries
        """
        return {
            "web_automation": {cls.SELENIUM_LIBRARY, cls.APPIUM_LIBRARY},
            # Add future conflict groups here as needed
            # "database": {cls.DATABASE_LIBRARY, cls.MONGODB_LIBRARY},
        }

    @classmethod
    def get_conflict_prone_libraries(cls) -> set["RobotFrameworkLibrary"]:
        """
        Get libraries that commonly have keyword conflicts requiring prefixes.

        Returns:
            Set of libraries that need explicit prefixes for disambiguation
        """
        conflict_prone = set()
        for group in cls.get_conflict_groups().values():
            if len(group) > 1:  # Only groups with actual conflicts
                conflict_prone.update(group)
        return conflict_prone

    @classmethod
    def from_string(cls, library_name: str) -> "RobotFrameworkLibrary":
        """
        Convert string library name to enum value.

        Args:
            library_name: Library name as string

        Returns:
            RobotFrameworkLibrary enum value

        Raises:
            ValueError: If library name is not recognized
        """
        try:
            return cls(library_name)
        except ValueError:
            # Handle legacy naming or common variations
            normalized_name = library_name.replace("Library", "").upper()
            for lib in cls:
                if lib.value.replace("Library", "").upper() == normalized_name:
                    return lib
            raise ValueError(f"Unknown library: {library_name}") from None


class IntentType(Enum):
    """Types of intents that can be detected in test steps."""

    COMMAND_EXECUTION = "command"
    FILE_EXISTS = "file_exists"
    FILE_REMOVE = "file_remove"
    FILE_TRANSFER = "file_transfer"
    FILE_VERIFICATION = "file_verification"
    FILE_REMOVAL = "file_removal"
    FILE_CREATION = "file_creation"
    FILE_STAT = "file_stat"
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
    CREDENTIAL_INPUT = "credential_input"  # Composite: username + password
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
    _compiled: Pattern[str] | None = None

    def compiled_pattern(self) -> Pattern[str]:
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
        self._pattern_cache: dict[str, Pattern[str]] = {}
        self._intent_cache: dict[str, IntentType | None] = {}

    def _build_patterns(self) -> list[IntentPattern]:
        """Build list of intent patterns."""
        return [
            # Command execution (highest priority for specific commands)
            IntentPattern(IntentType.FILE_STAT, r"\bstat\b", priority=10),
            IntentPattern(
                IntentType.COMMAND_EXECUTION,
                r"\b(?:initiate.*download|execute.*curl|run.*wget|curl|wget)\b",
                priority=10,
            ),
            IntentPattern(
                IntentType.COMMAND_EXECUTION,
                r"\b(?:echo|hash|blake2bsum)\b",
                priority=9,
            ),
            IntentPattern(
                IntentType.COMMAND_EXECUTION,
                r"\b(?:chmod|chown|stat|truncate|cp|rm|mkdir|rmdir|touch|ls|cat)\b",
                priority=9,
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
            # Browser operations (higher priority than SSH patterns)
            IntentPattern(
                IntentType.BROWSER_OPEN,
                r"\b(?:open|navigate|visit|launch).*(?:browser|page|url|application)\b",
                priority=8,
            ),
            IntentPattern(
                IntentType.BROWSER_NAVIGATE,
                (
                    r"\b(?:go to|navigate(?:\s+to)?)\b.*\b(?:url|page|site|screen|"
                    r"login|portal|dashboard|home)\b"
                ),
                priority=8,
            ),
            IntentPattern(
                IntentType.BROWSER_NAVIGATE,
                (
                    r"\bnavigate(?:\s+to)?\s+(?:login|home|dashboard|portal|"
                    r"application|app)(?:\s+page|\s+screen)?\b"
                ),
                priority=6,
            ),
            IntentPattern(
                IntentType.INPUT_USERNAME,
                (
                    r"\b(?:enter|input|type|fill).*(?:username|user\s*name|email|"
                    r"e-mail|email\s+address)\b"
                ),
                priority=5,
            ),
            IntentPattern(
                IntentType.INPUT_PASSWORD,
                r"\b(?:enter|input|type|fill).*password\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.CREDENTIAL_INPUT,
                r"\b(?:enter|input|type|fill|provide).*"
                r"(?:credentials?|login\s+(?:details|info))\b",
                priority=6,  # Higher priority than individual username/password
            ),
            IntentPattern(
                IntentType.CLICK_ACTION,
                r"\b(?:click|press|tap).*(?:button|element)\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.CLICK_ACTION,
                r"\bsubmit\b.*\b(?:form|button|login|request)\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.CLICK_ACTION,
                r"\b(?:click|press|tap)\b",
                priority=3,
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
                (
                    r"\b(?:verify|check|ensure|assert|validate)"
                    r".*(?:content|contains|displays)\b"
                ),
                priority=3,
            ),
            # General validation pattern (audit trails, compliance checks, etc.)
            IntentPattern(
                IntentType.CONTENT_VERIFICATION,
                r"\b(?:validate|verify|check|ensure|assert)\b",
                priority=2,
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

    # Library detection patterns using enum for extensibility
    LIBRARY_PATTERNS: ClassVar[dict[RobotFrameworkLibrary, str]] = {
        RobotFrameworkLibrary.SELENIUM_LIBRARY: (
            r"\b(?:browser|navigate|click|input|page|web|url|login|button|element"
            r"|selenium|page.*should.*contain|should.*contain.*page|verify.*content"
            r"|check.*content|ensure.*content|page.*contains|contains.*page"
            r"|verify.*text|check.*text|ensure.*text|title.*should|"
            r"location.*should)\b"
        ),
        RobotFrameworkLibrary.SSH_LIBRARY: (
            r"\b(?:ssh|remote|connection|host|server|ssh.*connect|ssh.*disconnect|"
            r"execute.*command|open.*connection|close.*connection|connect.*ssh)\b"
        ),
        RobotFrameworkLibrary.PROCESS: (
            r"\b(?:command|execute|run|curl|wget|bash|process|run.*process"
            r"|start.*process|terminate.*process|wait.*for.*process)\b"
        ),
        RobotFrameworkLibrary.OPERATING_SYSTEM: (
            r"\b(?:file|directory|exists|remove|delete|filesystem|create.*file"
            r"|copy.*file|move.*file|file.*should.*exist|create.*directory"
            r"|remove.*directory|list.*directory|get.*file)\b"
        ),
        RobotFrameworkLibrary.DATABASE_LIBRARY: (
            r"\b(?:database|sql|query|table|connect.*database|db_|execute.*sql"
            r"|row.*count|insert.*into|update.*table|delete.*from|select.*from"
            r"|database.*connection|db.*query|db.*execute|table.*exist"
            r"|row.*count|verify.*row|check.*database|"
            r"disconnect.*from.*database)\b"
        ),
        RobotFrameworkLibrary.REQUESTS_LIBRARY: (
            r"\b(?:api|rest|request|response|session|get.*request|post.*request"
            r"|put.*request|delete.*request|http|create.*session|make.*request"
            r"|send.*request|api.*call|rest.*api|http.*request|verify.*response"
            r"|check.*status|get.*response|status.*should.*be)\b"
        ),
        RobotFrameworkLibrary.COLLECTIONS: (
            r"\b(?:list|dictionary|collection|append|get.*from.*list"
            r"|get.*from.*dict|create.*list|create.*dictionary|dictionary.*key"
            r"|list.*item|collections|dict.*update|append.*to.*list)\b"
        ),
        RobotFrameworkLibrary.STRING: (
            r"\b(?:string|uppercase|lowercase|replace.*string|split.*string|strip"
            r"|string.*operation|string.*manipulation|convert.*case"
            r"|format.*string|convert.*to.*uppercase|convert.*to.*lowercase)\b"
        ),
        RobotFrameworkLibrary.TELNET: (
            r"\b(?:telnet|telnet.*connection|open.*telnet|telnet.*session"
            r"|telnet.*command|telnet.*read|telnet.*write)\b"
        ),
        RobotFrameworkLibrary.APPIUM_LIBRARY: (
            r"\b(?:mobile.*app|android.*app|ios.*app|mobile.*application|"
            r"appium.*server|mobile.*device.*automation|mobile.*testing|"
            r"launch.*app|install.*app|app.*package|bundle.*id|device.*name|"
            r"platform.*name|udid|native.*app|webview|hybrid.*app)\b"
        ),
        RobotFrameworkLibrary.FTP_LIBRARY: (
            r"\b(?:ftp.*server|ftp.*connection|ftp.*protocol|"
            r"file.*transfer.*protocol)\b"
        ),
        RobotFrameworkLibrary.MQTT_LIBRARY: (
            r"\b(?:mqtt|message.*queue|publish|subscribe|broker|iot|mqtt.*message"
            r"|mqtt.*topic|mqtt.*connect)\b"
        ),
        RobotFrameworkLibrary.REDIS_LIBRARY: (
            r"\b(?:redis|cache|key.*value|redis.*connect|redis.*get|redis.*set"
            r"|redis.*key|redis.*cache)\b"
        ),
        RobotFrameworkLibrary.MONGODB_LIBRARY: (
            r"\b(?:mongodb|mongo|nosql|document.*database|collection|mongo.*connect"
            r"|mongo.*insert|mongo.*query|mongo.*update|mongo.*delete)\b"
        ),
    }

    @classmethod
    def detect_libraries_from_text(
        cls, text: str, json_data: dict[str, Any] | None = None
    ) -> set[RobotFrameworkLibrary]:
        """Detect required Robot Framework libraries from text content."""
        if not text:
            return set()
        library_enums = set()
        text_lower = text.lower()
        for library_enum, pattern in cls.LIBRARY_PATTERNS.items():
            if re.search(pattern, text_lower):
                library_enums.add(library_enum)

        # Resolve conflicts between similar libraries
        library_enums = cls._resolve_library_conflicts(
            library_enums, text_lower, json_data
        )

        return library_enums

    @classmethod
    def detect_libraries_from_steps(
        cls, steps: list[dict[str, Any]], json_data: dict[str, Any] | None = None
    ) -> set[RobotFrameworkLibrary]:
        """Detect required libraries from step content."""
        combined_text = combine_step_text(steps)
        return cls.detect_libraries_from_text(combined_text, json_data)

    @classmethod
    def _resolve_library_conflicts(
        cls,
        libraries: set[RobotFrameworkLibrary],
        text: str,
        json_data: dict[str, Any] | None = None,
    ) -> set[RobotFrameworkLibrary]:
        """
        Resolve conflicts between libraries using Bayesian evidence collection.

        For library coverage scenarios (indicated by 'library_coverage' label),
        skips conflict resolution to allow full coverage testing of all libraries.
        """
        # Skip conflict resolution for library coverage scenarios
        # Check for explicit library_coverage label in test data
        if cls._is_library_coverage_scenario(json_data):
            return libraries

        # Conflict resolution: SeleniumLibrary vs AppiumLibrary
        if (
            RobotFrameworkLibrary.SELENIUM_LIBRARY in libraries
            and RobotFrameworkLibrary.APPIUM_LIBRARY in libraries
        ):
            return cls._resolve_selenium_appium_conflict(libraries, text)

        return libraries

    @classmethod
    def _is_library_coverage_scenario(cls, json_data: dict[str, Any] | None) -> bool:
        """Check if this is a library coverage scenario based on test data labels."""
        if not json_data:
            return False

        labels = cls._extract_labels_from_json(json_data)
        return cls._has_library_coverage_label(labels)

    @classmethod
    def _extract_labels_from_json(cls, json_data: dict[str, Any]) -> list[str]:
        """Extract all labels from JSON data structure."""
        labels = []

        # Direct labels field
        labels.extend(cls._extract_labels_from_field(json_data, "labels"))

        # Check test cases for labels
        if "steps" in json_data and isinstance(json_data["steps"], list):
            for step in json_data["steps"]:
                labels.extend(cls._extract_labels_from_field(step, "labels"))

        # Check nested test structures
        if "tests" in json_data and isinstance(json_data["tests"], list):
            for test in json_data["tests"]:
                labels.extend(cls._extract_labels_from_field(test, "labels"))

        return labels

    @classmethod
    def _extract_labels_from_field(cls, data: dict[str, Any], field: str) -> list[str]:
        """Extract labels from a specific field in a data structure."""
        if field not in data:
            return []

        field_data = data[field]
        if isinstance(field_data, list):
            return [str(label) for label in field_data]
        elif isinstance(field_data, str):
            return [field_data]
        return []

    @classmethod
    def _has_library_coverage_label(cls, labels: list[str]) -> bool:
        """Check if any label indicates a library coverage scenario."""
        return any("library_coverage" in label.lower() for label in labels)

    @classmethod
    def _resolve_selenium_appium_conflict(
        cls, libraries: set[RobotFrameworkLibrary], text: str
    ) -> set[RobotFrameworkLibrary]:
        """
        Resolve SeleniumLibrary vs AppiumLibrary conflict using Bayesian evidence.

        Creates library-specific evidence items and applies Bayesian inference
        principles to determine whether the automation context is web-based
        or mobile-based.
        """
        # Create evidence items for mobile patterns
        mobile_evidence_items = [
            EvidenceItem(
                source=EvidenceSource.STRUCTURE_INDICATOR,
                confidence=0.95,
                weight=EvidenceWeight.UNIQUE,
                details="Strong mobile automation indicator",
            ),
            EvidenceItem(
                source=EvidenceSource.STRUCTURE_INDICATOR,
                confidence=0.80,
                weight=EvidenceWeight.STRONG,
                details="Clear mobile application pattern",
            ),
            EvidenceItem(
                source=EvidenceSource.STRUCTURE_INDICATOR,
                confidence=0.60,
                weight=EvidenceWeight.MODERATE,
                details="Mobile suggestive pattern",
            ),
        ]

        # Create evidence items for web patterns
        web_evidence_items = [
            EvidenceItem(
                source=EvidenceSource.STRUCTURE_INDICATOR,
                confidence=0.95,
                weight=EvidenceWeight.UNIQUE,
                details="Strong web browser indicator",
            ),
            EvidenceItem(
                source=EvidenceSource.STRUCTURE_INDICATOR,
                confidence=0.80,
                weight=EvidenceWeight.STRONG,
                details="Clear web automation pattern",
            ),
            EvidenceItem(
                source=EvidenceSource.STRUCTURE_INDICATOR,
                confidence=0.60,
                weight=EvidenceWeight.MODERATE,
                details="Web suggestive pattern",
            ),
        ]

        # Pattern definitions for mobile detection
        mobile_patterns = [
            # UNIQUE patterns (0.95 confidence)
            (r"\b(?:android.*app|ios.*app|native.*app)\b", 0, 0.95),
            (r"\b(?:appium.*server|desired.*capabilities)\b", 0, 0.95),
            (r"\b(?:device.*orientation|screen.*rotation)\b", 0, 0.95),
            (r"\b(?:app.*package|bundle.*id)\b", 0, 0.95),
            # STRONG patterns (0.80 confidence)
            (r"\b(?:mobile.*device.*automation|mobile.*application)\b", 1, 0.80),
            (r"\b(?:install.*app|launch.*app)\b", 1, 0.80),
            (r"\b(?:touch|swipe|pinch|zoom).*screen\b", 1, 0.80),
            (r"\b(?:platform.*name|device.*name|udid)\b", 1, 0.80),
            # MODERATE patterns (0.60 confidence)
            (r"\b(?:webview|hybrid.*app)\b", 2, 0.60),
            (r"\b(?:mobile.*element|mobile.*test)\b", 2, 0.60),
        ]

        # Pattern definitions for web detection
        web_patterns = [
            # UNIQUE patterns (0.95 confidence)
            (r"\b(?:web.*browser|chrome|firefox|safari|edge)\b", 0, 0.95),
            (r"\b(?:xpath|css.*selector|html.*element)\b", 0, 0.95),
            (r"\b(?:javascript|dom|page.*object)\b", 0, 0.95),
            # STRONG patterns (0.80 confidence)
            (r"\b(?:url|http://|https://|www\.)\b", 1, 0.80),
            (r"\b(?:navigate.*to|open.*browser)\b", 1, 0.80),
            (r"\b(?:webElement|web.*element)\b", 1, 0.80),
            # MODERATE patterns (0.60 confidence)
            (r"\b(?:click|type|verify).*element\b", 2, 0.60),
            (r"\b(?:page.*title|browser.*window)\b", 2, 0.60),
        ]

        # Calculate Bayesian scores
        mobile_score = cls._calculate_bayesian_score(
            text, mobile_patterns, mobile_evidence_items
        )
        web_score = cls._calculate_bayesian_score(
            text, web_patterns, web_evidence_items
        )

        # Apply decision logic
        return cls._apply_bayesian_decision(libraries, mobile_score, web_score)

    @classmethod
    def _calculate_bayesian_score(
        cls,
        text: str,
        patterns: list[tuple[str, int, float]],
        evidence_items: list[EvidenceItem],
    ) -> float:
        """Calculate Bayesian score for a set of patterns and evidence items."""
        score = 0.0
        for pattern, evidence_idx, confidence in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                evidence = evidence_items[evidence_idx]
                score += confidence * evidence.effective_weight
        return score

    @classmethod
    def _apply_bayesian_decision(
        cls,
        libraries: set[RobotFrameworkLibrary],
        mobile_score: float,
        web_score: float,
    ) -> set[RobotFrameworkLibrary]:
        """Apply Bayesian decision logic to resolve library conflicts."""
        HIGH_CONFIDENCE_THRESHOLD = 2.85  # 3.0 * 0.95 (UNIQUE evidence)
        MODERATE_CONFIDENCE_THRESHOLD = 1.6  # 2.0 * 0.80 (STRONG evidence)

        if mobile_score >= HIGH_CONFIDENCE_THRESHOLD:
            # Strong evidence for mobile - discard SeleniumLibrary
            libraries.discard(RobotFrameworkLibrary.SELENIUM_LIBRARY)
        elif web_score >= HIGH_CONFIDENCE_THRESHOLD:
            # Strong evidence for web - discard AppiumLibrary
            libraries.discard(RobotFrameworkLibrary.APPIUM_LIBRARY)
        elif mobile_score > web_score and mobile_score >= MODERATE_CONFIDENCE_THRESHOLD:
            # Moderate preference for mobile
            libraries.discard(RobotFrameworkLibrary.SELENIUM_LIBRARY)
        elif web_score > mobile_score and web_score >= MODERATE_CONFIDENCE_THRESHOLD:
            # Moderate preference for web
            libraries.discard(RobotFrameworkLibrary.APPIUM_LIBRARY)
        else:
            # Low confidence or tie - prefer SeleniumLibrary (more common)
            libraries.discard(RobotFrameworkLibrary.APPIUM_LIBRARY)

        return libraries

    @classmethod
    def get_keyword_prefix_for_library(cls, library: RobotFrameworkLibrary) -> str:
        """
        Get the appropriate keyword prefix for disambiguation.

        When libraries have conflicting keywords, this returns the library name
        to use as a prefix (e.g., "SeleniumLibrary.Input Text").
        """
        # Use the enum's built-in conflict detection
        return (
            library.value
            if library in RobotFrameworkLibrary.get_conflict_prone_libraries()
            else ""
        )
