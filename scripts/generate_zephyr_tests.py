#!/usr/bin/env python3
"""
Generate realistic Zephyr-style test cases for bulk conversion demonstration.

Creates 800 diverse test cases across multiple categories and test types.
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from importobot.utils.test_generation.distributions import print_test_distribution

CategoryTypes = Dict[str, Dict[str, List[str]]]


class ZephyrTestGenerator:
    """Generates realistic Zephyr-style test cases for demonstration."""

    def __init__(self) -> None:
        """Initialize the ZephyrTestGenerator with test templates."""
        self.test_templates = {
            "web_automation": {
                "login": {
                    "description": "User authentication workflow",
                    "steps": [
                        {
                            "action": "Navigate to login page",
                            "data": "https://app.{domain}.com/login",
                        },
                        {"action": "Enter username", "data": "username: {username}"},
                        {"action": "Enter password", "data": "password: {password}"},
                        {"action": "Click login button", "data": "click: login_btn"},
                        {
                            "action": "Verify successful login",
                            "data": "verify: dashboard_visible",
                        },
                    ],
                },
                "registration": {
                    "description": "User registration process",
                    "steps": [
                        {
                            "action": "Navigate to registration",
                            "data": "https://app.{domain}.com/register",
                        },
                        {
                            "action": "Fill user details",
                            "data": "email: {email}, name: {name}",
                        },
                        {"action": "Set password", "data": "password: {password}"},
                        {"action": "Submit form", "data": "click: register_btn"},
                        {
                            "action": "Verify registration success",
                            "data": "verify: welcome_message",
                        },
                    ],
                },
                "form_validation": {
                    "description": "Form input validation testing",
                    "steps": [
                        {
                            "action": "Open form page",
                            "data": "https://app.{domain}.com/forms/{form_type}",
                        },
                        {
                            "action": "Enter invalid data",
                            "data": "input: {invalid_data}",
                        },
                        {"action": "Submit form", "data": "click: submit"},
                        {
                            "action": "Verify error message",
                            "data": "verify: error_displayed",
                        },
                        {
                            "action": "Correct data and resubmit",
                            "data": "input: {valid_data}",
                        },
                    ],
                },
            },
            "api_testing": {
                "crud_operations": {
                    "description": "API CRUD operations testing",
                    "steps": [
                        {
                            "action": "Create resource",
                            "data": "POST /api/{resource} "
                            '{"name": "{name}", "type": "{type}"}',
                        },
                        {"action": "Read resource", "data": "GET /api/{resource}/{id}"},
                        {
                            "action": "Update resource",
                            "data": "PUT /api/{resource}/{id} "
                            '\'{"name": "{updated_name}"}\'',
                        },
                        {"action": "Verify update", "data": "GET /api/{resource}/{id}"},
                        {
                            "action": "Delete resource",
                            "data": "DELETE /api/{resource}/{id}",
                        },
                    ],
                },
                "authentication": {
                    "description": "API authentication testing",
                    "steps": [
                        {
                            "action": "Request auth token",
                            "data": "POST /auth/token "
                            '\'{"username": "{username}", "password": "{password}"}\'',
                        },
                        {
                            "action": "Verify token received",
                            "data": "status: 200, token: present",
                        },
                        {
                            "action": "Use token for request",
                            "data": "GET /api/protected, Authorization: Bearer {token}",
                        },
                        {"action": "Verify authorized access", "data": "status: 200"},
                    ],
                },
                "error_handling": {
                    "description": "API error response testing",
                    "steps": [
                        {
                            "action": "Send invalid request",
                            "data": 'POST /api/{resource} {{"invalid": "data"}}',
                        },
                        {"action": "Verify error response", "data": "status: 400"},
                        {
                            "action": "Check error message",
                            "data": "verify: error_message_present",
                        },
                        {
                            "action": "Test unauthorized access",
                            "data": "GET /api/protected",
                        },
                    ],
                },
            },
            "database_testing": {
                "data_integrity": {
                    "description": "Database data integrity verification",
                    "steps": [
                        {
                            "action": "Connect to database",
                            "data": "database: {db_name}, user: {db_user}",
                        },
                        {
                            "action": "Insert test data",
                            "data": "INSERT INTO {table} VALUES ({values})",
                        },
                        {
                            "action": "Query inserted data",
                            "data": "SELECT * FROM {table} WHERE id = {id}",
                        },
                        {
                            "action": "Verify data integrity",
                            "data": "verify: data_matches_expected",
                        },
                        {
                            "action": "Cleanup test data",
                            "data": "DELETE FROM {table} WHERE id = {id}",
                        },
                    ],
                },
                "performance": {
                    "description": "Database performance testing",
                    "steps": [
                        {
                            "action": "Connect to database",
                            "data": "database: {db_name}",
                        },
                        {
                            "action": "Execute complex query",
                            "data": (
                                "SELECT * FROM {table} JOIN {other_table} "
                                "WHERE {condition}"
                            ),
                        },
                        {
                            "action": "Measure execution time",
                            "data": "measure: query_time",
                        },
                        {
                            "action": "Verify performance threshold",
                            "data": "assert: query_time < {threshold}ms",
                        },
                    ],
                },
            },
            "file_operations": {
                "file_transfer": {
                    "description": "File transfer operations",
                    "steps": [
                        {
                            "action": "Connect to remote server",
                            "data": "ssh {user}@{server}",
                        },
                        {
                            "action": "Upload file",
                            "data": "scp {local_file} {user}@{server}:{remote_path}",
                        },
                        {
                            "action": "Verify upload",
                            "data": 'ssh {user}@{server} "ls -la {remote_path}"',
                        },
                        {
                            "action": "Download file",
                            "data": "scp {user}@{server}:{remote_path} {download_path}",
                        },
                        {
                            "action": "Verify file integrity",
                            "data": "diff {local_file} {download_path}",
                        },
                    ],
                },
                "file_processing": {
                    "description": "File processing and validation",
                    "steps": [
                        {
                            "action": "Create test file",
                            "data": 'echo "{content}" > {file_path}',
                        },
                        {
                            "action": "Process file",
                            "data": "{processor_command} {file_path}",
                        },
                        {"action": "Verify output", "data": "test -f {output_file}"},
                        {
                            "action": "Validate content",
                            "data": 'grep "{expected_content}" {output_file}',
                        },
                    ],
                },
            },
        }

        self.domains = ["example", "testapp", "demosite", "webapp", "platform"]
        self.usernames = ["testuser", "admin", "user123", "demouser", "developer"]
        self.passwords = ["Test123!", "SecurePass456", "DemoPass789", "UserPass!23"]
        self.emails = ["test@example.com", "user@testapp.com", "demo@platform.org"]
        self.names: list[str] = ["John Doe", "Jane Smith", "Test User", "Demo Account"]
        self.resources = ["users", "products", "orders", "customers", "items"]
        self.databases = ["testdb", "appdb", "userdb", "productdb"]
        self.servers = ["testserver.com", "staging.example.com", "dev.platform.org"]

    def generate_test_case(
        self, category: str, test_type: str, test_id: int
    ) -> Dict[str, Any]:
        """Generate a single test case."""
        if category not in self.test_templates:
            raise ValueError(f"Unknown category: {category}")

        templates = self.test_templates[category]
        if test_type not in templates:
            test_type = random.choice(list(templates.keys()))

        template = templates[test_type]

        # Generate realistic test data
        test_data = {
            "domain": random.choice(self.domains),
            "username": random.choice(self.usernames),
            "password": random.choice(self.passwords),
            "email": random.choice(self.emails),
            "name": random.choice(self.names),
            "resource": random.choice(self.resources),
            "db_name": random.choice(self.databases),
            "db_user": random.choice(self.usernames),
            "server": random.choice(self.servers),
            "user": random.choice(self.usernames),
            "id": random.randint(1, 1000),
            "threshold": random.randint(100, 1000),
            "form_type": random.choice(["contact", "feedback", "registration"]),
            "table": random.choice(["users", "products", "orders"]),
            "other_table": random.choice(["profiles", "categories", "details"]),
            "condition": (
                f"status = 'active' AND created_date > '{datetime.now().date()}'"
            ),
            "values": (
                f"({random.randint(1, 1000)}, 'test_value_{random.randint(1, 100)}')"
            ),
            "local_file": f"/tmp/test_file_{random.randint(1, 100)}.txt",
            "remote_path": f"/remote/path/file_{random.randint(1, 100)}.txt",
            "download_path": f"/tmp/downloaded_{random.randint(1, 100)}.txt",
            "file_path": f"/tmp/process_{random.randint(1, 100)}.txt",
            "output_file": f"/tmp/output_{random.randint(1, 100)}.txt",
            "content": f"Test content {random.randint(1, 1000)}",
            "expected_content": "processed successfully",
            "processor_command": random.choice(
                ["sort", "grep pattern", "awk '{print $1}'", "sed s/old/new/g"]
            ),
            "type": random.choice(["standard", "premium", "basic"]),
            "updated_name": f"Updated_{random.choice(self.names).replace(' ', '_')}",
            "invalid_data": "invalid@email",
            "valid_data": random.choice(self.emails),
            "token": f"bearer_token_{random.randint(10000, 99999)}",
        }

        # Create test steps
        steps: List[Dict[str, Any]] = []
        template_steps: List[Dict[str, str]] = template["steps"]  # type: ignore
        for i, step_template in enumerate(template_steps):
            step = {
                "description": step_template["action"],
                "testData": step_template["data"].format(**test_data),
                "expectedResult": f"Step {i + 1} completes successfully",
                "index": i,
            }
            steps.append(step)

        # Create the full test case
        created_date = datetime.now() - timedelta(days=random.randint(1, 365))
        updated_date = created_date + timedelta(days=random.randint(1, 30))

        test_case = {
            "key": f"ZEPH-{test_id}",
            "name": f"{category.title()} {test_type.title()} Test {test_id}",
            "description": template["description"],
            "owner": f"JIRAUSER{random.randint(10000, 99999)}",
            "createdBy": f"JIRAUSER{random.randint(10000, 99999)}",
            "updatedBy": f"JIRAUSER{random.randint(10000, 99999)}",
            "createdOn": created_date.isoformat() + "Z",
            "updatedOn": updated_date.isoformat() + "Z",
            "priority": random.choice(["High", "Medium", "Low"]),
            "status": random.choice(["Review", "Approved", "Draft"]),
            "labels": [category, test_type, "automated"],
            "projectKey": "ZEPH",
            "folder": f"/Tests/{category.title()}",
            "latestVersion": True,
            "lastTestResultStatus": random.choice(["Pass", "Fail", "Blocked"]),
            "testScript": {
                "id": random.randint(10000, 99999),
                "type": "STEP_BY_STEP",
                "steps": steps,
            },
            "parameters": {"variables": [], "entries": []},
            "customFields": {
                "Test Level": random.choice(
                    ["Unit", "Integration", "System", "Acceptance"]
                ),
                "Supported Platforms": random.choice(
                    ["All Platforms", "Web Only", "Mobile Only"]
                ),
            },
        }

        return test_case

    def generate_test_suite(self, output_dir: str) -> Dict[str, int]:
        """Generate a complete test suite with specified number of tests."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Distribution of tests across categories
        distributions = {
            "regression": 250,
            "smoke": 150,
            "integration": 200,
            "e2e": 200,
        }

        # Test type distributions within categories
        category_types: CategoryTypes = {
            "regression": {
                "web_automation": ["login", "registration", "form_validation"],
                "api_testing": ["crud_operations", "authentication"],
                "database_testing": ["data_integrity"],
            },
            "smoke": {
                "web_automation": ["login"],
                "api_testing": ["authentication"],
                "file_operations": ["file_transfer"],
            },
            "integration": {
                "web_automation": ["registration", "form_validation"],
                "api_testing": ["crud_operations", "error_handling"],
                "database_testing": ["data_integrity", "performance"],
                "file_operations": ["file_transfer", "file_processing"],
            },
            "e2e": {
                "web_automation": ["login", "registration"],
                "api_testing": ["crud_operations"],
                "database_testing": ["data_integrity"],
                "file_operations": ["file_transfer"],
            },
        }

        generated_counts = {}
        test_id = 1

        for category, count in distributions.items():
            category_dir = Path(output_dir) / category
            category_dir.mkdir(exist_ok=True)
            generated_counts[category] = 0

            tests_per_type = count // len(list(category_types[category].keys()))
            remainder = count % len(list(category_types[category].keys()))

            for test_category, test_types in category_types[category].items():
                type_count = tests_per_type
                if remainder > 0:
                    type_count += 1
                    remainder -= 1

                for _ in range(type_count):
                    test_type = random.choice(test_types)
                    test_case = self.generate_test_case(
                        test_category, test_type, test_id
                    )

                    filename = f"{test_category}_{test_type}_{test_id:03d}.json"
                    file_path = category_dir / filename

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(test_case, f, indent=2, ensure_ascii=False)

                    generated_counts[category] += 1
                    test_id += 1

        return generated_counts


def main() -> None:
    """Generate the Zephyr test suite."""
    parser = argparse.ArgumentParser(description="Generate Zephyr-style test cases")
    parser.add_argument(
        "--output-dir",
        default="zephyr-tests",
        help="Output directory for generated tests",
    )
    parser.add_argument(
        "--count", type=int, default=800, help="Total number of tests to generate"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        print(f"Generating {args.count} test cases in {args.output_dir}/")

    generator = ZephyrTestGenerator()
    counts = generator.generate_test_suite(args.output_dir)

    if args.verbose:
        print()
        print_test_distribution(counts)

    print(f"Successfully generated {sum(counts.values())} test cases")


if __name__ == "__main__":
    main()
