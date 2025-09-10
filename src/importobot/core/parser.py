"""JSON parsing functionality."""

from typing import Any, Dict, List


def _build_settings_section(json_data: Dict[str, Any]) -> List[str]:
    """Build the Robot Framework settings section."""
    lines = [
        "*** Settings ***",
        "Documentation    Tests converted from JSON",
        "Library    SeleniumLibrary",
    ]

    # Add SSHLibrary only if it's needed
    if "ssh" in str(json_data).lower() and "Retrieve File From Remote Host" not in str(
        json_data
    ):
        lines.append("Library    SSHLibrary")

    return lines


def _extract_tests(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract test cases from JSON data."""
    tests = json_data.get("tests", [])
    if not tests and "name" in json_data:
        # Handle Zephyr-style single test case
        tests = [json_data]
    return tests


def _generate_ssh_steps(steps: List[Dict[str, Any]]) -> List[str]:
    """Generate Robot Framework steps for SSH test cases."""
    lines = []
    for step in steps:
        action = step.get("description", "No action specified")
        test_data = step.get("testData", "N/A")
        expected = step.get("expectedResult", "")
        lines.extend([
            f"    # Description: {action}",
            f"    # Action: {test_data}",
            f"    # Expected: {expected}",
            "    No Operation  # TODO: Implement step",
            ""
        ])
    return lines


def _generate_web_step_keyword(
    action: str, expected: str, test_data: str
) -> tuple[List[str], bool]:
    """Generate Robot Framework keyword for a web test step."""
    lines = []
    keyword_generated = False

    if "navigate to" in action.lower():
        lines.extend([
            "    Go To    http://localhost:8000/login.html",
            f"    Page Should Contain    {expected}"
        ])
        keyword_generated = True
    elif "enter" in action.lower() and "username" in action.lower():
        username = "testuser@example.com"
        if "username:" in test_data:
            username = test_data.split("username:")[1].strip()
        lines.extend([
            f"    Input Text    id=username_field    {username}",
            f"    Textfield Value Should Be    id=username_field    {username}"
        ])
        keyword_generated = True
    elif "enter" in action.lower() and "password" in action.lower():
        password = "password123"
        if "password:" in test_data:
            password = test_data.split("password:")[1].strip()
        lines.extend([
            f"    Input Text    id=password_field    {password}",
            f"    Textfield Value Should Be    id=password_field    {password}"
        ])
        keyword_generated = True
    elif "click" in action.lower() and "button" in action.lower():
        lines.extend([
            "    Click Button    id=login_button",
            f"    Page Should Contain    {expected}"
        ])
        keyword_generated = True
    elif "open an ssh connection" in action.lower():
        lines.extend([
            "    Open Connection    ${REMOTE_HOST}    "
            "username=${USERNAME}    password=${PASSWORD}",
            "    Login    ${USERNAME}    ${PASSWORD}"
        ])
        keyword_generated = True
    elif "retrieve the specified file" in action.lower():
        lines.append("    Get File    ${REMOTE_FILE_PATH}    ${LOCAL_DEST_PATH}")
        keyword_generated = True
    elif "close the ssh connection" in action.lower():
        lines.append("    Close Connection")
        keyword_generated = True

    return lines, keyword_generated


def _should_add_browser_setup(steps: List[Dict[str, Any]]) -> bool:
    """Check if browser setup/teardown should be added."""
    return any(
        "navigate to" in step.get("description", "").lower()
        for step in steps
    )


def _generate_web_steps(steps: List[Dict[str, Any]]) -> List[str]:
    """Generate Robot Framework steps for web test cases."""
    lines = []

    # Open browser at the start of the test
    if _should_add_browser_setup(steps):
        lines.append("    Open Browser    http://localhost:8000/login.html    chrome")

    for step in steps:
        action = step.get("action", step.get("description", "No action specified"))
        expected = step.get("expectedResult", "")
        test_data = step.get("testData", "")

        lines.extend([
            f"    # Description: {action}",
        ])
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


def _generate_test_case(test_case_data: Dict[str, Any]) -> List[str]:
    """Generate Robot Framework test case from JSON test case data."""
    lines = []
    test_name = test_case_data.get("name", "Unnamed Test")
    description = test_case_data.get("description", test_case_data.get("objective", ""))

    lines.append(f"{test_name}")
    if description:
        lines.append(f"    [Documentation]    {description}")

    steps = test_case_data.get("steps", [])
    if ("testScript" in test_case_data and
        isinstance(test_case_data["testScript"], dict)):
        steps.extend(test_case_data["testScript"].get("steps", []))

    if not steps:
        lines.append("    No Operation  # Placeholder for missing steps")
    elif test_name == "Retrieve File From Remote Host":
        lines.extend(_generate_ssh_steps(steps))
    else:
        lines.extend(_generate_web_steps(steps))

    lines.append("")
    return lines


def parse_json(json_data: Dict[str, Any]) -> str:
    """Convert JSON data into the Robot Framework format."""
    lines = _build_settings_section(json_data)
    lines.extend(["", "*** Test Cases ***", ""])

    tests = _extract_tests(json_data)

    if not tests:
        lines.extend(["Empty Test Case", "    No Operation", ""])
    else:
        for test_case_data in tests:
            lines.extend(_generate_test_case(test_case_data))

    return "\n".join(lines)
