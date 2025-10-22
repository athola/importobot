"""CLI blueprint rendering helpers."""

from __future__ import annotations

import re
from typing import Any

from .default_render import (
    build_suite_documentation,
    format_test_name,
    render_cli_task_documentation,
    render_cli_task_metadata,
    render_cli_task_settings,
)
from .expectations import render_expectation
from .models import BlueprintResult, MatchContext, Step
from .pattern_application import (
    apply_cli_pattern,
    apply_host_pattern,
    apply_target_pattern,
)
from .registry import (
    find_step_pattern,
    get_resource_imports,
    template_name_candidates,
)
from .utils import resolve_cli_command as _resolve_cli_command


class RenderState:
    """Mutable state while rendering CLI steps."""

    def __init__(self) -> None:
        """Initialise tracking fields for the current render pass."""
        self.current_connection: str | None = None
        self.last_target_var: str | None = None
        self.outputs: dict[int, str] = {}


def _build_cli_task_suite(
    test_cases: list[dict[str, Any]],
    step_groups: list[list[Step]],
    contexts: list[MatchContext],
) -> BlueprintResult | None:
    if not test_cases:
        return None

    commands: list[str] = []
    proc_names: list[str | None] = []

    for test_case, context in zip(test_cases, contexts, strict=True):
        command = _resolve_cli_command(test_case, context)
        if context and context.get("command"):
            command = context["command"].strip().lower()
        commands.append(command)
        proc_names.append(context.get("proc_name") if context else None)

    suite_doc = build_suite_documentation(commands)
    default_rendering = _render_cli_task_default(
        test_cases, step_groups, commands, proc_names, suite_doc
    )

    primary_command = commands[0] if commands else "cli-task"
    primary_proc = proc_names[0] or ""

    substitutions = {
        "command": primary_command,
        "test_name": format_test_name(test_cases[0]),
        "suite_doc": suite_doc,
        "test_doc": f"{primary_command} --proc_name task.",
        "proc_value": primary_proc,
        "proc_name_value": primary_proc,
    }
    base_for_cli_var = primary_command or (commands[0] if commands else "cli")
    substitutions["cli_assignment"] = _var_token(base_for_cli_var, suffix="cli")

    template_candidates = []
    if len(test_cases) == 1:
        template_candidates = template_name_candidates(
            "cli_proc_task",
            contexts[0].get("template") if contexts else None,
            primary_command,
            f"{primary_command}_task",
        )

    documentation = render_cli_task_documentation(test_cases[0], primary_command)
    substitutions.update(
        {
            "documentation": documentation,
            "proc_name": primary_proc,
        }
    )

    prefer_template = bool(template_candidates and primary_proc)

    return BlueprintResult(
        template_candidates=template_candidates,
        substitutions=substitutions,
        default_rendering=default_rendering,
        prefer_template=prefer_template,
    )


def _render_cli_task_default(
    test_cases: list[dict[str, Any]],
    step_groups: list[list[Step]],
    commands: list[str],
    proc_names: list[str | None],
    suite_doc: str,
) -> str:
    lines: list[str] = []

    # Settings section
    resource_imports = get_resource_imports()
    lines.extend(render_cli_task_settings(suite_doc, resource_imports))

    lines.append("*** Test Cases ***")

    for index, (test_case, steps, command, proc_name) in enumerate(
        zip(test_cases, step_groups, commands, proc_names, strict=True)
    ):
        if index > 0:
            lines.append("")

        test_name = format_test_name(test_case)
        lines.append(test_name)

        # Metadata
        lines.extend(render_cli_task_metadata(test_case, command, proc_name))

        # Steps
        state = RenderState()
        sorted_steps = sorted(
            steps,
            key=lambda step: step.get("index", 0),
        )

        for step in sorted_steps:
            step_index = int(step.get("index", len(state.outputs)))
            step_lines = _render_cli_step(step, command, proc_name, state, step_index)
            if step_lines:
                lines.append("")
                lines.extend(step_lines)

    return "\n".join(lines) + "\n"


def _render_cli_step(
    step: Step,
    command: str,
    proc_name: str | None,
    state: RenderState,
    step_index: int,
) -> list[str]:
    test_data = step.get("testData") or ""
    # Check for action description in multiple fields:
    # (description, action, step, instruction)
    description = (
        step.get("description")
        or step.get("action")
        or step.get("step")
        or step.get("instruction")
    )
    expected = step.get("expectedResult")
    # Check for additional test data field
    data_field = step.get("data")

    location, command_text, connection_override = _parse_step_location(test_data)

    step_lines: list[str] = []
    if description:
        step_lines.append(f"    # {description}")
    # Add data field as a comment if present
    if data_field and isinstance(data_field, str) and data_field.strip():
        step_lines.append(f"    # Data: {data_field}")

    if location == "cli":
        return _render_cli_location(
            step_lines,
            command_text,
            command,
            proc_name,
            expected,
            state,
            connection_override,
            step_index,
        )

    if location == "target":
        return _render_target_location(
            step_lines,
            command_text,
            command,
            proc_name,
            expected,
            state,
            connection_override,
            step_index,
        )

    if location == "host":
        return _render_host_location(
            step_lines,
            command_text,
            command,
            proc_name,
            expected,
            state,
            connection_override,
            step_index,
        )

    # Unknown location: log intent
    if command_text:
        step_lines.append(f"    Log    {command_text}")
    if expected:
        step_lines.append(f"    Log    Expected: {expected}")
    return step_lines


def _render_cli_location(
    step_lines: list[str],
    command_text: str,
    command: str,
    proc_name: str | None,
    expected: str | None,
    state: RenderState,
    connection_override: str | None,
    step_index: int,
) -> list[str]:
    normalized_cmd = _normalize_cli_command(command_text, proc_name)
    command_token = (normalized_cmd.split() or [command])[0].lower()

    # First try to find a specific pattern match for this command
    pattern = find_step_pattern("cli", command_token)

    # Only use generic patterns if the command is a common CLI command
    # and we don't have a specific pattern match
    if not pattern and _is_generic_cli_command(command_token):
        pattern = find_step_pattern("cli", command.lower(), allow_generic=True)

    if pattern:
        return apply_cli_pattern(
            pattern,
            normalized_cmd,
            command_token,
            expected,
            state,
            connection_override or "Controller",
            step_index,
            replace_connection=_replace_connection,
            extract_assigned_variable=_extract_assigned_variable,
            var_token=_var_token,
        )

    _ensure_connection(step_lines, state, connection_override or "Controller")
    normalized_cmd = _normalize_cli_command(command_text, proc_name)
    step_lines.append(f"    Write    {normalized_cmd}")
    cli_var = _var_token(command_token, suffix="cli")
    step_lines.append(f"    {cli_var}=    Read Until Prompt")
    state.outputs[step_index] = cli_var
    if state.last_target_var:
        step_lines.append(f"    Should Contain    {cli_var}    {state.last_target_var}")
    step_lines.extend(
        render_expectation(expected, cli_var, step_index=step_index, state=state)
    )
    return step_lines


def _render_target_location(
    step_lines: list[str],
    command_text: str,
    command: str,
    proc_name: str | None,
    expected: str | None,
    state: RenderState,
    connection_override: str | None,
    step_index: int,
) -> list[str]:
    command_exec, notes = _split_command_and_notes(command_text)
    normalized_exec = _normalize_cli_command(command_exec, proc_name)
    command_token = (command_exec.split() or [command])[0].lower()
    pattern = find_step_pattern("target", command_token)
    if pattern:
        return apply_target_pattern(
            pattern,
            normalized_exec,
            command_token,
            expected,
            notes,
            state,
            connection_override or "Target",
            step_index,
            replace_connection=_replace_connection,
            extract_assigned_variable=_extract_assigned_variable,
            var_token=_var_token,
        )

    connection_name = connection_override or "Target"
    _ensure_connection(step_lines, state, connection_name)
    var_name = _command_to_identifier(normalized_exec)
    target_var = _var_token(var_name or "target")
    state.last_target_var = target_var
    step_lines.append(f"    {target_var}=    Execute Command    {normalized_exec}")
    state.outputs[step_index] = target_var
    step_lines.extend(
        render_expectation(expected, target_var, step_index=step_index, state=state)
    )
    step_lines.extend([f"    # {note}" for note in notes])
    return step_lines


def _render_host_location(
    step_lines: list[str],
    command_text: str,
    command: str,
    proc_name: str | None,
    expected: str | None,
    state: RenderState,
    connection_override: str | None,
    step_index: int,
) -> list[str]:
    command_exec, notes = _split_command_and_notes(command_text)
    normalized_exec = _normalize_cli_command(command_exec, proc_name)
    command_token = (command_exec.split() or [command])[0].lower()
    pattern = find_step_pattern("host", command_token)
    if pattern:
        return apply_host_pattern(
            pattern,
            normalized_exec,
            command_token,
            expected,
            notes,
            state,
            connection_override or "Controller",
            step_index,
            replace_connection=_replace_connection,
            extract_assigned_variable=_extract_assigned_variable,
            var_token=_var_token,
        )

    _ensure_connection(step_lines, state, connection_override or "Controller")
    host_var = _var_token(_command_to_identifier(normalized_exec) or "host")
    step_lines.append(f"    {host_var}=    Execute Command    {normalized_exec}")
    state.outputs[step_index] = host_var
    step_lines.extend(
        render_expectation(expected, host_var, step_index=step_index, state=state)
    )
    step_lines.extend([f"    # {note}" for note in notes])
    return step_lines


def _parse_step_location(test_data: str) -> tuple[str, str, str | None]:
    # Try explicit location pattern first (e.g., "cli: command", "target: command")
    match = re.match(r"(?i)\s*(?:on\s+)?([A-Z_]+)\s*:\s*(.*)", test_data)
    if match:
        token = match.group(1).lower()
        command_text = match.group(2).strip()

        if token == "cli":
            return "cli", command_text, "Controller"
        if token in {"target", "remote_host"}:
            connection = "REMOTE_HOST" if token == "remote_host" else "Target"
            return "target", command_text, connection
        if token in {"host", "controller"}:
            return "host", command_text, "Controller"

        return token, command_text, None

    # Fallback: try to infer location from command patterns
    command_text = test_data.strip()
    if not command_text:
        return "", "", None

    # Common CLI commands that typically run on connected agent
    cli_commands = {
        "touch",
        "rm",
        "ls",
        "cat",
        "mkdir",
        "cp",
        "mv",
        "chmod",
        "chown",
        "echo",
        "grep",
        "find",
        "ps",
        "kill",
        "ping",
        "wget",
        "curl",
        "tar",
        "gzip",
        "gunzip",
        "df",
        "du",
        "free",
        "top",
        "netstat",
    }

    # Commands that typically modify target system state
    target_commands = {
        "mount",
        "umount",
        "fdisk",
        "parted",
        "mkfs",
        "systemctl",
        "service",
        "iptables",
        "ufw",
        "crontab",
        "passwd",
    }

    # Commands that typically run on host/controller
    host_commands = {
        "docker",
        "kubectl",
        "ssh",
        "scp",
        "rsync",
        "git",
        "svn",
        "make",
        "cmake",
        "gcc",
        "python",
        "pip",
        "npm",
        "apt",
        "yum",
    }

    first_token = command_text.split()[0].lower() if command_text.split() else ""

    if first_token in cli_commands:
        return "cli", command_text, "Controller"
    elif first_token in target_commands:
        return "target", command_text, "Target"
    elif first_token in host_commands:
        return "host", command_text, "Controller"

    # Default to CLI for unknown commands
    return "cli", command_text, "Controller"


def _normalize_cli_command(command_text: str, proc_name: str | None) -> str:
    if proc_name:
        command_text = command_text.replace(proc_name, "${proc_name}")
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


def _is_generic_cli_command(command_token: str) -> bool:
    """Check if a command is a generic CLI command that can use generic patterns."""
    # List of commands that are generic enough to use generic patterns
    generic_commands = {
        "ls",
        "cat",
        "echo",
        "grep",
        "find",
        "ps",
        "ping",
        "wget",
        "curl",
        "tar",
        "gzip",
        "gunzip",
        "df",
        "du",
        "free",
        "top",
        "netstat",
        "hostname",
        "ip",
    }

    # Commands that are very specific and should NOT use generic patterns
    specific_commands = {
        "quit",
        "exit",
        "connect",
        "disconnect",
        "login",
        "logout",
        "ssh",
        "scp",
        "cd",
        "mkdir",
        "rm",
        "touch",
        "chmod",
        "chown",
        "echo",
        "sha256sum",
        "hash",
    }

    if command_token in specific_commands:
        return False

    return command_token in generic_commands
