"""Tests for pattern matching functionality."""

# pylint: disable=protected-access

from importobot.core.pattern_matcher import (
    DataExtractor,
    IntentPattern,
    IntentType,
    LibraryDetector,
    PatternMatcher,
)


class TestIntentPattern:
    """Test IntentPattern functionality."""

    def test_intent_pattern_creation(self) -> None:
        """Test IntentPattern creation and basic functionality."""
        pattern = IntentPattern(
            intent_type=IntentType.SSH_CONNECT, pattern=r"\bopen.*ssh\b", priority=5
        )

        assert pattern.intent_type == IntentType.SSH_CONNECT
        assert pattern.pattern == r"\bopen.*ssh\b"
        assert pattern.priority == 5

    def test_intent_pattern_compiled_pattern_caching(self) -> None:
        """Test that compiled patterns are cached properly."""
        pattern = IntentPattern(
            intent_type=IntentType.SSH_CONNECT, pattern=r"\bopen.*ssh\b"
        )

        # First call should compile and cache
        compiled1 = pattern.compiled_pattern()
        # Second call should return cached version
        compiled2 = pattern.compiled_pattern()

        assert compiled1 is compiled2

    def test_intent_pattern_matches(self) -> None:
        """Test pattern matching functionality."""
        pattern = IntentPattern(
            intent_type=IntentType.SSH_CONNECT, pattern=r"\bopen.*ssh\b"
        )

        assert pattern.matches("open ssh connection")
        assert pattern.matches("Open SSH Connection")  # Case insensitive
        assert not pattern.matches("close ssh connection")
        assert not pattern.matches("ssh is open")


class TestPatternMatcher:
    """Test PatternMatcher functionality."""

    def test_pattern_matcher_initialization(self) -> None:
        """Test PatternMatcher initialization."""
        matcher = PatternMatcher()
        assert len(matcher.patterns) > 0
        assert hasattr(matcher, "_pattern_cache")
        assert hasattr(matcher, "_intent_cache")

    def test_detect_intent_ssh_operations(self) -> None:
        """Test intent detection for SSH operations."""
        matcher = PatternMatcher()

        # Test SSH connect patterns
        assert matcher.detect_intent("open ssh connection") == IntentType.SSH_CONNECT
        assert (
            matcher.detect_intent("establish remote connection")
            == IntentType.SSH_CONNECT
        )

        # Test SSH disconnect patterns
        assert (
            matcher.detect_intent("close ssh connection") == IntentType.SSH_DISCONNECT
        )
        assert (
            matcher.detect_intent("disconnect from remote") == IntentType.SSH_DISCONNECT
        )

    def test_detect_intent_command_execution(self) -> None:
        """Test intent detection for command execution."""
        matcher = PatternMatcher()

        assert (
            matcher.detect_intent("execute curl command")
            == IntentType.COMMAND_EXECUTION
        )
        assert (
            matcher.detect_intent("run wget download") == IntentType.COMMAND_EXECUTION
        )
        assert matcher.detect_intent("echo hello world") == IntentType.COMMAND_EXECUTION

    def test_detect_intent_file_operations(self) -> None:
        """Test intent detection for file operations."""
        matcher = PatternMatcher()

        assert matcher.detect_intent("verify file exists") == IntentType.FILE_EXISTS
        assert matcher.detect_intent("remove file from disk") == IntentType.FILE_REMOVE
        assert matcher.detect_intent("get file from server") == IntentType.FILE_TRANSFER

    def test_detect_intent_database_operations(self) -> None:
        """Test intent detection for database operations."""
        matcher = PatternMatcher()

        assert (
            matcher.detect_intent("connect to database") == IntentType.DATABASE_CONNECT
        )
        assert matcher.detect_intent("execute sql query") == IntentType.DATABASE_EXECUTE
        assert matcher.detect_intent("insert new record") == IntentType.DATABASE_MODIFY

    def test_detect_intent_api_operations(self) -> None:
        """Test intent detection for API operations."""
        matcher = PatternMatcher()

        assert matcher.detect_intent("make get request") == IntentType.API_REQUEST
        assert matcher.detect_intent("create api session") == IntentType.API_SESSION
        assert (
            matcher.detect_intent("verify response status") == IntentType.API_RESPONSE
        )

    def test_detect_intent_caching(self) -> None:
        """Test that intent detection results are cached."""
        matcher = PatternMatcher()

        text = "open ssh connection"
        result1 = matcher.detect_intent(text)
        result2 = matcher.detect_intent(text)

        assert result1 == result2
        assert text in matcher._intent_cache

    def test_detect_intent_cache_limit(self) -> None:
        """Test intent cache size limiting."""
        matcher = PatternMatcher()

        # Fill cache beyond limit
        for i in range(600):
            matcher.detect_intent(f"test text {i}")

        # Cache should be limited
        assert len(matcher._intent_cache) <= 512

        # Fill to trigger cleanup
        for i in range(600, 1100):
            matcher.detect_intent(f"test text {i}")

        # Cache should have been cleaned
        assert len(matcher._intent_cache) < 1024

    def test_detect_all_intents(self) -> None:
        """Test detection of all matching intents."""
        matcher = PatternMatcher()

        # Text that could match multiple patterns
        text = "verify file exists and check content displays correctly"
        intents = matcher.detect_all_intents(text)

        assert IntentType.FILE_EXISTS in intents
        assert IntentType.CONTENT_VERIFICATION in intents
        assert len(intents) >= 2

    def test_detect_intent_priority_ordering(self) -> None:
        """Test that higher priority patterns are matched first."""
        matcher = PatternMatcher()

        # Patterns are sorted by priority, so higher priority should match first
        assert len(matcher.patterns) > 0
        priorities = [p.priority for p in matcher.patterns]
        assert priorities == sorted(priorities, reverse=True)


class TestDataExtractor:
    """Test DataExtractor functionality."""

    def test_extract_pattern_basic(self) -> None:
        """Test basic pattern extraction."""
        result = DataExtractor.extract_pattern("user: testuser", r"user:\s*([^,\s]+)")
        assert result == "testuser"

    def test_extract_pattern_not_found(self) -> None:
        """Test pattern extraction when pattern not found."""
        result = DataExtractor.extract_pattern("no match here", r"user:\s*([^,\s]+)")
        assert result == ""

    def test_extract_pattern_empty_text(self) -> None:
        """Test pattern extraction with empty text."""
        result = DataExtractor.extract_pattern("", r"user:\s*([^,\s]+)")
        assert result == ""

    def test_extract_url(self) -> None:
        """Test URL extraction."""
        text = "Visit https://example.com for more info"
        result = DataExtractor.extract_url(text)
        assert result == "https://example.com"

        text = "Check http://test.org and https://secure.com"
        result = DataExtractor.extract_url(text)
        assert result in ["http://test.org", "https://secure.com"]

    def test_extract_url_not_found(self) -> None:
        """Test URL extraction when no URL present."""
        result = DataExtractor.extract_url("No URL in this text")
        assert result == ""

    def test_extract_file_path(self) -> None:
        """Test file path extraction."""
        # Test explicit paths
        result = DataExtractor.extract_file_path("File at /home/user/test.txt")
        assert result == "/home/user/test.txt"

        result = DataExtractor.extract_file_path(
            "Windows path C:\\Users\\test\\file.doc"
        )
        assert result == "C:\\Users\\test\\file.doc"

        # Test file names with extensions
        result = DataExtractor.extract_file_path("Process config.json file")
        assert result == "config.json"

    def test_extract_credentials(self) -> None:
        """Test credential extraction."""
        text = "username: admin, password: secret123"
        username, password = DataExtractor.extract_credentials(text)
        assert username == "admin"
        assert password == "secret123"

    def test_extract_credentials_partial(self) -> None:
        """Test credential extraction with partial info."""
        text = "username: admin"
        username, password = DataExtractor.extract_credentials(text)
        assert username == "admin"
        assert password == ""

    def test_extract_database_params(self) -> None:
        """Test database parameter extraction."""
        text = (
            "module: postgresql, database: testdb, username: dbuser, password: dbpass, "
            "host: localhost"
        )
        params = DataExtractor.extract_database_params(text)

        assert params["module"] == "postgresql"
        assert params["database"] == "testdb"
        assert params["username"] == "dbuser"
        assert params["password"] == "dbpass"
        assert params["host"] == "localhost"

    def test_extract_sql_query_optimized(self) -> None:
        """Test optimized SQL query extraction."""
        # Test SQL with label
        text = "sql: SELECT * FROM users WHERE id = 1"
        result = DataExtractor.extract_sql_query(text)
        assert result == "SELECT * FROM users WHERE id = 1"

        # Test raw SQL statements (optimized single pattern)
        text = "Execute this: INSERT INTO table VALUES (1, 'test')"
        result = DataExtractor.extract_sql_query(text)
        assert result == "INSERT INTO table VALUES (1, 'test')"

        text = "Run: UPDATE users SET name = 'new' WHERE id = 1"
        result = DataExtractor.extract_sql_query(text)
        assert result == "UPDATE users SET name = 'new' WHERE id = 1"

        text = "Please: DELETE FROM logs WHERE date < '2023-01-01'"
        result = DataExtractor.extract_sql_query(text)
        assert result == "DELETE FROM logs WHERE date < '2023-01-01'"

    def test_extract_sql_query_combined_pattern_efficiency(self) -> None:
        """Test that the optimized combined SQL pattern works correctly."""
        # Test optimization: single combined regex vs multiple individual
        queries = [
            "SELECT name FROM users",
            "INSERT INTO logs VALUES (1, 'test')",
            "UPDATE settings SET value = 'new'",
            "DELETE FROM temp_data",
        ]

        for query in queries:
            text = f"Execute: {query};"
            result = DataExtractor.extract_sql_query(text)
            assert result == query

    def test_extract_sql_query_not_found(self) -> None:
        """Test SQL query extraction when no SQL found."""
        result = DataExtractor.extract_sql_query("No SQL query in this text")
        assert result == ""

    def test_extract_api_params(self) -> None:
        """Test API parameter extraction."""
        text = (
            "method: POST, session: api_session, url: /api/users, "
            "data: {'name': 'test'}"
        )
        params = DataExtractor.extract_api_params(text)

        assert params["method"] == "POST"
        assert params["session"] == "api_session"
        assert params["url"] == "/api/users"
        assert params["data"] == "{'name': 'test'}"

    def test_extract_api_params_defaults(self) -> None:
        """Test API parameter extraction with default values."""
        text = "url: /api/test"
        params = DataExtractor.extract_api_params(text)

        assert params["method"] == "GET"  # Default
        assert params["session"] == "default_session"  # Default
        assert params["url"] == "/api/test"
        assert params["data"] == ""


class TestPatternMatchingIntegration:
    """Integration tests for pattern matching components."""

    def test_full_intent_detection_workflow(self) -> None:
        """Test complete intent detection workflow."""
        matcher = PatternMatcher()

        # SSH scenario
        ssh_text = "open ssh connection to server and execute command"
        intent = matcher.detect_intent(ssh_text)
        assert intent == IntentType.SSH_CONNECT

        # Extract relevant data
        credentials = DataExtractor.extract_credentials(
            "username: admin, password: secret"
        )
        assert credentials[0] == "admin"

        # Database scenario
        db_text = "connect to database and execute sql query"
        intent = matcher.detect_intent(db_text)
        assert intent == IntentType.DATABASE_CONNECT

        # Extract SQL
        sql = DataExtractor.extract_sql_query("query: SELECT * FROM users")
        assert sql == "SELECT * FROM users"

    def test_pattern_matching_performance(self) -> None:
        """Test pattern matching performance with caching."""
        matcher = PatternMatcher()

        # First execution (should compile patterns and cache result)
        text = "open ssh connection to remote server"
        result1 = matcher.detect_intent(text)

        # Second execution (should use cached result)
        result2 = matcher.detect_intent(text)

        assert result1 == result2
        assert result1 == IntentType.SSH_CONNECT

    def test_case_insensitive_matching(self) -> None:
        """Test that all pattern matching is case insensitive."""
        matcher = PatternMatcher()

        variations = [
            "OPEN SSH CONNECTION",
            "Open SSH Connection",
            "open ssh connection",
            "Open ssh Connection",
        ]

        for variation in variations:
            intent = matcher.detect_intent(variation)
            assert intent == IntentType.SSH_CONNECT


class TestLibraryDetectorIntegration:
    """Test LibraryDetector functionality integrated in pattern_matcher."""

    def test_library_detector_consolidation(self) -> None:
        """Test that LibraryDetector is properly consolidated in pattern_matcher."""
        # Test basic library detection
        text = "open browser and navigate to page"
        libraries = LibraryDetector.detect_libraries_from_text(text)
        assert "SeleniumLibrary" in libraries

        # Test SSH library detection
        ssh_text = "connect via ssh and execute commands"
        ssh_libraries = LibraryDetector.detect_libraries_from_text(ssh_text)
        assert "SSHLibrary" in ssh_libraries

        # Test database library detection
        db_text = "connect to database and execute sql query"
        db_libraries = LibraryDetector.detect_libraries_from_text(db_text)
        assert "DatabaseLibrary" in db_libraries

    def test_library_detector_steps_functionality(self) -> None:
        """Test LibraryDetector step processing functionality."""
        steps = [
            {"step": "open browser", "description": "launch web app"},
            {"action": "ssh connect", "details": "remote server"},
            {"operation": "file exists", "path": "/tmp/test.txt"},
        ]

        libraries = LibraryDetector.detect_libraries_from_steps(steps)

        # Should detect multiple libraries
        assert "SeleniumLibrary" in libraries
        assert "SSHLibrary" in libraries
        assert "OperatingSystem" in libraries

    def test_library_detector_integration_with_pattern_matcher(self) -> None:
        """Test that LibraryDetector works alongside PatternMatcher."""
        pattern_matcher = PatternMatcher()

        test_text = "upload file via ssh and verify it exists"

        # Get intent from PatternMatcher
        intent = pattern_matcher.detect_intent(test_text)
        assert intent is not None

        # Get libraries from LibraryDetector
        libraries = LibraryDetector.detect_libraries_from_text(test_text)

        # Should detect appropriate libraries for the intent
        assert "SSHLibrary" in libraries  # For SSH upload
        assert "OperatingSystem" in libraries  # For file verification
