"""Utility helpers for blueprint processing."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from importobot.utils.validation import sanitize_robot_string

Step = dict[str, Any]


def extract_test_cases(data: Any) -> list[dict[str, Any]]:
    """Return all candidate test case dictionaries from input data."""
    candidates: list[dict[str, Any]] = []
    for test_case in _iter_candidate_test_cases(data):
        if test_case not in candidates:
            candidates.append(test_case)
    return candidates


def get_steps(test_case: dict[str, Any]) -> list[Step]:
    """Return normalized step dictionaries from a test case."""
    script = test_case.get("testScript")
    if isinstance(script, dict):
        steps = script.get("steps")
        if isinstance(steps, list):
            return [step for step in steps if isinstance(step, dict)]

    steps = test_case.get("steps")
    if isinstance(steps, list):
        return [step for step in steps if isinstance(step, dict)]
    return []


def iter_step_text(step: Step) -> Iterable[str]:
    """Yield textual fields from a step in priority order."""
    fields = (
        "description",
        "action",
        "step",
        "instruction",
        "testData",
        "expectedResult",
    )
    for field in fields:
        value = step.get(field)
        if isinstance(value, str):
            yield value


def format_test_name(test_case: dict[str, Any]) -> str:
    """Produce a sanitized display name for a test case."""
    key = test_case.get("key")
    if isinstance(key, str) and key.strip():
        return sanitize_robot_string(key.replace("-", " "))

    name = test_case.get("name") or test_case.get("title") or "Unnamed Test"
    return sanitize_robot_string(str(name))


def resolve_cli_command(
    test_case: dict[str, Any], context: dict[str, str] | None
) -> str:
    """Choose the CLI command identifier for a test case and context."""
    command = context["command"].strip() if context and context.get("command") else ""

    test_name = test_case.get("name", "")
    if isinstance(test_name, str) and test_name.strip():
        command = test_name.strip()

    if not command:
        return "cli-task"
    return command.lower()


def build_suite_documentation(commands: list[str]) -> str:
    """Generate a Robot Framework suite docstring covering CLI commands."""
    unique: list[str] = []
    for command in commands:
        if command not in unique:
            unique.append(command)
    if not unique:
        return "CLI task suite"
    if len(unique) == 1:
        return f"``{unique[0]}`` task suite"
    decorated = ", ".join(f"``{cmd}``" for cmd in unique)
    return f"CLI tasks: {decorated}"


def _iter_candidate_test_cases(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, dict):
        yield from _iter_cases_from_dict(data)
    elif isinstance(data, list):
        for element in data:
            if isinstance(element, dict):
                yield element


def _iter_cases_from_dict(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key in ("testCases", "tests", "items"):
        value = data.get(key)
        if isinstance(value, list):
            for element in value:
                if isinstance(element, dict):
                    yield element

    test_case = data.get("testCase")
    if isinstance(test_case, dict):
        yield test_case

    if "name" in data and isinstance(data["name"], str):
        yield data


__all__ = [
    "Step",
    "build_suite_documentation",
    "extract_test_cases",
    "format_test_name",
    "get_steps",
    "iter_step_text",
    "resolve_cli_command",
]
