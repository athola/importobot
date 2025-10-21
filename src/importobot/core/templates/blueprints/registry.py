"""Template registry and pattern-learning utilities for blueprints."""

from __future__ import annotations

import ast
import re
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from importobot import exceptions
from importobot.utils.logging import get_logger

MAX_TEMPLATE_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_TEMPLATE_FILES = 512
MAX_TEMPLATE_VALUE_LENGTH = 4096
DISALLOWED_PLACEHOLDER_PREFIXES = ("__",)
DISALLOWED_TEMPLATE_PATTERNS = (
    re.compile(r"\$\{\{"),  # Inline Python evaluation in Robot
    re.compile(r"(?i)\bEvaluate\b"),
    re.compile(r"(?i)\bBuiltIn\s*\.\s*Evaluate\b"),
)


@dataclass
class StepPattern:
    """Generalised pattern learned from existing Robot templates."""

    location: str  # cli, target, host
    connection: str
    command_token: str
    lines: list[str]


class TemplateRegistry:
    """In-memory registry of Robot template snippets."""

    def __init__(self) -> None:
        """Initialise the registry with an empty template map."""
        self._templates: dict[str, SandboxedTemplate] = {}

    def clear(self) -> None:
        """Remove all templates from the registry."""
        self._templates.clear()

    def register(self, name: str, template: SandboxedTemplate) -> None:
        """Store a template under the provided lookup name."""
        self._templates[name] = template

    def get(self, name: str) -> SandboxedTemplate | None:
        """Return the template associated with ``name`` if present."""
        return self._templates.get(name)


class KnowledgeBase:
    """Aggregates patterns learned from templates."""

    def __init__(self) -> None:
        """Create empty pattern buckets for each recognised location."""
        self._patterns: dict[str, list[StepPattern]] = {
            "cli": [],
            "target": [],
            "host": [],
        }

    def clear(self) -> None:
        """Clear all learned pattern groups."""
        for patterns in self._patterns.values():
            patterns.clear()

    def add_pattern(self, pattern: StepPattern) -> None:
        """Store a learned pattern for lookups keyed by location."""
        self._patterns.setdefault(pattern.location, []).append(pattern)

    def find_pattern(
        self,
        location: str,
        command_token: str | None = None,
        *,
        allow_generic: bool = False,
    ) -> StepPattern | None:
        """Find a matching pattern, optionally falling back to generic ones."""
        patterns = self._patterns.get(location, [])
        if command_token:
            lowered = command_token.lower()
            for pattern in patterns:
                if pattern.command_token == lowered:
                    return pattern
        if allow_generic and patterns:
            return patterns[0]
        return None


class KeywordLibrary:
    """Stores discovered keyword names from templates/resources/python files."""

    def __init__(self) -> None:
        """Initialise the keyword store."""
        self._keywords: set[str] = set()

    def clear(self) -> None:
        """Clear all cached keyword names."""
        self._keywords.clear()

    def add(self, name: str) -> None:
        """Record a keyword name if it is non-empty."""
        if name:
            self._keywords.add(name.lower())


TEMPLATE_REGISTRY = TemplateRegistry()
KNOWLEDGE_BASE = KnowledgeBase()
KEYWORD_LIBRARY = KeywordLibrary()
RESOURCE_IMPORTS: list[str] = []
TEMPLATE_STATE: dict[str, Path | None] = {"base_dir": None}


class SandboxedTemplate(string.Template):
    """Template subclass that sanitises placeholders and substitutions."""

    idpattern = r"[A-Za-z_][A-Za-z0-9_]*"

    def __init__(self, template: str) -> None:
        _validate_template_content(template)
        super().__init__(template)

    def render_safe(self, substitutions: Mapping[str, Any]) -> str:
        safe_mapping: dict[str, str] = {}
        for key, value in substitutions.items():
            if not _is_safe_placeholder_name(key):
                logger.warning("Dropping unsafe placeholder '%s' in template", key)
                continue
            safe_mapping[key] = _coerce_template_value(value)
        return self.safe_substitute(safe_mapping)


Template = SandboxedTemplate


TEMPLATE_EXTENSIONS = {".robot", ".tmpl", ".txt"}
RESOURCE_EXTENSIONS = {".resource"}
PYTHON_EXTENSIONS = {".py"}
RESOURCE_LINE_PATTERN = re.compile(r"(?i)^\s*Resource[\t ]{2,}(.+?)\s*$")
ALLOWED_TEMPLATE_SUFFIXES = (
    TEMPLATE_EXTENSIONS | RESOURCE_EXTENSIONS | PYTHON_EXTENSIONS
)


class TemplateIngestionError(exceptions.ImportobotError):
    """Raised when blueprint template ingestion fails."""


def configure_template_sources(entries: Sequence[str]) -> None:
    """Register blueprint templates from user-provided files or directories."""
    TEMPLATE_REGISTRY.clear()
    KNOWLEDGE_BASE.clear()
    KEYWORD_LIBRARY.clear()
    RESOURCE_IMPORTS.clear()
    TEMPLATE_STATE["base_dir"] = None
    ingested_files = 0

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

        candidate_path = Path(entry).expanduser()
        if candidate_path.is_symlink():
            logger.warning("Skipping template source symlink %s", entry)
            continue

        candidate = candidate_path.resolve()
        if not candidate.exists():
            continue

        if TEMPLATE_STATE["base_dir"] is None:
            TEMPLATE_STATE["base_dir"] = (
                candidate if candidate.is_dir() else candidate.parent
            )

        try:
            ingested_files, limit_hit = _process_template_candidate(
                candidate, key_override, ingested_files
            )
            if limit_hit:
                return
        except TemplateIngestionError as err:
            logger.warning("Skipping template source %s: %s", candidate, err)


def _process_template_candidate(
    candidate: Path, key_override: str | None, ingested_files: int
) -> tuple[int, bool]:
    if candidate.is_dir():
        return _ingest_directory_sources(candidate, key_override, ingested_files)
    return _ingest_single_source(candidate, key_override, ingested_files)


def _ingest_directory_sources(
    directory: Path, key_override: str | None, ingested_files: int
) -> tuple[int, bool]:
    for child in sorted(directory.iterdir()):
        if child.is_symlink() or not child.is_file():
            continue
        if _has_reached_template_limit(ingested_files):
            return ingested_files, True
        _ingest_source_file(child, key_override, base_dir=directory)
        ingested_files += 1
    return ingested_files, False


def _ingest_single_source(
    path: Path, key_override: str | None, ingested_files: int
) -> tuple[int, bool]:
    if _has_reached_template_limit(ingested_files):
        return ingested_files, True
    _ingest_source_file(path, key_override, base_dir=path.parent)
    return ingested_files + 1, False


def _has_reached_template_limit(current_count: int) -> bool:
    if current_count >= MAX_TEMPLATE_FILES:
        logger.warning(
            "Template source limit (%d files) reached; remaining files skipped",
            MAX_TEMPLATE_FILES,
        )
        return True
    return False


def get_template(name: str) -> Template | None:
    """Return the first template matching any derived candidate name."""
    for candidate in template_name_candidates(name):
        template = TEMPLATE_REGISTRY.get(candidate)
        if template is not None:
            return template
    return None


def template_name_candidates(*identifiers: str | None) -> list[str]:
    """Generate unique lookup keys for the provided identifiers."""
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


def find_step_pattern(
    location: str,
    command_token: str | None,
    *,
    allow_generic: bool = False,
) -> StepPattern | None:
    """Look up a learned step pattern for ``location`` and ``command_token``."""
    return KNOWLEDGE_BASE.find_pattern(
        location, command_token, allow_generic=allow_generic
    )


def get_resource_imports() -> list[str]:
    """Return discovered Robot resource references."""
    return list(RESOURCE_IMPORTS)


def _ingest_source_file(
    path: Path, key_override: str | None, *, base_dir: Path | None
) -> None:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_TEMPLATE_SUFFIXES:
        raise TemplateIngestionError(f"Unsupported template type for {path}")
    if path.is_symlink():
        raise TemplateIngestionError(f"Refusing to follow template symlink {path}")
    _ensure_textual_file(path)

    suffix = path.suffix.lower()
    try:
        file_size = path.stat().st_size
    except OSError as exc:
        raise TemplateIngestionError(f"Failed to stat template {path}: {exc}") from exc
    if file_size > MAX_TEMPLATE_FILE_SIZE:
        raise TemplateIngestionError(
            f"Template {path} exceeds size limit ({MAX_TEMPLATE_FILE_SIZE} bytes)"
        )

    if suffix in TEMPLATE_EXTENSIONS:
        _register_template(path, key_override)
        return
    if suffix in RESOURCE_EXTENSIONS:
        _register_resource(path, base_dir=base_dir)
        return
    if suffix in PYTHON_EXTENSIONS:
        _register_python(path)


def _register_template(path: Path, key_override: str | None) -> None:
    try:
        raw_content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateIngestionError(f"Failed to read template {path}: {exc}") from exc

    content = _sanitize_template_payload(raw_content)

    template_obj = SandboxedTemplate(content)
    for key in _derive_template_keys(key_override or path.stem):
        if key and TEMPLATE_REGISTRY.get(key) is None:
            TEMPLATE_REGISTRY.register(key, template_obj)

    try:
        _learn_from_template(content)
        _collect_resource_imports_from_template(content)
    except ValueError as exc:
        raise TemplateIngestionError(f"Malformed template {path}: {exc}") from exc


def _register_resource(path: Path, *, base_dir: Path | None) -> None:
    try:
        raw_content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateIngestionError(f"Failed to read resource {path}: {exc}") from exc
    content = _sanitize_template_payload(raw_content)
    try:
        _validate_template_content(content)
        _learn_from_template(content)
        _register_resource_path(path, base_dir=base_dir)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise TemplateIngestionError(
            f"Resource contains invalid content {path}: {exc}"
        ) from exc


def _register_python(path: Path) -> None:
    try:
        raw_content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateIngestionError(
            f"Failed to read python template {path}: {exc}"
        ) from exc
    content = _sanitize_template_payload(raw_content)
    try:
        _learn_from_python(content)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise TemplateIngestionError(
            f"Python helper {path} has invalid content: {exc}"
        ) from exc


def _sanitize_template_payload(content: str) -> str:
    cleaned = content.replace("\ufeff", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    allowed_control = {"\n", "\t"}
    return "".join(ch for ch in cleaned if ch in allowed_control or ch.isprintable())


def _is_safe_placeholder_name(name: str | None) -> bool:
    if not name:
        return False
    return not any(
        name.startswith(prefix) for prefix in DISALLOWED_PLACEHOLDER_PREFIXES
    )


def _coerce_template_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) > MAX_TEMPLATE_VALUE_LENGTH:
        logger.warning(
            "Truncating template substitution value from %d to %d characters",
            len(text),
            MAX_TEMPLATE_VALUE_LENGTH,
        )
        text = text[:MAX_TEMPLATE_VALUE_LENGTH]
    allowed_control = {"\n", "\t"}
    return "".join(ch for ch in text if ch.isprintable() or ch in allowed_control)


def _ensure_textual_file(path: Path) -> None:
    try:
        with path.open("rb") as handle:
            sample = handle.read(2048)
    except OSError as exc:
        raise TemplateIngestionError(
            f"Failed to validate template {path}: {exc}"
        ) from exc
    if not sample:
        return
    if not _looks_textual(sample):
        raise TemplateIngestionError(f"Template {path} appears to contain binary data")


def _looks_textual(sample: bytes) -> bool:
    control_bytes = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
    return control_bytes / len(sample) < 0.05


def _validate_template_content(content: str) -> None:
    for pattern in DISALLOWED_TEMPLATE_PATTERNS:
        if pattern.search(content):
            raise TemplateIngestionError("Template contains disallowed constructs")
    for match in string.Template.pattern.finditer(content):
        identifier = match.group("named") or match.group("braced")
        if identifier and not _is_safe_placeholder_name(identifier):
            raise TemplateIngestionError(
                f"Template placeholder '{identifier}' is not permitted"
            )


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


def _template_base_dir() -> Path | None:
    base_dir = TEMPLATE_STATE.get("base_dir")
    return base_dir if isinstance(base_dir, Path) else None


def _add_resource_import(raw_path: str) -> None:
    path = raw_path.strip()
    if not path:
        return
    if path not in RESOURCE_IMPORTS:
        RESOURCE_IMPORTS.append(path)


def _collect_resource_imports_from_template(content: str) -> None:
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = RESOURCE_LINE_PATTERN.match(raw_line)
        if match:
            _add_resource_import(match.group(1).strip())


def _register_resource_path(path: Path, *, base_dir: Path | None) -> None:
    reference = _format_resource_reference(path, base_dir=base_dir)
    _add_resource_import(reference)


def _format_resource_reference(path: Path, *, base_dir: Path | None) -> str:
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

    template_dir = _template_base_dir()
    if template_dir and template_dir.name == "resources" and base_dir == template_dir:
        return f"${{CURDIR}}/../resources/{posix}"

    first = relative.parts[0].lower()
    if first == "resources":
        return f"${{CURDIR}}/../{posix}"

    return f"${{CURDIR}}/{posix}"


def _learn_from_template(content: str) -> None:
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

    KNOWLEDGE_BASE.add_pattern(
        StepPattern(
            location=location,
            connection=connection,
            command_token=command_token.lower(),
            lines=placeholder_lines,
        )
    )


def _learn_from_python(content: str) -> None:
    try:
        module = ast.parse(content)
    except SyntaxError:
        return

    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef):
            name = node.name.replace("_", " ")
            KEYWORD_LIBRARY.add(name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    KEYWORD_LIBRARY.add(target.id.lower())


def _extract_keywords_from_template(lines: list[str]) -> None:
    section: str | None = None

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("***") and stripped.endswith("***"):
            header = stripped.strip("*").strip().lower()
            section = "keywords" if header == "keywords" else None
            continue

        if (
            section == "keywords"
            and stripped
            and not stripped.startswith("#")
            and "    " not in stripped
        ):
            keyword_name = stripped.split("  ")[0].strip()
            KEYWORD_LIBRARY.add(keyword_name)


__all__ = [
    "KnowledgeBase",
    "StepPattern",
    "TemplateRegistry",
    "configure_template_sources",
    "find_step_pattern",
    "get_resource_imports",
    "get_template",
    "template_name_candidates",
]
logger = get_logger()
