"""Unit tests for core constants module.

Tests the constant definitions used across importobot core modules.
Following TDD principles with comprehensive constant validation.
"""

from importobot.core.constants import (
    EXPECTED_RESULT_FIELD_NAMES,
    ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR,
    ROBOT_FRAMEWORK_INDENT,
    STEP_DESCRIPTION_FIELD_NAMES,
    TEST_DATA_FIELD_NAMES,
)


class TestFieldNameConstants:
    """Test field name constant definitions."""

    def test_expected_result_field_names_contains_standard_variations(self):
        """Test that expected result field names include standard variations."""
        # Test that key variations are present without duplicating the list
        assert "expectedResult" in EXPECTED_RESULT_FIELD_NAMES
        assert "expected_result" in EXPECTED_RESULT_FIELD_NAMES
        assert "expected" in EXPECTED_RESULT_FIELD_NAMES
        assert "result" in EXPECTED_RESULT_FIELD_NAMES

    def test_expected_result_field_names_is_list(self):
        """Test that expected result field names is a list."""
        assert isinstance(EXPECTED_RESULT_FIELD_NAMES, list)

    def test_expected_result_field_names_contains_strings(self):
        """Test that all expected result field names are strings."""
        for field_name in EXPECTED_RESULT_FIELD_NAMES:
            assert isinstance(field_name, str)
            assert len(field_name) > 0

    def test_test_data_field_names_contains_standard_variations(self):
        """Test that test data field names include standard variations."""
        # Test that key variations are present without duplicating the list
        assert "testData" in TEST_DATA_FIELD_NAMES
        assert "test_data" in TEST_DATA_FIELD_NAMES
        assert "data" in TEST_DATA_FIELD_NAMES
        assert "input" in TEST_DATA_FIELD_NAMES

    def test_test_data_field_names_is_list(self):
        """Test that test data field names is a list."""
        assert isinstance(TEST_DATA_FIELD_NAMES, list)

    def test_test_data_field_names_contains_strings(self):
        """Test that all test data field names are strings."""
        for field_name in TEST_DATA_FIELD_NAMES:
            assert isinstance(field_name, str)
            assert len(field_name) > 0

    def test_step_description_field_names_contains_standard_variations(self):
        """Test that step description field names include standard variations."""
        # Test that key variations are present without duplicating the list
        assert "step" in STEP_DESCRIPTION_FIELD_NAMES
        assert "description" in STEP_DESCRIPTION_FIELD_NAMES
        assert "action" in STEP_DESCRIPTION_FIELD_NAMES
        assert "stepDescription" in STEP_DESCRIPTION_FIELD_NAMES
        assert "step_description" in STEP_DESCRIPTION_FIELD_NAMES

    def test_step_description_field_names_is_list(self):
        """Test that step description field names is a list."""
        assert isinstance(STEP_DESCRIPTION_FIELD_NAMES, list)

    def test_step_description_field_names_contains_strings(self):
        """Test that all step description field names are strings."""
        for field_name in STEP_DESCRIPTION_FIELD_NAMES:
            assert isinstance(field_name, str)
            assert len(field_name) > 0


class TestRobotFrameworkConstants:
    """Test Robot Framework formatting constants."""

    def test_robot_framework_argument_separator_is_four_spaces(self):
        """Test that argument separator is 4 spaces."""
        assert ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR == "    "
        assert len(ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR) == 4

    def test_robot_framework_indent_is_four_spaces(self):
        """Test that indent is 4 spaces."""
        assert ROBOT_FRAMEWORK_INDENT == "    "
        assert len(ROBOT_FRAMEWORK_INDENT) == 4

    def test_robot_framework_constants_are_strings(self):
        """Test that Robot Framework constants are strings."""
        assert isinstance(ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR, str)
        assert isinstance(ROBOT_FRAMEWORK_INDENT, str)

    def test_robot_framework_constants_contain_only_spaces(self):
        """Test that Robot Framework constants contain only spaces."""
        assert ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR.strip() == ""
        assert ROBOT_FRAMEWORK_INDENT.strip() == ""


class TestConstantIntegration:
    """Test constant integration and usage patterns."""

    def test_all_field_name_lists_are_non_empty(self):
        """Test that all field name constant lists are non-empty."""
        assert len(EXPECTED_RESULT_FIELD_NAMES) > 0
        assert len(TEST_DATA_FIELD_NAMES) > 0
        assert len(STEP_DESCRIPTION_FIELD_NAMES) > 0

    def test_field_name_constants_have_no_duplicates(self):
        """Test that field name constants contain no duplicates."""
        assert len(EXPECTED_RESULT_FIELD_NAMES) == len(set(EXPECTED_RESULT_FIELD_NAMES))
        assert len(TEST_DATA_FIELD_NAMES) == len(set(TEST_DATA_FIELD_NAMES))
        assert len(STEP_DESCRIPTION_FIELD_NAMES) == len(
            set(STEP_DESCRIPTION_FIELD_NAMES)
        )

    def test_field_name_constants_provide_case_variations(self):
        """Test that field name constants provide both camel and snake case "
        "variations."""
        # Check that we have both camelCase and snake_case variations

        # Expected results should have both camelCase and snake_case
        has_camel_case = any("Result" in name for name in EXPECTED_RESULT_FIELD_NAMES)
        has_snake_case = any("_result" in name for name in EXPECTED_RESULT_FIELD_NAMES)
        assert has_camel_case and has_snake_case

        # Test data should have both camelCase and snake_case
        has_camel_case = any("Data" in name for name in TEST_DATA_FIELD_NAMES)
        has_snake_case = any("_data" in name for name in TEST_DATA_FIELD_NAMES)
        assert has_camel_case and has_snake_case

        # Step description should have both camelCase and snake_case
        has_camel_case = any(
            "Description" in name for name in STEP_DESCRIPTION_FIELD_NAMES
        )
        has_snake_case = any(
            "_description" in name for name in STEP_DESCRIPTION_FIELD_NAMES
        )
        assert has_camel_case and has_snake_case
