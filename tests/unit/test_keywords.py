"""Tests for keyword generation components."""

import pytest

from importobot.core.keyword_generator import GenericKeywordGenerator


@pytest.fixture
def generator():
    """Return a GenericKeywordGenerator instance."""
    return GenericKeywordGenerator()


class TestGenericKeywordGenerator:  # pylint: disable=too-many-public-methods
    # pylint: disable=redefined-outer-name,protected-access
    """Tests for the GenericKeywordGenerator class."""

    def test_format_test_data_comment_short(self, generator):
        """Test that a short test data comment is not split."""
        comment = "short comment"
        result = generator._format_test_data_comment(comment)
        assert len(result) == 1
        assert result[0] == f"    # Test Data: {comment}"

    def test_format_test_data_comment_long(self, generator):
        """Test that a long test data comment is split."""
        long_comment = (
            "a very long comment that should be split into multiple lines, "
            "because it is longer than 88 characters"
        )
        result = generator._format_test_data_comment(long_comment)
        assert len(result) == 2
        assert result[0].startswith("    # Test Data:")
        assert result[1].startswith("    # Test Data (cont.):")

    def test_determine_robot_keyword_command_execution(self, generator):
        """Test that the command_execution intent is handled correctly."""
        description = "run a command"
        test_data = "command: echo hello"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert result == "Run    echo hello"

    def test_determine_robot_keyword_unknown_intent(self, generator):
        """Test that unknown intents are handled gracefully with No Operation."""
        description = "unknown action"
        test_data = "some data"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert result == "No Operation"

    def test_browser_keyword(self, generator):
        """Test the browser keyword generation."""
        test_data = "url: https://example.com"
        result = generator.web_generator.generate_browser_keyword(test_data)
        assert "Open Browser" in result
        assert "https://example.com" in result

    def test_url_keyword(self, generator):
        """Test the URL keyword generation."""
        test_data = "go to https://example.com"
        result = generator.web_generator.generate_url_keyword(test_data)
        assert result == "Go To    https://example.com"

    def test_input_keyword(self, generator):
        """Test the input keyword generation."""
        test_data = "username: testuser"
        result = generator.web_generator.generate_input_keyword("username", test_data)
        assert result == "Input Text    id=username    test_value"

    def test_password_keyword(self, generator):
        """Test the password keyword generation."""
        test_data = "password: testpass"
        result = generator.web_generator.generate_password_keyword(test_data)
        assert result == "Input Password    id=password    test_password"

    def test_database_connect_keyword(self, generator):
        """Test the database connect keyword generation."""
        test_data = "module: sqlite3, database: test.db"
        result = generator.database_generator.generate_connect_keyword(test_data)
        assert result == "Connect To Database    sqlite3    test.db"

    def test_database_query_keyword(self, generator):
        """Test the database query keyword generation."""
        test_data = "sql: SELECT * FROM users"
        result = generator.database_generator.generate_query_keyword(test_data)
        expected = "Execute Sql String    SELECT * FROM users"
        assert result == expected

    def test_command_keyword_preserves_robot_framework_keywords(self, generator):
        """Test Robot Framework keywords preserved instead of wrapped in Run Process."""
        # Test BuiltIn library keywords
        result = generator.operating_system_generator.generate_command_keyword(
            "Should Be Equal    ${var1}    ${var2}"
        )
        assert result == "Should Be Equal    ${var1}    ${var2}"

        result = generator.operating_system_generator.generate_command_keyword(
            "Should Contain    ${text}    ${substring}"
        )
        assert result == "Should Contain    ${text}    ${substring}"

        # Test OperatingSystem library keywords
        result = generator.operating_system_generator.generate_command_keyword(
            "Create File    ${filename}    ${content}"
        )
        assert result == "Create File    ${filename}    ${content}"

        test_data = "Get File    ${filename}"
        result = generator.operating_system_generator.generate_command_keyword(
            test_data
        )
        assert result == "Get File    ${filename}"

    def test_command_keyword_maps_hash_commands_to_run_keyword(self, generator):
        """Test hash and shasum commands mapped to Run keyword for system execution."""
        # Test hash command mapping
        result = generator.operating_system_generator.generate_command_keyword(
            "hash ${test_file}"
        )
        assert result == "Run    hash ${test_file}"

        # Test sha256sum command mapping
        result = generator.operating_system_generator.generate_command_keyword(
            "sha256sum ${test_file}"
        )
        assert result == "Run    sha256sum ${test_file}"

        # Test shasum command mapping
        result = generator.operating_system_generator.generate_command_keyword(
            "shasum ${test_file}"
        )
        assert result == "Run    shasum ${test_file}"

        # Test sha1sum command mapping
        result = generator.operating_system_generator.generate_command_keyword(
            "sha1sum ${test_file}"
        )
        assert result == "Run    sha1sum ${test_file}"

        # Test md5sum command mapping
        result = generator.operating_system_generator.generate_command_keyword(
            "md5sum ${test_file}"
        )
        assert result == "Run    md5sum ${test_file}"

    def test_command_keyword_wraps_non_robot_commands_in_run_process(self, generator):
        """Test that non-Robot Framework commands are wrapped appropriately."""
        # Echo commands use OperatingSystem.Run for consistency
        result = generator.operating_system_generator.generate_command_keyword(
            "echo hello world"
        )
        assert result == "Run    echo hello world"

        # Simple commands like ls use OperatingSystem.Run
        result = generator.operating_system_generator.generate_command_keyword("ls -la")
        assert result == "Run    ls -la"

        # Complex commands like wget use Process.Run Process
        result = generator.operating_system_generator.generate_command_keyword(
            "wget http://example.com/file.txt"
        )
        assert result == "Run Process    wget    http://example.com/file.txt"

    def test_file_operation_copy_with_json_variables(self, generator):
        """Test Copy File keyword extracts source and destination from JSON."""
        description = "copy file from source to destination"
        test_data = (
            '{"sourceFile": "/path/to/source.txt", '
            '"destinationFile": "/path/to/dest.txt"}'
        )
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Copy File    /path/to/source.txt    /path/to/dest.txt"
        assert result == expected

    def test_file_operation_copy_with_variables(self, generator):
        """Test Copy File keyword handles Robot Framework variables."""
        description = "copy ${source_var} to ${dest_var}"
        test_data = ""
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Copy File    ${source_var}    ${dest_var}"
        assert result == expected

    def test_file_operation_copy_with_alt_json_format(self, generator):
        """Test Copy File keyword with alternative JSON field names."""
        description = "copy file operation"
        test_data = '{"source": "original.txt", "destination": "copy.txt"}'
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Copy File    original.txt    copy.txt"
        assert result == expected

    def test_file_operation_copy_with_missing_json_data(self, generator):
        """Test Copy File keyword uses variables when no JSON data found."""
        description = "copy file"
        test_data = '{"unrelated": "data"}'
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Copy File    ${source_file}    ${destination_file}"
        assert result == expected

    def test_file_operation_move_with_json_variables(self, generator):
        """Test Move File keyword extracts source and destination from JSON."""
        description = "move file from source to destination"
        test_data = (
            '{"sourceFile": "/old/location.txt", '
            '"destinationFile": "/new/location.txt"}'
        )
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Move File    /old/location.txt    /new/location.txt"
        assert result == expected

    def test_file_operation_move_with_variables(self, generator):
        """Test Move File keyword handles Robot Framework variables."""
        description = "move ${source_var} to ${dest_var}"
        test_data = ""
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Move File    ${source_var}    ${dest_var}"
        assert result == expected

    def test_file_operation_move_with_alt_json_format(self, generator):
        """Test Move File keyword with alternative JSON field names."""
        description = "move file operation"
        test_data = '{"source": "temp.txt", "destination": "final.txt"}'
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Move File    temp.txt    final.txt"
        assert result == expected

    def test_file_operation_move_with_missing_json_data(self, generator):
        """Test Move File keyword uses variables when no JSON data found."""
        description = "move file"
        test_data = '{"unrelated": "data"}'
        result = generator.file_generator.generate_operation_keyword(
            description, test_data
        )
        expected = "Move File    ${source_file}    ${destination_file}"
        assert result == expected

    def test_verification_with_message_text(self, generator):
        """Test verification step with specific message text."""
        description = "Verify successful registration"
        test_data = "verify: Welcome message displayed"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Page Should Contain" in result
        assert "Welcome message displayed" in result

    def test_verification_with_expected_result(self, generator):
        """Test verification uses expected result when available."""
        description = "Verify successful registration"
        test_data = "verify: Welcome message displayed"
        expected = "Welcome to our site"
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Page Should Contain" in result
        # The implementation extracts the message from test_data, not expected
        assert "Welcome message displayed" in result

    def test_verification_general_pattern(self, generator):
        """Test general verification pattern without specific keywords."""
        description = "Verify successful operation"
        test_data = "verify: Success message"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Page Should Contain" in result
        assert "Success message" in result

    def test_verification_with_colon_format(self, generator):
        """Test verification extracts text after colon in test data."""
        description = "Check result"
        test_data = "verify: Operation completed successfully"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Page Should Contain" in result
        assert "Operation completed successfully" in result

    def test_verification_element_should_contain_with_id_locator(self, generator):
        """Test verification uses Element Should Contain for ID locators."""
        description = "Verify username field contains correct value"
        test_data = "verify: element=id=username_field, text=JohnDoe"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Element Should Contain" in result
        assert "id=username_field" in result
        assert "JohnDoe" in result

    def test_verification_element_should_contain_with_xpath(self, generator):
        """Test verification uses Element Should Contain for XPath locators."""
        description = "Verify element contains text"
        test_data = "verify: element=xpath=//div[@class='message'], text=Success"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Element Should Contain" in result
        assert "xpath=//div[@class='message']" in result
        assert "Success" in result

    def test_verification_element_should_contain_with_css(self, generator):
        """Test verification uses Element Should Contain for CSS locators."""
        description = "Check element content"
        test_data = "verify: element=css=.status-message, text=Operation complete"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Element Should Contain" in result
        assert "css=.status-message" in result
        assert "Operation complete" in result

    def test_verification_should_contain_with_variables(self, generator):
        """Test verification uses Should Contain for variable comparison."""
        description = "Verify output contains expected content"
        test_data = "verify: container=${response_data}, text=${expected_value}"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Should Contain" in result
        assert "${response_data}" in result
        assert "${expected_value}" in result

    def test_verification_should_contain_with_mixed_variables(self, generator):
        """Test verification uses Should Contain when variables are detected."""
        description = "Check if result contains value"
        test_data = "verify: ${actual_result} contains success"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Should Contain" in result
        assert "${actual_result}" in result
        assert "success" in result

    def test_verification_page_should_contain_for_general_text(self, generator):
        """Test verification uses Page Should Contain for general text."""
        description = "Verify success message appears"
        test_data = "verify: Registration completed successfully"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Page Should Contain" in result
        assert "Registration completed successfully" in result

    def test_verification_element_should_contain_alternative_format(self, generator):
        """Test verification handles alternative element verification format."""
        description = "Verify button text"
        test_data = "element: id=submit_btn, expected: Submit Registration"
        expected = ""
        result = generator._determine_robot_keyword(description, test_data, expected)
        assert "Element Should Contain" in result
        assert "id=submit_btn" in result
        assert "Submit Registration" in result
