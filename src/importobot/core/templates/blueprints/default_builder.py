"""CLI blueprint rendering helpers."""

from __future__ import annotations

import re
from typing import Any

from .default_render import (
    build_suite_documentation,
    format_test_name,
    render_test_documentation,
    render_test_metadata,
    render_test_settings,
)
from .expectations import render_expectation
from .models import BlueprintResult, MatchContext, Step
from .pattern_application import apply_pattern_generic
from .registry import (
    find_step_pattern,
    get_resource_imports,
    template_name_candidates,
)
from .utils import resolve_cli_command as _resolve_cli_command

# Constants for execution context
CONTEXT_LOCAL = "local"
CONTEXT_REMOTE = "remote"


class RenderState:
    """Mutable state while rendering CLI steps."""

    def __init__(self) -> None:
        """Initialise tracking fields for the current render pass."""
        self.current_connection: str | None = None
        self.last_target_var: str | None = None
        self.outputs: dict[int, str] = {}


def _build_command_suite(
    test_cases: list[dict[str, Any]],
    step_groups: list[list[Step]],
    contexts: list[MatchContext],
) -> BlueprintResult | None:
    if not test_cases:
        return None

    commands = _resolve_cli_commands(test_cases, contexts)
    suite_doc = build_suite_documentation(commands)
    default_rendering = _render_default_suite(
        test_cases, step_groups, commands, suite_doc
    )

    substitutions = _build_suite_substitutions(
        primary_test_case=test_cases[0],
        commands=commands,
        suite_doc=suite_doc,
    )
    template_candidates = _suggest_template_candidates(
        test_cases=test_cases,
        contexts=contexts,
        primary_command=substitutions["command"],
    )
    prefer_template = bool(template_candidates)

    return BlueprintResult(
        template_candidates=template_candidates,
        substitutions=substitutions,
        default_rendering=default_rendering,
        prefer_template=prefer_template,
    )


def _resolve_cli_commands(
    test_cases: list[dict[str, Any]], contexts: list[MatchContext]
) -> list[str]:
    """Normalize CLI commands for each test case/context pair."""
    commands: list[str] = []
    for test_case, context in zip(test_cases, contexts, strict=True):
        command = _resolve_cli_command(test_case, context)
        if context and context.get("command"):
            command = context["command"].strip().lower()
        commands.append(command)
    return commands


def _build_suite_substitutions(
    *,
    primary_test_case: dict[str, Any],
    commands: list[str],
    suite_doc: str,
) -> dict[str, Any]:
    """Compose substitution map for CLI blueprint rendering."""
    primary_command = commands[0] if commands else "command-execution"
    base_for_cli_var = (
        primary_command if primary_command else (commands[0] if commands else "result")
    )
    substitutions: dict[str, Any] = {
        "command": primary_command,
        "test_name": format_test_name(primary_test_case),
        "suite_doc": suite_doc,
        "test_doc": f"Execute {primary_command}",
        "command_result": _var_token(base_for_cli_var or "result", suffix="result"),
        "documentation": render_test_documentation(primary_test_case, primary_command),
    }
    return substitutions


def _suggest_template_candidates(
    *,
    test_cases: list[dict[str, Any]],
    contexts: list[MatchContext],
    primary_command: str,
) -> list[str]:
    """Suggest template names when only a single test case is present."""
    if len(test_cases) != 1:
        return []
    template_hint = contexts[0].get("template") if contexts else None
    return template_name_candidates(
        "command_execution",
        template_hint,
        primary_command,
        f"{primary_command}_task",
    )


def _render_default_suite(
    test_cases: list[dict[str, Any]],
    step_groups: list[list[Step]],
    commands: list[str],
    suite_doc: str,
) -> str:
    lines: list[str] = []

    # Settings section
    resource_imports = get_resource_imports()
    lines.extend(render_test_settings(suite_doc, resource_imports))

    lines.append("*** Test Cases ***")

    for index, (test_case, steps, command) in enumerate(
        zip(test_cases, step_groups, commands, strict=True)
    ):
        if index > 0:
            lines.append("")

        test_name = format_test_name(test_case)
        lines.append(test_name)

        # Metadata
        lines.extend(render_test_metadata(test_case, command))

        # Steps
        state = RenderState()
        sorted_steps = sorted(
            steps,
            key=lambda step: step.get("index", 0),
        )

        for step in sorted_steps:
            step_index = int(step.get("index", len(state.outputs)))
            step_lines = _render_command_step(step, command, state, step_index)
            if step_lines:
                lines.append("")
                lines.extend(step_lines)

    return "\n".join(lines) + "\n"


def _render_command_step(
    step: Step,
    command: str,
    state: RenderState,
    step_index: int,
) -> list[str]:
    """Render a command execution step using learned patterns or RF defaults."""
    test_data = step.get("testData") or ""
    description = (
        step.get("description")
        or step.get("action")
        or step.get("step")
        or step.get("instruction")
    )
    expected = step.get("expectedResult")
    data_field = step.get("data")

    # Parse execution context and command
    context, command_text = _parse_execution_context(test_data)

    step_lines: list[str] = []
    if description:
        step_lines.append(f"    # {description}")
    if data_field and isinstance(data_field, str) and data_field.strip():
        step_lines.append(f"    # Data: {data_field}")

    if not command_text:
        if description:
            step_lines.append(f"    Log    {description}")
        return step_lines

    # Try to find learned pattern from templates
    command_token = command_text.split()[0] if command_text.split() else ""
    pattern = find_step_pattern(command_token=command_token)

    if pattern:
        # Use learned pattern from customer templates
        return _apply_learned_pattern(
            pattern, command_text, expected, state, step_index, step_lines
        )

    # Default: use RobotFrameworkKeywordRegistry defaults
    # Default to SSHLibrary for remote command execution
    return _render_with_default_library(
        command_text, expected, context, state, step_index, step_lines
    )


def _apply_learned_pattern(
    pattern: Any,
    command_text: str,
    expected: str | None,
    state: RenderState,
    step_index: int,
    step_lines: list[str],
) -> list[str]:
    """Apply a learned pattern from templates."""
    return apply_pattern_generic(
        pattern,
        command_text,
        expected,
        state,
        step_index,
        step_lines,
        replace_connection=_replace_connection,
        extract_assigned_variable=_extract_assigned_variable,
        var_token=_var_token,
    )


def _render_with_default_library(
    command_text: str,
    expected: str | None,
    context: str,
    state: RenderState,
    step_index: int,
    step_lines: list[str],
) -> list[str]:
    """Render command using Robot Framework standard libraries.

    Uses SSHLibrary for remote execution (default), OperatingSystem for local.

    Args:
        command_text: The command to execute
        expected: Optional expected result for validation
        context: Execution context - CONTEXT_LOCAL for OperatingSystem library,
                 CONTEXT_REMOTE or custom name for SSHLibrary connections
        state: Current render state
        step_index: Index of this step
        step_lines: Accumulated lines for this step

    Returns:
        Updated step_lines with rendered command execution
    """
    # Determine library based on context
    if context == CONTEXT_LOCAL:
        # Local execution using OperatingSystem library
        var_name = _command_to_identifier(command_text)
        result_var = _var_token(var_name or "result")
        step_lines.append(
            f"    {result_var}=    Run And Return Stdout    {command_text}"
        )
        state.outputs[step_index] = result_var
    else:
        # Remote execution using SSHLibrary (default)
        connection_name = "Remote" if context == CONTEXT_REMOTE else context.title()
        _ensure_connection(step_lines, state, connection_name)

        var_name = _command_to_identifier(command_text)
        result_var = _var_token(var_name or "result")
        step_lines.append(f"    {result_var}=    Execute Command    {command_text}")
        state.outputs[step_index] = result_var

    # Add expectation checking if provided
    if expected:
        step_lines.extend(
            render_expectation(expected, result_var, step_index=step_index, state=state)
        )

    return step_lines


def _parse_execution_context(test_data: str) -> tuple[str, str]:
    """Parse execution context from test data.

    Args:
        test_data: Test data string that may contain context prefix

    Returns:
        Tuple of (context_name, command_text)

        Context values:
        - CONTEXT_LOCAL ("local"): Uses OperatingSystem library for local execution
        - CONTEXT_REMOTE ("remote"): Uses SSHLibrary with "Remote" connection (default)
        - Other string: Uses SSHLibrary with custom connection name

    Examples:
        >>> _parse_execution_context("local: echo hello")
        ('local', 'echo hello')
        >>> _parse_execution_context("remote: ls /tmp")
        ('remote', 'ls /tmp')
        >>> _parse_execution_context("database: SELECT * FROM users")
        ('database', 'SELECT * FROM users')
        >>> _parse_execution_context("uptime")
        ('remote', 'uptime')
    """
    # Try explicit context pattern (e.g., "remote: ls", "local: echo")
    match = re.match(r"(?i)\s*(?:on\s+)?([a-z_]+)\s*:\s*(.*)", test_data)
    if match:
        context = match.group(1).lower()
        command_text = match.group(2).strip()
        return context, command_text

    # No explicit context - return command as-is
    command_text = test_data.strip()
    return CONTEXT_REMOTE, command_text  # Default to remote execution


def _normalize_command(command_text: str) -> str:
    """Normalize command text (placeholder for future variable substitution)."""
    return command_text


def _split_command_and_notes(command_text: str) -> tuple[str, list[str]]:
    if ";" not in command_text:
        return command_text, []
    segments = [
        segment.strip() for segment in command_text.split(";") if segment.strip()
    ]
    if not segments:
        return command_text, []
    primary = segments[0]
    notes = segments[1:]
    return primary, notes


def _extract_assigned_variable(stripped_line: str) -> str | None:
    if "=" not in stripped_line:
        return None
    variable_part = stripped_line.split("=", 1)[0].strip()
    if variable_part.startswith("${") and variable_part.endswith("}"):
        return variable_part
    return None


def _replace_connection(line: str, connection_name: str) -> str:
    if "Switch Connection" not in line:
        return line
    prefix, _, _ = line.partition("Switch Connection")
    return f"{prefix}Switch Connection    {connection_name}"


def _ensure_connection(lines: list[str], state: RenderState, connection: str) -> None:
    if state.current_connection != connection:
        lines.append(f"    Switch Connection    {connection}")
        state.current_connection = connection


def _command_to_identifier(command_text: str) -> str:
    first_token = command_text.strip().split()[0] if command_text.strip() else ""
    return _sanitize_identifier(first_token)


def _var_token(base: str, suffix: str | None = None) -> str:
    identifier = _sanitize_identifier(base)
    if suffix:
        identifier = f"{identifier}_{suffix}"
    return f"${{{identifier}}}"


def _sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    if not sanitized:
        sanitized = "value"
    return sanitized.lower()
