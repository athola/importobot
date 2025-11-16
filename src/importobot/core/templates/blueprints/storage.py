"""Data models and storage for blueprint template system.

This module contains:
- Data classes for patterns and settings
- Storage classes for template registry
- Template processing utilities (SandboxedTemplate)
- Module-level registries for global state management
"""

from __future__ import annotations

import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from importobot import exceptions
from importobot.utils.logging import get_logger

logger = get_logger()

# Template validation constants
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

    library: str  # Robot Framework library (SSHLibrary, OperatingSystem, etc.)
    keyword: str  # Library keyword (Execute Command, Write, Run, etc.)
    connection: str | None  # Connection name if uses connections, else None
    command_token: str  # First token of the command for pattern matching
    lines: list[str]  # Template lines with placeholders


@dataclass
class SuiteSettings:
    """Suite-level configuration learned from Robot Framework templates.

    Captures Suite Setup, Suite Teardown, Test Setup, and Test Teardown
    settings from the *** Settings *** section of Robot Framework files.
    This allows generated tests to match the customer's infrastructure
    instead of using hardcoded assumptions.

    Example:
        From template:
            *** Settings ***
            Suite Setup         Run Keywords
            ...                     Connect To Production Servers
            ...                     CLI Entry

        Learned:
            SuiteSettings(
                suite_setup=["Suite Setup         Run Keywords",
                             "...                     Connect To Production Servers",
                             "...                     CLI Entry"]
            )
    """

    suite_setup: list[str] | None = None  # Lines for Suite Setup
    suite_teardown: list[str] | None = None  # Lines for Suite Teardown
    test_setup: list[str] | None = None  # Lines for Test Setup
    test_teardown: list[str] | None = None  # Lines for Test Teardown

    def has_setup_keywords(self) -> bool:
        """Check if any setup/teardown was learned from templates.

        Returns:
            True if at least one setup/teardown setting was found
        """
        return any(
            [
                self.suite_setup,
                self.suite_teardown,
                self.test_setup,
                self.test_teardown,
            ]
        )


@dataclass
class TemplateAnalysis:
    """Container for derived template metadata used by caches."""

    patterns: list[StepPattern]
    keywords: set[str]
    resource_imports: list[str]
    suite_settings: SuiteSettings | None = None


def _is_safe_placeholder_name(name: str | None) -> bool:
    """Check if placeholder name is safe (doesn't start with __)."""
    if not name:
        return False
    return not any(
        name.startswith(prefix) for prefix in DISALLOWED_PLACEHOLDER_PREFIXES
    )


def _coerce_template_value(value: Any) -> str:
    """Convert value to string with length limits and printability filtering."""
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


def _validate_template_content(content: str) -> None:
    """Validate template content for security issues."""
    for pattern in DISALLOWED_TEMPLATE_PATTERNS:
        if pattern.search(content):
            raise TemplateIngestionError("Template contains disallowed constructs")
    for match in string.Template.pattern.finditer(content):
        identifier = match.group("named") or match.group("braced")
        if identifier and not _is_safe_placeholder_name(identifier):
            raise TemplateIngestionError(
                f"Template placeholder '{identifier}' is not permitted"
            )


class SandboxedTemplate(string.Template):
    """Template subclass that sanitises placeholders and substitutions.

    Uses string.Template's idpattern to restrict placeholder names to valid Python
    identifiers, preventing template injection attacks.
    """

    idpattern = r"[A-Za-z_][A-Za-z0-9_]*"

    def __init__(self, template: str) -> None:
        """Initialize template with validation."""
        _validate_template_content(template)
        super().__init__(template)

    def render_safe(self, substitutions: Mapping[str, Any]) -> str:
        """Render template with safe substitutions only.

        Args:
            substitutions: Mapping of placeholder names to values

        Returns:
            Rendered template string with unsafe placeholders filtered out
        """
        safe_mapping: dict[str, str] = {}
        for key, value in substitutions.items():
            if not _is_safe_placeholder_name(key):
                logger.warning('Dropping unsafe placeholder "%s" in template', key)
                continue
            safe_mapping[key] = _coerce_template_value(value)
        return self.safe_substitute(safe_mapping)


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
        """Create empty pattern storage keyed by (library, keyword) tuples."""
        self._patterns: dict[tuple[str, str], list[StepPattern]] = {}

    def clear(self) -> None:
        """Clear all learned pattern groups."""
        self._patterns.clear()

    def add_pattern(self, pattern: StepPattern) -> None:
        """Store a learned pattern indexed by (library, keyword)."""
        key = (pattern.library, pattern.keyword)
        self._patterns.setdefault(key, []).append(pattern)

    def find_pattern(
        self,
        library: str | None = None,
        keyword: str | None = None,
        command_token: str | None = None,
    ) -> StepPattern | None:
        """Find a matching pattern by library+keyword or command token.

        Args:
            library: Robot Framework library name (e.g., "SSHLibrary")
            keyword: Library keyword (e.g., "Execute Command")
            command_token: Command token to match (e.g., "ls")

        Returns:
            Matching StepPattern or None
        """
        # Primary: exact library+keyword match
        if library and keyword:
            key = (library, keyword)
            patterns = self._patterns.get(key, [])
            if command_token:
                lowered = command_token.lower()
                for pattern in patterns:
                    if pattern.command_token == lowered:
                        return pattern
            elif patterns:
                return patterns[0]

        # Secondary: search all patterns for command token match
        if command_token:
            lowered = command_token.lower()
            for patterns_list in self._patterns.values():
                for pattern in patterns_list:
                    if pattern.command_token == lowered:
                        return pattern

        return None


class KeywordLibrary:
    """Store discovered keyword names from templates/resources/python files."""

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


class TemplateIngestionError(exceptions.ImportobotError):
    """Raised when template file ingestion encounters problems."""


# Module-level global registries
# These maintain state across the application lifetime
TEMPLATE_REGISTRY = TemplateRegistry()
KNOWLEDGE_BASE = KnowledgeBase()
KEYWORD_LIBRARY = KeywordLibrary()
RESOURCE_IMPORTS: list[str] = []
SUITE_SETTINGS_REGISTRY: list[SuiteSettings] = []
# Stores base directory and enabled status for template system
TEMPLATE_STATE: dict[str, Path | None | bool] = {"base_dir": None, "enabled": False}


__all__ = [
    "DISALLOWED_PLACEHOLDER_PREFIXES",
    "DISALLOWED_TEMPLATE_PATTERNS",
    "KEYWORD_LIBRARY",
    "KNOWLEDGE_BASE",
    "MAX_TEMPLATE_VALUE_LENGTH",
    "RESOURCE_IMPORTS",
    "SUITE_SETTINGS_REGISTRY",
    "TEMPLATE_REGISTRY",
    "TEMPLATE_STATE",
    "KeywordLibrary",
    "KnowledgeBase",
    "SandboxedTemplate",
    "StepPattern",
    "SuiteSettings",
    "TemplateAnalysis",
    "TemplateIngestionError",
    "TemplateRegistry",
    "_coerce_template_value",
    "_is_safe_placeholder_name",
    "_validate_template_content",
]
