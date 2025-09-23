"""Core test generation logic and enterprise test generator."""

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from importobot.core.business_domains import BusinessDomainTemplates, TestCaseTemplates
from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.utils.defaults import (
    KEYWORD_PATTERNS,
    PROGRESS_CONFIG,
    get_default_value,
)
from importobot.utils.progress_reporter import BatchProgressReporter, ProgressReporter
from importobot.utils.resource_manager import get_resource_manager
from importobot.utils.test_generation.categories import CategoryInfo
from importobot.utils.test_generation.distributions import (
    DistributionDict,
    DistributionManager,
    WeightsDict,
)
from importobot.utils.test_generation.templates import TemplateManager

# Resource limits to prevent exhaustion
MAX_TOTAL_TESTS = 50000  # Maximum number of tests in a single generation
MAX_FILE_SIZE_MB = 100  # Maximum size per generated file in MB
MAX_MEMORY_USAGE_MB = 500  # Maximum memory usage for generation process


class EnterpriseTestGenerator:
    """
    Advanced test generator for enterprise-scale Robot Framework test suites.

    Generates realistic, production-ready test cases across multiple business domains
    with sophisticated test data, enterprise-grade scenarios, and comprehensive
    metadata.
    """

    def __init__(self) -> None:
        """Initialize enterprise test generator with domain templates and keywords."""
        self.domain_templates = BusinessDomainTemplates()
        self.test_templates = TestCaseTemplates()
        self.keyword_registry = RobotFrameworkKeywordRegistry()
        self.template_manager = TemplateManager()
        self.resource_manager = get_resource_manager()
        self.logger = logging.getLogger(__name__)
        self._file_write_queue: list[Any] = []

    def generate_realistic_test_data(self) -> dict[str, str]:
        """Generate realistic test data for enterprise scenarios."""
        # Enterprise environment configurations
        environments = ["prod", "staging", "dev", "qa", "uat"]
        regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

        # Enterprise authentication methods
        auth_methods = ["oauth2", "saml", "ldap", "mfa", "jwt"]

        # Enterprise data sources
        databases = ["postgresql", "mysql", "oracle", "sqlserver", "mongodb"]

        # Enterprise systems
        systems = ["erp", "crm", "hr", "finance", "inventory", "reporting"]

        base_data = {
            "environment": random.choice(environments),
            "region": random.choice(regions),
            "auth_method": random.choice(auth_methods),
            "database": random.choice(databases),
            "system": random.choice(systems),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "correlation_id": f"test_{random.randint(100000, 999999)}",
            "user_role": random.choice(["admin", "manager", "analyst", "operator"]),
            "business_unit": random.choice(["finance", "hr", "operations", "sales"]),
        }

        return base_data

    def generate_enterprise_test_step(
        self, template: str, test_data: dict[str, str], step_index: int
    ) -> dict[str, Any]:
        """Generate a sophisticated test step with realistic enterprise context."""
        try:
            step_description = template.format(**test_data)
            self.logger.debug(
                "Successfully formatted template: '%s...' -> '%s...'",
                template[:30],
                step_description[:50],
            )
        except KeyError as e:
            self.logger.error(
                "Template formatting failed for step %d: "
                "Template: '%s' | "
                "Missing key: %s | "
                "Available keys: %s | "
                "Context: enterprise test step generation",
                step_index,
                template,
                e,
                list(test_data.keys()),
            )
            step_description = template
            # Add diagnostic information to help debug template issues
            self.logger.info(
                "Using fallback template without formatting: '%s'", template
            )
        except Exception as e:
            self.logger.error(
                "Unexpected template error for step %d: "
                "Template: '%s' | "
                "Error: %s: %s | "
                "Test data keys: %s",
                step_index,
                template,
                type(e).__name__,
                e,
                list(test_data.keys()),
            )
            step_description = f"Step {step_index}: Template error - {template}"

        # Enhanced step metadata for enterprise scenarios
        return {
            "description": step_description,
            "testData": self._extract_test_data_from_template(template, test_data),
            "expectedResult": self._generate_expected_result_for_step(step_description),
            "stepType": self._determine_step_type(template),
            "index": step_index,
            "estimatedDuration": self._estimate_step_duration(template),
            "riskLevel": self._assess_step_risk_level(step_description),
            "automationComplexity": self._evaluate_automation_complexity(template),
        }

    def _extract_test_data_from_template(
        self, template: str, test_data: dict[str, str]
    ) -> str:
        """Extract relevant test data from template context."""
        # Enhanced test data extraction for enterprise scenarios
        if "database" in template.lower():
            return (
                f"Database: {test_data.get('database', 'N/A')}, "
                f"Environment: {test_data.get('environment', 'N/A')}"
            )
        if "api" in template.lower():
            return (
                f"Endpoint: /api/v1/{test_data.get('system', 'service')}, "
                f"Auth: {test_data.get('auth_method', 'N/A')}"
            )
        if "web" in template.lower() or "browser" in template.lower():
            return (
                f"Environment: {test_data.get('environment', 'N/A')}, "
                f"User Role: {test_data.get('user_role', 'N/A')}"
            )
        if "ssh" in template.lower() or "file" in template.lower():
            return (
                f"Region: {test_data.get('region', 'N/A')}, "
                f"System: {test_data.get('system', 'N/A')}"
            )

        return f"Correlation ID: {test_data.get('correlation_id', 'N/A')}"

    def _generate_expected_result_for_step(self, step_description: str) -> str:
        """Generate realistic expected results for enterprise test steps."""
        # Enhanced expected result generation
        if "login" in step_description.lower():
            return "User successfully authenticated and redirected to dashboard"
        if (
            "query" in step_description.lower()
            or "database" in step_description.lower()
        ):
            return "Query executed successfully with expected data returned"
        if "api" in step_description.lower():
            return "API responds with status 200 and valid JSON payload"
        if "file" in step_description.lower():
            return "File operation completed successfully with proper permissions"
        if "verify" in step_description.lower():
            return "Verification passed with expected values confirmed"

        return "Operation completed successfully with expected outcome"

    def _determine_step_type(self, template: str) -> str:
        """Determine the type of test step for enterprise categorization."""
        template_lower = template.lower()
        if any(
            keyword in template_lower
            for keyword in ["verify", "check", "assert", "validate"]
        ):
            return "verification"
        if any(
            keyword in template_lower
            for keyword in ["click", "input", "select", "enter"]
        ):
            return "action"
        if any(keyword in template_lower for keyword in ["navigate", "open", "go"]):
            return "navigation"
        if any(keyword in template_lower for keyword in ["wait", "pause", "sleep"]):
            return "synchronization"
        return "operation"

    def _estimate_step_duration(self, template: str) -> int:
        """Estimate step execution duration in seconds for enterprise planning."""
        template_lower = template.lower()
        if "database" in template_lower or "query" in template_lower:
            return random.randint(2, 8)  # Database operations
        if "api" in template_lower:
            return random.randint(1, 4)  # API calls
        if "web" in template_lower or "browser" in template_lower:
            return random.randint(3, 10)  # Web interactions
        if "file" in template_lower:
            return random.randint(1, 5)  # File operations
        return random.randint(1, 3)  # Basic operations

    def _assess_step_risk_level(self, step_description: str) -> str:
        """Assess risk level for enterprise test step planning."""
        high_risk_keywords = ["delete", "remove", "truncate", "drop", "production"]
        medium_risk_keywords = ["update", "modify", "insert", "create", "admin"]

        step_lower = step_description.lower()
        if any(keyword in step_lower for keyword in high_risk_keywords):
            return "high"
        if any(keyword in step_lower for keyword in medium_risk_keywords):
            return "medium"
        return "low"

    def _determine_criticality(self, step_description: str) -> str:
        """Determine criticality level for enterprise test step planning."""
        high_risk_keywords = ["delete", "remove", "truncate", "drop", "production"]
        medium_risk_keywords = ["update", "modify", "insert", "create", "admin"]

        step_lower = step_description.lower()
        if any(keyword in step_lower for keyword in high_risk_keywords):
            return "critical"
        if any(keyword in step_lower for keyword in medium_risk_keywords):
            return "high"
        return "medium"

    def _evaluate_automation_complexity(self, template: str) -> str:
        """Evaluate automation complexity for enterprise resource planning."""
        complex_keywords = ["file", "ssh", "database", "integration"]
        simple_keywords = ["click", "input", "verify", "navigate"]

        template_lower = template.lower()
        if any(keyword in template_lower for keyword in complex_keywords):
            return "high"
        if any(keyword in template_lower for keyword in simple_keywords):
            return "low"
        return "medium"

    def generate_enterprise_test_case(
        self,
        category: str,
        scenario: str,
        test_id: int,
        complexity_override: str | None = None,
    ) -> dict[str, Any]:
        """Generate an enterprise test case."""
        # Validate scenario exists
        if not self.template_manager.validate_scenario(category, scenario):
            # Fallback to available scenario
            available_scenarios = self.template_manager.get_available_scenarios()
            if category in available_scenarios:
                scenario = next(iter(available_scenarios[category].values()))[0]
            else:
                category = "regression"
                scenario = "user_authentication"

        # Get scenario information from template manager
        scenario_info = self.template_manager.get_scenario_info(
            category, scenario, complexity_override
        )
        complexity = scenario_info["complexity"]

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
        self, scenario_info: dict[str, Any], complexity: str, test_data: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Generate test steps for a test case."""
        min_steps, max_steps = scenario_info.get("steps_count", (3, 8))

        # Select appropriate number of steps based on complexity
        if complexity == "very_high":
            num_steps = random.randint(max(min_steps, 12), max_steps)
        if complexity == "high":
            num_steps = random.randint(max(min_steps, 8), min(max_steps, 14))
        else:
            num_steps = random.randint(min_steps, max(min_steps + 4, max_steps - 4))

        # Use optimized template selection from template manager
        category = scenario_info.get("category", "regression")
        scenario = scenario_info.get("scenario", "user_authentication")
        selected_templates = self.template_manager.get_optimized_random_templates(
            category, scenario, num_steps
        )

        steps = []
        for i, template in enumerate(selected_templates):
            step = self.generate_enterprise_test_step(template, test_data, i)
            steps.append(step)

        return steps

    def _generate_test_case_metadata(
        self,
        *,
        category: str,
        scenario: str,
        test_id: int,
        complexity: str,
        test_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive test case metadata."""
        created_date = datetime.now() - timedelta(days=random.randint(1, 180))
        updated_date = created_date + timedelta(days=random.randint(1, 30))

        return {
            "key": f"ENTERPRISE-{test_id:04d}",
            "name": (
                f"{category.replace('_', ' ').title()} - "
                f"{scenario.replace('_', ' ').title()} Test Case {test_id}"
            ),
            "description": (
                f"Enterprise test case for {scenario.replace('_', ' ')} functionality"
            ),
            "testObjective": (
                f"Validate {scenario.replace('_', ' ')} functionality in "
                f"enterprise environment"
            ),
            "owner": f"TESTENG{random.randint(1000, 9999)}",
            "createdBy": f"AUTOMATION{random.randint(100, 999)}",
            "updatedBy": f"TESTENG{random.randint(1000, 9999)}",
            "createdOn": created_date.isoformat() + "Z",
            "updatedOn": updated_date.isoformat() + "Z",
            "priority": self._determine_test_priority(complexity),
            "status": random.choice(
                ["Approved", "Ready for Execution", "Under Review"]
            ),
            "estimatedExecutionTime": self._calculate_estimated_execution_time(
                test_context["steps"]
            ),
            "tags": self._generate_test_tags(category, scenario, complexity),
            "testScript": {
                "type": "STEP_BY_STEP",
                "steps": test_context["steps"],
            },
        }

    def _determine_test_priority(self, complexity: str) -> str:
        """Determine test priority based on complexity and business impact."""
        if complexity in ["very_high", "high"]:
            return random.choice(["High", "Critical"])
        if complexity == "medium":
            return random.choice(["Medium", "High"])
        return random.choice(["Low", "Medium"])

    def _calculate_estimated_execution_time(self, steps: list[dict[str, Any]]) -> int:
        """Calculate estimated execution time in seconds."""
        total_time = 0
        for step in steps:
            total_time += step.get("estimatedDuration", 2)

        # Add buffer time for setup and teardown
        buffer_time = int(total_time * 0.2)
        return total_time + buffer_time

    def _generate_test_tags(
        self, category: str, scenario: str, complexity: str
    ) -> list[str]:
        """Generate relevant tags for test categorization."""
        tags = [category, scenario, complexity]

        # Add environment tags
        if "prod" in scenario or "production" in scenario:
            tags.append("production")
        else:
            tags.extend(["regression", "automation"])

        # Add functional tags
        if "api" in scenario:
            tags.append("api-testing")
        if "database" in scenario:
            tags.append("data-testing")
        if "web" in scenario:
            tags.append("ui-testing")

        return tags

    def generate_test_suite(
        self,
        output_dir: str,
        total_tests: int = 800,
        distribution: DistributionDict | None = None,
        weights: WeightsDict | None = None,
    ) -> DistributionDict:
        """Generate an enterprise test suite."""
        # Create output directory before validation
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Comprehensive resource validation
        self.resource_manager.validate_generation_request(total_tests, output_dir)

        # Start operation tracking
        operation_id = self.resource_manager.start_operation(
            f"test_generation_{total_tests}"
        )

        try:
            distribution = DistributionManager.get_test_distribution(
                total_tests, distribution, weights
            )
            category_scenarios = self.template_manager.get_available_scenarios()

            generated_counts: dict[str, int] = {}
            test_id = 1

            for category, count in distribution.items():
                # Check resource limits periodically
                self.resource_manager.check_operation_limits(operation_id)

                # Handle category directory setup
                category_info: CategoryInfo = {
                    "dir": Path(output_dir) / category,
                    "count": 0,
                }
                category_info["dir"].mkdir(exist_ok=True)

                # Get scenarios for this category
                scenarios = category_scenarios.get(category, {})
                self._generate_category_tests(
                    category, count, scenarios, category_info, generated_counts, test_id
                )

                generated_counts[category] = category_info["count"]
                test_id += count

            return generated_counts

        finally:
            # Always finish operation tracking
            self.resource_manager.finish_operation(operation_id)

    def _generate_category_tests(
        # pylint: disable=too-many-positional-arguments,too-many-locals
        self,
        category: str,
        count: int,
        scenarios: dict[str, list[str]],
        category_info: CategoryInfo,
        generated_counts: dict[str, int],
        start_test_id: int,
    ) -> None:
        """Generate tests for a specific category."""
        # Mark unused parameter to avoid lint warning
        _ = generated_counts
        # Comprehensive validation to prevent division by zero and other issues
        if not scenarios:
            raise ValueError(
                f"No scenarios found for category: '{category}'. "
                f"Available: {list(scenarios.keys()) if scenarios else 'None'}"
            )

        if count <= 0:
            self.logger.warning(
                "Invalid count %d for category '%s'. Skipping.", count, category
            )
            return

        # Additional validation for scenario content
        valid_scenarios = {
            k: v for k, v in scenarios.items() if v
        }  # Filter out empty scenario lists
        if not valid_scenarios:
            raise ValueError(
                f"No valid scenarios with content found for category: '{category}'"
            )

        num_scenario_types = len(valid_scenarios)
        tests_per_scenario_type = count // num_scenario_types
        remainder = count % num_scenario_types
        test_id = start_test_id

        self.logger.info(
            "Generating %d tests for category '%s': "
            "%d per scenario type, %d remainder, "
            "%d scenario types",
            count,
            category,
            tests_per_scenario_type,
            remainder,
            num_scenario_types,
        )

        # Initialize progress reporting
        progress_reporter = ProgressReporter(
            self.logger, f"category '{category}' test generation"
        )
        progress_reporter.initialize(count)

        for _business_category, scenario_list in valid_scenarios.items():
            scenario_count = tests_per_scenario_type
            if remainder > 0:
                scenario_count += 1
                remainder -= 1

            for _scenario_index in range(scenario_count):
                scenario = random.choice(scenario_list)
                test_case = self.generate_enterprise_test_case(
                    category, scenario, test_id
                )

                # Queue test case for optimized writing
                filename = f"test_{category}_{test_id:04d}.json"
                filepath = Path(category_info["dir"]) / filename

                self._queue_file_write(filepath, test_case)

                category_info["count"] += 1
                test_id += 1

                # Update progress reporting
                progress_reporter.update()

        # Flush any remaining queued writes
        self._flush_write_queue()

    def _queue_file_write(self, filepath: Path, content: dict[str, Any]) -> None:
        """Queue a file write operation for batching."""
        self._file_write_queue.append({"filepath": filepath, "content": content})

        # Batch write based on configured batch size
        if len(self._file_write_queue) >= PROGRESS_CONFIG.file_write_batch_size:
            self._flush_write_queue()

    def _flush_write_queue(self) -> None:
        """Flush all queued file writes to disk."""
        if not self._file_write_queue:
            return

        queue_size = len(self._file_write_queue)
        self.logger.debug("Writing %d files to disk", queue_size)

        # Initialize batch progress reporter
        batch_reporter = BatchProgressReporter(self.logger, "File write")

        for index, item in enumerate(self._file_write_queue, 1):
            try:
                with open(item["filepath"], "w", encoding="utf-8") as f:
                    json.dump(item["content"], f, indent=2, ensure_ascii=False)

                # Report progress for large batches
                batch_reporter.report_batch_progress(index, queue_size)

            except IOError as e:
                self.logger.error("Failed to write %s: %s", item["filepath"], e)

        self._file_write_queue.clear()

    def _gen_browser_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate browser keyword data."""
        return {
            "data": f"{test_data.get('url', get_default_value('web', 'url'))} "
            f"{test_data.get('browser', get_default_value('web', 'browser'))}"
        }

    def _gen_input_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate input keyword data."""
        locator = test_data.get("locator", get_default_value("web", "locator"))
        username = test_data.get("username", get_default_value("user", "username"))
        return {"data": f"{locator} {username}"}

    def _gen_click_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate click keyword data."""
        locator = test_data.get("locator", get_default_value("web", "locator"))
        return {"data": f"{locator}"}

    def _gen_wait_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate wait keyword data."""
        timeout = test_data.get("timeout", get_default_value("web", "timeout"))
        return {"data": f"{timeout}"}

    def _gen_verify_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate verify keyword data."""
        expected = test_data.get("expected", "value")
        actual = test_data.get("actual", "value")
        return {"data": f"{expected} {actual}"}

    def _gen_ssh_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate SSH keyword data."""
        host = test_data.get("host", get_default_value("ssh", "host"))
        username = test_data.get("username", get_default_value("ssh", "username"))
        return {"data": f"{host} {username}"}

    def _gen_db_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate database keyword data."""
        query = test_data.get("query", get_default_value("database", "query"))
        connection = test_data.get(
            "connection", get_default_value("database", "connection")
        )
        return {"data": f"{query} {connection}"}

    def _gen_api_data(self, test_data: dict[str, str]) -> dict[str, Any]:
        """Generate API keyword data."""
        endpoint = test_data.get("endpoint", get_default_value("api", "endpoint"))
        method = test_data.get("method", get_default_value("api", "method"))
        return {"data": f"{endpoint} {method}"}

    def _gen_builtin_conversion_data(
        self, _test_data: dict[str, str]
    ) -> dict[str, Any]:
        """Generate BuiltIn conversion keyword data."""
        values = ["123", "hello", "true", "false", "3.14"]
        return {"data": f"value: {random.choice(values)}"}

    def _gen_builtin_conditional_data(
        self, _test_data: dict[str, str]
    ) -> dict[str, Any]:
        """Generate BuiltIn conditional keyword data."""
        conditions = ["${status} == 'pass'", "${count} > 0", "${result} != 'failed'"]
        keywords = ["Log", "Continue For Loop", "Exit For Loop"]
        args = ["Success", "Continuing", "Condition met"]
        return {
            "data": (
                f"condition: {random.choice(conditions)}, "
                f"keyword: {random.choice(keywords)}, "
                f"args: {random.choice(args)}"
            )
        }

    def _gen_builtin_repeat_data(self, _test_data: dict[str, str]) -> dict[str, Any]:
        """Generate BuiltIn repeat keyword data."""
        times = random.randint(2, 5)
        keywords = ["Log", "Sleep", "No Operation"]
        args = ["Repeated message", "1s", ""]
        return {
            "data": (
                f"times: {times}, keyword: {random.choice(keywords)}, "
                f"args: {random.choice(args)}"
            )
        }

    def _gen_builtin_variable_data(self, _test_data: dict[str, str]) -> dict[str, Any]:
        """Generate BuiltIn variable keyword data."""
        var_names = ["test_var", "result", "counter", "status"]
        var_values = ["test_value", "success", "1", "pass"]
        return {
            "data": (
                f"name: {random.choice(var_names)}, value: {random.choice(var_values)}"
            )
        }

    def _gen_builtin_collection_data(
        self, _test_data: dict[str, str]
    ) -> dict[str, Any]:
        """Generate BuiltIn collection keyword data."""
        items = ["item1", "item2", "item3"]
        containers = ["${test_list}", "${data}", "${results}"]
        return {
            "data": (
                f"container: {random.choice(containers)}, item: {random.choice(items)}"
            )
        }

    def _gen_builtin_log_data(self, _test_data: dict[str, str]) -> dict[str, Any]:
        """Generate BuiltIn log keyword data."""
        messages = ["Test message", "Operation completed", "Debug info", "Status check"]
        levels = ["INFO", "DEBUG", "WARN", "ERROR"]
        return {
            "data": (
                f"message: {random.choice(messages)}, level: {random.choice(levels)}"
            )
        }

    def _gen_builtin_evaluation_data(
        self, _test_data: dict[str, str]
    ) -> dict[str, Any]:
        """Generate BuiltIn evaluation keyword data."""
        expressions = [
            "2 + 3",
            "len('hello')",
            "datetime.now()",
            "random.randint(1, 10)",
        ]
        modules = ["", "datetime", "random", "os"]
        expr = random.choice(expressions)
        mod = random.choice(modules)
        if mod:
            return {"data": f"expression: {expr}, modules: {mod}"}
        return {"data": f"expression: {expr}"}

    def _get_keyword_generator_map(
        self, test_data: dict[str, str]
    ) -> dict[str, dict[str, Any]]:
        """Get keyword generator mapping for test data generation."""
        return {
            "browser": {
                "patterns": KEYWORD_PATTERNS.browser_patterns,
                "generator": lambda: self._gen_browser_data(test_data),
            },
            "input": {
                "patterns": KEYWORD_PATTERNS.input_patterns,
                "generator": lambda: self._gen_input_data(test_data),
            },
            "click": {
                "patterns": KEYWORD_PATTERNS.click_patterns,
                "generator": lambda: self._gen_click_data(test_data),
            },
            "wait": {
                "patterns": KEYWORD_PATTERNS.wait_patterns,
                "generator": lambda: self._gen_wait_data(test_data),
            },
            "verification": {
                "patterns": KEYWORD_PATTERNS.verification_patterns,
                "generator": lambda: self._gen_verify_data(test_data),
            },
            "ssh": {
                "patterns": KEYWORD_PATTERNS.ssh_patterns,
                "library_check": lambda lib: "ssh" in lib.lower(),
                "generator": lambda: self._gen_ssh_data(test_data),
            },
            "database": {
                "patterns": KEYWORD_PATTERNS.database_patterns,
                "library_check": lambda lib: "database" in lib.lower(),
                "generator": lambda: self._gen_db_data(test_data),
            },
            "api": {
                "patterns": KEYWORD_PATTERNS.api_patterns,
                "library_check": lambda lib: "requests" in lib.lower(),
                "generator": lambda: self._gen_api_data(test_data),
            },
            "builtin_conversion": {
                "patterns": ["Convert To", "convert", "conversion"],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_conversion_data(test_data)),
            },
            "builtin_conditional": {
                "patterns": [
                    "Run Keyword If",
                    "Run Keyword Unless",
                    "conditional",
                    "if",
                ],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_conditional_data(test_data)),
            },
            "builtin_repeat": {
                "patterns": ["Repeat Keyword", "repeat", "loop"],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_repeat_data(test_data)),
            },
            "builtin_variable": {
                "patterns": [
                    "Set Variable",
                    "Get Variable",
                    "variable",
                    "set",
                    "create",
                ],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_variable_data(test_data)),
            },
            "builtin_collection": {
                "patterns": [
                    "Get Count",
                    "Should Contain",
                    "Length",
                    "count",
                    "contain",
                ],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_collection_data(test_data)),
            },
            "builtin_log": {
                "patterns": ["Log", "Log Many", "Log To Console", "log"],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_log_data(test_data)),
            },
            "builtin_evaluation": {
                "patterns": ["Evaluate", "evaluate", "expression"],
                "library_check": lambda lib: "builtin" in lib.lower(),
                "generator": (lambda: self._gen_builtin_evaluation_data(test_data)),
            },
        }

    def generate_keyword_specific_data(
        self, keyword_info: dict[str, Any], test_data: dict[str, str]
    ) -> str:
        """Generate keyword-specific test data based on keyword info and test context.

        Args:
            keyword_info: Dictionary containing keyword information with 'keyword',
                'library', and 'description' keys
            test_data: General test data from generate_realistic_test_data()

        Returns:
            String containing keyword-specific test data
        """
        keyword = keyword_info.get("keyword", "")
        library = keyword_info.get("library", "")

        # Get keyword generator mapping
        keyword_generators = self._get_keyword_generator_map(test_data)

        # Switch-style pattern matching
        for _keyword_type, config in keyword_generators.items():
            patterns = config["patterns"]
            library_check = config.get("library_check")

            # Check if keyword matches patterns or library check
            if any(pattern in keyword for pattern in patterns) or (
                library_check and library_check(library)
            ):
                result = config["generator"]()
                return (
                    str(result.get("data", ""))
                    if isinstance(result, dict)
                    else str(result)
                )

        # Default case - return a generic test data string
        return f"test_data_for_{keyword.lower().replace(' ', '_')}  # {library.lower()}"

    def _get_test_distribution(
        self,
        total_tests: int,
        distribution: DistributionDict | None = None,
        weights: WeightsDict | None = None,
    ) -> DistributionDict:
        """Get test distribution (delegate to DistributionManager)."""
        return DistributionManager.get_test_distribution(
            total_tests, distribution, weights
        )

    def generate_random_json(
        self,
        structure: str | None = None,
        complexity: str | None = None,
    ) -> dict[str, Any]:
        """Generate random JSON test data."""
        # Use structure to determine category and scenario
        if structure == "zephyr_basic":
            category = "functional"
            scenario = "basic_workflow"
        else:
            category = "regression"
            scenario = "user_authentication"

        # Use complexity if provided
        test_complexity = complexity or "medium"

        return self.generate_enterprise_test_case(
            category=category,
            scenario=scenario,
            test_id=random.randint(1000, 9999),
            complexity_override=test_complexity,
        )

    def _get_category_scenarios(self) -> dict[str, dict[str, list[str]]]:
        """Get available scenarios by category."""
        return self.template_manager.get_available_scenarios()
