#!/usr/bin/env python3
"""
Advanced features examples for Importobot.

This script demonstrates advanced functionality including API toolkit usage,
validation features, and enterprise-scale processing capabilities.
"""

import time
from pathlib import Path
from typing import Any, cast

import importobot

# Get root directory for file paths
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent


def api_toolkit_example() -> None:
    """Demonstrate the API toolkit features."""
    print("=== API Toolkit Example ===")

    try:
        # Access the API toolkit
        api = importobot.api
        print("API toolkit access successful")

        # Example of accessing validation features
        if hasattr(api, "validation"):
            print("Validation toolkit available")

        # Example of accessing converters
        if hasattr(api, "converters"):
            print("Converters toolkit available")

        # Example of accessing suggestions
        if hasattr(api, "suggestions"):
            print("Suggestions toolkit available")

    except Exception as e:
        print(f"API toolkit error: {e}")


def validation_example() -> None:
    """Demonstrate validation features."""
    print("\n=== Validation Example ===")

    # Test data with potential issues
    test_cases = [
        # Valid test case
        {
            "tests": [
                {
                    "name": "Valid Test Case",
                    "description": "This is a properly formatted test",
                    "steps": [
                        {
                            "action": "Perform action",
                            "expectedResult": "Expected result occurs",
                        }
                    ],
                }
            ]
        },
        # Invalid test case - missing required fields
        {
            "tests": [
                {
                    "name": "Invalid Test Case",
                    # Missing description
                    "steps": [
                        {
                            "action": "Perform action"
                            # Missing expectedResult
                        }
                    ],
                }
            ]
        },
        # Edge case - empty steps
        {
            "tests": [
                {
                    "name": "Edge Case Test",
                    "description": "Test with no steps",
                    "steps": [],
                }
            ]
        },
    ]

    converter = importobot.JsonToRobotConverter()

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nValidating test case {i}:")
        try:
            result = converter.convert_json_data(cast(dict[str, Any], test_case))
            print(" Conversion successful")
            # Show only first few lines of output
            lines = result.split("\n")[:5]
            print("Preview:", "\n".join(lines))

        except Exception as e:
            print(f" Validation failed: {e}")


def performance_example() -> None:
    """Demonstrate performance with larger datasets."""
    print("\n=== Performance Example ===")

    # Generate a larger test suite
    def generate_test_suite(num_tests: int) -> dict[str, Any]:
        """Generate a test suite with specified number of tests."""
        tests = []
        for i in range(num_tests):
            test = {
                "name": f"Performance Test Case {i + 1}",
                "description": f"Automated test case {i + 1} for performance testing",
                "steps": [
                    {
                        "action": f"Initialize test environment {i + 1}",
                        "expectedResult": "Environment ready",
                    },
                    {
                        "action": f"Execute test logic {i + 1}",
                        "expectedResult": "Test executed successfully",
                    },
                    {
                        "action": f"Validate results {i + 1}",
                        "expectedResult": "Results are correct",
                    },
                    {
                        "action": f"Cleanup test environment {i + 1}",
                        "expectedResult": "Environment cleaned",
                    },
                ],
            }
            tests.append(test)

        return {"tests": tests}

    # Test with different sizes
    test_sizes = [10, 50, 100]

    converter = importobot.JsonToRobotConverter()

    for size in test_sizes:
        print(f"\nProcessing {size} test cases...")

        # Generate test suite
        test_suite = generate_test_suite(size)

        # Measure conversion time
        start_time = time.time()
        result = converter.convert_json_data(test_suite)
        end_time = time.time()

        conversion_time = end_time - start_time
        lines_generated = len(result.split("\n"))

        print(f" Converted {size} tests in {conversion_time:.3f} seconds")
        print(f"   Generated {lines_generated:,} lines of Robot Framework code")
        print(f"   Performance: {size / conversion_time:.1f} tests/second")


def complex_scenario_example() -> None:
    """Demonstrate complex test scenarios."""
    print("\n=== Complex Scenario Example ===")

    # Complex multi-step test scenario
    complex_scenario = {
        "tests": [
            {
                "name": "End-to-End User Registration Flow",
                "description": "Complete user registration with email verification",
                "steps": [
                    {
                        "action": "Navigate to registration page",
                        "expectedResult": "Registration form is displayed",
                    },
                    {
                        "action": (
                            "Fill in personal information "
                            "(Name: John Doe, Email: john@example.com)"
                        ),
                        "expectedResult": "Form fields are populated correctly",
                    },
                    {
                        "action": "Create password with special characters (!@#$%^&*)",
                        "expectedResult": "Password meets complexity requirements",
                    },
                    {
                        "action": "Agree to terms and conditions",
                        "expectedResult": "Checkbox is selected",
                    },
                    {
                        "action": "Submit registration form",
                        "expectedResult": "Confirmation message is displayed",
                    },
                    {
                        "action": "Check email inbox for verification link",
                        "expectedResult": "Verification email is received",
                    },
                    {
                        "action": "Click verification link in email",
                        "expectedResult": "Account is activated successfully",
                    },
                    {
                        "action": "Login with new credentials",
                        "expectedResult": "User is logged into dashboard",
                    },
                ],
            },
            {
                "name": "Database Integration Test",
                "description": "Verify data persistence and retrieval",
                "steps": [
                    {
                        "action": "Connect to test database",
                        "expectedResult": "Database connection established",
                    },
                    {
                        "action": (
                            "Insert test record: "
                            "{id: 123, name: 'Test User', created: NOW()}"
                        ),
                        "expectedResult": "Record inserted successfully",
                    },
                    {
                        "action": "Query database for inserted record",
                        "expectedResult": "Record retrieved with correct values",
                    },
                    {
                        "action": (
                            "Update record: SET name = 'Updated User' WHERE id = 123"
                        ),
                        "expectedResult": "Record updated successfully",
                    },
                    {
                        "action": "Verify update through API call: GET /api/users/123",
                        "expectedResult": "API returns updated user data",
                    },
                    {
                        "action": (
                            "Delete test record: DELETE FROM users WHERE id = 123"
                        ),
                        "expectedResult": "Record deleted successfully",
                    },
                ],
            },
        ]
    }

    converter = importobot.JsonToRobotConverter()
    result = converter.convert_json_data(complex_scenario)

    print("Complex scenarios converted successfully!")
    newline = "\n"
    test_cases_section = result.split("*** Test Cases ***")[1].split("***")[0]
    test_cases_count = len(test_cases_section.strip().split(newline))
    print(f"Generated {test_cases_count} test cases")

    # Save complex example
    output_dir = root_dir / "examples" / "output"
    output_dir.mkdir(exist_ok=True)

    complex_file = output_dir / "complex_scenarios.robot"
    with open(complex_file, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"Complex scenarios saved to: {complex_file}")


def enterprise_integration_example() -> None:
    """Demonstrate enterprise-scale integration patterns."""
    print("\n=== Enterprise Integration Example ===")

    # Simulate enterprise test suite structure
    enterprise_suite = {
        "metadata": {
            "project": "Enterprise Application",
            "version": "2.1.0",
            "environment": "production-test",
            "created": "2025-01-01T00:00:00Z",
        },
        "tests": [
            {
                "name": "Security Authentication Flow",
                "description": "Multi-factor authentication with SSO integration",
                "priority": "High",
                "category": "Security",
                "steps": [
                    {
                        "action": "Initiate SSO login with corporate credentials",
                        "expectedResult": "SSO provider authentication page displayed",
                    },
                    {
                        "action": "Authenticate with domain credentials",
                        "expectedResult": "MFA challenge presented",
                    },
                    {
                        "action": "Complete MFA using authenticator app",
                        "expectedResult": "Authentication successful, token issued",
                    },
                    {
                        "action": "Redirect to application dashboard",
                        "expectedResult": "User dashboard with role-based permissions",
                    },
                ],
            },
            {
                "name": "Data Migration Verification",
                "description": "Verify data integrity after migration",
                "priority": "Critical",
                "category": "Data",
                "steps": [
                    {
                        "action": (
                            "Execute data count validation: "
                            "SELECT COUNT(*) FROM production_table"
                        ),
                        "expectedResult": "Record count matches expected baseline",
                    },
                    {
                        "action": "Verify data integrity: Run checksum validation",
                        "expectedResult": "All checksums match reference values",
                    },
                    {
                        "action": "Test foreign key constraints",
                        "expectedResult": "All relationships maintained correctly",
                    },
                ],
            },
            {
                "name": "Performance Benchmark Test",
                "description": "System performance under load",
                "priority": "Medium",
                "category": "Performance",
                "steps": [
                    {
                        "action": "Generate load: 1000 concurrent users",
                        "expectedResult": "System maintains <2s response time",
                    },
                    {
                        "action": "Monitor system resources during load",
                        "expectedResult": "CPU usage <80%, Memory usage <90%",
                    },
                    {
                        "action": "Verify system stability after load test",
                        "expectedResult": "No errors, system operational",
                    },
                ],
            },
        ],
    }

    converter = importobot.JsonToRobotConverter()

    print("Processing enterprise test suite...")
    start_time = time.time()

    try:
        result = converter.convert_json_data(enterprise_suite)
        conversion_time = time.time() - start_time

        print(f" Enterprise suite converted in {conversion_time:.3f} seconds")

        # Extract metrics
        test_cases = len(enterprise_suite["tests"])
        total_steps = sum(
            len(test["steps"])
            for test in cast(list[dict[str, Any]], enterprise_suite["tests"])
        )
        output_lines = len(result.split("\n"))

        print(f"   Processed: {test_cases} test cases, {total_steps} steps")
        print(f"   Generated: {output_lines:,} lines of Robot Framework code")

        # Save enterprise example
        output_dir = root_dir / "examples" / "output"
        output_dir.mkdir(exist_ok=True)

        enterprise_file = output_dir / "enterprise_suite.robot"
        with open(enterprise_file, "w", encoding="utf-8") as f:
            f.write(result)

        print(f"   Saved to: {enterprise_file}")

    except Exception as e:
        print(f" Enterprise conversion failed: {e}")


def main() -> int:
    """Run all advanced examples."""
    print("Importobot Advanced Features Examples")
    print("=" * 50)

    try:
        # Create output directory
        output_dir = root_dir / "examples" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run advanced examples
        api_toolkit_example()
        validation_example()
        performance_example()
        complex_scenario_example()
        enterprise_integration_example()

        print("\n" + "=" * 50)
        print("All advanced examples completed successfully!")
        print("\nGenerated files:")
        if output_dir.exists():
            for file in output_dir.glob("*.robot"):
                print(f"  File: {file}")

    except Exception as e:
        print(f"\nError running advanced examples: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
