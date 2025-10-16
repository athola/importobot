"""Blueprint-driven Robot Framework rendering with learned context."""

from __future__ import annotations

import ast
import re
import string
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from importobot.utils.validation import sanitize_robot_string

Step = dict[str, Any]
MatchContext = dict[str, str]
Template = string.Template


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------


class TemplateRegistry:
    """In-memory registry of Robot template snippets."""

    def __init__(self) -> None:
        self._templates: dict[str, Template] = {}

    def clear(self) -> None:
        self._templates.clear()

    def register(self, name: str, content: str) -> None:
        self._templates[name] = Template(content)

    def get(self, name: str) -> Template | None:
        return self._templates.get(name)


_TEMPLATE_REGISTRY = TemplateRegistry()
_TEMPLATE_EXTENSIONS = {".robot", ".tmpl", ".txt"}
_RESOURCE_EXTENSIONS = {".resource"}
_PYTHON_EXTENSIONS = {".py"}


@dataclass
class StepPattern:
    """Generalised pattern learned from existing Robot templates."""

    location: str  # cli, target, host
    connection: str
    command_token: str
    lines: list[str]


class KnowledgeBase:
    """Aggregates patterns learned from templates."""

    def __init__(self) -> None:
        self._patterns: dict[str, list[StepPattern]] = {
            "cli": [],
            "target": [],
            "host": [],
        }

    def clear(self) -> None:
        for patterns in self._patterns.values():
            patterns.clear()

    def add_pattern(self, pattern: StepPattern) -> None:
        self._patterns.setdefault(pattern.location, []).append(pattern)

    def find_pattern(
        self,
        location: str,
        command_token: str | None = None,
        *,
        allow_generic: bool = False,
    ) -> StepPattern | None:
        patterns = self._patterns.get(location, [])
        if command_token:
            lowered = command_token.lower()
            for pattern in patterns:
                if pattern.command_token == lowered:
                    return pattern
        if allow_generic and patterns:
            return patterns[0]
        return None


_KNOWLEDGE_BASE = KnowledgeBase()


class KeywordLibrary:
    """Stores discovered keyword names from templates/resources/python files."""

    def __init__(self) -> None:
        self._keywords: set[str] = set()

    def clear(self) -> None:
        self._keywords.clear()

    def add(self, name: str) -> None:
        if name:
            self._keywords.add(name.lower())

    def has(self, name: str) -> bool:
        return name.lower() in self._keywords


_KEYWORD_LIBRARY = KeywordLibrary()
_RESOURCE_IMPORTS: list[str] = []
_TEMPLATE_STATE: dict[str, Path | None] = {"base_dir": None}


def _template_base_dir() -> Path | None:
    base_dir = _TEMPLATE_STATE.get("base_dir")
    return base_dir if isinstance(base_dir, Path) else None


def configure_template_sources(entries: Sequence[str]) -> None:
    """Register blueprint templates from user-provided files or directories."""
    _TEMPLATE_REGISTRY.clear()
    _KNOWLEDGE_BASE.clear()
    _KEYWORD_LIBRARY.clear()
    _RESOURCE_IMPORTS.clear()
    _TEMPLATE_STATE["base_dir"] = None

    for raw_entry in entries:
        if not raw_entry:
            continue

        key_override: str | None = None
        entry = raw_entry
        if "=" in raw_entry:
            potential_key, potential_path = raw_entry.split("=", 1)
            if potential_key:
                key_override = potential_key.strip()
                entry = potential_path

        candidate = Path(entry).expanduser().resolve()
        if not candidate.exists():
            continue

        # Track a base directory for later relative resource path calculations.
        if _TEMPLATE_STATE["base_dir"] is None:
            _TEMPLATE_STATE["base_dir"] = (
                candidate if candidate.is_dir() else candidate.parent
            )

        if candidate.is_dir():
            for child in candidate.iterdir():
                if child.is_file():
                    _ingest_source_file(child, key_override, base_dir=candidate)
        else:
            _ingest_source_file(candidate, key_override, base_dir=candidate.parent)


def _ingest_source_file(
    path: Path, key_override: str | None, *, base_dir: Path | None
) -> None:
    suffix = path.suffix.lower()
    if suffix in _TEMPLATE_EXTENSIONS:
        _register_template(path, key_override)
        return
    if suffix in _RESOURCE_EXTENSIONS:
        _register_resource(path, base_dir=base_dir)
        return
    if suffix in _PYTHON_EXTENSIONS:
        _register_python(path)
        return


def _register_template(path: Path, key_override: str | None) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return

    for key in _derive_template_keys(key_override or path.stem):
        if key and _TEMPLATE_REGISTRY.get(key) is None:
            _TEMPLATE_REGISTRY.register(key, content)

    _learn_from_template(content)
    _collect_resource_imports_from_template(content)


def _register_resource(path: Path, *, base_dir: Path | None) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return
    _learn_from_template(content)
    _register_resource_path(path, base_dir=base_dir)


def _register_python(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return
    _learn_from_python(content)


def _get_template(name: str) -> Template | None:
    for candidate in _derive_template_keys(name):
        template = _TEMPLATE_REGISTRY.get(candidate)
        if template is not None:
            return template
    return None


def _derive_template_keys(name: str) -> list[str]:
    base = name.strip()
    if not base:
        return []

    lower = base.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lower).strip("_")
    compact = slug.replace("_", "") if slug else ""

    keys: list[str] = []
    seen: set[str] = set()
    for candidate in (base, lower, slug, compact):
        if candidate and candidate not in seen:
            seen.add(candidate)
            keys.append(candidate)

    return keys


def _template_name_candidates(*identifiers: str | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    for ident in identifiers:
        if not ident:
            continue
        for key in _derive_template_keys(ident):
            if key not in seen:
                seen.add(key)
                ordered.append(key)

    return ordered


def _add_resource_import(raw_path: str) -> None:
    """Track resource import paths discovered from templates or resource files."""
    path = raw_path.strip()
    if not path:
        return
    if path not in _RESOURCE_IMPORTS:
        _RESOURCE_IMPORTS.append(path)


def get_resource_imports() -> list[str]:
    """Return discovered resource import statements."""
    return list(_RESOURCE_IMPORTS)


_RESOURCE_LINE_PATTERN = re.compile(r"(?i)^\s*Resource[\t ]{2,}(.+?)\s*$")


def _collect_resource_imports_from_template(content: str) -> None:
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _RESOURCE_LINE_PATTERN.match(raw_line)
        if match:
            _add_resource_import(match.group(1).strip())


def _register_resource_path(path: Path, *, base_dir: Path | None) -> None:
    reference = _format_resource_reference(path, base_dir=base_dir)
    _add_resource_import(reference)


def _format_resource_reference(path: Path, *, base_dir: Path | None) -> str:
    """Format resource path using ${CURDIR} for portability."""

    def _relative_to(candidate: Path | None) -> Path | None:
        if candidate is None:
            return None
        try:
            return path.relative_to(candidate)
        except ValueError:
            return None

    relative = _relative_to(base_dir) or _relative_to(_template_base_dir())
    if relative is None:
        return path.name

    posix = relative.as_posix()
    if not posix:
        return path.name

    # Check if the base directory is the resources directory itself
    template_dir = _template_base_dir()
    if template_dir and template_dir.name == "resources" and base_dir == template_dir:
        # When base_dir is the resources directory, robot files are in a subdirectory
        # so we need to go up one level to reach the resources
        return f"${{CURDIR}}/../resources/{posix}"

    first = relative.parts[0].lower()
    if first == "resources":
        return f"${{CURDIR}}/../{posix}"

    return f"${{CURDIR}}/{posix}"


def _learn_from_template(content: str) -> None:
    """Analyse a Robot template and extract reusable patterns."""
    lines = content.splitlines()
    total = len(lines)
    i = 0
    current_block: list[str] = []

    while i < total:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            _analyze_block(current_block)
            current_block = []
            i += 1
            continue

        if stripped.startswith("Switch Connection"):
            _analyze_block(current_block)
            current_block = [line]
        elif current_block:
            current_block.append(line)

        i += 1

    _analyze_block(current_block)
    _extract_keywords_from_template(lines)


def _analyze_block(block: list[str]) -> None:
    """Convert a block of Robot lines into a reusable pattern."""
    if not block:
        return

    first_line = block[0].strip()
    if not first_line.startswith("Switch Connection"):
        return

    connection = first_line.split("Switch Connection", 1)[1].strip()
    command_line: str | None = None
    location: str | None = None

    for raw_line in block:
        stripped = raw_line.strip()
        if stripped.startswith("Write"):
            command_line = stripped.split("Write", 1)[1].strip()
            location = "cli"
            break
        if stripped.startswith("Execute Command"):
            command_line = stripped.split("Execute Command", 1)[1].strip()
            location = "target" if connection.lower() == "target" else "host"
            break

    if not command_line or not location:
        return

    tokens = command_line.split()
    if not tokens:
        return
    command_token = tokens[0]

    placeholder_lines: list[str] = []
    for raw_line in block:
        line = raw_line.replace(command_line, "{{COMMAND_LINE}}")
        line = line.replace(command_token.upper(), "{{COMMAND_UPPER}}")
        line = line.replace(command_token, "{{COMMAND}}")
        placeholder_lines.append(line)

    _KNOWLEDGE_BASE.add_pattern(
        StepPattern(
            location=location,
            connection=connection,
            command_token=command_token.lower(),
            lines=placeholder_lines,
        )
    )


def _learn_from_python(content: str) -> None:
    """Extract keyword/function names from Python libraries."""
    try:
        module = ast.parse(content)
    except SyntaxError:
        return

    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef):
            name = node.name.replace("_", " ")
            _KEYWORD_LIBRARY.add(name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    _KEYWORD_LIBRARY.add(target.id.lower())


def _extract_keywords_from_template(lines: list[str]) -> None:
    section = None
    keyword_name: str | None = None

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("***") and stripped.endswith("***"):
            header = stripped.strip("*").strip().lower()
            section = "keywords" if header == "keywords" else None
            keyword_name = None
            continue

        if (
            section == "keywords"
            and stripped
            and not stripped.startswith("#")
            and "    " not in stripped
        ):
            keyword_name = stripped.split("  ")[0].strip()
            _KEYWORD_LIBRARY.add(keyword_name)


# ---------------------------------------------------------------------------
# Blueprint data model
# ---------------------------------------------------------------------------


@dataclass
class BlueprintResult:
    """Result returned by blueprint builders."""

    template_candidates: list[str]
    substitutions: dict[str, str]
    default_rendering: str | None = None
    prefer_template: bool = False


@dataclass
class Blueprint:
    """Data-driven blueprint definition."""

    name: str
    trigger_patterns: tuple[re.Pattern[str], ...]
    builder: Callable[
        [dict[str, Any], list[Step], MatchContext], BlueprintResult | None
    ]

    def try_render(self, data: Any) -> str | None:
        """Attempt to render given test data."""
        test_case = _extract_test_case(data)
        if not test_case:
            return None

        steps = _get_steps(test_case)
        if not steps:
            return None

        context = self._build_match_context(steps)
        if not context:
            return None

        result = self.builder(test_case, steps, context)
        if not result:
            return None

        if result.default_rendering and not result.prefer_template:
            return result.default_rendering

        for candidate in result.template_candidates:
            template = _get_template(candidate)
            if template is not None:
                return template.safe_substitute(result.substitutions)

        if result.default_rendering:
            return result.default_rendering
        return None

    def _build_match_context(self, steps: list[Step]) -> MatchContext:
        """Extract pattern matching context from test steps."""
        context: MatchContext = {}
        for step in steps:
            aggregate = " ".join(_iter_step_text(step))
            for pattern in self.trigger_patterns:
                match = pattern.search(aggregate)
                if match:
                    for key, value in match.groupdict().items():
                        if value:
                            context[key] = value
        return context


# ---------------------------------------------------------------------------
# Heuristic CLI blueprint
# ---------------------------------------------------------------------------


class RenderState:
    """Mutable state while rendering CLI steps."""

    def __init__(self) -> None:
        self.current_connection: str | None = None
        self.last_target_var: str | None = None
        self.outputs: dict[int, str] = {}


def _build_cli_task_suite(
    test_case: dict[str, Any], steps: list[Step], context: MatchContext
) -> BlueprintResult | None:
    command = context.get("command")
    if not command:
        return None

    command = command.lower()
    proc_name = context.get("proc_name")

    # Prefer the test case name for the command when available
    test_name = test_case.get("name", "")
    if test_name and test_name.strip():
        command = test_name.strip().lower()

    default_rendering = _render_cli_task_default(test_case, steps, command, proc_name)

    substitutions = {
        "command": command,
        "test_name": _format_test_name(test_case),
        "suite_doc": f"``{command}`` task suite",
        "test_doc": f"{command} --proc_name task.",
        "proc_value": proc_name or "",
        "proc_name_value": proc_name or "",
    }

    template_candidates = _template_name_candidates(
        context.get("template"),
        command,
        f"{command}_task",
        "cli_proc_task",
    )

    return BlueprintResult(
        template_candidates=template_candidates,
        substitutions=substitutions,
        default_rendering=default_rendering,
    )


# ---------------------------------------------------------------------------
# Blueprint registry
# ---------------------------------------------------------------------------


BLUEPRINTS: tuple[Blueprint, ...] = (
    Blueprint(
        name="cli_proc_task",
        trigger_patterns=(
            # Original pattern for explicit CLI: command format
            re.compile(
                r"(?:on\s+)?cli\s*:\s*(?P<command>[a-z0-9_\-]+)"
                r"(?:[\s\S]*?--proc_name\s+(?P<proc_name>[^\s]+))?",
                re.IGNORECASE,
            ),
            # New pattern for CLI commands without explicit prefix
            re.compile(
                r"(?P<command>touch|rm|ls|cat|mkdir|cp|mv|chmod|chown|echo|grep|find|ps|kill|ping|wget|curl|tar|gzip|gunzip|df|du|free|top|netstat)\s+"
                r"(?:[\s\S]*?--proc_name\s+(?P<proc_name>[^\s]+))?",
                re.IGNORECASE,
            ),
        ),
        builder=_build_cli_task_suite,
    ),
)


def render_with_blueprints(data: Any) -> str | None:
    """Render Robot Framework content using registered blueprints."""
    for blueprint in BLUEPRINTS:
        rendered = blueprint.try_render(data)
        if rendered is not None:
            return rendered
    return None


# ---------------------------------------------------------------------------
# Helpers for default rendering
# ---------------------------------------------------------------------------


def _extract_test_case(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict):
        for key in ("testCases", "tests", "items"):
            value = data.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                return first if isinstance(first, dict) else None
        test_case = data.get("testCase")
        if isinstance(test_case, dict):
            return test_case
        if "name" in data and isinstance(data["name"], str):
            return data
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def _get_steps(test_case: dict[str, Any]) -> list[Step]:
    script = test_case.get("testScript")
    if isinstance(script, dict):
        steps = script.get("steps")
        if isinstance(steps, list):
            return [step for step in steps if isinstance(step, dict)]

    steps = test_case.get("steps")
    if isinstance(steps, list):
        return [step for step in steps if isinstance(step, dict)]
    return []


def _iter_step_text(step: Step) -> Iterable[str]:
    for field in ("description", "testData", "expectedResult"):
        value = step.get(field)
        if isinstance(value, str):
            yield value


def _format_test_name(test_case: dict[str, Any]) -> str:
    key = test_case.get("key")
    if isinstance(key, str) and key.strip():
        return sanitize_robot_string(key.replace("-", " "))

    name = test_case.get("name") or test_case.get("title") or "Unnamed Test"
    return sanitize_robot_string(str(name))


def _render_cli_task_default(
    test_case: dict[str, Any],
    steps: list[Step],
    command: str,
    proc_name: str | None,
) -> str:
    lines: list[str] = []

    # Settings
    lines.append("*** Settings ***")
    lines.append(f"Documentation       ``{command}`` task suite")
    lines.append("")
    lines.append("# ``SSHLibrary`` keywords:")
    lines.append("# ``Close All Connections``")
    lines.append("# ``Switch Connection``")
    lines.append("# ``Read Until Regexp``")
    lines.append("# ``Write``")
    lines.append("Library             SSHLibrary")
    resource_imports = get_resource_imports()
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

    # Test cases
    lines.append("*** Test Cases ***")
    test_name = _format_test_name(test_case)
    lines.append(test_name)
    # Use objective if available, fallback to name, then command
    objective = test_case.get("objective") or test_case.get("summary")
    test_doc = sanitize_robot_string(objective or test_case.get("name") or f"``{command}`` task")
    if not test_doc:
        test_doc = f"``{command}`` task"
    lines.append(f"    [Documentation]    {test_doc}")

    if proc_name:
        lines.append(f"    VAR    ${{proc_name}}    {proc_name}")

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
    description = step.get("description")
    expected = step.get("expectedResult")

    location, command_text, connection_override = _parse_step_location(test_data)

    step_lines: list[str] = []
    if description:
        step_lines.append(f"    # {description}")

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
    pattern = _KNOWLEDGE_BASE.find_pattern("cli", command_token)

    # Only use generic patterns if the command is a common CLI command
    # and we don't have a specific pattern match
    if not pattern and _is_generic_cli_command(command_token):
        pattern = _KNOWLEDGE_BASE.find_pattern(
            "cli", command.lower(), allow_generic=True
        )

    if pattern:
        return _apply_cli_pattern(
            pattern,
            normalized_cmd,
            command_token,
            expected,
            state,
            connection_override or "Controller",
            step_index,
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
        _render_expectation(expected, cli_var, step_index=step_index, state=state)
    )
    return step_lines


def _render_target_location(
    step_lines: list[str],
    command_text: str,
    command: str,
    expected: str | None,
    state: RenderState,
    connection_override: str | None,
    step_index: int,
) -> list[str]:
    command_exec, notes = _split_command_and_notes(command_text)
    command_token = (command_exec.split() or [command])[0].lower()
    pattern = _KNOWLEDGE_BASE.find_pattern("target", command_token)
    if pattern:
        return _apply_target_pattern(
            pattern,
            command_exec,
            command_token,
            expected,
            notes,
            state,
            connection_override or "Target",
            step_index,
        )

    connection_name = connection_override or "Target"
    _ensure_connection(step_lines, state, connection_name)
    var_name = _command_to_identifier(command_exec)
    target_var = _var_token(var_name or "target")
    state.last_target_var = target_var
    step_lines.append(f"    {target_var}=    Execute Command    {command_exec}")
    state.outputs[step_index] = target_var
    step_lines.extend(
        _render_expectation(expected, target_var, step_index=step_index, state=state)
    )
    step_lines.extend([f"    # {note}" for note in notes])
    return step_lines


def _render_host_location(
    step_lines: list[str],
    command_text: str,
    command: str,
    expected: str | None,
    state: RenderState,
    connection_override: str | None,
    step_index: int,
) -> list[str]:
    command_exec, notes = _split_command_and_notes(command_text)
    command_token = (command_exec.split() or [command])[0].lower()
    pattern = _KNOWLEDGE_BASE.find_pattern("host", command_token)
    if pattern:
        return _apply_host_pattern(
            pattern,
            command_exec,
            command_token,
            expected,
            notes,
            state,
            connection_override or "Controller",
            step_index,
        )

    _ensure_connection(step_lines, state, connection_override or "Controller")
    host_var = _var_token(_command_to_identifier(command_exec) or "host")
    step_lines.append(f"    {host_var}=    Execute Command    {command_exec}")
    state.outputs[step_index] = host_var
    step_lines.extend(
        _render_expectation(expected, host_var, step_index=step_index, state=state)
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


def _apply_cli_pattern(
    pattern: StepPattern,
    command_line: str,
    command_token: str,
    expected: str | None,
    state: RenderState,
    connection_override: str,
    step_index: int,
) -> list[str]:
    replacements = {
        "{{COMMAND_LINE}}": command_line,
        "{{COMMAND}}": command_token,
        "{{COMMAND_UPPER}}": command_token.upper(),
    }
    lines: list[str] = []
    cli_var: str | None = None

    for template_line in pattern.lines:
        new_line = _substitute_placeholders(template_line, replacements)

        lines.append(new_line)
        stripped = new_line.strip()
        if stripped.startswith("Switch Connection"):
            new_line = _replace_connection(new_line, connection_override)
            state.current_connection = connection_override
        lines[-1] = new_line
        stripped = new_line.strip()
        assigned = _extract_assigned_variable(stripped)
        if assigned and "Read" in stripped:
            cli_var = assigned

    if cli_var is None:
        auto_var = _var_token(f"{command_token}_cli")
        for idx, line in enumerate(lines):
            if "Read Until" in line:
                indent = line.split("Read Until", 1)[0]
                remainder = line[line.index("Read Until") :]
                lines[idx] = f"{indent}{auto_var}=    {remainder}"
                cli_var = auto_var
                break

    if state.last_target_var and cli_var:
        lines.append(f"    Should Contain    {cli_var}    {state.last_target_var}")

    if cli_var:
        state.outputs[step_index] = cli_var

    expectation_lines = _render_expectation(
        expected,
        cli_var,
        step_index=step_index,
        state=state,
    )
    lines.extend(expectation_lines)

    return lines


def _apply_target_pattern(
    pattern: StepPattern,
    command_line: str,
    command_token: str,
    expected: str | None,
    notes: list[str],
    state: RenderState,
    connection_override: str,
    step_index: int,
) -> list[str]:
    replacements = {
        "{{COMMAND_LINE}}": command_line,
        "{{COMMAND}}": command_token,
        "{{COMMAND_UPPER}}": command_token.upper(),
    }
    lines: list[str] = []
    assigned_var: str | None = None

    for template_line in pattern.lines:
        new_line = _substitute_placeholders(template_line, replacements)
        lines.append(new_line)
        stripped = new_line.strip()
        if stripped.startswith("Switch Connection"):
            new_line = _replace_connection(new_line, connection_override)
            state.current_connection = connection_override
        lines[-1] = new_line
        stripped = new_line.strip()
        assigned = _extract_assigned_variable(stripped)
        if assigned and "Execute Command" in stripped:
            assigned_var = assigned
            state.last_target_var = assigned_var

    if assigned_var is None:
        auto_var = _var_token(f"{command_token}_remote")
        for idx, line in enumerate(lines):
            if "Execute Command" in line:
                indent = line.split("Execute Command", 1)[0]
                remainder = line[line.index("Execute Command") :]
                lines[idx] = f"{indent}{auto_var}=    {remainder}"
                assigned_var = auto_var
                state.last_target_var = assigned_var
                break

    lines.extend([f"    # {note}" for note in notes])

    if assigned_var:
        state.outputs[step_index] = assigned_var

    expectation_lines = _render_expectation(
        expected,
        assigned_var,
        step_index=step_index,
        state=state,
    )
    lines.extend(expectation_lines)

    return lines


def _apply_host_pattern(
    pattern: StepPattern,
    command_line: str,
    command_token: str,
    expected: str | None,
    notes: list[str],
    state: RenderState,
    connection_override: str,
    step_index: int,
) -> list[str]:
    replacements = {
        "{{COMMAND_LINE}}": command_line,
        "{{COMMAND}}": command_token,
        "{{COMMAND_UPPER}}": command_token.upper(),
    }
    lines: list[str] = []
    assigned_var: str | None = None

    for template_line in pattern.lines:
        new_line = _substitute_placeholders(template_line, replacements)
        lines.append(new_line)
        stripped = new_line.strip()
        if stripped.startswith("Switch Connection"):
            new_line = _replace_connection(new_line, connection_override)
            state.current_connection = connection_override
        lines[-1] = new_line
        stripped = new_line.strip()
        assigned = _extract_assigned_variable(stripped)
        if assigned and "Execute Command" in stripped:
            assigned_var = assigned

    if assigned_var is None:
        auto_var = _var_token(f"{command_token}_host")
        for idx, line in enumerate(lines):
            if "Execute Command" in line:
                indent = line.split("Execute Command", 1)[0]
                remainder = line[line.index("Execute Command") :]
                lines[idx] = f"{indent}{auto_var}=    {remainder}"
                assigned_var = auto_var
                break

    lines.extend([f"    # {note}" for note in notes])

    if assigned_var:
        state.outputs[step_index] = assigned_var

    expectation_lines = _render_expectation(
        expected,
        assigned_var,
        step_index=step_index,
        state=state,
    )
    lines.extend(expectation_lines)

    return lines


def _substitute_placeholders(line: str, replacements: dict[str, str]) -> str:
    result = line
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    result = result.replace("$$", "$")
    return result


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


def _render_expectation(
    expected: str | None,
    var_token: str | None,
    *,
    step_index: int,
    state: RenderState,
) -> list[str]:
    if not expected:
        return []

    expectation = expected.strip()
    if not expectation:
        return []

    lowered = expectation.lower()
    lines: list[str] = []

    # Always log the expected result for traceability
    lines.append(f"    Log    Expected: {expectation}")

    # Add comparison/containment checks if detected
    target_step = _extract_step_reference(lowered)
    if target_step is not None and var_token:
        ref_var = state.outputs.get(target_step)
        if ref_var:
            lines.append(f"    Should Be Equal As Strings    {var_token}    {ref_var}")

    literal_match = _extract_literal(lowered, ["should include", "contains"])
    if var_token and literal_match:
        lines.append(f"    Should Contain    {var_token}    {literal_match}")

    if var_token:
        state.outputs.setdefault(step_index, var_token)

    return lines


def _literal_expectation(text: str) -> str | None:
    lowered = text.lower()
    if any(
        lowered.startswith(prefix)
        for prefix in ("verify", "ensure", "no ", "completed")
    ):
        return None
    if len(text.split()) > 12:
        return None
    return text


def _ensure_connection(lines: list[str], state: RenderState, connection: str) -> None:
    if state.current_connection != connection:
        lines.append(f"    Switch Connection    {connection}")
        state.current_connection = connection


def _extract_step_reference(text: str) -> int | None:
    match = re.search(r"step\s*(\d+)", text)
    if match:
        try:
            return max(int(match.group(1)) - 1, 0)
        except ValueError:
            return None
    if "step1" in text:
        return 0
    if "step2" in text:
        return 1
    return None


def _extract_literal(text: str, triggers: list[str]) -> str | None:
    for trigger in triggers:
        if trigger in text:
            start = text.find(trigger) + len(trigger)
            literal = text[start:].strip().strip(". ")
            if literal:
                return literal
    return None


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


__all__ = [
    "BLUEPRINTS",
    "Blueprint",
    "configure_template_sources",
    "render_with_blueprints",
]
