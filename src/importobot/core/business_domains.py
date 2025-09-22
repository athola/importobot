"""Business domain templates and enterprise scenarios for test generation."""

import random
from typing import Any

from importobot.utils.lazy_loader import LazyDataLoader


class BusinessDomainTemplates:
    """Business domain templates for test scenarios."""

    @property
    def enterprise_scenarios(self) -> dict[str, Any]:
        """Enterprise scenario templates for various testing domains."""
        return LazyDataLoader.load_templates("enterprise_scenarios")

    @property
    def enterprise_data_pools(self) -> dict[str, Any]:
        """Data pools for test parameterization."""
        return LazyDataLoader.load_templates("enterprise_data_pools")

    ENVIRONMENT_REQUIREMENTS = {
        "web_automation": [
            "Selenium WebDriver",
            "Chrome/Firefox browser",
            "Test environment URL",
        ],
        "api_testing": [
            "API endpoint access",
            "Authentication credentials",
            "Network connectivity",
        ],
        "database_testing": [
            "Database connection",
            "Test data access",
            "Backup procedures",
        ],
        "infrastructure_testing": [
            "Cloud account access",
            "Infrastructure as code tools",
            "Monitoring tools",
        ],
    }

    COMPLIANCE_REQUIREMENTS = {
        "web_automation": ["GDPR compliance", "Accessibility standards"],
        "api_testing": ["API security standards", "Data privacy"],
        "database_testing": ["Data retention policies", "Encryption standards"],
        "infrastructure_testing": ["Security compliance", "Audit requirements"],
    }

    SETUP_INSTRUCTIONS = {
        "web_automation": [
            "Configure browser settings",
            "Set up test data",
            "Initialize page objects",
        ],
        "api_testing": [
            "Configure API client",
            "Set authentication headers",
            "Prepare test payload",
        ],
        "database_testing": [
            "Establish database connection",
            "Prepare test dataset",
            "Set transaction isolation",
        ],
        "infrastructure_testing": [
            "Initialize cloud environment",
            "Configure deployment tools",
            "Set up monitoring",
        ],
    }

    TEARDOWN_INSTRUCTIONS = {
        "web_automation": [
            "Close browser sessions",
            "Clear test data",
            "Reset environment state",
        ],
        "api_testing": [
            "Clean up test resources",
            "Invalidate tokens",
            "Reset API state",
        ],
        "database_testing": [
            "Rollback transactions",
            "Clean test data",
            "Close connections",
        ],
        "infrastructure_testing": [
            "Destroy test resources",
            "Clean up artifacts",
            "Reset configurations",
        ],
    }

    @classmethod
    def get_scenario(cls, category: str, scenario: str) -> dict[str, Any]:
        """Get specific scenario from category."""
        scenarios = cls().enterprise_scenarios.get(category, {})
        result = scenarios.get(scenario, {})
        return result if isinstance(result, dict) else {}

    @classmethod
    def get_all_scenarios(cls, category: str) -> dict[str, Any]:
        """Get all scenarios for category."""
        result = cls().enterprise_scenarios.get(category, {})
        return result if isinstance(result, dict) else {}

    @classmethod
    def get_data_pool(cls, pool_name: str) -> list[str]:
        """Get data pool by name."""
        data_pools = cls().enterprise_data_pools
        result = data_pools.get(pool_name, [])
        return result if isinstance(result, list) else []

    @classmethod
    def get_environment_requirements(cls, category: str) -> list[str]:
        """Get environment requirements for category."""
        return cls.ENVIRONMENT_REQUIREMENTS.get(category, ["Standard Test Environment"])

    @classmethod
    def get_compliance_requirements(cls, category: str) -> list[str]:
        """Get compliance requirements for category."""
        return cls.COMPLIANCE_REQUIREMENTS.get(category, ["Standard Compliance"])

    @classmethod
    def get_setup_instructions(cls, category: str) -> list[str]:
        """Get setup instructions for category."""
        return cls.SETUP_INSTRUCTIONS.get(category, ["Initialize test environment"])

    @classmethod
    def get_teardown_instructions(cls, category: str) -> list[str]:
        """Get teardown instructions for category."""
        return cls.TEARDOWN_INSTRUCTIONS.get(category, ["Clean up test environment"])


class TestCaseTemplates:
    """Template structures for test case generation."""

    JSON_STRUCTURES = [
        "zephyr",
        "testlink",
        "jira",
        "xray",
        "generic",
    ]

    ENTERPRISE_LABELS = [
        "regression",
        "smoke",
        "integration",
        "e2e",
        "performance",
        "security",
        "accessibility",
        "api",
        "database",
        "ui",
        "mobile",
        "cross_browser",
        "load_testing",
        "stress_testing",
        "compatibility",
        "usability",
        "functional",
        "non_functional",
        "automated",
        "manual",
        "critical_path",
        "edge_cases",
        "boundary_testing",
        "negative_testing",
        "positive_testing",
        "data_driven",
        "keyword_driven",
        "hybrid",
        "bdd",
        "tdd",
        "exploratory",
        "ad_hoc",
        "user_acceptance",
        "system_testing",
        "component_testing",
        "unit_testing",
        "microservices",
        "ci_cd",
        "business_critical",
    ]

    TEST_PRIORITIES = ["Critical", "High", "Medium", "Low"]

    TEST_STATUSES = ["Approved", "Ready for Execution", "Under Review"]

    AUTOMATION_READINESS_LEVELS = {
        "very_high": "Partial - Manual verification required",
        "web_automation": "Full - Ready for CI/CD",
        "api_testing": "Full - Ready for CI/CD",
        "default": "High - Suitable for automation",
    }

    SECURITY_CLASSIFICATIONS = {
        "web_automation": "Internal",
        "api_testing": "Confidential",
        "database_testing": "Restricted",
        "infrastructure_testing": "Confidential",
    }

    @classmethod
    def get_available_structures(cls) -> list[str]:
        """Get available JSON structures."""
        return cls.JSON_STRUCTURES.copy()

    @classmethod
    def get_enterprise_labels(cls, count: int | None = None) -> list[str]:
        """Get enterprise labels, optionally limited to count."""
        if count:
            return random.sample(
                cls.ENTERPRISE_LABELS, min(count, len(cls.ENTERPRISE_LABELS))
            )
        return cls.ENTERPRISE_LABELS.copy()

    @classmethod
    def get_automation_readiness(cls, category: str, complexity: str) -> str:
        """Get automation readiness assessment."""
        if complexity == "very_high":
            return cls.AUTOMATION_READINESS_LEVELS["very_high"]
        if category in ["web_automation", "api_testing"]:
            return cls.AUTOMATION_READINESS_LEVELS[category]
        return cls.AUTOMATION_READINESS_LEVELS["default"]

    @classmethod
    def get_security_classification(cls, category: str) -> str:
        """Get security classification for category."""
        return cls.SECURITY_CLASSIFICATIONS.get(category, "Internal")
