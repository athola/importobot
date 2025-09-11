"""JSON parsing functionality."""

import json
import uuid
from typing import Any, Dict, List


def _build_settings_section(json_data: Dict[str, Any]) -> List[str]:
    """Build the Robot Framework settings section."""
    lines = [
        "*** Settings ***",
        "Documentation    Tests converted from JSON",
        "Library    SeleniumLibrary",
    ]

    # Add SSHLibrary only if it's needed
    json_data_str = str(json_data).lower()
    ssh_in_str = "ssh" in json_data_str
    no_retrieve_file = "Retrieve File From Remote Host" not in json_data_str
    if ssh_in_str and no_retrieve_file:
        lines.append("Library    SSHLibrary")

    return lines


def _extract_tests(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract test cases from JSON data."""
    tests = json_data.get("tests")
    if not isinstance(tests, list):
        if "name" in json_data and isinstance(json_data, dict):
            # Handle Zephyr-style single test case if json_data is a dict
            return [json_data]
        # Return empty list if 'tests' is not a list and not a single Zephyr-style test
        return []
    return tests


def _generate_ssh_steps(steps: List[Dict[str, Any]]) -> List[str]:
    """Generate Robot Framework steps for SSH test cases."""
    lines = []
    for step in steps:
        action = step.get("description", "No action specified")
        test_data = step.get("testData", "N/A")
        expected = step.get("expectedResult", "")
        lines.extend(
            [
                f"    # Description: {action}",
                f"    # Action: {test_data}",
                f"    # Expected: {expected}",
                "    No Operation  # TODO: Implement step",
                "",
            ]
        )
    return lines


def _generate_web_step_keyword(
    action: Any, expected: str, test_data: str
) -> tuple[List[str], bool]:
    """Generate Robot Framework keyword for a web test step."""
    lines = []
    keyword_generated = False

    action_str = str(action).lower() if action is not None else ""

    if "navigate to" in action_str:
        lines.extend(
            [
                "    Go To    http://localhost:8000/login.html",
                f"    Page Should Contain    {expected}",
            ]
        )
        keyword_generated = True
    elif "enter" in action_str and "username" in action_str:
        username = "testuser@example.com"
        if "username:" in test_data:
            username = test_data.split("username:")[1].strip()
        lines.extend(
            [
                f"    Input Text    id=username_field    {username}",
                f"    Textfield Value Should Be    id=username_field    {username}",
            ]
        )
        keyword_generated = True
    elif "enter" in action_str and "password" in action_str:
        password = "password123"
        if "password:" in test_data:
            password = test_data.split("password:")[1].strip()
        lines.extend(
            [
                f"    Input Text    id=password_field    {password}",
                f"    Textfield Value Should Be    id=password_field    {password}",
            ]
        )
        keyword_generated = True
    elif "click" in action_str and "button" in action_str:
        lines.extend(
            [
                "    Click Button    id=login_button",
                "    Sleep    1s    # Wait for JavaScript to execute",
                f"    Page Should Contain    {expected}",
            ]
        )
        keyword_generated = True
    elif "open an ssh connection" in action_str:
        lines.extend(
            [
                "    Open Connection    ${REMOTE_HOST}    "
                "username=${USERNAME}    password=${PASSWORD}",
                "    Login    ${USERNAME}    ${PASSWORD}",
            ]
        )
        keyword_generated = True
    elif "retrieve the specified file" in action_str:
        lines.append("    Get File    ${REMOTE_FILE_PATH}    ${LOCAL_DEST_PATH}")
        keyword_generated = True
    elif "close the ssh connection" in action_str:
        lines.append("    Close Connection")
        keyword_generated = True

    return lines, keyword_generated


def _should_add_browser_setup(steps: Any) -> bool:
    """Check if browser setup/teardown should be added."""
    if not isinstance(steps, list):
        return False
    return any(
        isinstance(step, dict) and "navigate to" in step.get("description", "").lower()
        for step in steps
    )


def _generate_web_steps(steps: Any) -> List[str]:
    """Generate Robot Framework steps for web test cases."""
    lines = []

    if not isinstance(steps, list):
        lines.append("    # Invalid steps data provided")
        return lines

    # Open browser at the start of the test
    if _should_add_browser_setup(steps):
        unique_id = str(uuid.uuid4())[:8]
        lines.extend(
            [
                "    ${chrome_options}=    Evaluate    "
                "sys.modules['selenium.webdriver'].ChromeOptions()    "
                "sys,selenium.webdriver",
                "    Call Method    ${chrome_options}    add_argument    "
                "argument=--headless",
                "    Call Method    ${chrome_options}    add_argument    "
                "argument=--no-sandbox",
                "    Call Method    ${chrome_options}    add_argument    "
                "argument=--disable-dev-shm-usage",
                "    Call Method    ${chrome_options}    add_argument    "
                "argument=--disable-gpu",
                "    Call Method    ${chrome_options}    add_argument    "
                "argument=--disable-extensions",
                f"    Call Method    ${{chrome_options}}    add_argument    "
                f"argument=--user-data-dir=/tmp/chrome_user_data_{unique_id}",
                "    Open Browser    http://localhost:8000/login.html    chrome    "
                "options=${chrome_options}",
            ]
        )

    for step in steps:
        if not isinstance(step, dict):
            lines.append("    # Invalid step format, skipping")
            continue

        action = step.get("action", step.get("description", "No action specified"))
        expected = step.get("expectedResult", "")
        test_data = step.get("testData", "")

        lines.extend(
            [
                f"    # Description: {action}",
            ]
        )
        if test_data != "N/A":
            lines.append(f"    # Action: {test_data}")
        lines.append(f"    # Expected: {expected}")

        keyword_lines, keyword_generated = _generate_web_step_keyword(
            action, expected, test_data
        )
        lines.extend(keyword_lines)

        if not keyword_generated:
            lines.append("    No Operation  # TODO: Implement step")
        lines.append("")

    # Close browser at the end of the test
    if _should_add_browser_setup(steps):
        lines.append("    Close Browser")

    return lines


def _generate_test_case(test_case_data: Any) -> List[str]:
    """Generate Robot Framework test case from JSON test case data."""
    lines = []
    if not isinstance(test_case_data, dict):
        return ["Invalid Test Case Data", "    No Operation", ""]

    test_name = test_case_data.get("name", "Unnamed Test")
    description = test_case_data.get("description", test_case_data.get("objective", ""))

    lines.append(f"{test_name}")
    if description and isinstance(description, str):
        lines.append(f"    [Documentation]    {description}")

    steps = test_case_data.get("steps")
    if "testScript" in test_case_data and isinstance(
        test_case_data["testScript"], dict
    ):
        script_steps = test_case_data["testScript"].get("steps")
        if isinstance(script_steps, list):
            if steps is None:
                steps = []
            steps.extend(script_steps)

    if not isinstance(steps, list) or not steps:
        lines.append("    No Operation  # Placeholder for missing or invalid steps")
    elif test_name == "Retrieve File From Remote Host":
        lines.extend(_generate_ssh_steps(steps))
    else:
        lines.extend(_generate_web_steps(steps))

    lines.append("")
    return lines


def parse_json(json_data: Dict[str, Any]) -> str:
    """Convert JSON data into the Robot Framework format."""
    if not isinstance(json_data, dict):
        raise TypeError("Input to parse_json must be a dictionary.")

    lines = _build_settings_section(json_data)
    lines.extend(["", "*** Test Cases ***", ""])

    tests = _extract_tests(json_data)

    if not tests:
        lines.extend(["Empty Test Case", "    No Operation", ""])
    else:
        for test_case_data in tests:
            lines.extend(_generate_test_case(test_case_data))

    return "\n".join(lines)


def load_and_parse_json(json_string: str) -> str:
    """Load JSON from string and convert to Robot Framework format."""
    try:
        json_data = json.loads(json_string)
        return parse_json(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON input: {e}") from e
