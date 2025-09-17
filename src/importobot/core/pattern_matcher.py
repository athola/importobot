"""Pattern matching engine for intent-based keyword generation."""

import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional, Pattern, Tuple

from importobot.utils.defaults import PROGRESS_CONFIG


class IntentType(Enum):
    """Types of intents that can be detected in test steps."""

    COMMAND_EXECUTION = "command"
    FILE_EXISTS = "file_exists"
    FILE_REMOVE = "file_remove"
    FILE_TRANSFER = "file_transfer"
    SSH_CONNECT = "ssh_connect"
    SSH_DISCONNECT = "ssh_disconnect"
    BROWSER_OPEN = "browser_open"
    BROWSER_NAVIGATE = "browser_navigate"
    INPUT_USERNAME = "input_username"
    INPUT_PASSWORD = "input_password"
    CLICK_ACTION = "click"
    VERIFY_CONTENT = "verify"
    DATABASE_CONNECT = "db_connect"
    DATABASE_QUERY = "db_query"
    DATABASE_DISCONNECT = "db_disconnect"
    DATABASE_MODIFY = "db_modify"
    DATABASE_ROW_COUNT = "db_row_count"
    API_REQUEST = "api_request"
    API_SESSION = "api_session"
    API_RESPONSE = "api_response"


@dataclass(frozen=True)
class IntentPattern:
    """Represents a pattern for detecting an intent."""

    intent_type: IntentType
    pattern: str
    priority: int = 0  # Higher priority patterns are checked first

    # Dynamically created compiled pattern cache
    _compiled: Optional[Pattern] = None

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
        self._pattern_cache: Dict[str, Pattern] = {}
        self._intent_cache: Dict[str, Optional[IntentType]] = {}

    def _build_patterns(self) -> List[IntentPattern]:
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
            # File operations
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
            # SSH operations
            IntentPattern(
                IntentType.SSH_CONNECT,
                r"\b(?:open|establish|create).*(?:ssh|connection|remote)\b",
                priority=6,
            ),
            IntentPattern(
                IntentType.SSH_DISCONNECT,
                r"\b(?:close|disconnect|terminate).*(?:connection|ssh|remote)\b",
                priority=6,
            ),
            # Browser operations
            IntentPattern(
                IntentType.BROWSER_OPEN,
                r"\b(?:open|navigate|visit).*(?:browser|page|url|application)\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.BROWSER_NAVIGATE,
                r"\b(?:go to|navigate to)\b.*\b(?:url|page|site)\b",
                priority=5,
            ),
            # Input operations
            IntentPattern(
                IntentType.INPUT_USERNAME,
                r"\b(?:enter|input|type|fill).*username\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.INPUT_PASSWORD,
                r"\b(?:enter|input|type|fill).*password\b",
                priority=4,
            ),
            # Click operations
            IntentPattern(
                IntentType.CLICK_ACTION,
                r"\b(?:click|press|tap).*(?:button|element)\b",
                priority=3,
            ),
            # Verification
            IntentPattern(
                IntentType.VERIFY_CONTENT,
                r"\b(?:verify|check|ensure|assert).*(?:content|contains|displays)\b",
                priority=2,
            ),
            # Database operations
            IntentPattern(
                IntentType.DATABASE_CONNECT,
                r"\b(?:connect|establish|open).*(?:database|db connection)\b",
                priority=5,
            ),
            IntentPattern(
                IntentType.DATABASE_QUERY,
                r"\b(?:execute|run).*(?:sql|query)\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.DATABASE_DISCONNECT,
                r"\b(?:disconnect|close|terminate).*(?:database|db)\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.DATABASE_MODIFY,
                r"\b(?:insert|update|delete).*(?:record|row)\b",
                priority=4,
            ),
            IntentPattern(
                IntentType.DATABASE_ROW_COUNT,
                r"\b(?:verify|check|validate).*(?:row|record).*count\b",
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
        ]

    def detect_intent(self, text: str) -> Optional[IntentType]:
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

    def detect_all_intents(self, text: str) -> List[IntentType]:
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
    def extract_credentials(text: str) -> Tuple[str, str]:
        """Extract username and password from text."""
        username = DataExtractor.extract_pattern(
            text, r"(?:username|user):\s*([^,\s]+)"
        )
        password = DataExtractor.extract_pattern(
            text, r"(?:password|pass|pwd):\s*([^,\s]+)"
        )
        return username, password

    @staticmethod
    def extract_database_params(text: str) -> Dict[str, str]:
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
    def extract_api_params(text: str) -> Dict[str, str]:
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
