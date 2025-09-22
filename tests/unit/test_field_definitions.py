"""Tests for field definitions and library detection."""

from importobot.core.field_definitions import (
    LIBRARY_KEYWORDS,
    STEP_ACTION_FIELDS,
    STEP_DATA_FIELDS,
    STEP_EXPECTED_FIELDS,
    TEST_DESCRIPTION_FIELDS,
    TEST_INDICATORS,
    TEST_NAME_FIELDS,
    TEST_STEP_FIELDS,
    TEST_TAG_FIELDS,
    FieldGroup,
    detect_libraries_from_text,
    get_field_value,
    has_field,
    is_test_case,
)
from tests.shared_test_data import LIBRARY_DETECTION_TEST_CASES


class TestFieldGroup:
    """Test FieldGroup class."""

    def test_field_group_creation(self):
        """Test creating a FieldGroup."""
        group = FieldGroup(
            fields=("field1", "field2", "field3"), description="Test group"
        )

        assert group.fields == ("field1", "field2", "field3")
        assert group.description == "Test group"

    def test_field_group_contains_case_insensitive(self):
        """Test __contains__ method with case insensitivity."""
        group = FieldGroup(fields=("Name", "Title"), description="Name fields")

        assert "name" in group
        assert "NAME" in group
        assert "title" in group
        assert "TITLE" in group
        assert "other" not in group

    def test_field_group_contains_empty_fields(self):
        """Test __contains__ with empty fields."""
        group = FieldGroup(fields=(), description="Empty group")

        assert "any" not in group

    def test_find_first_no_matches(self):
        """Test find_first with no matching fields."""
        group = FieldGroup(fields=("name", "title"), description="Name fields")
        data = {"other": "value"}

        field, value = group.find_first(data)
        assert field is None
        assert value is None

    def test_find_first_empty_value(self):
        """Test find_first with matching field but empty value."""
        group = FieldGroup(fields=("name", "title"), description="Name fields")
        data = {"name": "", "title": "Test"}

        field, value = group.find_first(data)
        assert field == "title"
        assert value == "Test"

    def test_find_first_falsy_values_ignored(self):
        """Test find_first ignores falsy values."""
        group = FieldGroup(
            fields=("name", "title", "summary"), description="Name fields"
        )
        data = {"name": 0, "title": False, "summary": ""}

        field, value = group.find_first(data)
        assert field is None
        assert value is None

    def test_find_first_multiple_matches(self):
        """Test find_first returns first matching field."""
        group = FieldGroup(
            fields=("name", "title", "summary"), description="Name fields"
        )
        data = {
            "title": "Title Value",
            "name": "Name Value",
            "summary": "Summary Value",
        }

        field, value = group.find_first(data)
        assert field == "name"  # First in fields tuple
        assert value == "Name Value"

    def test_find_first_partial_match(self):
        """Test find_first with partial field name matches."""
        group = FieldGroup(fields=("name", "title"), description="Name fields")
        data = {"name": "test", "nam": "partial"}

        field, value = group.find_first(data)
        assert field == "name"
        assert value == "test"


class TestPredefinedFieldGroups:
    """Test predefined field group constants."""

    def test_test_name_fields(self):
        """Test TEST_NAME_FIELDS definition."""
        assert "name" in TEST_NAME_FIELDS
        assert "title" in TEST_NAME_FIELDS
        assert "testname" in TEST_NAME_FIELDS
        assert "summary" in TEST_NAME_FIELDS
        assert TEST_NAME_FIELDS.description == "Test case name or title"

    def test_test_description_fields(self):
        """Test TEST_DESCRIPTION_FIELDS definition."""
        assert "description" in TEST_DESCRIPTION_FIELDS
        assert "objective" in TEST_DESCRIPTION_FIELDS
        assert "documentation" in TEST_DESCRIPTION_FIELDS
        assert (
            TEST_DESCRIPTION_FIELDS.description
            == "Test case description or documentation"
        )

    def test_test_tag_fields(self):
        """Test TEST_TAG_FIELDS definition."""
        assert "tags" in TEST_TAG_FIELDS
        assert "labels" in TEST_TAG_FIELDS
        assert "categories" in TEST_TAG_FIELDS
        assert "priority" in TEST_TAG_FIELDS
        assert TEST_TAG_FIELDS.description == "Test categorization and tagging"

    def test_test_step_fields(self):
        """Test TEST_STEP_FIELDS definition."""
        assert "steps" in TEST_STEP_FIELDS
        assert "teststeps" in TEST_STEP_FIELDS
        assert "actions" in TEST_STEP_FIELDS
        assert TEST_STEP_FIELDS.description == "Test execution steps"

    def test_step_action_fields(self):
        """Test STEP_ACTION_FIELDS definition."""
        assert "step" in STEP_ACTION_FIELDS
        assert "description" in STEP_ACTION_FIELDS
        assert "action" in STEP_ACTION_FIELDS
        assert "instruction" in STEP_ACTION_FIELDS
        assert STEP_ACTION_FIELDS.description == "Step action or instruction"

    def test_step_data_fields(self):
        """Test STEP_DATA_FIELDS uses TEST_DATA_FIELD_NAMES."""
        # Should contain standard test data field names
        assert len(STEP_DATA_FIELDS.fields) > 0
        assert STEP_DATA_FIELDS.description == "Step input data"

    def test_step_expected_fields(self):
        """Test STEP_EXPECTED_FIELDS uses EXPECTED_RESULT_FIELD_NAMES."""
        # Should contain standard expected result field names
        assert len(STEP_EXPECTED_FIELDS.fields) > 0
        assert STEP_EXPECTED_FIELDS.description == "Step expected result"


class TestTestIndicators:
    """Test TEST_INDICATORS constant."""

    def test_test_indicators_content(self):
        """Test TEST_INDICATORS contains expected field names."""
        # Test key indicators are present without duplicating the complete set
        assert "name" in TEST_INDICATORS
        assert "description" in TEST_INDICATORS
        assert "steps" in TEST_INDICATORS
        assert "testscript" in TEST_INDICATORS
        assert "objective" in TEST_INDICATORS
        assert "summary" in TEST_INDICATORS
        assert "title" in TEST_INDICATORS
        assert "testname" in TEST_INDICATORS

        # Verify it's a frozenset with expected length
        assert isinstance(TEST_INDICATORS, frozenset)
        assert len(TEST_INDICATORS) >= 8  # At least these 8 indicators

    def test_test_indicators_case_sensitivity(self):
        """Test TEST_INDICATORS is case sensitive."""
        # Should not contain lowercase versions
        assert "Name" not in TEST_INDICATORS
        assert "NAME" not in TEST_INDICATORS

    def test_test_indicators_is_frozenset(self):
        """Test TEST_INDICATORS is a frozenset."""
        assert isinstance(TEST_INDICATORS, frozenset)


class TestLibraryDetectionKeywords:
    """Test LIBRARY_KEYWORDS constant."""

    def test_library_keywords_structure(self):
        """Test LIBRARY_KEYWORDS has expected structure."""
        assert isinstance(LIBRARY_KEYWORDS, dict)

        # Check that each library has a frozenset of keywords
        for library, keywords in LIBRARY_KEYWORDS.items():
            assert isinstance(library, str)
            assert isinstance(keywords, frozenset)
            assert len(keywords) > 0

    def test_common_libraries_present(self):
        """Test that common libraries are defined."""
        expected_libraries = [
            "SeleniumLibrary",
            "SSHLibrary",
            "Process",
            "OperatingSystem",
            "DatabaseLibrary",
            "RequestsLibrary",
            "Collections",
            "String",
        ]

        for library in expected_libraries:
            assert library in LIBRARY_KEYWORDS

    def test_selenium_library_keywords(self):
        """Test SeleniumLibrary keywords."""
        selenium_keywords = LIBRARY_KEYWORDS["SeleniumLibrary"]
        expected_keywords = {"browser", "navigate", "click", "input", "selenium"}

        assert expected_keywords.issubset(selenium_keywords)

    def test_ssh_library_keywords(self):
        """Test SSHLibrary keywords."""
        ssh_keywords = LIBRARY_KEYWORDS["SSHLibrary"]
        expected_keywords = {"ssh", "remote", "connection", "host"}

        assert expected_keywords.issubset(ssh_keywords)

    def test_database_library_keywords(self):
        """Test DatabaseLibrary keywords."""
        db_keywords = LIBRARY_KEYWORDS["DatabaseLibrary"]
        expected_keywords = {"database", "sql", "query", "select", "insert"}

        assert expected_keywords.issubset(db_keywords)


class TestGetFieldValue:
    """Test get_field_value function."""

    def test_get_field_value_no_match(self):
        """Test get_field_value with no matching fields."""
        data = {"other": "value"}
        result = get_field_value(data, TEST_NAME_FIELDS)

        assert result == ""

    def test_get_field_value_with_match(self):
        """Test get_field_value with matching field."""
        data = {"title": "Test Title", "name": "Test Name"}
        result = get_field_value(data, TEST_NAME_FIELDS)

        assert result == "Test Name"  # First matching field

    def test_get_field_value_empty_value(self):
        """Test get_field_value with empty value."""
        data = {"name": ""}
        result = get_field_value(data, TEST_NAME_FIELDS)

        assert result == ""

    def test_get_field_value_non_string_value(self):
        """Test get_field_value converts non-string values."""
        data = {"name": 42}
        result = get_field_value(data, TEST_NAME_FIELDS)

        assert result == "42"


class TestHasField:
    """Test has_field function."""

    def test_has_field_no_match(self):
        """Test has_field with no matching fields."""
        data = {"other": "value"}
        result = has_field(data, TEST_NAME_FIELDS)

        assert result is False

    def test_has_field_with_match(self):
        """Test has_field with matching field."""
        data = {"title": "Test Title"}
        result = has_field(data, TEST_NAME_FIELDS)

        assert result is True

    def test_has_field_empty_value(self):
        """Test has_field with empty value."""
        data = {"name": ""}
        result = has_field(data, TEST_NAME_FIELDS)

        assert result is False

    def test_has_field_falsy_value(self):
        """Test has_field with falsy value."""
        data = {"name": 0}
        result = has_field(data, TEST_NAME_FIELDS)

        assert result is False  # 0 is falsy

    def test_has_field_none_value(self):
        """Test has_field with None value."""
        data = {"name": None}
        result = has_field(data, TEST_NAME_FIELDS)

        assert result is False


class TestDetectLibrariesFromText:
    """Test detect_libraries_from_text function."""

    def test_detect_libraries_empty_text(self):
        """Test library detection with empty text."""
        result = detect_libraries_from_text("")

        assert result == set()

    def test_detect_libraries_no_keywords(self):
        """Test library detection with no matching keywords."""
        result = detect_libraries_from_text(
            "This is a simple test without any library keywords"
        )

        assert result == set()

    def test_detect_libraries_single_library(self):
        """Test library detection with single library match."""
        result = detect_libraries_from_text(
            "Click the browser button and navigate to the page"
        )

        assert "SeleniumLibrary" in result

    def test_detect_libraries_multiple_libraries(self):
        """Test library detection with multiple library matches."""
        text = "Connect to SSH server, run SQL query, and check file existence"
        result = detect_libraries_from_text(text)

        assert "SSHLibrary" in result
        assert "DatabaseLibrary" in result
        assert "OperatingSystem" in result

    def test_detect_libraries_case_insensitive(self):
        """Test library detection is case insensitive."""
        result = detect_libraries_from_text("BROWSER click and SQL query")

        assert "SeleniumLibrary" in result
        assert "DatabaseLibrary" in result

    def test_detect_libraries_partial_words(self):
        """Test library detection doesn't match partial words."""
        # "row" is a keyword for DatabaseLibrary, but "brow" shouldn't match "browser"
        result = detect_libraries_from_text("brow row")

        assert "DatabaseLibrary" in result
        assert "SeleniumLibrary" not in result

    def test_detect_libraries_word_boundaries(self):
        """Test library detection respects word boundaries."""
        result = detect_libraries_from_text("databasex sqlx")  # Should not match

        assert result == set()

    def test_detect_libraries_all_libraries(self):
        """Test detection of all library types."""
        for text, expected_library in LIBRARY_DETECTION_TEST_CASES:
            result = detect_libraries_from_text(text)
            assert expected_library in result, (
                f"Failed to detect {expected_library} in '{text}'"
            )


class TestIsTestCase:
    """Test is_test_case function."""

    def test_is_test_case_non_dict(self):
        """Test is_test_case with non-dict input."""
        assert not is_test_case("string")
        assert not is_test_case([])
        assert not is_test_case(42)
        assert not is_test_case(None)

    def test_is_test_case_empty_dict(self):
        """Test is_test_case with empty dict."""
        assert not is_test_case({})

    def test_is_test_case_no_indicators(self):
        """Test is_test_case with dict containing no test indicators."""
        data = {"field1": "value1", "field2": "value2"}
        assert not is_test_case(data)

    def test_is_test_case_with_indicators(self):
        """Test is_test_case with dict containing test indicators."""
        test_cases = [
            {"name": "Test Case"},
            {"description": "Test description"},
            {"steps": []},
            {"testscript": "script"},
            {"objective": "objective"},
            {"summary": "summary"},
            {"title": "Title"},
            {"testname": "Test Name"},
        ]

        for data in test_cases:
            assert is_test_case(data), f"Failed to recognize test case: {data}"

    def test_is_test_case_case_insensitive_indicators(self):
        """Test is_test_case with case variations of indicators."""
        # TEST_INDICATORS contains lowercase versions, function converts to lowercase
        data = {"Name": "Test Case", "STEPS": []}
        assert is_test_case(data)

    def test_is_test_case_multiple_indicators(self):
        """Test is_test_case with multiple indicators."""
        data = {"name": "Test Case", "description": "Description", "steps": []}
        assert is_test_case(data)

    def test_is_test_case_indicator_with_empty_value(self):
        """Test is_test_case considers indicators regardless of value."""
        data = {"name": "", "other": "value"}
        assert is_test_case(data)  # "name" is an indicator, even if empty
