"""Template management for test generation."""

import random
from typing import Any

from importobot.utils.logging import get_logger


class TemplateManager:
    """Manages test case templates and scenarios for generation."""

    def __init__(self) -> None:
        """Initialize template manager with cached templates."""
        self._scenario_cache: dict[str, Any] = {}
        self._template_cache: dict[str, Any] = {}
        self.logger = get_logger()
        self._build_template_cache()
        self.logger.info(
            "TemplateManager initialized with %d categories", len(self._template_cache)
        )

    def _build_template_cache(self) -> None:
        """Build and cache templates."""
        # Cache web automation templates
        self._template_cache["web_automation"] = [
            "Navigate to {environment} login page",
            "Enter username '{user_role}' in login field",
            "Enter password in password field",
            "Click login button",
            "Verify dashboard displays for {business_unit} user",
            "Navigate to {system} module",
            "Click on 'New Record' button",
            "Fill in required fields with test data",
            "Save the record and verify success message",
            "Log out from application",
        ]

        # Cache API testing templates
        self._template_cache["api_testing"] = [
            "Establish connection to {environment} API endpoint",
            "Send GET request to /{system}/api/v1/users",
            "Verify response status code is 200",
            "Validate response contains user data",
            "Send POST request with new user data",
            "Verify user creation response",
            "Send PUT request to update user information",
            "Verify update was successful",
            "Send DELETE request to remove test user",
            "Verify user was deleted successfully",
        ]

        # Cache database testing templates
        self._template_cache["database_testing"] = [
            "Connect to {database} database in {environment}",
            "Execute SELECT query on users table",
            "Verify query returns expected number of rows",
            "Insert test record into {system} table",
            "Verify record was inserted successfully",
            "Update test record with new values",
            "Verify update affected correct number of rows",
            "Delete test record from table",
            "Verify record was deleted",
            "Close database connection",
        ]

        # Cache SSH/infrastructure templates
        self._template_cache["infrastructure_testing"] = [
            "Connect to {region} server via SSH",
            "Verify server connectivity and authentication",
            "Check system resources and disk space",
            "Execute system health check commands",
            "Upload configuration file to remote server",
            "Restart {system} service on remote host",
            "Verify service status after restart",
            "Download log files for analysis",
            "Clean up temporary files",
            "Disconnect from remote server",
        ]

    def get_templates_for_scenario(self, category: str, scenario: str) -> list[str]:
        """Get templates for a specific scenario with caching."""
        cache_key = f"{category}_{scenario}"

        if cache_key in self._scenario_cache:
            cached_result = self._scenario_cache[cache_key]
            return cached_result if isinstance(cached_result, list) else []

        # Map scenarios to template categories
        scenario_mapping = {
            "user_authentication": "web_automation",
            "e2e_workflow": "web_automation",
            "performance_testing": "web_automation",
            "microservices_integration": "api_testing",
            "data_pipeline_testing": "api_testing",
            "enterprise_data_operations": "database_testing",
            "cloud_native_operations": "infrastructure_testing",
            "security_testing": "infrastructure_testing",
        }

        template_category = scenario_mapping.get(scenario, "web_automation")
        templates_raw = self._template_cache.get(template_category, [])
        templates = templates_raw if isinstance(templates_raw, list) else []

        # Cache the result
        self._scenario_cache[cache_key] = templates
        return templates

    def get_optimized_random_templates(
        self, category: str, scenario: str, count: int
    ) -> list[str]:
        """Get random templates."""
        available_templates = self.get_templates_for_scenario(category, scenario)

        if not available_templates:
            self.logger.warning(
                "No templates found for scenario '%s' in "
                "category '%s'. "
                "Using default template. Available categories: %s",
                scenario,
                category,
                list(self._template_cache.keys()),
            )
            return [f"Step {{step_index}}: Perform {scenario} operation in {category}"]

        self.logger.debug(
            "Template selection: category='%s', "
            "scenario='%s', requested=%d, "
            "available=%d",
            category,
            scenario,
            count,
            len(available_templates),
        )

        # Optimize: use random.sample when possible, fall back to
        # choices for replacement
        if count <= len(available_templates):
            selected = random.sample(available_templates, count)
            self.logger.debug("Using random.sample for %d unique templates", count)
            return selected

        # Need more templates than available, use choices with replacement
        selected = random.choices(available_templates, k=count)
        self.logger.debug(
            "Using random.choices with replacement for %d templates from %d available",
            count,
            len(available_templates),
        )
        return selected

    def get_scenario_complexity(self, scenario: str) -> str:
        """Get complexity level for a scenario."""
        complexity_map = {
            "user_authentication": "low",
            "microservices_integration": "high",
            "enterprise_data_operations": "high",
            "e2e_workflow": "very_high",
            "performance_testing": "very_high",
            "data_pipeline_testing": "high",
            "cloud_native_operations": "medium",
            "security_testing": "high",
        }
        return complexity_map.get(scenario, "medium")

    def get_scenario_steps_range(
        self, scenario: str, complexity: str
    ) -> tuple[int, int]:
        """Get the steps range for a scenario and complexity."""
        base_ranges = {
            "user_authentication": (3, 6),
            "microservices_integration": (5, 10),
            "enterprise_data_operations": (4, 8),
            "e2e_workflow": (8, 15),
            "performance_testing": (6, 12),
            "data_pipeline_testing": (5, 10),
            "cloud_native_operations": (4, 9),
            "security_testing": (6, 12),
        }

        min_steps, max_steps = base_ranges.get(scenario, (3, 8))

        # Adjust based on complexity
        if complexity == "very_high":
            min_steps = max(min_steps, 8)
            max_steps = min(max_steps + 5, 20)
        elif complexity == "high":
            min_steps = max(min_steps, 5)
            max_steps = min(max_steps + 3, 15)
        elif complexity == "low":
            max_steps = min(max_steps, 6)

        return (min_steps, max_steps)

    def get_scenario_info(
        self, category: str, scenario: str, complexity_override: str | None = None
    ) -> dict[str, Any]:
        """Get scenario information."""
        complexity = complexity_override or self.get_scenario_complexity(scenario)
        min_steps, max_steps = self.get_scenario_steps_range(scenario, complexity)
        templates = self.get_templates_for_scenario(category, scenario)

        return {
            "complexity": complexity,
            "steps_count": (min_steps, max_steps),
            "templates": templates,
            "description": (
                f"Enterprise {category} test for "
                f"{scenario.replace('_', ' ')} functionality"
            ),
            "category": category,
            "scenario": scenario,
        }

    def refresh_cache(self) -> None:
        """Clear and rebuild template cache."""
        self._scenario_cache.clear()
        self._template_cache.clear()
        self._build_template_cache()

    def get_available_scenarios(self) -> dict[str, dict[str, list[str]]]:
        """Get all available scenarios organized by category."""
        return {
            "regression": {
                "web_automation": ["user_authentication", "e2e_workflow"],
                "api_testing": ["microservices_integration"],
                "database_testing": ["enterprise_data_operations"],
            },
            "smoke": {
                "web_automation": ["user_authentication"],
                "api_testing": ["microservices_integration"],
                "infrastructure_testing": ["cloud_native_operations"],
            },
            "integration": {
                "web_automation": ["e2e_workflow", "performance_testing"],
                "api_testing": ["microservices_integration", "data_pipeline_testing"],
                "database_testing": ["enterprise_data_operations"],
                "infrastructure_testing": [
                    "cloud_native_operations",
                    "security_testing",
                ],
            },
            "e2e": {
                "web_automation": ["e2e_workflow"],
                "api_testing": ["microservices_integration"],
                "database_testing": ["enterprise_data_operations"],
                "infrastructure_testing": ["cloud_native_operations"],
            },
        }

    def validate_scenario(self, category: str, scenario: str) -> bool:
        """Validate if a scenario exists in the given category."""
        scenarios = self.get_available_scenarios()
        return category in scenarios and any(
            scenario in scenario_list for scenario_list in scenarios[category].values()
        )
