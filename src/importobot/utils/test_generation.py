"""
Simplified test generation utility focusing on realistic test data creation.

This module uses the shared keyword registry and business domain templates
to generate test suites for integration testing and demos.
"""

import json
import random
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from typing_extensions import TypedDict

from ..core.business_domains import BusinessDomainTemplates, TestCaseTemplates
from ..core.keywords_registry import RobotFrameworkKeywordRegistry


class CategoryInfo(TypedDict):
    """TypedDict for category information."""

    dir: Path
    count: int


class CategoryEnum(Enum):
    """Enumeration of supported test categories for distribution weights."""

    REGRESSION = "regression"
    SMOKE = "smoke"
    INTEGRATION = "integration"
    E2E = "e2e"

    @classmethod
    def get_default_weights(cls) -> Dict["CategoryEnum", float]:
        """Get default distribution weights for enterprise testing."""
        return {
            cls.REGRESSION: 0.3125,  # 31.25%
            cls.SMOKE: 0.1875,  # 18.75%
            cls.INTEGRATION: 0.25,  # 25%
            cls.E2E: 0.25,  # 25%
        }

    @classmethod
    def from_string(cls, category_str: str) -> "CategoryEnum":
        """Convert string to CategoryEnum enum."""
        for category in cls:
            if category.value == category_str:
                return category
        raise ValueError(f"Unknown test category: {category_str}")

    @classmethod
    def get_all_values(cls) -> List[str]:
        """Get all category values as strings."""
        return [category.value for category in cls]


# Type aliases for flexibility in weight specification
WeightsDict = Union[Dict["CategoryEnum", float], Dict[str, float]]
DistributionDict = Dict[str, int]


class EnterpriseTestGenerator:
    """
    Simplified enterprise test generator focusing on realistic test data creation.
    Uses shared business domain templates and keyword registry.
    """

    def __init__(self) -> None:
        """Initialize with shared business domain templates."""
        # Use shared templates instead of duplicating them
        self.business_scenarios = BusinessDomainTemplates.ENTERPRISE_SCENARIOS
        self.enterprise_data = BusinessDomainTemplates.ENTERPRISE_DATA_POOLS

    def generate_realistic_test_data(self) -> Dict[str, str]:
        """Generate realistic test data based on scenario context."""
        base_data = {
            "base_url": f"https://app.{random.choice(self.enterprise_data['domains'])}",
            "portal_url": (
                f"https://portal.{random.choice(self.enterprise_data['domains'])}"
            ),
            "username": random.choice(self.enterprise_data["usernames"]),
            "password": random.choice(self.enterprise_data["passwords"]),
            "email": (
                f"{random.choice(self.enterprise_data['usernames'])}"
                f"@{random.choice(self.enterprise_data['email_domains'])}"
            ),
            "user_role": random.choice(self.enterprise_data["user_roles"]),
            "business_module": random.choice(self.enterprise_data["business_modules"]),
            "entity_type": random.choice(self.enterprise_data["entity_types"]),
            "cloud_provider": random.choice(self.enterprise_data["cloud_providers"]),
            "orchestrator": random.choice(self.enterprise_data["orchestrators"]),
            "db_cluster": f"{random.choice(self.enterprise_data['databases'])}-cluster-"
            f"{random.randint(1, 5)}",
            "queue_system": random.choice(self.enterprise_data["queue_systems"]),
            "sso_provider": random.choice(self.enterprise_data["sso_providers"]),
            "scan_type": random.choice(self.enterprise_data["scan_types"]),
            "verification_code": f"{random.randint(100000, 999999)}",
            "concurrent_users": str(random.randint(100, 1000)),
            "sla_threshold": str(random.randint(500, 2000)),
            "entity_id": f"ENT-{random.randint(10000, 99999)}",
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "session_token": f"token_{random.randint(1000000, 9999999)}",
            "api_version": f"v{random.randint(1, 3)}.{random.randint(0, 9)}",
            "test_environment": random.choice(
                ["staging", "uat", "integration", "performance"]
            ),
            "data_volume": f"{random.randint(10, 1000)}GB",
            "field_set": f"fields_{random.randint(1, 10)}",
            "validation_set": f"rules_{random.randint(1, 5)}",
            "approval_chain": f"chain_{random.randint(1, 3)}",
            "transformation_set": f"transform_{random.randint(1, 8)}",
            "data_sources": f"sources_{random.randint(2, 6)}",
            "integration_targets": ", ".join(
                random.sample(self.enterprise_data["integration_targets"], 2)
            ),
        }

        return base_data

    def generate_enterprise_test_step(
        self, template: str, test_data: Dict[str, str], step_index: int
    ) -> Dict[str, Any]:
        """Generate a sophisticated test step with realistic enterprise context."""
        try:
            step_description = template.format(**test_data)
        except KeyError:
            step_description = template

        # Enhanced step metadata for enterprise scenarios
        return {
            "description": step_description,
            "testData": self._extract_test_data_from_template(template, test_data),
            "expectedResult": self._generate_expected_result_for_step(step_description),
            "stepType": self._determine_step_type(template),
            "index": step_index,
            "estimatedDuration": self._estimate_step_duration(template),
            "criticalityLevel": self._determine_criticality(template),
            "dependencies": self._identify_dependencies(template, step_index),
        }

    def _extract_test_data_from_template(
        self, template: str, test_data: Dict[str, str]
    ) -> str:
        """Extract and format test data from template."""
        # Identify the type of operation and format accordingly
        if "Navigate to" in template or "url" in template.lower():
            return f"URL: {test_data.get('base_url', 'https://example.com')}"
        if "username" in template.lower() and "password" in template.lower():
            return (
                f"Credentials: {test_data.get('username', 'user')}, "
                f"Password: {test_data.get('password', 'pass')}"
            )
        if "database" in template.lower() or "sql" in template.lower():
            return (
                f"Database: {test_data.get('db_cluster', 'test-db')}, "
                "Query timeout: 30s"
            )
        if "api" in template.lower() or "POST" in template or "GET" in template:
            return (
                f"API Endpoint: {test_data.get('api_version', 'v1')}, "
                "Content-Type: application/json"
            )
        if "cloud" in template.lower() or "container" in template.lower():
            return (
                f"Cloud Provider: {test_data.get('cloud_provider', 'AWS')}, "
                f"Environment: {test_data.get('test_environment', 'staging')}"
            )
        # Generic data extraction
        return f"Test context: {template[:50]}..."

    def _generate_expected_result_for_step(self, step_description: str) -> str:
        """Generate sophisticated expected results based on step description."""
        if (
            "authenticate" in step_description.lower()
            or "login" in step_description.lower()
        ):
            return (
                "Authentication successful, user session established, "
                "security tokens generated"
            )
        if "navigate" in step_description.lower():
            return "Page loads successfully, response time < 3s, no console errors"
        if (
            "verify" in step_description.lower()
            or "validate" in step_description.lower()
        ):
            return (
                "Validation passes, data integrity confirmed, "
                "compliance requirements met"
            )
        if "execute" in step_description.lower() or "test" in step_description.lower():
            return (
                "Operation completes successfully, performance metrics within "
                "acceptable range"
            )
        if "monitor" in step_description.lower():
            return "Monitoring data collected, alerts triggered if thresholds exceeded"
        if "security" in step_description.lower():
            return "Security controls function correctly, no vulnerabilities detected"
        return "Step completes successfully, system state remains consistent"

    def _determine_step_type(self, template: str) -> str:
        """Determine the type of test step based on template content."""
        template_lower = template.lower()
        if "navigate" in template_lower or "open" in template_lower:
            return "navigation"
        if "authenticate" in template_lower or "login" in template_lower:
            return "authentication"
        if "verify" in template_lower or "validate" in template_lower:
            return "verification"
        if "execute" in template_lower or "run" in template_lower:
            return "execution"
        if "monitor" in template_lower or "measure" in template_lower:
            return "monitoring"
        if "configure" in template_lower or "initialize" in template_lower:
            return "configuration"
        return "action"

    def _estimate_step_duration(self, template: str) -> str:
        """Estimate realistic step duration based on complexity."""
        template_lower = template.lower()
        if "performance" in template_lower or "load" in template_lower:
            return f"{random.randint(5, 15)} minutes"
        if "security" in template_lower or "penetration" in template_lower:
            return f"{random.randint(10, 30)} minutes"
        if "navigate" in template_lower or "click" in template_lower:
            return f"{random.randint(5, 30)} seconds"
        if "verify" in template_lower or "validate" in template_lower:
            return f"{random.randint(1, 5)} minutes"
        return f"{random.randint(30, 180)} seconds"

    def _determine_criticality(self, template: str) -> str:
        """Determine step criticality level."""
        template_lower = template.lower()
        if "security" in template_lower or "authenticate" in template_lower:
            return "critical"
        if "verify" in template_lower or "validate" in template_lower:
            return "high"
        if "monitor" in template_lower or "performance" in template_lower:
            return "medium"
        return "low"

    def _identify_dependencies(self, template: str, step_index: int) -> List[int]:
        """Identify step dependencies based on content and position."""
        dependencies = []
        template_lower = template.lower()

        # Steps that typically depend on previous authentication
        if any(
            keyword in template_lower
            for keyword in ["verify", "validate", "execute", "monitor"]
        ):
            if step_index > 0:
                dependencies.append(step_index - 1)

        # Steps that depend on initial setup
        if any(
            keyword in template_lower for keyword in ["cleanup", "logout", "terminate"]
        ):
            if step_index > 2:
                dependencies.extend([0, 1])

        return dependencies

    def generate_enterprise_test_case(
        self,
        category: str,
        scenario: str,
        test_id: int,
        complexity_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an enterprise test case."""
        if category not in self.business_scenarios:
            raise ValueError(f"Unknown category: {category}")

        # Get scenario information
        scenario_templates = self.business_scenarios[category]
        if scenario not in scenario_templates:
            scenario = random.choice(list(scenario_templates.keys()))

        scenario_info = scenario_templates[scenario]
        complexity = cast(str, complexity_override or scenario_info["complexity"])

        # Generate test data and steps
        test_data = self.generate_realistic_test_data()
        steps = self._generate_test_steps(scenario_info, complexity, test_data)

        test_case = {}
        # Generate test metadata
        test_context = {"steps": steps, "test_data": test_data}
        metadata = self._generate_test_case_metadata(
            category=category,
            scenario=scenario,
            test_id=test_id,
            complexity=complexity,
            test_context=test_context,
        )
        test_case.update(metadata)

        return test_case

    def _generate_test_steps(
        self, scenario_info: Dict[str, Any], complexity: str, test_data: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Generate test steps for a test case."""
        min_steps, max_steps = scenario_info["steps_count"]

        # Select appropriate number of steps based on complexity
        if complexity == "very_high":
            num_steps = random.randint(max(min_steps, 12), max_steps)
        elif complexity == "high":
            num_steps = random.randint(max(min_steps, 8), min(max_steps, 14))
        else:
            num_steps = random.randint(min_steps, max(min_steps + 4, max_steps - 4))

        # Generate steps
        templates = scenario_info["templates"]
        selected_templates = random.sample(templates, min(num_steps, len(templates)))
        if len(selected_templates) < num_steps:
            # Add some repeated templates with variations
            selected_templates.extend(
                random.choices(templates, k=num_steps - len(selected_templates))
            )

        steps = []
        for i, template in enumerate(selected_templates):
            step = self.generate_enterprise_test_step(template, test_data, i)
            steps.append(step)

        return steps

    def _generate_test_case_metadata(
        self,
        *,
        category: Any,
        scenario: Any,
        test_id: Any,
        complexity: Any,
        test_context: Any,
    ) -> Dict[str, Any]:
        created_date = datetime.now() - timedelta(days=random.randint(1, 180))
        updated_date = created_date + timedelta(days=random.randint(1, 30))
        return {
            "key": f"ENTERPRISE-{test_id:04d}",
            "name": f"{category.replace('_', ' ').title()} - "
            f"{scenario.replace('_', ' ').title()} Test Case {test_id}",
            "description": self.business_scenarios[category][scenario]["description"],
            "testObjective": f"Validate {scenario.replace('_', ' ')} functionality in "
            f"enterprise environment",
            "owner": f"TESTENG{random.randint(1000, 9999)}",
            "createdBy": f"AUTOMATION{random.randint(100, 999)}",
            "updatedBy": f"TESTENG{random.randint(1000, 9999)}",
            "createdOn": created_date.isoformat() + "Z",
            "updatedOn": updated_date.isoformat() + "Z",
            "priority": self._determine_test_priority(complexity),
            "status": random.choice(
                ["Approved", "Ready for Execution", "Under Review"]
            ),
            "labels": [category, scenario, complexity, "enterprise", "automated"],
            "projectKey": "ENTERPRISE",
            "folder": f"/Enterprise Tests/{category.replace('_', ' ').title()}",
            "latestVersion": True,
            "estimatedDuration": self._calculate_total_duration(test_context["steps"]),
            "complexityScore": self._calculate_complexity_score(
                complexity, len(test_context["steps"])
            ),
            "riskLevel": self._determine_risk_level(category, complexity),
            "environmentRequirements": self._determine_environment_requirements(
                category
            ),
            "testData": test_context["test_data"],
            "testScript": {
                "id": random.randint(100000, 999999),
                "type": "STEP_BY_STEP_ENTERPRISE",
                "steps": test_context["steps"],
                "setupInstructions": self._generate_setup_instructions(category),
                "teardownInstructions": self._generate_teardown_instructions(category),
            },
            "automationReadiness": self._assess_automation_readiness(
                category, complexity
            ),
            "complianceRequirements": self._identify_compliance_requirements(category),
            "customFields": {
                "Test Level": "Enterprise Integration",
                "Automation Framework": "Robot Framework",
                "CI/CD Integration": "Yes",
                "Performance Impact": self._assess_performance_impact(complexity),
                "Security Classification": self._determine_security_classification(
                    category
                ),
                "Business Impact": self._assess_business_impact(complexity),
            },
        }

    def _determine_test_priority(self, complexity: str) -> str:
        """Determine test priority based on complexity."""
        priority_map = {
            "very_high": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        return priority_map.get(complexity, "Medium")

    def _calculate_total_duration(self, steps: List[Dict[str, Any]]) -> str:
        """Calculate total estimated test duration."""
        total_minutes = 0.0
        for step in steps:
            duration_str = step.get("estimatedDuration", "1 minute")
            if "second" in duration_str:
                seconds = int(duration_str.split()[0])
                total_minutes += seconds / 60
            elif "minute" in duration_str:
                minutes = int(duration_str.split()[0])
                total_minutes += minutes

        if total_minutes < 60:
            return f"{int(total_minutes)} minutes"
        hours = int(total_minutes // 60)
        remaining_minutes = int(total_minutes % 60)
        return f"{hours}h {remaining_minutes}m"

    def _calculate_complexity_score(self, complexity: str, num_steps: int) -> int:
        """Calculate numerical complexity score."""
        base_scores = {"very_high": 90, "high": 70, "medium": 50, "low": 30}
        base_score = base_scores.get(complexity, 50)
        step_bonus = min(num_steps * 2, 20)  # Cap at 20 points
        return base_score + step_bonus

    def _determine_risk_level(self, category: str, complexity: str) -> str:
        """Determine risk level based on category and complexity."""
        high_risk_categories = ["infrastructure_testing", "database_testing"]
        if category in high_risk_categories and complexity in ["high", "very_high"]:
            return "High"
        if complexity == "very_high":
            return "Medium-High"
        if complexity == "high":
            return "Medium"
        return "Low"

    def _determine_environment_requirements(self, category: str) -> List[str]:
        """Determine environment requirements based on category."""
        return BusinessDomainTemplates.get_environment_requirements(category)

    def _generate_setup_instructions(self, category: str) -> List[str]:
        """Generate setup instructions based on category."""
        return BusinessDomainTemplates.get_setup_instructions(category)

    def _generate_teardown_instructions(self, category: str) -> List[str]:
        """Generate teardown instructions based on category."""
        return BusinessDomainTemplates.get_teardown_instructions(category)

    def _assess_automation_readiness(self, category: str, complexity: str) -> str:
        """Assess automation readiness based on category and complexity."""
        return TestCaseTemplates.get_automation_readiness(category, complexity)

    def _identify_compliance_requirements(self, category: str) -> List[str]:
        """Identify compliance requirements based on category."""
        return BusinessDomainTemplates.get_compliance_requirements(category)

    def _assess_performance_impact(self, complexity: str) -> str:
        """Assess performance impact based on complexity."""
        impact_map = {
            "very_high": "High - Resource intensive",
            "high": "Medium - Moderate resource usage",
            "medium": "Low - Minimal resource usage",
            "low": "Minimal - Lightweight execution",
        }
        return impact_map.get(complexity, "Low")

    def _determine_security_classification(self, category: str) -> str:
        """Determine security classification based on category."""
        return TestCaseTemplates.get_security_classification(category)

    def _assess_business_impact(self, complexity: str) -> str:
        """Assess business impact based on complexity."""
        impact_map = {
            "very_high": "Critical - Core business functionality",
            "high": "High - Important business processes",
            "medium": "Medium - Supporting processes",
            "low": "Low - Minor functionality",
        }
        return impact_map.get(complexity, "Medium")

    def _get_test_distribution(
        self,
        total_tests: int,
        distribution: Optional[DistributionDict] = None,
        weights: Optional[WeightsDict] = None,
    ) -> DistributionDict:
        """Get normalized test distribution from weights or absolute counts."""
        # Use absolute distribution if provided (takes precedence over weights)
        if distribution is not None:
            # Create a copy to avoid modifying the input
            distribution_copy: DistributionDict = distribution.copy()
            # Ensure distribution adds up to total_tests
            current_total = sum(distribution_copy.values())
            if current_total != total_tests:
                # Adjust the largest category
                largest_category = max(
                    distribution_copy.keys(), key=lambda k: distribution_copy[k]
                )
                distribution_copy[largest_category] += total_tests - current_total
            return distribution_copy

        # If weights are provided, calculate distribution from weights
        if weights is not None:
            # Convert enum-based weights to string-based for consistency
            string_weights = {}
            for key, value in weights.items():
                if isinstance(key, CategoryEnum):
                    string_weights[key.value] = value
                else:
                    # Validate string-based category
                    if key not in CategoryEnum.get_all_values():
                        raise ValueError(
                            f"Invalid test category: {key}. Valid categories: "
                            f"{CategoryEnum.get_all_values()}"
                        )
                    string_weights[key] = value

            # Normalize weights to sum to 1.0
            total_weight = sum(string_weights.values())
            if total_weight == 0:
                raise ValueError("Total weight cannot be zero")

            normalized_weights = {
                k: v / total_weight for k, v in string_weights.items()
            }
            computed_distribution: DistributionDict = {
                k: int(total_tests * weight) for k, weight in normalized_weights.items()
            }

            # Adjust for rounding errors
            current_total = sum(computed_distribution.values())
            if current_total != total_tests:
                # Add remaining tests to the largest category
                largest_category = max(
                    computed_distribution.keys(), key=lambda k: computed_distribution[k]
                )
                computed_distribution[largest_category] += total_tests - current_total

            return computed_distribution

        # Use default weights from enum
        return self._get_test_distribution(
            total_tests, None, CategoryEnum.get_default_weights()
        )

    def _get_category_scenarios(self) -> Dict[str, Dict[str, List[str]]]:
        """Get category to business scenario mapping."""
        return {
            "regression": {
                "web_automation": ["user_authentication", "e2e_workflow"],
                "api_testing": ["microservices_integration", "data_pipeline_testing"],
                "database_testing": ["enterprise_data_operations"],
                "infrastructure_testing": ["cloud_native_operations"],
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

    def generate_test_suite(
        self,
        output_dir: str,
        total_tests: int = 800,
        distribution: Optional[DistributionDict] = None,
        weights: Optional[WeightsDict] = None,
    ) -> DistributionDict:
        """Generate an enterprise test suite.

        Args:
            output_dir: Directory to save generated test files
            total_tests: Total number of tests to generate
            distribution: Absolute test count per category
                (e.g., {"regression": 250, "smoke": 150})
            weights: Relative weights per category.
                Can use CategoryEnum enum or strings:
                    - Enum: {CategoryEnum.REGRESSION: 0.5, CategoryEnum.SMOKE: 0.3}
                    - String: {"regression": 0.5, "smoke": 0.3, "integration": 0.2}
                    Weights will be normalized to sum to 1.0 automatically.

        Note: If both distribution and weights are provided,
              distribution takes precedence.
              Valid categories: {CategoryEnum.get_all_values()}
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        distribution = self._get_test_distribution(total_tests, distribution, weights)
        category_scenarios = self._get_category_scenarios()

        generated_counts = {}
        test_id = 1

        for category, count in distribution.items():
            # Handle category directory setup
            category_info: CategoryInfo = {
                "dir": Path(output_dir) / category,
                "count": 0,
            }
            category_info["dir"].mkdir(exist_ok=True)
            generated_counts[category] = 0

            # Generate tests for this category
            self._generate_category_tests(
                category=category,
                count=count,
                scenarios=category_scenarios[category],
                category_info=category_info,
                generated_counts=generated_counts,
                start_test_id=test_id,
            )
            test_id += count

        return generated_counts

    def _generate_category_tests(
        self,
        *,
        category: str,
        count: int,
        scenarios: Dict[str, List[str]],
        category_info: CategoryInfo,
        generated_counts: Dict[str, int],
        start_test_id: int,
    ) -> None:
        """Generate tests for a specific category."""
        tests_per_scenario_type = count // len(scenarios)
        remainder = count % len(scenarios)
        test_id = start_test_id

        for business_category, scenario_list in scenarios.items():
            scenario_count = tests_per_scenario_type
            if remainder > 0:
                scenario_count += 1
                remainder -= 1

            for _ in range(scenario_count):
                scenario = random.choice(scenario_list)
                test_case = self.generate_enterprise_test_case(
                    business_category, scenario, test_id
                )

                filename = f"{business_category}_{scenario}_{test_id:04d}.json"
                file_path = category_info["dir"] / filename

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(test_case, f, indent=2, ensure_ascii=False)

                generated_counts[category] += 1
                test_id += 1

    def generate_random_json(self, structure: Optional[str] = None) -> Dict[str, Any]:
        """Generate random JSON test artifact using keyword mapping."""
        if structure is None:
            structure = random.choice(TestCaseTemplates.get_available_structures())

        # Generate random keywords for sophisticated testing
        keywords = self._get_random_keyword_combination()

        # Generate enterprise-quality steps
        steps = []
        test_data = self.generate_realistic_test_data()

        for i, kw in enumerate(keywords):
            step = {
                "description": f"Execute {kw['description'].lower()}",
                "testData": self.generate_keyword_specific_data(kw, test_data),
                "expectedResult": f"{kw['description']} completes successfully",
                "index": i,
                "stepType": "execution",
                "estimatedDuration": "30 seconds",
                "criticalityLevel": "medium",
            }
            steps.append(step)

        # Generate test metadata
        test_name = self._generate_enterprise_test_name()
        description = self._generate_enterprise_description()
        labels = self._generate_enterprise_labels()

        if structure == "zephyr_basic":
            return self._create_zephyr_basic_json(test_name, description, labels, steps)

        if structure == "zephyr_nested":
            return self._create_zephyr_nested_json(
                test_name, description, labels, steps
            )

        if structure == "simple_tests_array":
            return self._create_simple_tests_array_json(test_name, description, steps)

        if structure == "test_suite_format":
            return self._create_test_suite_format_json(
                test_name, description, labels, steps
            )

        if structure == "single_test_object":
            return self._create_single_test_object_json(
                test_name, description, labels, steps
            )

        return {"tests": []}  # Fallback

    def _create_zephyr_basic_json(
        self,
        test_name: str,
        description: str,
        labels: List[str],
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "key": f"ENT-{random.randint(1000, 9999)}",
            "name": test_name,
            "description": description,
            "objective": description,
            "priority": random.choice(["Critical", "High", "Medium", "Low"]),
            "labels": labels,
            "status": random.choice(["Approved", "Ready", "Under Review"]),
            "testScript": {"type": "STEP_BY_STEP", "steps": steps},
            "environmentRequirements": ["Enterprise Test Environment"],
            "automationReadiness": "High",
        }

    def _create_zephyr_nested_json(
        self,
        test_name: str,
        description: str,
        labels: List[str],
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "projectKey": "ENTERPRISE",
            "name": test_name,
            "description": description,
            "priority": random.choice(["Critical", "High", "Medium"]),
            "labels": labels,
            "testScript": {"type": "STEP_BY_STEP_ENTERPRISE", "steps": steps},
            "customFields": {
                "Test Level": "Enterprise Integration",
                "Automation Framework": "Robot Framework",
            },
        }

    def _create_simple_tests_array_json(
        self, test_name: str, description: str, steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {
            "tests": [{"name": test_name, "description": description, "steps": steps}]
        }

    def _create_test_suite_format_json(
        self,
        test_name: str,
        description: str,
        labels: List[str],
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "testSuite": f"Enterprise Test Suite - {test_name}",
            "description": f"Suite containing {test_name}",
            "tests": [
                {
                    "name": test_name,
                    "description": description,
                    "labels": labels,
                    "steps": steps,
                }
            ],
        }

    def _create_single_test_object_json(
        self,
        test_name: str,
        description: str,
        labels: List[str],
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "name": test_name,
            "description": description,
            "labels": labels,
            "priority": random.choice(["P1", "P2", "P3"]),
            "steps": steps,
            "estimatedDuration": self._calculate_total_duration(steps),
            "automationReadiness": "High",
        }

    def generate_keyword_specific_data(
        self, keyword: Dict[str, Any], test_data: Dict[str, str]
    ) -> str:
        """Generate keyword-specific test data."""
        intent = keyword["intent"]
        if intent.startswith("web_"):
            return (
                f"Browser: Chrome, URL: "
                f"{test_data.get('base_url', 'https://example.com')}"
            )
        if intent.startswith("api_"):
            return f"API: {test_data.get('api_version', 'v1')}, Auth: Bearer token"
        if intent.startswith("db_"):
            return (
                f"Database: {test_data.get('db_cluster', 'test-db')}, "
                f"Connection pool: 10"
            )
        if intent.startswith("ssh_"):
            return f"Host: {test_data.get('cloud_provider', 'test-server')}, Port: 22"
        return f"Context: {keyword['description']}"

    def _generate_enterprise_test_name(self) -> str:
        """Generate enterprise-quality test name."""
        actions = ["Validate", "Verify", "Test", "Execute", "Confirm", "Assess"]
        subjects = [
            "Enterprise Authentication Workflow",
            "Microservices Integration",
            "Data Pipeline Operations",
            "Cloud Infrastructure Deployment",
            "Security Compliance Validation",
            "Performance Optimization",
            "Business Process Automation",
            "API Gateway Configuration",
        ]
        return f"{random.choice(actions)} {random.choice(subjects)}"

    def _generate_enterprise_description(self) -> str:
        """Generate enterprise-quality test description."""
        templates = [
            "Comprehensive validation of enterprise system functionality ensuring "
            "compliance with business requirements and technical specifications",
            "End-to-end testing of critical business processes with focus on security, "
            "performance, and reliability",
            "Integration testing across multiple enterprise components validating data "
            "flow and system interactions",
            "Validation of enterprise architecture components ensuring scalability and "
            "maintainability",
            "Business process verification with emphasis on user experience and "
            "operational efficiency",
        ]
        return random.choice(templates)

    def _generate_enterprise_labels(self) -> List[str]:
        """Generate enterprise-appropriate labels."""
        num_labels = random.randint(3, 6)
        return TestCaseTemplates.get_enterprise_labels(num_labels)

    def _get_random_keyword_combination(
        self, num_keywords: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generate random combination of RF keywords using shared registry."""
        if num_keywords is None:
            num_keywords = random.randint(4, 10)

        keywords = []
        intent_keys = list(
            RobotFrameworkKeywordRegistry.INTENT_TO_LIBRARY_KEYWORDS.keys()
        )

        for _ in range(num_keywords):
            intent = random.choice(intent_keys)
            library, keyword = RobotFrameworkKeywordRegistry.get_intent_keyword(intent)
            keyword_info = RobotFrameworkKeywordRegistry.get_keyword_info(
                library, keyword
            )

            keywords.append(
                {
                    "intent": intent,
                    "library": library,
                    "keyword": keyword,
                    "args": keyword_info.get("args", []),
                    "description": keyword_info.get("description", "Execute operation"),
                }
            )

        return keywords


# Convenience functions for easy access
def generate_test_suite(
    output_dir: str,
    total_tests: int = 800,
    distribution: Optional[DistributionDict] = None,
    weights: Optional[WeightsDict] = None,
) -> DistributionDict:
    """Generate a test suite using the enterprise generator.

    Args:
        output_dir: Directory to save generated test files
        total_tests: Total number of tests to generate
        distribution: Absolute test count per category
            (e.g., {"regression": 250, "smoke": 150})
        weights: Relative weights per category. Can use CategoryEnum enum or strings:
                - Enum: {CategoryEnum.REGRESSION: 0.5, CategoryEnum.SMOKE: 0.3}
                - String: {"regression": 0.5, "smoke": 0.3, "integration": 0.2}
                Weights will be normalized to sum to 1.0 automatically.

    Note: If both distribution and weights are provided, distribution takes precedence.
          Valid categories: regression, smoke, integration, e2e
    """
    generator = EnterpriseTestGenerator()
    return generator.generate_test_suite(output_dir, total_tests, distribution, weights)


def generate_random_test_json(
    structure: Optional[str] = None, complexity: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a random JSON test artifact."""
    # pylint: disable=unused-argument  # complexity may be used in future enhancements
    generator = EnterpriseTestGenerator()
    return generator.generate_random_json(structure)


def get_available_structures() -> List[str]:
    """Get list of available JSON structures."""
    return TestCaseTemplates.get_available_structures()


def get_required_libraries_for_keywords(keywords: List[Dict[str, Any]]) -> List[str]:
    """Get required Robot Framework libraries for given keywords."""
    return RobotFrameworkKeywordRegistry.get_required_libraries(keywords)


def print_test_distribution(counts: DistributionDict) -> None:
    """Print test distribution summary in a consistent format.

    Args:
        counts: Dictionary mapping test category names to count values
    """
    print("Generated test distribution:")
    total = 0
    for category, count in counts.items():
        print(f"  {category}: {count} tests")
        total += count
    print(f"  Total: {total} tests")


def generate_keyword_list(num_keywords: int) -> List[Dict[str, Any]]:
    """Generate a list of random keywords with metadata.

    Args:
        num_keywords: Number of keywords to generate

    Returns:
        List of keyword dictionaries with intent, library, keyword, args,
        and description
    """
    keywords = []
    intent_keys = list(RobotFrameworkKeywordRegistry.INTENT_TO_LIBRARY_KEYWORDS.keys())

    for _ in range(num_keywords):
        intent = intent_keys[_ % len(intent_keys)]
        library, keyword = RobotFrameworkKeywordRegistry.get_intent_keyword(intent)
        keyword_info = RobotFrameworkKeywordRegistry.get_keyword_info(library, keyword)
        keywords.append(
            {
                "intent": intent,
                "library": library,
                "keyword": keyword,
                "args": keyword_info.get("args", []),
                "description": keyword_info.get("description", "Execute operation"),
            }
        )

    return keywords
