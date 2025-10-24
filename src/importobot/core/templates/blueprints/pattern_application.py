"""Helpers for applying learned step patterns."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from .expectations import render_expectation
from .registry import StepPattern

if TYPE_CHECKING:  # pragma: no cover
    from .default_builder import RenderState

__all__ = [
    "apply_cli_pattern",
    "apply_host_pattern",
    "apply_pattern_generic",
    "apply_target_pattern",
]

_placeholder_cache: dict[tuple[str, ...], re.Pattern[str]] = {}


def apply_pattern_generic(
    pattern: StepPattern,
    command_text: str,
    expected: str | None,
    state: RenderState,
    step_index: int,
    step_lines: list[str],
    *,
    replace_connection: Callable[[str, str], str],
    extract_assigned_variable: Callable[[str], str | None],
    var_token: Callable[[str, str | None], str],
) -> list[str]:
    """Apply a learned pattern from templates."""
    command_token = command_text.split()[0] if command_text.split() else ""
    lines = step_lines.copy()

    # Apply pattern with placeholders
    for template_line in pattern.lines:
        line = template_line.replace("{{COMMAND_LINE}}", command_text)
        line = line.replace("{{COMMAND_UPPER}}", command_token.upper())
        line = line.replace("{{COMMAND}}", command_token)

        # Update connection if pattern uses connections
        if pattern.connection and "Switch Connection" in line:
            line = replace_connection(line, pattern.connection)

        lines.append(line)

        # Track output variable
        extracted_var = extract_assigned_variable(line.strip())
        if extracted_var:
            state.outputs[step_index] = extracted_var

    # Add expectation checking
    if expected and state.outputs.get(step_index):
        lines.extend(
            render_expectation(
                expected, state.outputs[step_index], step_index=step_index, state=state
            )
        )

    return lines


def apply_cli_pattern(
    pattern: StepPattern,
    command_line: str,
    command_token: str,
    expected: str | None,
    state: RenderState,
    connection_override: str,
    step_index: int,
    *,
    replace_connection: Callable[[str, str], str],
    extract_assigned_variable: Callable[[str], str | None],
    var_token: Callable[[str, str | None], str],
) -> list[str]:
    """Apply CLI-specific pattern substitutions."""
    replacements = _placeholder_replacements(command_line, command_token)
    lines: list[str] = []
    cli_var: str | None = None

    for template_line in pattern.lines:
        new_line = _normalize_regexp_line(
            _substitute_placeholders(template_line, replacements)
        )
        lines.append(new_line)
        stripped = new_line.strip()
        if stripped.startswith("Switch Connection"):
            new_line = replace_connection(new_line, connection_override)
            state.current_connection = connection_override
        lines[-1] = new_line
        stripped = new_line.strip()
        assigned = extract_assigned_variable(stripped)
        if assigned and "Read" in stripped:
            cli_var = assigned

    if cli_var is None:
        cli_var = _auto_assign(
            lines,
            "Read Until",
            command_token,
            suffix="cli",
            factory=var_token,
        )

    if state.last_target_var and cli_var:
        lines.append(f"    Should Contain    {cli_var}    {state.last_target_var}")

    if cli_var:
        state.outputs[step_index] = cli_var

    lines.extend(
        render_expectation(
            expected,
            cli_var,
            step_index=step_index,
            state=state,
        )
    )
    return lines


def apply_target_pattern(
    pattern: StepPattern,
    command_line: str,
    command_token: str,
    expected: str | None,
    notes: list[str],
    state: RenderState,
    connection_override: str,
    step_index: int,
    *,
    replace_connection: Callable[[str, str], str],
    extract_assigned_variable: Callable[[str], str | None],
    var_token: Callable[[str, str | None], str],
) -> list[str]:
    """Apply target-side pattern substitutions."""
    replacements = _placeholder_replacements(command_line, command_token)
    lines: list[str] = []
    assigned_var: str | None = None

    for template_line in pattern.lines:
        new_line = _normalize_regexp_line(
            _substitute_placeholders(template_line, replacements)
        )
        lines.append(new_line)
        stripped = new_line.strip()
        if stripped.startswith("Switch Connection"):
            new_line = replace_connection(new_line, connection_override)
            state.current_connection = connection_override
        lines[-1] = new_line
        stripped = new_line.strip()
        assigned = extract_assigned_variable(stripped)
        if assigned and "Execute Command" in stripped:
            assigned_var = assigned
            state.last_target_var = assigned_var

    if assigned_var is None:
        assigned_var = _auto_assign(
            lines,
            "Execute Command",
            command_token,
            suffix="remote",
            factory=var_token,
        )
        state.last_target_var = assigned_var

    lines.extend([f"    # {note}" for note in notes])

    if assigned_var:
        state.outputs[step_index] = assigned_var

    lines.extend(
        render_expectation(
            expected,
            assigned_var,
            step_index=step_index,
            state=state,
        )
    )
    return lines


def apply_host_pattern(
    pattern: StepPattern,
    command_line: str,
    command_token: str,
    expected: str | None,
    notes: list[str],
    state: RenderState,
    connection_override: str,
    step_index: int,
    *,
    replace_connection: Callable[[str, str], str],
    extract_assigned_variable: Callable[[str], str | None],
    var_token: Callable[[str, str | None], str],
) -> list[str]:
    """Apply host-side pattern substitutions."""
    replacements = _placeholder_replacements(command_line, command_token)
    lines: list[str] = []
    assigned_var: str | None = None

    for template_line in pattern.lines:
        new_line = _normalize_regexp_line(
            _substitute_placeholders(template_line, replacements)
        )
        lines.append(new_line)
        stripped = new_line.strip()
        if stripped.startswith("Switch Connection"):
            new_line = replace_connection(new_line, connection_override)
            state.current_connection = connection_override
        lines[-1] = new_line
        stripped = new_line.strip()
        assigned = extract_assigned_variable(stripped)
        if assigned and "Execute Command" in stripped:
            assigned_var = assigned

    if assigned_var is None:
        assigned_var = _auto_assign(
            lines,
            "Execute Command",
            command_token,
            suffix="host",
            factory=var_token,
        )

    lines.extend([f"    # {note}" for note in notes])

    if assigned_var:
        state.outputs[step_index] = assigned_var

    lines.extend(
        render_expectation(
            expected,
            assigned_var,
            step_index=step_index,
            state=state,
        )
    )
    return lines


def _placeholder_replacements(command_line: str, command_token: str) -> dict[str, str]:
    return {
        "{{COMMAND_LINE}}": command_line,
        "{{COMMAND}}": command_token,
        "{{COMMAND_UPPER}}": command_token.upper(),
    }


def _substitute_placeholders(line: str, replacements: dict[str, str]) -> str:
    if not replacements:
        return line.replace("$$", "$")

    cache_key = tuple(sorted(replacements.keys()))
    pattern = _placeholder_cache.get(cache_key)
    if pattern is None:
        escaped = (re.escape(key) for key in cache_key)
        pattern = re.compile("|".join(escaped))
        _placeholder_cache[cache_key] = pattern

    def _replace(match: re.Match[str]) -> str:
        return replacements[match.group(0)]

    result = pattern.sub(_replace, line)
    return result.replace("$$", "$")


def _auto_assign(
    lines: list[str],
    trigger: str,
    command_token: str,
    *,
    suffix: str,
    factory: Callable[[str, str | None], str],
) -> str:
    var_name = command_token
    for idx, line in enumerate(lines):
        if trigger in line:
            indent, match, remainder_tail = line.partition(trigger)
            remainder = match + remainder_tail
            auto_var = _sanitize_and_tokenize(var_name, suffix=suffix, factory=factory)
            lines[idx] = f"{indent}{auto_var}=    {remainder}"
            return auto_var
    auto_var = _sanitize_and_tokenize(var_name, suffix=suffix, factory=factory)
    lines.append(f"    {auto_var}=    {trigger}")
    return auto_var


def _sanitize_and_tokenize(
    value: str,
    *,
    suffix: str | None,
    factory: Callable[[str, str | None], str],
) -> str:
    return factory(value, suffix)


def _normalize_regexp_line(line: str) -> str:
    if (
        "Read Until Regexp" in line
        and " task " in line
        and "(\\S+)" not in line
        and line.rstrip().endswith("completed successfully!")
    ):
        prefix, _, suffix = line.partition(" task ")
        return f"{prefix} task (\\S+) {suffix}"
    return line
