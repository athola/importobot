"""Template registry and pattern-learning utilities for blueprints.

This module implements the blueprint system that learns patterns from existing Robot
Framework files and applies them to new conversions. The system extracts structural
patterns, keyword imports, and step templates from source files, then uses these
learned patterns to generate consistent Robot Framework output.

Cross-template learning works by:
1. **Pattern Extraction**: Analyzing existing .robot files to identify common
   step patterns
2. **Template Registration**: Storing patterns with metadata about their usage
   context
3. **Pattern Matching**: Finding the best matching pattern for each step
   during conversion
4. **Context Application**: Applying learned settings and imports to generated output

The system supports:
- Multiple template sources (directories, individual files)
- Cross-template pattern sharing
- Resource file discovery and import handling
- Safe template validation (no symlinks, size limits, content validation)

Example usage:
    from importobot.core.templates.blueprints.registry import configure_template_sources

    # Configure template sources
    configure_template_sources(["./templates/", "./legacy_tests/"])

    # Templates are automatically applied during conversion
    converter = JsonToRobotConverter()
    result = converter.convert_file("input.json", "output.robot")
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from importobot.config import MAX_TEMPLATE_FILE_SIZE_BYTES
from importobot.core.templates.blueprints.storage import (
    KEYWORD_LIBRARY,
    KNOWLEDGE_BASE,
    MAX_TEMPLATE_VALUE_LENGTH,
    RESOURCE_IMPORTS,
    SUITE_SETTINGS_REGISTRY,
    TEMPLATE_REGISTRY,
    TEMPLATE_STATE,
    KnowledgeBase,
    SandboxedTemplate,
    StepPattern,
    SuiteSettings,
    TemplateAnalysis,
    TemplateIngestionError,
    TemplateRegistry,
    _validate_template_content,
)
from importobot.utils.logging import get_logger

MAX_TEMPLATE_FILES = 512

Template = SandboxedTemplate

TEMPLATE_EXTENSIONS = {".robot", ".tmpl", ".txt"}
RESOURCE_EXTENSIONS = {".resource"}
PYTHON_EXTENSIONS = {".py"}
RESOURCE_LINE_PATTERN = re.compile(r"(?i)^\s*Resource[\t ]{2,}(.+?)\s*$")
ALLOWED_TEMPLATE_SUFFIXES = (
    TEMPLATE_EXTENSIONS | RESOURCE_EXTENSIONS | PYTHON_EXTENSIONS
)

TEMPLATE_CACHE_VERSION = 1


def _is_path_within_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _prepare_template_entry(
    raw_entry: str, safe_root: Path
) -> tuple[str | None, Path] | None:
    if not raw_entry:
        return None

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
        return None

    candidate = candidate_path.resolve()
    allow_external = os.getenv("IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES", "0") == "1"

    try:
        candidate.relative_to(safe_root)
    except ValueError:
        if not allow_external:
            logger.warning(
                "Skipping template source outside working directory: %s",
                candidate,
            )
            return None
        logger.debug("Allowing template outside working directory: %s", candidate)

    if not candidate.exists():
        logger.warning("Skipping missing template source: %s", entry)
        return None

    return key_override, candidate


def configure_template_sources(entries: Sequence[str]) -> None:
    """Register blueprint templates from user-provided files or directories.

    This routine clears and rebuilds the in-memory registry, so callers should
    invoke it as part of initial setup rather than on hot paths.
    Only files under the current working directory are ingested to prevent
    accidental traversal of sensitive paths (e.g., via ``~`` expansion).
    """
    safe_root = Path.cwd().resolve()
    TEMPLATE_REGISTRY.clear()
    KNOWLEDGE_BASE.clear()
    KEYWORD_LIBRARY.clear()
    RESOURCE_IMPORTS.clear()
    SUITE_SETTINGS_REGISTRY.clear()
    TEMPLATE_STATE["base_dir"] = None
    TEMPLATE_STATE["enabled"] = False
    ingested_files = 0

    for raw_entry in entries:
        prepared = _prepare_template_entry(raw_entry, safe_root)
        if prepared is None:
            continue

        key_override, candidate = prepared

        if TEMPLATE_STATE["base_dir"] is None:
            TEMPLATE_STATE["base_dir"] = (
                candidate if candidate.is_dir() else candidate.parent
            )

        try:
            ingested_files, limit_hit = _process_template_candidate(
                candidate, key_override, ingested_files
            )
            if limit_hit:
                TEMPLATE_STATE["enabled"] = ingested_files > 0
                return
        except TemplateIngestionError as err:
            logger.warning("Skipping template source %s: %s", candidate, err)
    TEMPLATE_STATE["enabled"] = ingested_files > 0


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
        _log_ingestion_progress(ingested_files)
    return ingested_files, False


def _ingest_single_source(
    path: Path, key_override: str | None, ingested_files: int
) -> tuple[int, bool]:
    if _has_reached_template_limit(ingested_files):
        return ingested_files, True
    _ingest_source_file(path, key_override, base_dir=path.parent)
    updated = ingested_files + 1
    _log_ingestion_progress(updated)
    return updated, False


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
    library: str | None = None,
    keyword: str | None = None,
    command_token: str | None = None,
) -> StepPattern | None:
    """Look up a learned step pattern by library+keyword or command token."""
    pattern = KNOWLEDGE_BASE.find_pattern(
        library=library, keyword=keyword, command_token=command_token
    )
    if pattern is not None:
        return pattern

    # Backwards compatibility: older call sites pass the command token as the
    # second positional argument (`keyword`) without naming `command_token`.
    if command_token is None and keyword:
        return KNOWLEDGE_BASE.find_pattern(command_token=keyword)

    return None


def get_resource_imports() -> list[str]:
    """Return discovered Robot resource references."""
    return list(RESOURCE_IMPORTS)


def get_suite_settings() -> SuiteSettings | None:
    """Retrieve learned suite settings from configured templates.

    Returns the first SuiteSettings found from analyzed templates,
    or None if no templates were configured or no suite settings
    were discovered.

    Returns:
        SuiteSettings with learned Suite Setup/Teardown, or None
    """
    if not SUITE_SETTINGS_REGISTRY:
        return None

    # Return the first suite settings from the registry
    return SUITE_SETTINGS_REGISTRY[0]


def _ingest_source_file(
    path: Path, key_override: str | None, *, base_dir: Path | None
) -> None:
    """Ingest a template file and register it in the template system.

    Args:
        path: Path to the template file
        key_override: Optional key override for the template
        base_dir: Base directory for relative path calculations

    Raises:
        TemplateIngestionError: If the file cannot be ingested
    """
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
    if file_size > MAX_TEMPLATE_FILE_SIZE_BYTES:
        raise TemplateIngestionError(
            f"Template {path} exceeds size limit ({MAX_TEMPLATE_FILE_SIZE_BYTES} bytes)"
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
        stat = path.stat()
    except OSError as exc:
        raise TemplateIngestionError(f"Failed to stat template {path}: {exc}") from exc

    cache_payload = _load_template_cache(path, stat)
    if cache_payload is not None:
        content = cache_payload["content"]
        analysis = _deserialize_analysis(cache_payload["analysis"])
        _apply_template_analysis(analysis, base_dir=path.parent)
    else:
        try:
            raw_content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TemplateIngestionError(
                f"Failed to read template {path}: {exc}"
            ) from exc

        content = _sanitize_template_payload(raw_content)

        try:
            analysis = _learn_from_template(content, base_dir=path.parent)
        except ValueError as exc:
            raise TemplateIngestionError(f"Malformed template {path}: {exc}") from exc
        _store_template_cache(path, stat, content, analysis)

    template_obj = SandboxedTemplate(content)
    for key in _derive_template_keys(key_override or path.stem):
        if key and TEMPLATE_REGISTRY.get(key) is None:
            TEMPLATE_REGISTRY.register(key, template_obj)


def _register_resource(path: Path, *, base_dir: Path | None) -> None:
    try:
        raw_content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateIngestionError(f"Failed to read resource {path}: {exc}") from exc
    content = _sanitize_template_payload(raw_content)
    try:
        _validate_template_content(content)
        _learn_from_template(content, base_dir=base_dir)
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
    """Get the configured base directory for template files.

    Returns:
        Path to the base directory if configured, None otherwise.
    """
    base_dir = TEMPLATE_STATE.get("base_dir")
    return base_dir if isinstance(base_dir, Path) else None


def _add_resource_import(raw_path: str) -> None:
    path = raw_path.strip()
    if not path:
        return
    if path not in RESOURCE_IMPORTS:
        RESOURCE_IMPORTS.append(path)


def _collect_resource_imports_from_template(content: str) -> None:
    for reference in _collect_resource_imports_from_lines(content.splitlines()):
        _add_resource_import(reference)


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
        # Preserve the original relative path from template if resolution fails
        # instead of falling back to just the filename
        return path.as_posix()

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


def _detect_setting_name(stripped: str) -> str | None:
    """Detect which setting type a line starts (if any).

    Args:
        stripped: Stripped line content

    Returns:
        Setting name ('suite_setup', 'suite_teardown', etc.) or None
    """
    if stripped.startswith("Suite Setup"):
        return "suite_setup"
    elif stripped.startswith("Suite Teardown"):
        return "suite_teardown"
    elif stripped.startswith("Test Setup"):
        return "test_setup"
    elif stripped.startswith("Test Teardown"):
        return "test_teardown"
    return None


def _extract_suite_settings(lines: list[str]) -> SuiteSettings:
    """Extract Suite Setup/Teardown from Robot Framework Settings section.

    Parses the *** Settings *** section to extract:
    - Suite Setup
    - Suite Teardown
    - Test Setup
    - Test Teardown

    Args:
        lines: Lines from Robot Framework template file

    Returns:
        SuiteSettings with extracted configuration lines
    """
    settings = SuiteSettings()
    in_settings = False
    current_setting: str | None = None
    setting_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Detect Settings section
        if stripped.startswith("***") and "Settings" in stripped:
            in_settings = True
            continue

        # Exit Settings section when hitting next section
        if in_settings and stripped.startswith("***"):
            _save_setting(settings, current_setting, setting_lines)
            break

        if not in_settings:
            continue

        # Handle multi-line settings (continuations with ...)
        if stripped.startswith("..."):
            if current_setting and setting_lines:
                setting_lines.append(line)
            continue

        # Check if this starts a new setting
        detected_setting = _detect_setting_name(stripped)
        if detected_setting:
            _save_setting(settings, current_setting, setting_lines)
            current_setting = detected_setting
            setting_lines = [line]

    # Save final setting if we reached end of file
    _save_setting(settings, current_setting, setting_lines)

    return settings


def _save_setting(
    settings: SuiteSettings,
    setting_name: str | None,
    lines: list[str],
) -> None:
    """Save accumulated setting lines to SuiteSettings object.

    Args:
        settings: SuiteSettings object to update
        setting_name: Name of setting (suite_setup, suite_teardown, etc.)
        lines: Lines to save for this setting
    """
    if not setting_name or not lines:
        return

    if setting_name == "suite_setup":
        settings.suite_setup = lines.copy()
    elif setting_name == "suite_teardown":
        settings.suite_teardown = lines.copy()
    elif setting_name == "test_setup":
        settings.test_setup = lines.copy()
    elif setting_name == "test_teardown":
        settings.test_teardown = lines.copy()


def _learn_from_template(
    content: str, *, base_dir: Path | None = None
) -> TemplateAnalysis:
    analysis = _analyze_template_content(content)
    _apply_template_analysis(analysis, base_dir=base_dir)
    return analysis


def _analyze_template_content(content: str) -> TemplateAnalysis:
    lines = content.splitlines()
    total = len(lines)
    i = 0
    current_block: list[str] = []
    patterns: list[StepPattern] = []
    keywords: set[str] = set()
    resource_imports: list[str] = []

    while i < total:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            pattern = _pattern_from_block(current_block)
            if pattern:
                patterns.append(pattern)
            current_block = []
            i += 1
            continue

        if stripped.startswith("Switch Connection"):
            pattern = _pattern_from_block(current_block)
            if pattern:
                patterns.append(pattern)
            current_block = [line]
        elif current_block:
            current_block.append(line)

        i += 1

    pattern = _pattern_from_block(current_block)
    if pattern:
        patterns.append(pattern)

    _extract_keywords_from_lines(lines, keywords)
    resource_imports.extend(_collect_resource_imports_from_lines(lines))

    # Extract suite settings from Settings section
    suite_settings = _extract_suite_settings(lines)

    return TemplateAnalysis(
        patterns=patterns,
        keywords=keywords,
        resource_imports=resource_imports,
        suite_settings=suite_settings,
    )


def _extract_connection_metadata(block: list[str]) -> tuple[str | None, str | None]:
    """Identify connection handling and associated library."""
    for raw_line in block:
        stripped = raw_line.strip()
        if stripped.startswith("Switch Connection"):
            connection = stripped.split("Switch Connection", 1)[1].strip()
            return connection or None, "SSHLibrary"
    return None, None


def _is_telnet_block(block: list[str]) -> bool:
    """Detect whether the block is operating within a Telnet context."""
    if not block:
        return False
    return "Telnet" in block[0]


def _identify_keyword_and_command(
    block: list[str], base_library: str | None
) -> tuple[str | None, str | None, str | None]:
    """Return detected keyword, library, and command payload."""
    telnet_context = _is_telnet_block(block)

    for raw_line in block:
        stripped = raw_line.strip()
        if stripped.startswith("Write"):
            keyword = "Write"
            library = base_library or "SSHLibrary"
            command_line = stripped.split("Write", 1)[1].strip()
        elif stripped.startswith("Execute Command"):
            keyword = "Execute Command"
            library = base_library or ("Telnet" if telnet_context else "SSHLibrary")
            command_line = stripped.split("Execute Command", 1)[1].strip()
        elif stripped.startswith("Run And Return Stdout"):
            keyword = "Run And Return Stdout"
            library = "OperatingSystem"
            command_line = stripped.split("Run And Return Stdout", 1)[1].strip()
        elif stripped.startswith("Run Process"):
            keyword = "Run Process"
            library = "Process"
            command_line = stripped.split("Run Process", 1)[1].strip()
        elif stripped.startswith("Start Process"):
            keyword = "Start Process"
            library = "Process"
            command_line = stripped.split("Start Process", 1)[1].strip()
        elif stripped.startswith("Run "):
            keyword = "Run"
            library = "OperatingSystem"
            command_line = stripped.split("Run", 1)[1].strip()
        else:
            continue

        return keyword, library, command_line

    return None, base_library, None


def _command_token(command_line: str) -> str | None:
    """Return the primary command token for placeholder substitution."""
    tokens = command_line.split()
    return tokens[0] if tokens else None


def _build_placeholder_lines(
    block: list[str], command_line: str, command_token: str
) -> list[str]:
    """Construct placeholder-rich template lines for a detected pattern."""
    placeholder_lines: list[str] = []
    for raw_line in block:
        line = raw_line.replace(command_line, "{{COMMAND_LINE}}")
        line = line.replace(command_token.upper(), "{{COMMAND_UPPER}}")
        line = line.replace(command_token, "{{COMMAND}}")
        placeholder_lines.append(line)
    return placeholder_lines


def _pattern_from_block(block: list[str]) -> StepPattern | None:
    """Extract a step pattern from a code block using RF library keywords."""
    if not block:
        return None

    connection, base_library = _extract_connection_metadata(block)
    keyword, library, command_line = _identify_keyword_and_command(block, base_library)
    if not command_line or not library or not keyword:
        return None

    command_token = _command_token(command_line)
    if not command_token:
        return None

    # Create template with placeholders
    placeholder_lines = _build_placeholder_lines(block, command_line, command_token)

    return StepPattern(
        library=library,
        keyword=keyword,
        connection=connection,
        command_token=command_token.lower(),
        lines=placeholder_lines,
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


def _extract_keywords_from_lines(lines: list[str], keywords: set[str]) -> None:
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
            keywords.add(keyword_name)


def _collect_resource_imports_from_lines(lines: list[str]) -> list[str]:
    resources: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = RESOURCE_LINE_PATTERN.match(raw_line)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate not in resources:
                resources.append(candidate)
    return resources


def _apply_template_analysis(
    analysis: TemplateAnalysis, *, base_dir: Path | None = None
) -> None:
    """Apply learned template analysis to global registries.

    Args:
        analysis: TemplateAnalysis with patterns, keywords, resources,
            and suite settings
        base_dir: Base directory for resolving relative resource paths
    """
    for pattern in analysis.patterns:
        KNOWLEDGE_BASE.add_pattern(pattern)
    for keyword in analysis.keywords:
        KEYWORD_LIBRARY.add(keyword)
    for resource in analysis.resource_imports:
        # Resolve resource paths relative to the template file's location
        if base_dir and not resource.startswith("${"):
            resource_path = Path(base_dir) / resource
            resolved_resource = _format_resource_reference(
                resource_path, base_dir=base_dir
            )
            _add_resource_import(resolved_resource)
        else:
            _add_resource_import(resource)

    # Store suite settings if present
    if analysis.suite_settings and analysis.suite_settings.has_setup_keywords():
        SUITE_SETTINGS_REGISTRY.append(analysis.suite_settings)


def _template_cache_enabled() -> bool:
    return os.getenv("IMPORTOBOT_BLUEPRINT_CACHE", "1") != "0"


def _template_cache_dir() -> Path:
    default_root = Path(".importobot/cache/blueprints")
    root = Path(
        os.getenv("IMPORTOBOT_BLUEPRINT_CACHE_DIR", str(default_root))
    ).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _template_cache_key(path: Path) -> str:
    return hashlib.blake2s(str(path).encode("utf-8"), digest_size=16).hexdigest()


def _load_template_cache(path: Path, stat: os.stat_result) -> dict[str, Any] | None:
    if not _template_cache_enabled():
        return None
    cache_file = _template_cache_dir() / f"{_template_cache_key(path)}.json"
    try:
        raw = cache_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:  # pragma: no cover - filesystem edge cases
        logger.debug("Failed reading template cache for %s: %s", path, exc)
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("Invalid template cache payload for %s", path)
        return None
    if payload.get("version") != TEMPLATE_CACHE_VERSION:
        return None
    if (
        payload.get("mtime_ns") != stat.st_mtime_ns
        or payload.get("size") != stat.st_size
    ):
        return None
    analysis = payload.get("analysis")
    if not isinstance(analysis, dict):
        return None
    content = payload.get("content")
    if not isinstance(content, str):
        return None
    return {"content": content, "analysis": analysis}


def _store_template_cache(
    path: Path, stat: os.stat_result, content: str, analysis: TemplateAnalysis
) -> None:
    if not _template_cache_enabled():
        return
    cache_dir = _template_cache_dir()
    cache_file = cache_dir / f"{_template_cache_key(path)}.json"
    payload = {
        "version": TEMPLATE_CACHE_VERSION,
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "content": content,
        "analysis": _serialize_analysis(analysis),
    }
    try:
        tmp = cache_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cache_file)
    except OSError as exc:  # pragma: no cover - best effort cache
        logger.debug("Failed writing template cache for %s: %s", path, exc)


def _serialize_analysis(analysis: TemplateAnalysis) -> dict[str, Any]:
    return {
        "patterns": [_serialize_step_pattern(pattern) for pattern in analysis.patterns],
        "keywords": sorted(analysis.keywords),
        "resource_imports": analysis.resource_imports,
    }


def _deserialize_analysis(data: dict[str, Any]) -> TemplateAnalysis:
    pattern_items = data.get("patterns", [])
    patterns: list[StepPattern] = []
    if isinstance(pattern_items, list):
        for item in pattern_items:
            pattern = _deserialize_step_pattern(item)
            if pattern is not None:
                patterns.append(pattern)
    keywords_raw = data.get("keywords", [])
    keywords = set(keywords_raw) if isinstance(keywords_raw, list) else set()
    resources_raw = data.get("resource_imports", [])
    if isinstance(resources_raw, list):
        resource_imports = list(dict.fromkeys(resources_raw))
    else:
        resource_imports = []
    return TemplateAnalysis(
        patterns=patterns, keywords=keywords, resource_imports=resource_imports
    )


def _serialize_step_pattern(pattern: StepPattern) -> dict[str, Any]:
    """Convert StepPattern into JSON-serialisable payload."""
    return {
        "library": pattern.library,
        "keyword": pattern.keyword,
        "connection": pattern.connection,
        "command_token": pattern.command_token,
        "lines": list(pattern.lines),
    }


def _deserialize_step_pattern(payload: Any) -> StepPattern | None:
    """Reconstruct StepPattern from cached payload, skipping invalid entries."""
    if not isinstance(payload, dict):
        return None
    required = ("library", "keyword", "command_token", "lines")
    if not all(key in payload for key in required):
        return None
    lines = payload.get("lines", [])
    if not isinstance(lines, list):
        return None
    connection = payload.get("connection")
    if connection is not None and not isinstance(connection, str):
        connection = str(connection)
    try:
        return StepPattern(
            library=str(payload["library"]),
            keyword=str(payload["keyword"]),
            connection=connection,
            command_token=str(payload["command_token"]),
            lines=[str(line) for line in lines],
        )
    except (TypeError, ValueError):
        return None


def _log_ingestion_progress(count: int) -> None:
    if count and count % 50 == 0:
        logger.info(
            "Blueprint ingestion processed %d template sources (limit %d).",
            count,
            MAX_TEMPLATE_FILES,
        )


__all__ = [
    "KEYWORD_LIBRARY",
    "KNOWLEDGE_BASE",
    "MAX_TEMPLATE_VALUE_LENGTH",
    "RESOURCE_IMPORTS",
    "SUITE_SETTINGS_REGISTRY",
    "TEMPLATE_REGISTRY",
    "TEMPLATE_STATE",
    "KnowledgeBase",
    "SandboxedTemplate",
    "StepPattern",
    "TemplateRegistry",
    "configure_template_sources",
    "find_step_pattern",
    "get_resource_imports",
    "get_template",
    "template_name_candidates",
]
logger = get_logger()
