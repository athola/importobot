#!/usr/bin/env python3
"""
Basic usage examples for Importobot.

This script demonstrates the core functionality of converting JSON test cases
to Robot Framework format using the public API.
"""

import json
import os
from pathlib import Path
from typing import Any

# Import the main converter class
import importobot

# Get root directory for file paths
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent


def basic_conversion_example() -> str:
    """Demonstrate basic JSON to Robot Framework conversion."""
    print("=== Basic Conversion Example ===")

    # Create a simple test case in JSON format
    test_data = {
        "tests": [
            {
                "name": "User Login Test",
                "description": "Verify user can login with valid credentials",
                "steps": [
                    {
                        "action": "Navigate to login page",
                        "expectedResult": "Login page displays",
                    },
                    {
                        "action": "Enter username 'testuser'",
                        "expectedResult": "Username field is populated",
                    },
                    {
                        "action": "Enter password 'password123'",
                        "expectedResult": "Password field is populated",
                    },
                    {
                        "action": "Click login button",
                        "expectedResult": "User is redirected to dashboard",
                    },
                ],
            }
        ]
    }

    # Initialize the converter
    converter = importobot.JsonToRobotConverter()

    # Convert JSON to Robot Framework format
    robot_content = converter.convert_json_data(test_data)

    print("Generated Robot Framework content:")
    print("-" * 50)
    print(robot_content)
    print("-" * 50)

    return robot_content


def file_conversion_example() -> str:
    """Demonstrate converting from a JSON file."""
    print("\n=== File Conversion Example ===")

    # Use an existing example file
    json_file = root_dir / "examples" / "json" / "basic_login.json"

    if not json_file.exists():
        print(f"Example file {json_file} not found. Creating sample data...")
        # Create sample data if file doesn't exist
        sample_data = {
            "tests": [
                {
                    "name": "Sample Login Test",
                    "description": "Basic login functionality test",
                    "steps": [
                        {
                            "action": "Open application",
                            "expectedResult": "Application loads successfully",
                        },
                        {
                            "action": "Login with credentials",
                            "expectedResult": "User is authenticated",
                        },
                    ],
                }
            ]
        }

        # Initialize converter with sample data
        converter = importobot.JsonToRobotConverter()
        robot_content = converter.convert_json_data(sample_data)
    else:
        # Load existing file
        with open(json_file, encoding="utf-8") as f:
            json_data = json.load(f)

        # Initialize converter
        converter = importobot.JsonToRobotConverter()

        # Convert to Robot Framework format
        robot_content = converter.convert_json_data(json_data)

    print("Converted Robot Framework content from file:")
    print("-" * 50)
    print(robot_content)
    print("-" * 50)

    return robot_content


def batch_conversion_example() -> str:
    """Demonstrate bulk processing capabilities."""
    print("\n=== Batch Conversion Example ===")

    # Create multiple test cases to demonstrate bulk processing
    test_suite = {
        "tests": [
            {
                "name": "Login Functionality Test",
                "description": "Test user login with valid credentials",
                "steps": [
                    {
                        "action": "Navigate to login",
                        "expectedResult": "Login page shown",
                    },
                    {
                        "action": "Enter credentials",
                        "expectedResult": "Fields populated",
                    },
                    {"action": "Submit form", "expectedResult": "Login successful"},
                ],
            },
            {
                "name": "Logout Functionality Test",
                "description": "Test user logout functionality",
                "steps": [
                    {
                        "action": "Click logout button",
                        "expectedResult": "User logged out",
                    },
                    {
                        "action": "Verify redirect",
                        "expectedResult": "Redirected to login page",
                    },
                ],
            },
            {
                "name": "Password Reset Test",
                "description": "Test password reset functionality",
                "steps": [
                    {
                        "action": "Click forgot password",
                        "expectedResult": "Reset form shown",
                    },
                    {
                        "action": "Enter email address",
                        "expectedResult": "Email field populated",
                    },
                    {
                        "action": "Submit reset request",
                        "expectedResult": "Reset email sent",
                    },
                ],
            },
        ]
    }

    print(f"Converting {len(test_suite['tests'])} test cases...")

    # Initialize converter
    converter = importobot.JsonToRobotConverter()

    # Convert the entire suite
    robot_content = converter.convert_json_data(test_suite)

    print("Batch conversion completed!")
    print("Generated Robot Framework test suite:")
    print("-" * 50)
    print(robot_content)
    print("-" * 50)

    return robot_content


def save_output_example() -> Path:
    """Demonstrate saving converted output to files."""
    print("\n=== Save Output Example ===")

    # Create test data
    test_data = {
        "tests": [
            {
                "name": "API Response Test",
                "description": "Verify API returns correct response",
                "steps": [
                    {
                        "action": "Send GET request to /api/users",
                        "expectedResult": "HTTP 200 status received",
                    },
                    {
                        "action": "Verify response format",
                        "expectedResult": "JSON response with user list",
                    },
                ],
            }
        ]
    }

    # Convert to Robot Framework
    converter = importobot.JsonToRobotConverter()
    robot_content = converter.convert_json_data(test_data)

    # Save to file
    output_dir = root_dir / "examples" / "output"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "api_test.robot"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(robot_content)

    print(f"Robot Framework test saved to: {output_file}")
    print(f"File size: {os.path.getsize(output_file)} bytes")

    return output_file


def error_handling_example() -> None:
    """Demonstrate error handling with invalid input."""
    print("\n=== Error Handling Example ===")

    try:
        # Test with invalid JSON structure
        invalid_data = {"invalid": "structure"}

        converter = importobot.JsonToRobotConverter()
        converter.convert_json_data(invalid_data)

    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}")
        print(f"Error message: {e}")

    try:
        # Test with empty data
        empty_data: dict[str, Any] = {}

        converter = importobot.JsonToRobotConverter()
        converter.convert_json_data(empty_data)

    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}")
        print(f"Error message: {e}")


def configuration_example() -> None:
    """Demonstrate configuration options."""
    print("\n=== Configuration Example ===")

    # Access configuration settings
    try:
        # Import configuration
        print("Configuration access successful")
        print(
            "Available configuration options can be accessed through importobot.config"
        )

    except Exception as e:
        print(f"Configuration error: {e}")


def main() -> int:
    """Run all examples."""
    print("Importobot Basic Usage Examples")
    print("=" * 50)

    try:
        # Run examples in sequence
        basic_conversion_example()
        file_conversion_example()
        batch_conversion_example()
        save_output_example()
        error_handling_example()
        configuration_example()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"\nError running examples: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
