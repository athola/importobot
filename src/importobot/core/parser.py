"""JSON parsing functionality."""

from typing import Any, Dict


def parse_json(json_data: Dict[str, Any]) -> str:
    """Converts JSON data into the Robot Framework format."""
    lines = [
        "*** Settings ***",
        "Documentation    Tests converted from JSON",
        "Library    SeleniumLibrary",
        "",
        "*** Test Cases ***",
        "",
    ]

    for test in json_data.get("tests", []):
        lines.append(f"{test.get('name', 'Unnamed Test')}")
        lines.append(f"    [Documentation]    {test.get('description', '')}")

        for step in test.get("steps", []):
            action = step.get("action", "")
            expected = step.get("expectedResult", "")
            lines.append(f"    # Action: {action}")
            lines.append(f"    # Expected: {expected}")
            lines.append("    No Operation  # TODO: Implement step")
        lines.append("")

    return "\n".join(lines)
