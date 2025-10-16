"""Tests for business domain templates and enterprise scenarios."""

from unittest.mock import patch

from importobot.core.business_domains import (
    BusinessDomainTemplates,
    TestCaseTemplates,
)


class TestBusinessDomainTemplatesStructure:
    """Test BusinessDomainTemplates structure and data validation."""

    def test_enterprise_scenarios_structure(self):
        """Test that enterprise_scenarios has expected structure."""
        bt = BusinessDomainTemplates()
        scenarios = bt.enterprise_scenarios

        assert isinstance(scenarios, dict)
        assert len(scenarios) > 0

        # Check expected categories
        expected_categories = [
            "web_automation",
            "api_testing",
        ]
        for category in expected_categories:
            assert category in scenarios
            assert isinstance(scenarios[category], dict)

    def test_enterprise_scenarios_have_required_fields(self):
        """Test that scenarios have required fields."""
        bt = BusinessDomainTemplates()
        scenarios = bt.enterprise_scenarios

        for category_scenarios in scenarios.values():
            for scenario_data in category_scenarios.values():
                assert "description" in scenario_data
                assert "complexity" in scenario_data
                assert "steps_count" in scenario_data
                assert "templates" in scenario_data

                assert isinstance(scenario_data["description"], str)
                assert scenario_data["complexity"] in ["high", "very_high"]
                assert isinstance(scenario_data["steps_count"], tuple | list)
                assert len(scenario_data["steps_count"]) == 2
                assert isinstance(scenario_data["templates"], list)
                assert len(scenario_data["templates"]) > 0

    def test_enterprise_data_pools_structure(self):
        """Test that enterprise_data_pools has expected structure."""
        bt = BusinessDomainTemplates()
        data_pools = bt.enterprise_data_pools

        assert isinstance(data_pools, dict)
        assert len(data_pools) > 0

        # Check that all values are lists
        for pool_data in data_pools.values():
            assert isinstance(pool_data, list)
            assert len(pool_data) > 0

    def test_environment_requirements_structure(self):
        """Test ENVIRONMENT_REQUIREMENTS structure."""
        requirements = BusinessDomainTemplates.ENVIRONMENT_REQUIREMENTS

        assert isinstance(requirements, dict)
        for reqs in requirements.values():
            assert isinstance(reqs, list)
            assert len(reqs) > 0

    def test_compliance_requirements_structure(self):
        """Test COMPLIANCE_REQUIREMENTS structure."""
        requirements = BusinessDomainTemplates.COMPLIANCE_REQUIREMENTS

        assert isinstance(requirements, dict)
        for reqs in requirements.values():
            assert isinstance(reqs, list)
            assert len(reqs) > 0

    def test_setup_instructions_structure(self):
        """Test SETUP_INSTRUCTIONS structure."""
        instructions = BusinessDomainTemplates.SETUP_INSTRUCTIONS

        assert isinstance(instructions, dict)
        for instrs in instructions.values():
            assert isinstance(instrs, list)
            assert len(instrs) > 0

    def test_teardown_instructions_structure(self):
        """Test TEARDOWN_INSTRUCTIONS structure."""
        instructions = BusinessDomainTemplates.TEARDOWN_INSTRUCTIONS

        assert isinstance(instructions, dict)
        for instrs in instructions.values():
            assert isinstance(instrs, list)
            assert len(instrs) > 0


class TestBusinessDomainTemplatesMethods:
    """Test BusinessDomainTemplates method behavior."""

    def test_get_scenario_existing_scenario(self):
        """Test get_scenario with existing scenario."""
        result = BusinessDomainTemplates.get_scenario(
            "web_automation", "user_authentication"
        )

        assert isinstance(result, dict)
        assert "description" in result
        assert "complexity" in result
        assert "steps_count" in result
        assert "templates" in result

    def test_get_scenario_nonexistent_scenario(self):
        """Test get_scenario with nonexistent scenario."""
        result = BusinessDomainTemplates.get_scenario("web_automation", "nonexistent")

        assert result == {}

    def test_get_scenario_nonexistent_category(self):
        """Test get_scenario with nonexistent category."""
        result = BusinessDomainTemplates.get_scenario("nonexistent", "scenario")

        assert result == {}

    def test_get_all_scenarios_existing_category(self):
        """Test get_all_scenarios with existing category."""
        result = BusinessDomainTemplates.get_all_scenarios("web_automation")

        assert isinstance(result, dict)
        assert len(result) > 0
        assert "user_authentication" in result

    def test_get_all_scenarios_nonexistent_category(self):
        """Test get_all_scenarios with nonexistent category."""
        result = BusinessDomainTemplates.get_all_scenarios("nonexistent")

        assert result == {}

    def test_get_data_pool_existing_pool(self):
        """Test get_data_pool with existing pool."""
        result = BusinessDomainTemplates.get_data_pool("domains")

        assert isinstance(result, list)
        assert len(result) > 0
        assert "enterprise.com" in result

    def test_get_data_pool_nonexistent_pool(self):
        """Test get_data_pool with nonexistent pool."""
        result = BusinessDomainTemplates.get_data_pool("nonexistent")

        assert not result

    def test_get_environment_requirements_existing_category(self):
        """Test get_environment_requirements with existing category."""
        result = BusinessDomainTemplates.get_environment_requirements("web_automation")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_environment_requirements_nonexistent_category(self):
        """Test get_environment_requirements with nonexistent category."""
        result = BusinessDomainTemplates.get_environment_requirements("nonexistent")

        assert result == ["Standard Test Environment"]

    def test_get_compliance_requirements_existing_category(self):
        """Test get_compliance_requirements with existing category."""
        result = BusinessDomainTemplates.get_compliance_requirements("web_automation")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_compliance_requirements_nonexistent_category(self):
        """Test get_compliance_requirements with nonexistent category."""
        result = BusinessDomainTemplates.get_compliance_requirements("nonexistent")

        assert result == ["Standard Compliance"]

    def test_get_setup_instructions_existing_category(self):
        """Test get_setup_instructions with existing category."""
        result = BusinessDomainTemplates.get_setup_instructions("web_automation")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_setup_instructions_nonexistent_category(self):
        """Test get_setup_instructions with nonexistent category."""
        result = BusinessDomainTemplates.get_setup_instructions("nonexistent")

        assert result == ["Initialize test environment"]

    def test_get_teardown_instructions_existing_category(self):
        """Test get_teardown_instructions with existing category."""
        result = BusinessDomainTemplates.get_teardown_instructions("web_automation")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_teardown_instructions_nonexistent_category(self):
        """Test get_teardown_instructions with nonexistent category."""
        result = BusinessDomainTemplates.get_teardown_instructions("nonexistent")

        assert result == ["Clean up test environment"]


class TestBusinessDomainTemplatesLazyLoading:
    """Test BusinessDomainTemplates lazy loading behavior."""

    def test_lazy_loading_property_enterprise_scenarios(self):
        """Test that enterprise_scenarios property uses lazy loading."""
        bt = BusinessDomainTemplates()

        # Mock the LazyDataLoader
        with patch(
            "importobot.core.business_domains.LazyDataLoader.load_templates"
        ) as mock_load:
            mock_load.return_value = {"test": "data"}

            # Access the property
            result = bt.enterprise_scenarios

            # Verify lazy loader was called with correct template type
            mock_load.assert_called_once_with("enterprise_scenarios")
            assert result == {"test": "data"}

    def test_lazy_loading_property_enterprise_data_pools(self):
        """Test that enterprise_data_pools property uses lazy loading."""
        bt = BusinessDomainTemplates()

        # Mock the LazyDataLoader
        with patch(
            "importobot.core.business_domains.LazyDataLoader.load_templates"
        ) as mock_load:
            mock_load.return_value = {"pools": "data"}

            # Access the property
            result = bt.enterprise_data_pools

            # Verify lazy loader was called with correct template type
            mock_load.assert_called_once_with("enterprise_data_pools")
            assert result == {"pools": "data"}

    def test_lazy_loading_caching_behavior(self):
        """Test that lazy loading properties work with caching."""
        bt = BusinessDomainTemplates()

        # Mock the LazyDataLoader to track calls
        with patch(
            "importobot.core.business_domains.LazyDataLoader.load_templates"
        ) as mock_load:
            mock_load.return_value = {"cached": "data"}

            # Access the property multiple times
            result1 = bt.enterprise_scenarios
            result2 = bt.enterprise_scenarios

            # LazyDataLoader's @lru_cache should make this efficient
            # We expect the loader to be called for each property access
            # since the property doesn't cache the result itself
            assert mock_load.call_count >= 1
            assert result1 == result2


class TestTestCaseTemplates:
    """Test TestCaseTemplates class."""

    def test_json_structures_content(self):
        """Test JSON_STRUCTURES contains expected structures."""
        structures = TestCaseTemplates.JSON_STRUCTURES

        assert isinstance(structures, list)
        assert len(structures) > 0

        expected_structures = ["zephyr", "testlink", "jira"]
        for structure in expected_structures:
            assert structure in structures

    def test_enterprise_labels_content(self):
        """Test ENTERPRISE_LABELS contains expected labels."""
        labels = TestCaseTemplates.ENTERPRISE_LABELS

        assert isinstance(labels, list)
        assert len(labels) > 0

        expected_labels = ["integration", "security", "performance", "regression"]
        for label in expected_labels:
            assert label in labels

    def test_test_priorities_content(self):
        """Test TEST_PRIORITIES contains expected priorities."""
        priorities = TestCaseTemplates.TEST_PRIORITIES

        assert isinstance(priorities, list)
        assert len(priorities) == 4
        assert "Critical" in priorities
        assert "High" in priorities
        assert "Medium" in priorities
        assert "Low" in priorities

    def test_test_statuses_content(self):
        """Test TEST_STATUSES contains expected statuses."""
        statuses = TestCaseTemplates.TEST_STATUSES

        assert isinstance(statuses, list)
        assert len(statuses) >= 3
        assert "Approved" in statuses
        assert "Ready for Execution" in statuses

    def test_automation_readiness_levels_structure(self):
        """Test AUTOMATION_READINESS_LEVELS structure."""
        levels = TestCaseTemplates.AUTOMATION_READINESS_LEVELS

        assert isinstance(levels, dict)
        assert len(levels) > 0

        # Check expected keys
        expected_keys = ["very_high", "web_automation", "api_testing", "default"]
        for key in expected_keys:
            assert key in levels

    def test_security_classifications_structure(self):
        """Test SECURITY_CLASSIFICATIONS structure."""
        classifications = TestCaseTemplates.SECURITY_CLASSIFICATIONS

        assert isinstance(classifications, dict)
        assert len(classifications) > 0

        # Check that all values are strings
        for classification in classifications.values():
            assert isinstance(classification, str)

    def test_get_available_structures_returns_copy(self):
        """Test get_available_structures returns a copy."""
        structures1 = TestCaseTemplates.get_available_structures()
        structures2 = TestCaseTemplates.get_available_structures()

        assert structures1 is not structures2
        assert structures1 == structures2

    def test_get_enterprise_labels_no_count(self):
        """Test get_enterprise_labels with no count limit."""
        labels = TestCaseTemplates.get_enterprise_labels()

        assert isinstance(labels, list)
        assert len(labels) == len(TestCaseTemplates.ENTERPRISE_LABELS)

    def test_get_enterprise_labels_with_count(self):
        """Test get_enterprise_labels with count limit."""
        count = 3
        labels = TestCaseTemplates.get_enterprise_labels(count)

        assert isinstance(labels, list)
        assert len(labels) == count

        # Ensure all selected labels are from the original list
        for label in labels:
            assert label in TestCaseTemplates.ENTERPRISE_LABELS

    def test_get_enterprise_labels_count_larger_than_available(self):
        """Test get_enterprise_labels with count larger than available labels."""
        large_count = len(TestCaseTemplates.ENTERPRISE_LABELS) + 10
        labels = TestCaseTemplates.get_enterprise_labels(large_count)

        assert len(labels) == len(TestCaseTemplates.ENTERPRISE_LABELS)

    @patch("random.sample")
    def test_get_enterprise_labels_uses_random_sample(self, mock_sample):
        """Test get_enterprise_labels uses random.sample for selection."""
        mock_sample.return_value = ["selected1", "selected2"]

        result = TestCaseTemplates.get_enterprise_labels(2)

        mock_sample.assert_called_once_with(TestCaseTemplates.ENTERPRISE_LABELS, 2)
        assert result == ["selected1", "selected2"]

    def test_get_automation_readiness_very_high_complexity(self):
        """Test get_automation_readiness with very_high complexity."""
        result = TestCaseTemplates.get_automation_readiness("any_category", "very_high")

        assert result == "Partial - Manual verification required"

    def test_get_automation_readiness_web_automation(self):
        """Test get_automation_readiness for web_automation category."""
        result = TestCaseTemplates.get_automation_readiness("web_automation", "high")

        assert result == "Full - Ready for CI/CD"

    def test_get_automation_readiness_api_testing(self):
        """Test get_automation_readiness for api_testing category."""
        result = TestCaseTemplates.get_automation_readiness("api_testing", "high")

        assert result == "Full - Ready for CI/CD"

    def test_get_automation_readiness_default(self):
        """Test get_automation_readiness default case."""
        result = TestCaseTemplates.get_automation_readiness("other_category", "high")

        assert result == "High - Suitable for automation"

    def test_get_security_classification_existing_category(self):
        """Test get_security_classification for existing category."""
        result = TestCaseTemplates.get_security_classification("web_automation")

        assert result == "Internal"

    def test_get_security_classification_api_testing(self):
        """Test get_security_classification for api_testing."""
        result = TestCaseTemplates.get_security_classification("api_testing")

        assert result == "Confidential"

    def test_get_security_classification_nonexistent_category(self):
        """Test get_security_classification for nonexistent category."""
        result = TestCaseTemplates.get_security_classification("nonexistent")

        assert result == "Internal"  # Default value
