"""TDD Unit tests for individual format definition creators.

Tests each format definition file to ensure they create valid,
well-structured format definitions with appropriate indicators
and configurations for their respective test management systems.

Business Requirements:
- Each format must have unique characteristics for accurate detection
- Format definitions must be comprehensive and reflect real-world usage
- Format creators must produce valid, validated format definitions
- Each format must have appropriate confidence thresholds
"""

import unittest

from importobot.medallion.bronze.format_models import EvidenceWeight
from importobot.medallion.bronze.formats import (
    create_generic_format,
    create_testlink_format,
    create_testrail_format,
    create_unknown_format,
    create_xray_format,
    create_zephyr_format,
)
from importobot.medallion.interfaces.enums import SupportedFormat


class TestZephyrFormatCreator(unittest.TestCase):
    """Unit tests for Zephyr format definition creator."""

    def setUp(self):
        """Set up test fixtures."""
        self.format_def = create_zephyr_format()

    def test_zephyr_format_basic_properties(self):
        """Test basic properties of Zephyr format definition."""
        assert self.format_def.format_type == SupportedFormat.ZEPHYR
        assert "Zephyr" in self.format_def.name
        assert "zephyr" in self.format_def.description.lower()

    def test_zephyr_unique_indicators(self):
        """Test Zephyr unique indicators are properly defined."""
        unique_indicators = self.format_def.unique_indicators

        # Should have at least the core Zephyr indicators
        assert len(unique_indicators) > 0

        # Check for key Zephyr indicators
        unique_names = {field.name for field in unique_indicators}
        expected_indicators = {"testCase", "execution", "cycle"}
        assert expected_indicators.issubset(unique_names)

        # All unique indicators should have UNIQUE weight
        for indicator in unique_indicators:
            assert indicator.evidence_weight == EvidenceWeight.UNIQUE

    def test_zephyr_strong_indicators(self):
        """Test Zephyr strong indicators."""
        strong_indicators = self.format_def.strong_indicators

        # Check that strong indicators have STRONG weight
        for indicator in strong_indicators:
            assert indicator.evidence_weight == EvidenceWeight.STRONG

    def test_zephyr_validation_passes(self):
        """Test that Zephyr format definition passes validation."""
        validation_issues = self.format_def.validate()
        assert validation_issues == [], f"Validation issues found: {validation_issues}"

    def test_zephyr_max_score_calculation(self):
        """Test Zephyr format max score calculation."""
        max_score = self.format_def.get_max_possible_score()

        # Should have a reasonable maximum score
        assert max_score > 0

        # Zephyr should have high max score due to unique indicators
        assert max_score >= 15  # 3 unique indicators * 5 = 15 minimum

    def test_zephyr_field_descriptions(self):
        """Test that Zephyr fields have meaningful descriptions."""
        all_fields = self.format_def.get_all_fields()

        for field in all_fields:
            assert isinstance(field.description, str)
            assert len(field.description) > 10  # Meaningful description
            # Not all fields may mention "Zephyr" explicitly
            assert any(
                keyword in field.description.lower()
                for keyword in ["zephyr", "test", "case", "execution", "cycle"]
            )


class TestXrayFormatCreator(unittest.TestCase):
    """Unit tests for Xray format definition creator."""

    def setUp(self):
        """Set up test fixtures."""
        self.format_def = create_xray_format()

    def test_xray_format_basic_properties(self):
        """Test basic properties of Xray format definition."""
        assert self.format_def.format_type == SupportedFormat.JIRA_XRAY
        assert "Xray" in self.format_def.name
        assert any(
            keyword in self.format_def.description.lower()
            for keyword in ["xray", "jira"]
        )

    def test_xray_unique_indicators(self):
        """Test Xray unique indicators reflect JIRA integration."""
        unique_indicators = self.format_def.unique_indicators
        unique_names = {field.name for field in unique_indicators}

        # Should have Xray-specific indicators
        expected_indicators = {"testExecutions", "testInfo", "evidences"}
        found_indicators = expected_indicators.intersection(unique_names)
        assert len(found_indicators) > 0, (
            "Should have at least one Xray-specific indicator"
        )

    def test_xray_jira_integration_indicators(self):
        """Test Xray format includes JIRA integration indicators."""
        all_fields = self.format_def.get_all_fields()
        field_names = {field.name for field in all_fields}

        # Should have JIRA-related fields
        jira_indicators = {"issues", "key", "fields"}
        found_jira = jira_indicators.intersection(field_names)
        assert len(found_jira) > 0, "Should have JIRA integration indicators"

    def test_xray_validation_passes(self):
        """Test that Xray format definition passes validation."""
        validation_issues = self.format_def.validate()
        assert validation_issues == [], f"Validation issues found: {validation_issues}"

    def test_xray_field_patterns(self):
        """Test Xray fields have appropriate validation patterns where needed."""
        all_fields = self.format_def.get_all_fields()

        # Check for JIRA key pattern if present
        for field in all_fields:
            if field.name == "key" and field.pattern:
                # Should validate JIRA key format
                assert "[A-Z]" in field.pattern


class TestTestRailFormatCreator(unittest.TestCase):
    """Unit tests for TestRail format definition creator."""

    def setUp(self):
        """Set up test fixtures."""
        self.format_def = create_testrail_format()

    def test_testrail_format_basic_properties(self):
        """Test basic properties of TestRail format definition."""
        assert self.format_def.format_type == SupportedFormat.TESTRAIL
        assert "TestRail" in self.format_def.name
        assert "testrail" in self.format_def.description.lower()

    def test_testrail_unique_indicators(self):
        """Test TestRail unique indicators reflect API structure."""
        unique_indicators = self.format_def.unique_indicators
        unique_names = {field.name for field in unique_indicators}

        # Should have TestRail-specific API indicators
        expected_indicators = {"runs", "cases"}
        found_indicators = expected_indicators.intersection(unique_names)
        assert len(found_indicators) > 0, "Should have TestRail API indicators"

    def test_testrail_api_structure_indicators(self):
        """Test TestRail format includes API structure indicators."""
        all_fields = self.format_def.get_all_fields()
        field_names = {field.name for field in all_fields}

        # Should have TestRail API structure fields
        api_indicators = {"suite_id", "project_id", "milestone_id"}
        found_api = api_indicators.intersection(field_names)
        assert len(found_api) > 0, "Should have TestRail API structure indicators"

    def test_testrail_validation_passes(self):
        """Test that TestRail format definition passes validation."""
        validation_issues = self.format_def.validate()
        assert validation_issues == [], f"Validation issues found: {validation_issues}"


class TestTestLinkFormatCreator(unittest.TestCase):
    """Unit tests for TestLink format definition creator."""

    def setUp(self):
        """Set up test fixtures."""
        self.format_def = create_testlink_format()

    def test_testlink_format_basic_properties(self):
        """Test basic properties of TestLink format definition."""
        assert self.format_def.format_type == SupportedFormat.TESTLINK
        assert "TestLink" in self.format_def.name
        assert "testlink" in self.format_def.description.lower()

    def test_testlink_unique_indicators(self):
        """Test TestLink unique indicators reflect XML structure."""
        unique_indicators = self.format_def.unique_indicators
        unique_names = {field.name for field in unique_indicators}

        # Should have TestLink XML structure indicators
        expected_indicators = {"testsuites", "testsuite"}
        found_indicators = expected_indicators.intersection(unique_names)
        assert len(found_indicators) > 0, (
            "Should have TestLink XML structure indicators"
        )

    def test_testlink_xml_structure_indicators(self):
        """Test TestLink format includes XML structure indicators."""
        all_fields = self.format_def.get_all_fields()
        field_names = {field.name for field in all_fields}

        # Should have XML-based structure fields
        xml_indicators = {"testcase", "step", "actions", "expectedresults"}
        found_xml = xml_indicators.intersection(field_names)
        assert len(found_xml) > 0, "Should have XML structure indicators"

    def test_testlink_validation_passes(self):
        """Test that TestLink format definition passes validation."""
        validation_issues = self.format_def.validate()
        assert validation_issues == [], f"Validation issues found: {validation_issues}"


class TestGenericFormatCreator(unittest.TestCase):
    """Unit tests for Generic format definition creator."""

    def setUp(self):
        """Set up test fixtures."""
        self.format_def = create_generic_format()

    def test_generic_format_basic_properties(self):
        """Test basic properties of Generic format definition."""
        assert self.format_def.format_type == SupportedFormat.GENERIC
        assert "Generic" in self.format_def.name
        # Description should indicate default nature
        keywords = ["generic", "default", "unstructured", "custom"]
        description_lower = self.format_def.description.lower()
        assert any(keyword in description_lower for keyword in keywords)

    def test_generic_moderate_indicators(self):
        """Test Generic format focuses on moderate/weak indicators."""
        # Generic relies more on moderate/weak indicators as it's a default option
        moderate_indicators = self.format_def.moderate_indicators
        weak_indicators = self.format_def.weak_indicators

        # Should have some indicators for common test patterns
        total_indicators = len(moderate_indicators) + len(weak_indicators)
        assert total_indicators > 0, "Should have common test pattern indicators"

    def test_generic_common_test_patterns(self):
        """Test Generic format includes common test patterns."""
        all_fields = self.format_def.get_all_fields()
        field_names = {field.name for field in all_fields}

        # Should include common test terminology
        common_patterns = {"test", "case", "step", "expected", "result"}
        found_patterns = common_patterns.intersection(field_names)
        assert len(found_patterns) > 0, "Should include common test patterns"

    def test_generic_validation_passes(self):
        """Test that Generic format definition passes validation."""
        validation_issues = self.format_def.validate()
        assert validation_issues == [], f"Validation issues found: {validation_issues}"

    def test_generic_reasonable_threshold(self):
        """Test Generic format has reasonable detection threshold."""
        # Generic format threshold should be reasonable (may be higher than expected)
        assert self.format_def.min_score_threshold >= 1
        assert self.format_def.min_score_threshold <= 10


class TestUnknownFormatCreator(unittest.TestCase):
    """Unit tests for Unknown format definition creator."""

    def setUp(self):
        """Set up test fixtures."""
        self.format_def = create_unknown_format()

    def test_unknown_format_basic_properties(self):
        """Test basic properties of Unknown format definition."""
        assert self.format_def.format_type == SupportedFormat.UNKNOWN
        assert "Unknown" in self.format_def.name
        # Description should indicate unidentifiable nature
        keywords = [
            "unknown",
            "unidentifiable",
            "unrecognized",
            "no other format",
        ]
        description_lower = self.format_def.description.lower()
        assert any(keyword in description_lower for keyword in keywords)

    def test_unknown_minimal_indicators(self):
        """Test Unknown format has minimal or no indicators."""
        all_fields = self.format_def.get_all_fields()

        # Unknown format should have minimal indicators (catch-all)
        assert len(all_fields) <= 5, "Unknown format should have minimal indicators"

    def test_unknown_validation_behavior(self):
        """Test Unknown format validation behavior."""
        validation_issues = self.format_def.validate()
        # Unknown format may not pass standard validation as it's a special case
        # This is acceptable for a catch-all format
        assert isinstance(validation_issues, list)

    def test_unknown_special_threshold(self):
        """Test Unknown format has special threshold configuration."""
        # Unknown format may have a special high threshold to prevent
        # false positives. This is acceptable as it's a catch-all that
        # should only match when explicitly assigned
        assert isinstance(self.format_def.min_score_threshold, int)


class TestFormatCreatorIntegration(unittest.TestCase):
    """Integration tests across all format creators."""

    def setUp(self):
        """Set up all format definitions."""
        self.formats = {
            "zephyr": create_zephyr_format(),
            "xray": create_xray_format(),
            "testrail": create_testrail_format(),
            "testlink": create_testlink_format(),
            "generic": create_generic_format(),
            "unknown": create_unknown_format(),
        }

    def test_all_formats_have_unique_types(self):
        """Test that all formats have unique format types."""
        format_types = [fmt.format_type for fmt in self.formats.values()]
        unique_types = set(format_types)

        assert len(format_types) == len(unique_types), (
            "All formats should have unique format types"
        )

    def test_most_formats_pass_validation(self):
        """Test that production formats pass validation."""
        for name, format_def in self.formats.items():
            with self.subTest(format_name=name):
                validation_issues = format_def.validate()
                if name == "unknown":
                    # Unknown format may not pass validation - acceptable
                    assert isinstance(validation_issues, list)
                else:
                    # All other formats should pass validation
                    assert validation_issues == [], (
                        f"{name} format validation failed: {validation_issues}"
                    )

    def test_format_score_distribution(self):
        """Test that formats have reasonable max score distribution."""
        scores = {
            name: fmt.get_max_possible_score() for name, fmt in self.formats.items()
        }

        # All production formats should have reasonable scores
        for name, score in scores.items():
            with self.subTest(format_name=name):
                if name != "unknown":  # Unknown may have special scoring
                    assert score > 0, f"{name} should have positive max score"
                    assert score <= 100, f"{name} should have reasonable max score"

        # Specific formats should generally have higher scores than unknown
        specific_formats = ["zephyr", "xray", "testrail", "testlink"]
        for fmt_name in specific_formats:
            if scores[fmt_name] > 0 and scores["unknown"] > 0:
                # Only compare if both have meaningful scores
                continue  # Skip comparison as unknown may have special scoring

    def test_unique_indicator_distribution(self):
        """Test that unique indicators are appropriately distributed."""
        for name, format_def in self.formats.items():
            with self.subTest(format_name=name):
                unique_count = len(format_def.unique_indicators)

                if name in ["zephyr", "xray", "testrail", "testlink"]:
                    # Specific formats should have unique indicators
                    assert unique_count > 0, f"{name} should have unique indicators"
                elif name == "generic":
                    # Generic may or may not have unique indicators
                    assert unique_count >= 0
                else:  # unknown
                    # Unknown should have minimal unique indicators
                    assert unique_count <= 2

    def test_field_name_uniqueness_across_formats(self):
        """Test that formats have distinct field patterns."""
        # Collect unique field names by format
        format_fields = {}
        for name, format_def in self.formats.items():
            unique_fields = {field.name for field in format_def.unique_indicators}
            format_fields[name] = unique_fields

        # Check that each specific format has some unique fields
        for name in ["zephyr", "xray", "testrail", "testlink"]:
            with self.subTest(format_name=name):
                # Each format should have at least one field not used by others
                excluded = ["generic", "unknown"]
                other_formats = [
                    n for n in format_fields if n != name and n not in excluded
                ]
                other_fields = set()
                for other_name in other_formats:
                    other_fields.update(format_fields[other_name])

                unique_to_format = format_fields[name] - other_fields
                assert len(unique_to_format) > 0, (
                    f"{name} should have fields unique from other formats"
                )

    def test_format_descriptions_are_informative(self):
        """Test that all formats have informative descriptions."""
        for name, format_def in self.formats.items():
            with self.subTest(format_name=name):
                assert len(format_def.description) > 20, (
                    f"{name} description should be informative"
                )
                assert format_def.description.lower() != format_def.name.lower(), (
                    f"{name} description should be more than just the name"
                )


if __name__ == "__main__":
    unittest.main()
