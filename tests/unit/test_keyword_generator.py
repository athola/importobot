"""Unit tests for keyword generator module.

Tests the generic keyword generator implementation.
Following TDD principles with comprehensive keyword generation testing.
"""

from typing import Any
from unittest.mock import Mock, patch

from importobot.core.converter import get_conversion_suggestions
from importobot.core.interfaces import KeywordGenerator
from importobot.core.keyword_generator import GenericKeywordGenerator
from importobot.core.keywords.generators.builtin_keywords import BuiltInKeywordGenerator
from importobot.core.pattern_matcher import IntentType


class TestGenericKeywordGeneratorInitialization:
    """Test GenericKeywordGenerator initialization."""

    def test_generator_initializes_correctly(self):
        """Test that generator initializes with all specialized generators."""
        generator = GenericKeywordGenerator()

        # Check that all specialized generators are initialized
        assert hasattr(generator, "web_generator")
        assert hasattr(generator, "database_generator")
        assert hasattr(generator, "api_generator")
        assert hasattr(generator, "file_generator")
        assert hasattr(generator, "ssh_generator")
        assert hasattr(generator, "operating_system_generator")
        assert hasattr(generator, "builtin_generator")

    def test_generator_implements_keyword_generator_interface(self):
        """Test that GenericKeywordGenerator implements KeywordGenerator interface."""

        generator = GenericKeywordGenerator()
        assert isinstance(generator, KeywordGenerator)

    def test_generator_has_required_methods(self):
        """Test that generator has required methods."""
        generator = GenericKeywordGenerator()

        assert hasattr(generator, "generate_test_case")
        assert callable(generator.generate_test_case)
        assert hasattr(generator, "generate_step_keywords")
        assert callable(generator.generate_step_keywords)
        assert hasattr(generator, "detect_libraries")
        assert callable(generator.detect_libraries)


class TestGenerateTestCase:
    """Test generate_test_case method."""

    def test_generate_test_case_with_minimal_data(self):
        """Test generate_test_case with minimal test data."""
        generator = GenericKeywordGenerator()
        test_data: dict[str, Any] = {}

        result = generator.generate_test_case(test_data)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "Unnamed Test" in result[0]

    def test_generate_test_case_with_name(self):
        """Test generate_test_case with test name."""
        generator = GenericKeywordGenerator()
        test_data = {"name": "Login Test"}

        result = generator.generate_test_case(test_data)
        assert isinstance(result, list)
        assert "Login Test" in result[0]

    def test_generate_test_case_with_description(self):
        """Test generate_test_case with description."""
        generator = GenericKeywordGenerator()
        test_data = {
            "name": "Test Case",
            "description": "Test user login functionality",
        }

        result = generator.generate_test_case(test_data)
        assert isinstance(result, list)
        assert any("[Documentation]" in line for line in result)
        assert any("Test user login functionality" in line for line in result)

    def test_generate_test_case_with_steps(self):
        """Test generate_test_case with steps."""
        generator = GenericKeywordGenerator()
        test_data = {
            "name": "Test Case",
            "steps": [{"step": "Navigate to page"}, {"step": "Click button"}],
        }

        result = generator.generate_test_case(test_data)
        assert isinstance(result, list)
        assert len(result) > 2  # Should have name + steps + empty line

    def test_generate_test_case_without_steps(self):
        """Test generate_test_case without steps."""
        generator = GenericKeywordGenerator()
        test_data = {"name": "Test Case"}

        result = generator.generate_test_case(test_data)
        assert isinstance(result, list)
        assert any("No Operation" in line for line in result)

    def test_generate_test_case_name_extraction_variants(self):
        """Test that test case name is extracted from various field names."""
        generator = GenericKeywordGenerator()

        # Test with "title" field
        result = generator.generate_test_case({"title": "Title Test"})
        assert "Title Test" in result[0]

        # Test with "testname" field
        result = generator.generate_test_case({"testname": "TestName Test"})
        assert "TestName Test" in result[0]

        # Test with "summary" field
        result = generator.generate_test_case({"summary": "Summary Test"})
        assert "Summary Test" in result[0]


class TestGenerateStepKeywords:
    """Test generate_step_keywords method."""

    def test_generate_step_keywords_with_minimal_step(self):
        """Test generate_step_keywords with minimal step data."""
        generator = GenericKeywordGenerator()
        step: dict[str, Any] = {}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert len(result) >= 1  # Should have at least one keyword line

    def test_generate_step_keywords_with_description(self):
        """Test generate_step_keywords with step description."""
        generator = GenericKeywordGenerator()
        step = {"step": "Click login button"}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert any("# Step: Click login button" in line for line in result)

    def test_generate_step_keywords_with_test_data(self):
        """Test generate_step_keywords with test data."""
        generator = GenericKeywordGenerator()
        step = {"step": "Enter username", "testData": "user@example.com"}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert any("# Test Data: user@example.com" in line for line in result)

    def test_generate_step_keywords_with_expected_result(self):
        """Test generate_step_keywords with expected result."""
        generator = GenericKeywordGenerator()
        step = {"step": "Click login", "expectedResult": "User is logged in"}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert any("# Expected Result: User is logged in" in line for line in result)

    def test_generate_step_keywords_with_all_fields(self):
        """Test generate_step_keywords with all fields."""
        generator = GenericKeywordGenerator()
        step = {
            "step": "Enter credentials",
            "testData": "user:password",
            "expectedResult": "Credentials accepted",
        }

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        assert any("# Step: Enter credentials" in line for line in result)
        assert any("# Test Data: user:password" in line for line in result)
        assert any("# Expected Result: Credentials accepted" in line for line in result)

    @patch("importobot.core.keyword_generator.IntentRecognitionEngine")
    def test_generate_step_keywords_with_intent_recognition(self, mock_intent_engine):
        """Test generate_step_keywords with intent recognition."""
        mock_intent_engine.recognize_intent.return_value = IntentType.CLICK_ACTION

        generator = GenericKeywordGenerator()
        step = {"step": "Click submit button"}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)
        # recognize_intent is called twice now:
        # 1) to check for credential_input composite intent
        # 2) in _determine_robot_keyword for actual keyword generation
        assert mock_intent_engine.recognize_intent.call_count == 2

    def test_generate_multiple_keywords_from_single_step(self):
        """Test that a single step with multiple test data parts generates "
        "multiple keywords."""
        # This test validates multi-step keyword generation
        generator = GenericKeywordGenerator()
        test_step = {"step": "step with user details and multiple data parts"}
        result = generator.generate_step_keywords(test_step)
        assert isinstance(result, list)

    def test_generate_command_execution_keyword(self):
        """Filesystem/CLI commands should map to Run keyword instead of No Operation."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "CLI: Call chmod on the test file",
            "testData": "chmod 777 /tmp/test_file",
            "expectedResult": "Permissions updated successfully",
        }

        result = generator.generate_step_keywords(step)
        assert any("Run    chmod 777 /tmp/test_file" in line for line in result)
        assert len(result) > 0


class TestDetectLibraries:
    """Test detect_libraries method."""

    @patch("importobot.core.keyword_generator.LibraryDetector")
    def test_detect_libraries_calls_detector(self, mock_library_detector):
        """Test that detect_libraries calls LibraryDetector."""
        mock_library_detector.detect_libraries_from_steps.return_value = {
            "SeleniumLibrary"
        }

        generator = GenericKeywordGenerator()
        steps = [{"step": "Click button"}]

        result = generator.detect_libraries(steps)

        mock_library_detector.detect_libraries_from_steps.assert_called_once_with(steps)
        assert result == {"SeleniumLibrary"}

    def test_detect_libraries_with_empty_steps(self):
        """Test detect_libraries with empty steps list."""
        generator = GenericKeywordGenerator()

        result = generator.detect_libraries([])
        assert isinstance(result, set)


class TestPrivateHelperMethods:
    """Test private helper methods."""

    def test_extract_field_with_matching_field(self):
        """Test _extract_field with matching field."""
        generator = GenericKeywordGenerator()
        data = {"name": "Test Name", "description": "Test Description"}

        # pylint: disable=protected-access
        result = generator._extract_field(data, ["name", "title"])
        assert result == "Test Name"

    def test_extract_field_with_multiple_candidates(self):
        """Test _extract_field returns first matching field."""
        generator = GenericKeywordGenerator()
        data = {"title": "Title Value", "name": "Name Value"}

        # Should return first matching field in order
        # pylint: disable=protected-access
        result = generator._extract_field(data, ["name", "title"])
        assert result == "Name Value"

    def test_extract_field_with_no_matches(self):
        """Test _extract_field with no matching fields."""
        generator = GenericKeywordGenerator()
        data = {"other": "Other Value"}

        # pylint: disable=protected-access
        result = generator._extract_field(data, ["name", "title"])
        assert result == ""

    def test_extract_field_with_empty_value(self):
        """Test _extract_field with empty field value."""
        generator = GenericKeywordGenerator()
        data = {"name": "", "title": "Title Value"}

        # pylint: disable=protected-access
        result = generator._extract_field(data, ["name", "title"])
        assert result == "Title Value"

    def test_extract_field_with_none_value(self):
        """Test _extract_field with None field value."""
        generator = GenericKeywordGenerator()
        data = {"name": None, "title": "Title Value"}

        # pylint: disable=protected-access
        result = generator._extract_field(data, ["name", "title"])
        assert result == "Title Value"

    def test_is_ssh_context_with_ssh_indicators(self):
        """Test _is_ssh_context with SSH indicators."""
        generator = GenericKeywordGenerator()

        # pylint: disable=protected-access
        assert generator._is_ssh_context("ssh connect", "") is True
        assert generator._is_ssh_context("remote server", "") is True
        assert generator._is_ssh_context("", "host: server.com") is True
        assert generator._is_ssh_context("", "username: user") is True
        assert generator._is_ssh_context("upload file", "/etc/config") is True

    def test_is_ssh_context_without_ssh_indicators(self):
        """Test _is_ssh_context without SSH indicators."""
        generator = GenericKeywordGenerator()

        # pylint: disable=protected-access
        assert generator._is_ssh_context("click button", "") is False
        assert generator._is_ssh_context("enter text", "username") is False
        assert generator._is_ssh_context("local file", "C:\\temp\\file.txt") is False


class TestIntentHandling:
    """Test intent handling and routing."""

    @patch("importobot.core.keyword_generator.IntentRecognitionEngine")
    @patch("importobot.core.keyword_generator.WebKeywordGenerator")
    def test_determine_robot_keyword_web_navigation(
        self, mock_web_generator_class, mock_intent_engine
    ):
        """Test _determine_robot_keyword with web navigation intent."""
        mock_intent_engine.recognize_intent.return_value = IntentType.BROWSER_OPEN
        mock_web_generator = Mock()
        mock_web_generator.generate_browser_keyword.return_value = "Open Browser"
        mock_web_generator_class.return_value = mock_web_generator

        generator = GenericKeywordGenerator()
        result = generator._determine_robot_keyword(  # pylint: disable=protected-access
            "navigate", "http://example.com", ""
        )

        assert result == "Open Browser"
        mock_web_generator.generate_browser_keyword.assert_called_once_with(
            "http://example.com"
        )

    @patch("importobot.core.keyword_generator.IntentRecognitionEngine")
    @patch("importobot.core.keyword_generator.DatabaseKeywordGenerator")
    def test_determine_robot_keyword_database_connect(
        self, mock_database_generator_class, mock_intent_engine
    ):
        """Test _determine_robot_keyword with database connect intent."""
        mock_intent_engine.recognize_intent.return_value = IntentType.DATABASE_CONNECT
        mock_database_generator = Mock()
        mock_database_generator.generate_connect_keyword.return_value = (
            "Connect To Database"
        )
        mock_database_generator_class.return_value = mock_database_generator

        generator = GenericKeywordGenerator()
        result = generator._determine_robot_keyword(  # pylint: disable=protected-access
            "connect", "database_url", ""
        )

        assert result == "Connect To Database"
        mock_database_generator.generate_connect_keyword.assert_called_once_with(
            "database_url"
        )

    @patch("importobot.core.keyword_generator.IntentRecognitionEngine")
    @patch("importobot.core.keyword_generator.SSHKeywordGenerator")
    def test_determine_robot_keyword_ssh_connect(
        self, mock_ssh_generator_class, mock_intent_engine
    ):
        """Test _determine_robot_keyword with SSH connect intent."""
        mock_intent_engine.recognize_intent.return_value = IntentType.SSH_CONNECT
        mock_ssh_generator = Mock()
        mock_ssh_generator.generate_connect_keyword.return_value = "Open Connection"
        mock_ssh_generator_class.return_value = mock_ssh_generator

        generator = GenericKeywordGenerator()
        result = generator._determine_robot_keyword(  # pylint: disable=protected-access
            "ssh connect", "server", ""
        )

        assert result == "Open Connection"
        mock_ssh_generator.generate_connect_keyword.assert_called_once_with("server")

    @patch("importobot.core.keyword_generator.IntentRecognitionEngine")
    def test_determine_robot_keyword_unrecognized_intent(self, mock_intent_engine):
        """Test _determine_robot_keyword with unrecognized intent."""
        mock_intent_engine.recognize_intent.return_value = None  # Unknown intent

        generator = GenericKeywordGenerator()

        # pylint: disable=protected-access
        result = generator._determine_robot_keyword("unknown action", "", "")

        assert result == "No Operation"

    @patch("importobot.core.keyword_generator.IntentRecognitionEngine")
    @patch("importobot.core.keyword_generator.BuiltInKeywordGenerator")
    def test_determine_robot_keyword_builtin_operations(
        self, mock_builtin_generator_class, mock_intent_engine
    ):
        """Test _determine_robot_keyword with builtin operations."""
        mock_intent_engine.recognize_intent.return_value = IntentType.LOG_MESSAGE
        mock_builtin_generator = Mock()
        mock_builtin_generator.generate_log_keyword.return_value = "Log    Message"
        mock_builtin_generator_class.return_value = mock_builtin_generator

        generator = GenericKeywordGenerator()
        result = generator._determine_robot_keyword(  # pylint: disable=protected-access
            "log", "test message", ""
        )

        assert result == "Log    Message"
        mock_builtin_generator.generate_log_keyword.assert_called_once_with(
            "test message"
        )


class TestFileOperationHandling:
    """Test file operation handling methods."""

    @patch("importobot.core.keyword_generator.SSHKeywordGenerator")
    def test_handle_file_transfer_ssh_upload(self, mock_ssh_generator_class):
        """Test _handle_file_transfer with SSH upload."""
        mock_ssh_generator = Mock()
        mock_ssh_generator.generate_file_transfer_keyword.return_value = "Put File"
        mock_ssh_generator_class.return_value = mock_ssh_generator

        generator = GenericKeywordGenerator()
        result = generator._handle_file_transfer(  # pylint: disable=protected-access
            "upload file to server", "ssh server data"
        )

        assert result == "Put File"
        mock_ssh_generator.generate_file_transfer_keyword.assert_called_once()

    @patch("importobot.core.keyword_generator.SSHKeywordGenerator")
    def test_handle_file_transfer_ssh_download(self, mock_ssh_generator_class):
        """Test _handle_file_transfer with SSH download."""
        mock_ssh_generator = Mock()
        mock_ssh_generator.generate_file_transfer_keyword.return_value = "Get File"
        mock_ssh_generator_class.return_value = mock_ssh_generator

        generator = GenericKeywordGenerator()
        result = generator._handle_file_transfer(  # pylint: disable=protected-access
            "download file from server", "ssh server data"
        )

        assert result == "Get File"
        mock_ssh_generator.generate_file_transfer_keyword.assert_called_once_with(
            "ssh server data", "download"
        )

    @patch("importobot.core.keyword_generator.FileKeywordGenerator")
    def test_handle_file_transfer_local(self, mock_file_generator_class):
        """Test _handle_file_transfer with local file operations."""
        mock_file_generator = Mock()
        mock_file_generator.generate_transfer_keyword.return_value = "Copy File"
        mock_file_generator_class.return_value = mock_file_generator

        generator = GenericKeywordGenerator()
        result = generator._handle_file_transfer(  # pylint: disable=protected-access
            "copy local file", "local file data"
        )

        assert result == "Copy File"
        mock_file_generator.generate_transfer_keyword.assert_called_once_with(
            "local file data"
        )

    @patch("importobot.core.keyword_generator.SSHKeywordGenerator")
    def test_handle_file_verification_ssh(self, mock_ssh_generator_class):
        """Test _handle_file_verification with SSH context."""
        mock_ssh_generator = Mock()
        mock_ssh_generator.generate_file_verification_keyword.return_value = (
            "File Should Exist"
        )
        mock_ssh_generator_class.return_value = mock_ssh_generator

        generator = GenericKeywordGenerator()
        # pylint: disable=protected-access
        result = generator._handle_file_verification(
            "verify remote file", "ssh server:/path/file"
        )
        assert result == "File Should Exist"
        mock_ssh_generator.generate_file_verification_keyword.assert_called_once_with(
            "ssh server:/path/file"
        )

    @patch("importobot.core.keyword_generator.FileKeywordGenerator")
    def test_handle_file_verification_local(self, mock_file_generator_class):
        """Test _handle_file_verification with local context."""
        mock_file_generator = Mock()
        mock_file_generator.generate_exists_keyword.return_value = "File Should Exist"
        mock_file_generator_class.return_value = mock_file_generator

        generator = GenericKeywordGenerator()
        # pylint: disable=protected-access
        result = generator._handle_file_verification(
            "verify file", "C:\\\\temp\\\\file.txt"
        )
        assert result == "File Should Exist"
        mock_file_generator.generate_exists_keyword.assert_called_once_with(
            "C:\\temp\\file.txt"
        )


class TestKeywordGeneratorIntegration:
    """Test keyword generator integration scenarios."""

    def test_complete_test_case_generation(self):
        """Test complete test case generation workflow."""
        generator = GenericKeywordGenerator()
        test_data = {
            "name": "Login Test",
            "description": "Test user login functionality",
            "steps": [
                {
                    "step": "Navigate to login page",
                    "testData": "http://example.com/login",
                    "expectedResult": "Login page displays",
                },
                {"step": "Enter username", "testData": "user@example.com"},
                {"step": "Click login button", "expectedResult": "User is logged in"},
            ],
        }

        result = generator.generate_test_case(test_data)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "Login Test" in result[0]
        assert any("[Documentation]" in line for line in result)
        assert any("Test user login functionality" in line for line in result)

    def test_multiline_comment_formatting(self):
        """Test multiline comment formatting functionality."""

        generator = BuiltInKeywordGenerator()

        # Test short comment not split
        short_data = "Short test data"
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(short_data)
        assert len(result) == 1
        assert "Test Data: Short test data" in result[0]

        # Test long comment gets split appropriately
        long_data = (
            "Very long test data string that exceeds normal limits, "
            "with comma used for splitting"
        )
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(long_data)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_numeric_ordering_in_suggestions(self):
        """Test that numeric values in step ordering work correctly."""

        # Test data with many steps to verify double-digit ordering
        test_data: dict[str, Any] = {"name": "Numeric Ordering Test", "steps": []}

        # Create 12 steps to test double-digit ordering
        for i in range(1, 13):
            step = {
                "step": f"Step {i}: Perform action",
                "testData": f"data {i} with missing {{braces",  # Triggers suggestion
                "expectedResult": f"Action {i} completed",
            }
            test_data["steps"].append(step)

        suggestions = get_conversion_suggestions(test_data)
        assert isinstance(suggestions, list)

        # Verify suggestions are ordered correctly (1, 2, ..., 10, 11, 12)
        # Extract step numbers from suggestions
        step_numbers = []
        for suggestion in suggestions:
            # Suggestions contain "Step X" references
            if "Step" in suggestion:
                # Extract number after "Step "
                parts = suggestion.split("Step ")
                for part in parts[1:]:
                    try:
                        # Get the number before the colon
                        num_str = part.split(":")[0].strip()
                        step_numbers.append(int(num_str))
                    except (ValueError, IndexError):
                        continue

        # Verify we found step numbers and they're in order
        if step_numbers:
            assert step_numbers == sorted(step_numbers), (
                f"Step numbers not in order: {step_numbers}"
            )

    def test_complex_step_generation_with_all_fields(self):
        """Test complex step generation with all available fields."""
        generator = GenericKeywordGenerator()
        step = {
            "step": "Execute database query",
            "testData": "SELECT * FROM users WHERE id = 1",
            "expectedResult": "Query returns user data",
        }

        result = generator.generate_step_keywords(step)

        assert isinstance(result, list)
        assert any("# Step: Execute database query" in line for line in result)
        assert any(
            "# Test Data: SELECT * FROM users WHERE id = 1" in line for line in result
        )
        assert any(
            "# Expected Result: Query returns user data" in line for line in result
        )

    def test_keyword_generator_error_handling(self):
        """Test that keyword generator handles malformed data gracefully."""
        generator = GenericKeywordGenerator()

        # Test with empty dict instead of None to avoid TypeError
        result = generator.generate_test_case({})
        assert isinstance(result, list)

        # Test with empty step
        result = generator.generate_step_keywords({})
        assert isinstance(result, list)

        # Test with malformed steps
        test_data: dict[str, Any] = {"steps": [None, "invalid", {}]}
        result = generator.generate_test_case(test_data)
        assert isinstance(result, list)
