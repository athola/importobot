"""Integration tests for new Zephyr format conversion with Robot Framework execution."""

import json
from pathlib import Path

from robot.api import get_model

from importobot.core.converter import convert_file
from tests.utils import parse_robot_file


def test_zephyr_integration_keyword_types(tmp_path: Path) -> None:
    """Tests that the generated robot file contains expected keywords."""
    zephyr_json_content = {
        "name": "Sample Zephyr Test",
        "objective": "Testing Zephyr format conversion to Robot Framework.",
        "precondition": "User has valid login credentials.",
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "description": "Navigate to the application login page.",
                    "expectedResult": "Login page is displayed successfully.",
                },
                {
                    "description": "Enter valid username in the 'Username' field.",
                    "testData": "username: testuser@example.com",
                    "expectedResult": "The username field accepts the input.",
                },
                {
                    "description": "Enter valid password in the 'Password' field.",
                    "testData": "password: password123",
                    "expectedResult": "The password field accepts the input.",
                },
                {
                    "description": "Click the 'Login' button.",
                    "expectedResult": (
                        "User is redirected to the application dashboard."
                    ),
                },
            ],
        },
    }

    input_json_file = tmp_path / "test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "output.robot"

    convert_file(str(input_json_file), str(output_robot_file))

    assert output_robot_file.exists(), "Output robot file was not created"

    # Parse generated robot file for testing
    generated_data = parse_robot_file(str(output_robot_file))

    # Verify minimum expected structure
    assert len(generated_data) >= 1
    assert any(
        "Sample Zephyr Test" in item.get("name", "") for item in generated_data
    ), "Test case name not found in generated data"

    # Verify key functional keywords are present
    # Get keywords from both individual keyword items and nested keywords lists
    keyword_names = []
    for item in generated_data:
        if "keyword" in item:
            keyword_names.append(item["keyword"])
        elif "keywords" in item:
            keyword_names.extend([kw["keyword"] for kw in item["keywords"]])

    assert "Open Browser" in keyword_names
    assert "Input Text" in keyword_names
    assert "Click Button" in keyword_names or "Click Element" in keyword_names


def test_robot_execution_against_mock_server(tmp_path: Path) -> None:
    """
    Generates a .robot file and executes it against the mock web server
    to verify its functionality.
    """
    zephyr_json_content = {
        "projectKey": "YOUR_PROJECT_KEY",
        "name": "Verify User Login Functionality",
        "priorityName": "High",
        "statusName": "Draft",
        "objective": (
            "To ensure users can successfully log in to the application "
            "with valid credentials."
        ),
        "precondition": "User has an active account and valid login credentials.",
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "description": "Navigate to the application login page.",
                    "expectedResult": "Login",
                },
                {
                    "description": "Enter a valid username in the 'Username' field.",
                    "testData": "username: testuser@example.com",
                    "expectedResult": "The username field accepts the input.",
                },
                {
                    "description": "Enter a valid password in the 'Password' field.",
                    "testData": "password: password123",
                    "expectedResult": "The password field accepts the input.",
                },
                {
                    "description": "Click the 'Login' button.",
                    "expectedResult": "Login",
                },
            ],
        },
    }

    input_json_file = tmp_path / "mock_server_test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "mock_server_test.robot"

    convert_file(str(input_json_file), str(output_robot_file))

    # Verify that the Robot Framework file was created
    assert output_robot_file.exists()

    # Use Robot Framework's parsing API to validate the generated suite structure
    model = get_model(str(output_robot_file))
    assert not model.errors, f"Robot Framework reported parse errors: {model.errors}"

    test_sections = [
        section
        for section in model.sections
        if section.__class__.__name__ == "TestCaseSection"
    ]
    assert test_sections, "No test cases found in generated Robot file"
    total_tests = sum(len(section.body) for section in test_sections)
    assert total_tests > 0, "Generated Robot file does not contain any test steps"
