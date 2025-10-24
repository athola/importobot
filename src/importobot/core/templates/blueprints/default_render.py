"""Helpers for rendering default CLI task sections."""

from __future__ import annotations

from typing import Any

from importobot.utils.validation import sanitize_robot_string

from .registry import get_suite_settings
from .utils import (
    build_suite_documentation as _build_suite_documentation,
)
from .utils import (
    format_test_name as _format_test_name,
)

__all__ = [
    "build_suite_documentation",
    "format_test_name",
    "render_test_documentation",
    "render_test_metadata",
    "render_test_metadata_comments",
    "render_test_settings",
    "render_test_tags",
]


build_suite_documentation = _build_suite_documentation
format_test_name = _format_test_name


def render_test_settings(suite_doc: str, resource_imports: list[str]) -> list[str]:
    """Render the Settings section for command execution tests.

    Uses learned Suite Setup/Teardown from templates if available,
    otherwise uses minimal generic defaults.

    Args:
        suite_doc: Documentation string for the suite
        resource_imports: List of resource file paths to import

    Returns:
        List of lines for the Settings section
    """
    lines: list[str] = []
    lines.append("*** Settings ***")
    lines.append(f"Documentation       {suite_doc}")
    lines.append("")
    lines.append("# ``SSHLibrary`` keywords:")
    lines.append("# ``Close All Connections``")
    lines.append("# ``Switch Connection``")
    lines.append("# ``Read Until Regexp``")
    lines.append("# ``Write``")
    lines.append("Library             SSHLibrary")

    if resource_imports:
        lines.append("# Resource imports discovered from templates:")
        lines.extend(
            f"Resource            {resource_path}" for resource_path in resource_imports
        )
    else:
        lines.append(
            "# No resource imports discovered; add Robot resources via "
            "--robot-template."
        )
    lines.append("")

    # Use learned suite settings if available
    suite_settings = get_suite_settings()

    if suite_settings and suite_settings.has_setup_keywords():
        # Use learned setup/teardown from customer templates
        if suite_settings.suite_setup:
            lines.extend(suite_settings.suite_setup)
        if suite_settings.suite_teardown:
            lines.extend(suite_settings.suite_teardown)
        if suite_settings.test_setup:
            lines.extend(suite_settings.test_setup)
        if suite_settings.test_teardown:
            lines.extend(suite_settings.test_teardown)
    else:
        # Default to minimal generic teardown
        lines.append("# No Suite Setup/Teardown learned from templates.")
        lines.append("# Provide --robot-template with your infrastructure keywords.")
        lines.append("")
        lines.append("# Generic SSHLibrary teardown:")
        lines.append("Suite Teardown      Close All Connections")

    lines.append("")
    lines.append("")
    return lines


def render_test_documentation(test_case: dict[str, Any], command: str) -> str:
    """Generate documentation string for a command execution test."""
    objective = (
        test_case.get("objective")
        or test_case.get("summary")
        or test_case.get("description")
    )
    default_text = objective or test_case.get("name") or f"``{command}`` task"
    test_doc = sanitize_robot_string(default_text)
    if not test_doc:
        test_doc = f"``{command}`` task"
    return test_doc


def render_test_tags(test_case: dict[str, Any]) -> list[str]:
    """Extract tags from test case metadata."""
    tags: list[str] = []
    if test_case.get("priority"):
        tags.append(str(test_case["priority"]))
    if test_case.get("category"):
        tags.append(str(test_case["category"]))
    for field_name in ("labels", "tags"):
        field_value = test_case.get(field_name)
        if isinstance(field_value, list):
            tags.extend(str(tag) for tag in field_value if tag)
        elif isinstance(field_value, str) and field_value.strip():
            tags.append(field_value)
    return tags


def render_test_metadata_comments(test_case: dict[str, Any]) -> list[str]:
    """Generate metadata comment lines for traceability."""
    lines: list[str] = []
    metadata_fields = {
        "requirement": "Requirement",
        "test_suite": "Test Suite",
        "evidences": "Evidence Files",
    }
    for field_key, field_label in metadata_fields.items():
        field_value = test_case.get(field_key)
        if field_value:
            if isinstance(field_value, list):
                items = ", ".join(str(item) for item in field_value if item)
                if items:
                    lines.append(f"    # {field_label}: {items}")
            elif isinstance(field_value, str) and field_value.strip():
                lines.append(f"    # {field_label}: {field_value}")
    return lines


def render_test_metadata(test_case: dict[str, Any], command: str) -> list[str]:
    """Render metadata fields for a command execution test."""
    lines: list[str] = []

    test_doc = render_test_documentation(test_case, command)
    lines.append(f"    [Documentation]    {test_doc}")

    tags = render_test_tags(test_case)
    if tags:
        tags_str = "    ".join(tags)
        lines.append(f"    [Tags]    {tags_str}")

    lines.extend(render_test_metadata_comments(test_case))

    return lines
