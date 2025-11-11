"""Comprehensive TDD tests for Zephyr-specific field definitions and detection."""

from importobot.core.field_definitions import (
    TEST_DESCRIPTION_FIELDS,
    ZEPHYR_DETAILS_FIELDS,
    ZEPHYR_LEVEL_FIELDS,
    ZEPHYR_PLATFORM_FIELDS,
    ZEPHYR_PRECONDITION_FIELDS,
    ZEPHYR_STEP_STRUCTURE_FIELDS,
    ZEPHYR_TEST_INDICATORS,
    ZEPHYR_TRACEABILITY_FIELDS,
    FieldGroup,
    get_field_value,
    has_field,
    is_test_case,
    is_zephyr_test_case,
)


class TestZephyrFieldGroups:
    """Test Zephyr-specific field group definitions."""

    def test_zephyr_details_fields_definition(self) -> None:
        """Test ZEPHYR_DETAILS_FIELDS contains expected metadata fields."""
        expected_fields = [
            "status",
            "priority",
            "component",
            "owner",
            "estimatedTime",
            "folder",
        ]

        for field in expected_fields:
            assert field in ZEPHYR_DETAILS_FIELDS

        assert (
            ZEPHYR_DETAILS_FIELDS.description == "Zephyr test case details and metadata"
        )
        assert isinstance(ZEPHYR_DETAILS_FIELDS, FieldGroup)

    def test_zephyr_precondition_fields_definition(self) -> None:
        """Test ZEPHYR_PRECONDITION_FIELDS contains setup-related fields."""
        expected_fields = ["precondition", "preconditions", "setup", "requirements"]

        for field in expected_fields:
            assert field in ZEPHYR_PRECONDITION_FIELDS

        assert (
            ZEPHYR_PRECONDITION_FIELDS.description
            == "Test setup requirements and preconditions"
        )
        assert isinstance(ZEPHYR_PRECONDITION_FIELDS, FieldGroup)

    def test_zephyr_traceability_fields_definition(self) -> None:
        """Test ZEPHYR_TRACEABILITY_FIELDS contains requirement tracking fields."""
        expected_fields = [
            "issues",
            "confluence",
            "webLinks",
            "linkedCRS",
            "requirements",
        ]

        for field in expected_fields:
            assert field in ZEPHYR_TRACEABILITY_FIELDS

        assert (
            ZEPHYR_TRACEABILITY_FIELDS.description
            == "Test case traceability and requirement links"
        )
        assert isinstance(ZEPHYR_TRACEABILITY_FIELDS, FieldGroup)

    def test_zephyr_level_fields_definition(self) -> None:
        """Test ZEPHYR_LEVEL_FIELDS contains test classification fields."""
        expected_fields = ["testLevel", "level", "importance", "criticality"]

        for field in expected_fields:
            assert field in ZEPHYR_LEVEL_FIELDS

        assert (
            ZEPHYR_LEVEL_FIELDS.description
            == "Test level and importance classification"
        )
        assert isinstance(ZEPHYR_LEVEL_FIELDS, FieldGroup)

    def test_zephyr_platform_fields_definition(self) -> None:
        """Test ZEPHYR_PLATFORM_FIELDS contains platform support fields."""
        expected_fields = ["supportedPlatforms", "platforms", "targets"]

        for field in expected_fields:
            assert field in ZEPHYR_PLATFORM_FIELDS

        assert (
            ZEPHYR_PLATFORM_FIELDS.description
            == "Supported target platforms and architectures"
        )
        assert isinstance(ZEPHYR_PLATFORM_FIELDS, FieldGroup)

    def test_zephyr_step_structure_fields_definition(self) -> None:
        """Test ZEPHYR_STEP_STRUCTURE_FIELDS contains three-segment step fields."""
        expected_fields = [
            "step",
            "testData",
            "expectedResult",
            "description",
            "actual",
        ]

        for field in expected_fields:
            assert field in ZEPHYR_STEP_STRUCTURE_FIELDS

        assert (
            ZEPHYR_STEP_STRUCTURE_FIELDS.description
            == "Zephyr step structure with action, data, and expected result"
        )
        assert isinstance(ZEPHYR_STEP_STRUCTURE_FIELDS, FieldGroup)

    def test_zephyr_field_groups_case_insensitive(self) -> None:
        """Test Zephyr field groups are case insensitive."""
        assert "status" in ZEPHYR_DETAILS_FIELDS
        assert "STATUS" in ZEPHYR_DETAILS_FIELDS
        assert "Status" in ZEPHYR_DETAILS_FIELDS

        assert "precondition" in ZEPHYR_PRECONDITION_FIELDS
        assert "PRECONDITION" in ZEPHYR_PRECONDITION_FIELDS
        assert "Precondition" in ZEPHYR_PRECONDITION_FIELDS

    def test_zephyr_field_groups_find_first(self) -> None:
        """Test Zephyr field groups find_first method."""
        data = {
            "STATUS": "In Progress",
            "priority": "High",
            "component": "Authentication",
        }

        field, value = ZEPHYR_DETAILS_FIELDS.find_first(data)
        # Should find the first matching field based on definition order
        assert field in ["status", "priority", "component"]
        assert value in ["In Progress", "High", "Authentication"]

    def test_zephyr_field_groups_no_matches(self) -> None:
        """Test Zephyr field groups with no matching fields."""
        data = {"other": "value", "unknown": "field"}

        field, value = ZEPHYR_DETAILS_FIELDS.find_first(data)
        assert field is None
        assert value is None


class TestZephyrTestIndicators:
    """Test Zephyr-specific test indicators."""

    def test_zephyr_test_indicators_content(self) -> None:
        """Test ZEPHYR_TEST_INDICATORS contains Zephyr-specific fields."""
        expected_indicators = [
            "testscript",
            "precondition",
            "testlevel",
            "supportedplatforms",
            "objective",
        ]

        for indicator in expected_indicators:
            assert indicator in ZEPHYR_TEST_INDICATORS

        assert isinstance(ZEPHYR_TEST_INDICATORS, frozenset)

    def test_zephyr_test_indicators_is_frozenset(self) -> None:
        """Test ZEPHYR_TEST_INDICATORS is a frozenset."""
        assert isinstance(ZEPHYR_TEST_INDICATORS, frozenset)

        # Verify it's immutable - frozenset doesn't have add method
        assert not hasattr(ZEPHYR_TEST_INDICATORS, "add")

    def test_zephyr_test_indicators_case_sensitivity(self) -> None:
        """Test ZEPHYR_TEST_INDICATORS are lowercase."""
        # Should contain lowercase versions
        assert "testscript" in ZEPHYR_TEST_INDICATORS
        assert "precondition" in ZEPHYR_TEST_INDICATORS

        # Should not contain uppercase versions
        assert "testScript" not in ZEPHYR_TEST_INDICATORS
        assert "Precondition" not in ZEPHYR_TEST_INDICATORS


class TestIsZephyrTestCase:
    """Test is_zephyr_test_case function."""

    def test_is_zephyr_test_case_non_dict(self) -> None:
        """Test is_zephyr_test_case with non-dict input."""
        assert not is_zephyr_test_case("string")
        assert not is_zephyr_test_case([])
        assert not is_zephyr_test_case(42)
        assert not is_zephyr_test_case(None)

    def test_is_zephyr_test_case_empty_dict(self) -> None:
        """Test is_zephyr_test_case with empty dict."""
        assert not is_zephyr_test_case({})

    def test_is_zephyr_test_case_no_zephyr_indicators(self) -> None:
        """Test is_zephyr_test_case with dict containing no Zephyr indicators."""
        data = {"name": "Test Case", "description": "Description"}
        assert not is_zephyr_test_case(data)
        # But should still be recognized as a regular test case
        assert is_test_case(data)

    def test_is_zephyr_test_case_with_single_indicator(self) -> None:
        """Test is_zephyr_test_case with single Zephyr indicator."""
        test_cases = [
            {"testscript": "script content"},
            {"precondition": "setup requirements"},
            {"testLevel": "Smoke"},
            {"supportedPlatforms": ["Linux", "Windows"]},
            {"objective": "test objective"},
        ]

        for data in test_cases:
            assert is_zephyr_test_case(data), (
                f"Failed to recognize Zephyr test case: {data}"
            )

    def test_is_zephyr_test_case_case_insensitive(self) -> None:
        """Test is_zephyr_test_case with case variations of indicators."""
        test_cases = [
            {"testScript": "script content"},
            {"Precondition": "setup requirements"},
            {"TESTLEVEL": "Smoke"},
            {"SupportedPlatforms": ["Linux", "Windows"]},
            {"Objective": "test objective"},
        ]

        for data in test_cases:
            assert is_zephyr_test_case(data), (
                f"Failed to recognize case-insensitive Zephyr test case: {data}"
            )

    def test_is_zephyr_test_case_multiple_indicators(self) -> None:
        """Test is_zephyr_test_case with multiple Zephyr indicators."""
        data = {
            "testscript": "script content",
            "precondition": "setup requirements",
            "testLevel": "Smoke",
            "objective": "test objective",
        }
        assert is_zephyr_test_case(data)

    def test_is_zephyr_test_case_mixed_with_regular_indicators(self) -> None:
        """Test is_zephyr_test_case with mixed Zephyr and regular indicators."""
        data = {
            "name": "Regular Test Name",
            "testscript": "Zephyr script content",
            "description": "Regular description",
        }
        assert is_zephyr_test_case(data)
        assert is_test_case(data)  # Should also be recognized as regular test case

    def test_is_zephyr_test_case_with_empty_values(self) -> None:
        """Test is_zephyr_test_case considers indicators regardless of value."""
        data = {"testscript": "", "precondition": None}
        assert is_zephyr_test_case(data)

    def test_is_zephyr_test_case_complex_structure(self) -> None:
        """Test is_zephyr_test_case with complex Zephyr structure."""
        data = {
            "name": "Authentication Test",
            "testScript": {
                "step": ["Enter credentials", "Submit form"],
                "testData": ["user=admin", "password=secret"],
                "expectedResult": ["Login successful", "Redirect to dashboard"],
            },
            "precondition": "User is on login page",
            "testLevel": "Minimum Viable CRS",
            "supportedPlatforms": ["Linux", "Windows", "macOS"],
            "issues": ["PROJ-123", "PROJ-456"],
        }
        assert is_zephyr_test_case(data)

    def test_is_zephyr_test_case_distinguishes_from_regular(self) -> None:
        """Test that is_zephyr_test_case distinguishes from regular test cases."""
        regular_test = {
            "name": "Regular Test",
            "description": "Regular description",
            "steps": ["step1", "step2"],
        }
        zephyr_test = {
            "name": "Zephyr Test",
            "testscript": "Zephyr script",
            "precondition": "Setup required",
        }

        assert not is_zephyr_test_case(regular_test)
        assert is_test_case(regular_test)

        assert is_zephyr_test_case(zephyr_test)
        assert is_test_case(zephyr_test)


class TestZephyrFieldIntegration:
    """Test integration of Zephyr field groups with utility functions."""

    def test_get_field_value_with_zephyr_groups(self) -> None:
        """Test get_field_value works with Zephyr field groups."""
        data = {"status": "In Progress", "priority": "High", "testLevel": "Smoke"}

        status_value = get_field_value(data, ZEPHYR_DETAILS_FIELDS)
        assert (
            status_value == "In Progress"
        )  # First matching field in ZEPHYR_DETAILS_FIELDS

        level_value = get_field_value(data, ZEPHYR_LEVEL_FIELDS)
        assert level_value == "Smoke"

    def test_has_field_with_zephyr_groups(self) -> None:
        """Test has_field works with Zephyr field groups."""
        data = {"precondition": "Setup requirements", "issues": ["PROJ-123"]}

        assert has_field(data, ZEPHYR_PRECONDITION_FIELDS)
        assert has_field(data, ZEPHYR_TRACEABILITY_FIELDS)
        assert not has_field(data, ZEPHYR_PLATFORM_FIELDS)

    def test_zephyr_field_groups_with_complex_data(self) -> None:
        """Test Zephyr field groups with complex nested data."""
        data = {
            "status": "Ready",
            "priority": "Critical",
            "component": "Authentication Module",
            "testScript": {
                "step": ["Enter username", "Enter password", "Click login"],
                "testData": ["user=test@example.com", "password=Secret123"],
                "expectedResult": ["Login successful", "Dashboard displayed"],
            },
            "supportedPlatforms": ["Linux", "Windows", "Unix"],
            "testLevel": "Minimum Viable CRS",
            "issues": ["AUTH-001", "AUTH-002"],
            "linkedCRS": ["CRS-AUTH-001"],
        }

        # Test all Zephyr field groups can find data
        assert has_field(data, ZEPHYR_DETAILS_FIELDS)
        assert has_field(data, ZEPHYR_PLATFORM_FIELDS)
        assert has_field(data, ZEPHYR_LEVEL_FIELDS)
        assert has_field(data, ZEPHYR_TRACEABILITY_FIELDS)
        # Note: ZEPHYR_STEP_STRUCTURE_FIELDS looks for direct fields, not testScript

        # Test specific value extraction
        priority = get_field_value(data, ZEPHYR_DETAILS_FIELDS)
        assert priority == "Ready"  # First matching field

        platforms = get_field_value(data, ZEPHYR_PLATFORM_FIELDS)
        # Should return the string representation of the first matching platform
        expected = "['Linux', 'Windows', 'Unix']"
        assert platforms == expected


class TestZephyrFieldGroupEdgeCases:
    """Test edge cases and boundary conditions for Zephyr field groups."""

    def test_zephyr_field_groups_with_none_values(self) -> None:
        """Test Zephyr field groups handle None values correctly."""
        data = {"status": None, "priority": "", "component": False, "owner": 0}

        # find_first should skip falsy values
        field, value = ZEPHYR_DETAILS_FIELDS.find_first(data)
        assert field is None
        assert value is None

    def test_zephyr_field_groups_with_mixed_types(self) -> None:
        """Test Zephyr field groups with mixed value types."""
        data = {
            "status": "Active",
            "priority": 1,  # integer
            "estimatedTime": 2.5,  # float
            "owner": ["user1", "user2"],  # list
            "folder": {"path": "/tests"},  # dict
        }

        # find_first should return the first non-empty value
        field, value = ZEPHYR_DETAILS_FIELDS.find_first(data)
        assert field == "status"
        assert value == "Active"

    def test_zephyr_test_indicators_with_unicode(self) -> None:
        """Test Zephyr test indicators with unicode characters."""
        data = {
            "testscript": "Test with ñiño and café",
            "precondition": "Configuración con caracteres especiales",
        }
        assert is_zephyr_test_case(data)

    def test_zephyr_field_groups_large_values(self) -> None:
        """Test Zephyr field groups with large values."""
        large_text = "x" * 10000
        large_list = list(range(1000))

        data = {"objective": large_text, "supportedPlatforms": large_list}

        assert is_zephyr_test_case(data)
        # objective is in TEST_DESCRIPTION_FIELDS, not ZEPHYR_LEVEL_FIELDS
        assert get_field_value(data, TEST_DESCRIPTION_FIELDS) == large_text
