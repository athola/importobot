"""Helpers for rendering default CLI task sections."""

from __future__ import annotations

from typing import Any

from importobot.utils.validation import sanitize_robot_string

from .utils import (
    build_suite_documentation as _build_suite_documentation,
)
from .utils import (
    format_test_name as _format_test_name,
)

__all__ = [
    "build_suite_documentation",
    "format_test_name",
    "render_cli_task_documentation",
    "render_cli_task_metadata",
    "render_cli_task_metadata_comments",
    "render_cli_task_settings",
    "render_cli_task_tags",
]


build_suite_documentation = _build_suite_documentation
format_test_name = _format_test_name


def render_cli_task_settings(suite_doc: str, resource_imports: list[str]) -> list[str]:
    """Render the Settings section of a CLI task."""
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
    lines.append("Suite Setup         Run Keywords")
    lines.append("...                     Connect Hosts SSH")
    lines.append("...                     CLI Entry")
    lines.append("Suite Teardown      Run Keywords")
    lines.append("...                     Quit CLI")
    lines.append("...                     Close All Connections")
    lines.append("")
    lines.append("")
    return lines


def render_cli_task_documentation(test_case: dict[str, Any], command: str) -> str:
    """Generate documentation string for a CLI task."""
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


def render_cli_task_tags(test_case: dict[str, Any]) -> list[str]:
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


def render_cli_task_metadata_comments(test_case: dict[str, Any]) -> list[str]:
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


def render_cli_task_metadata(
    test_case: dict[str, Any], command: str, proc_name: str | None
) -> list[str]:
    """Render metadata fields (tags, documentation, etc.) for a CLI task."""
    lines: list[str] = []

    test_doc = render_cli_task_documentation(test_case, command)
    lines.append(f"    [Documentation]    {test_doc}")

    tags = render_cli_task_tags(test_case)
    if tags:
        tags_str = "    ".join(tags)
        lines.append(f"    [Tags]    {tags_str}")

    lines.extend(render_cli_task_metadata_comments(test_case))

    if proc_name:
        lines.append(f"    VAR    ${{proc_name}}    {proc_name}")

    return lines
