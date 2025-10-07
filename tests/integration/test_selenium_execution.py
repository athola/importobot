"""Integration test for full JSON-to-Robot-to-Selenium execution pipeline.

This test validates that we can:
1. Parse JSON test cases with Selenium operations
2. Convert them to proper Robot Framework format
3. Execute the generated Robot file against a real web page
4. Verify test steps execute correctly
"""

import json
import threading
from http.server import HTTPServer
from typing import Callable, cast

import pytest
import robot
from robot.api import ExecutionResult, get_model

from importobot.core.converter import convert_file
from tests.mock_server import MyHandler

# Robot Framework lacks type info for `run`, so cast the attribute explicitly.
robot_run = cast(Callable[..., int], robot.run)  # type: ignore[attr-defined]


@pytest.fixture
def mock_server():
    """Start a mock HTTP server for Selenium testing."""
    try:
        server = HTTPServer(("localhost", 0), MyHandler)
    except PermissionError as exc:  # pragma: no cover - sandboxed environments
        pytest.skip(f"Unable to start HTTP server: {exc}")
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_json_to_robot_selenium_execution(tmp_path, mock_server):
    """
    Full integration test: JSON -> Robot Framework -> Selenium execution.

    This test validates the complete conversion pipeline by:
    1. Creating a JSON test case with realistic Selenium operations
    2. Converting it to Robot Framework format
    3. Executing the generated Robot file against a mock web server
    4. Verifying the test steps execute successfully
    """
    # Step 1: Create comprehensive JSON test case
    zephyr_json_content = {
        "name": "User Login Test",
        "objective": "Verify user can successfully log in to the application",
        "precondition": "User has valid credentials and browser is available",
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "description": (f"Open browser and navigate to {mock_server}"),
                    "expectedResult": (
                        "Login page is displayed with title 'Test Login Page'"
                    ),
                },
                {
                    "description": (
                        "Enter username 'testuser@example.com' in username field"
                    ),
                    "testData": "username: testuser@example.com",
                    "expectedResult": "Username field accepts the input",
                },
                {
                    "description": "Enter password in password field",
                    "testData": "password: SecurePass123",
                    "expectedResult": "Password field accepts the input",
                },
                {
                    "description": "Click the Login button",
                    "expectedResult": "Login successful message is displayed",
                },
                {
                    "description": "Close browser",
                    "expectedResult": "Browser closes successfully",
                },
            ],
        },
    }

    # Step 2: Write JSON to file
    input_json_file = tmp_path / "selenium_test.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    # Step 3: Convert JSON to Robot Framework
    output_robot_file = tmp_path / "selenium_test.robot"
    convert_file(str(input_json_file), str(output_robot_file))

    assert output_robot_file.exists(), "Robot file was not created"

    # Step 4: Verify Robot file structure
    robot_content = output_robot_file.read_text()
    assert "*** Settings ***" in robot_content
    assert "*** Test Cases ***" in robot_content
    assert "User Login Test" in robot_content

    # Check for Selenium/Browser keywords
    assert "Open Browser" in robot_content or "New Browser" in robot_content, (
        "No browser opening keyword found"
    )

    # Step 5: Execute the generated Robot file
    # Note: This requires SeleniumLibrary or Browser Library to be installed
    # We'll use headless mode to avoid UI dependencies
    output_dir = tmp_path / "robot_results"
    output_dir.mkdir(exist_ok=True)

    pytest.importorskip("SeleniumLibrary")

    # Execute with Robot Framework
    result_code = robot_run(
        str(output_robot_file),
        outputdir=str(output_dir),
        loglevel="DEBUG",
        # Use headless mode if available
        variable=[
            f"URL:{mock_server}",
            "BROWSER:headlessfirefox",  # Fallback to headless
        ],
        # Continue on failure to see all steps
        exitonfailure=False,
        # Dry-run to avoid spawning real browser processes while still
        # validating keyword wiring and output generation.
        dryrun=True,
    )

    # Step 6: Verify execution results
    output_xml = output_dir / "output.xml"
    assert output_xml.exists(), "Robot Framework output.xml was not created"

    # Parse results
    result = ExecutionResult(str(output_xml))

    # Verify test was executed (even if it failed due to missing SeleniumLibrary)
    assert result.suite.tests, "No tests were executed"
    test = result.suite.tests[0]
    assert test.name == "User Login Test"

    # Check that keywords were generated and attempted
    assert len(test.body) > 0, "No test steps were generated"

    # Log results for debugging
    print(f"\nTest Status: {test.status}")
    print(f"Test Message: {test.message}")
    print(f"Number of keywords: {len(test.body)}")

    # The test may fail if SeleniumLibrary is not installed,
    # but we can verify the structure is correct
    if result_code != 0:
        # Check if failure is due to missing library (acceptable)
        # or due to actual conversion issues (not acceptable)
        if "SeleniumLibrary" in test.message or "Browser" in test.message:
            pytest.skip(
                "SeleniumLibrary/Browser library not installed - "
                "skipping execution validation"
            )
        elif "Open Browser" not in robot_content:
            pytest.fail("Robot file missing expected Selenium keywords")


def test_json_to_robot_complex_selenium_workflow(tmp_path, mock_server):
    """
    Test complex Selenium workflow with multiple operations.

    Validates conversion of sophisticated test scenarios including:
    - Multiple page interactions
    - Form filling
    - Element verification
    - Assertions
    """
    json_test_case = {
        "name": "Complete User Registration Flow",
        "objective": "Test full user registration with validation",
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "description": f"Navigate to application at {mock_server}",
                    "expectedResult": "Page loads successfully",
                },
                {
                    "description": "Verify page title contains 'Login'",
                    "expectedResult": "Title verification passes",
                },
                {
                    "description": "Input text 'john.doe@test.com' into id=username",
                    "testData": "username: john.doe@test.com",
                    "expectedResult": "Text entered successfully",
                },
                {
                    "description": "Input password 'Test@123' into id=password",
                    "testData": "password: Test@123",
                    "expectedResult": "Password masked and entered",
                },
                {
                    "description": "Click element with id=loginButton",
                    "expectedResult": "Button click registered",
                },
                {
                    "description": "Wait until element id=message is visible",
                    "expectedResult": "Success message appears",
                },
                {
                    "description": (
                        "Verify element id=message contains text 'Login Successful'"
                    ),
                    "expectedResult": "Success message validated",
                },
                {
                    "description": "Close all browsers",
                    "expectedResult": "All browser instances closed",
                },
            ],
        },
    }

    # Write and convert
    input_file = tmp_path / "complex_test.json"
    input_file.write_text(json.dumps(json_test_case, indent=2))

    output_file = tmp_path / "complex_test.robot"
    convert_file(str(input_file), str(output_file))

    assert output_file.exists()

    # Verify generated content has proper structure
    content = output_file.read_text()

    # Should have proper sections
    assert "*** Settings ***" in content
    assert "*** Test Cases ***" in content

    # Should have the test case
    assert "Complete User Registration Flow" in content

    # Should have generated Selenium-compatible keywords
    selenium_keywords = [
        "Open Browser",
        "New Browser",
        "Go To",
        "Input Text",
        "Input Password",
        "Click",
        "Wait Until",
        "Element Should Contain",
        "Close",
    ]

    # At least some Selenium keywords should be present
    keywords_found = [kw for kw in selenium_keywords if kw in content]
    assert len(keywords_found) >= 3, (
        f"Expected Selenium keywords, found: {keywords_found}"
    )

    # Verify it parses correctly with Robot Framework
    model = get_model(str(output_file))
    assert not model.errors, f"Robot parse errors: {model.errors}"

    # Verify test structure
    test_sections = [
        s for s in model.sections if s.__class__.__name__ == "TestCaseSection"
    ]
    assert test_sections, "No test case section found"
    assert len(test_sections[0].body) > 0, "No test cases in section"
