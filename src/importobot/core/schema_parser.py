"""Parse customer documentation to extract test data schema information.

This module enables users to provide documentation (e.g., SOPs, READMEs) that
describes their test data format, thereby enhancing parsing quality and suggestions.

Security Considerations
-----------------------
Schema files are considered untrusted user input and must undergo rigorous validation
before processing:

1.  **File Size Limits**: Files restricted to `MAX_SCHEMA_FILE_SIZE_BYTES`
    (default: 1MB, configurable via `IMPORTOBOT_MAX_SCHEMA_BYTES`). For extensive
    documentation, split into multiple files and register
    each one; the `SchemaRegistry` merges fields from all registered schemas.

2.  **Content Length Validation**: Content is validated and truncated prior to parsing
    to prevent memory exhaustion attacks.

3.  **File Type Restrictions**: Only text-based formats are accepted
    (e.g., `.md`, `.markdown`, `.rst`, `.txt`, `.json`, `.yaml`, `.yml`).

4.  **Symlink Protection**: Symlinks rejected to prevent path traversal vulnerabilities.

5.  **Character Sanitization**: Control characters (excluding newline and tab) are
    stripped to prevent injection attacks.

6.  **Section Limits**: A maximum of `MAX_SCHEMA_SECTIONS` (256) sections is enforced
    to prevent algorithmic complexity attacks.

Multiple File Support
---------------------
Large schemas should be organized into multiple files for improved structure
and to adhere to size limitations:

    ```python
    from importobot.core.schema_parser import register_schema_file

    # Register multiple schema files; fields are merged automatically.
    register_schema_file("schemas/test_fields.md")
    register_schema_file("schemas/metadata_fields.md")
    register_schema_file("schemas/execution_fields.md")
    ```
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from importobot import exceptions
from importobot.config import MAX_SCHEMA_FILE_SIZE_BYTES, MAX_SCHEMA_SECTIONS
from importobot.utils.logging import get_logger

logger = get_logger()


@dataclass
class FieldSchema:
    """Represents schema information for a specific field."""

    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    examples: list[str] = field(default_factory=list)
    required: bool = False
    field_type: str = "text"  # text, list, number, boolean


@dataclass
class SchemaDocument:
    """Represents a parsed schema document."""

    fields: dict[str, FieldSchema] = field(default_factory=dict)
    source_file: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def get_field_aliases(self, field_name: str) -> list[str]:
        """Retrieve all known aliases for a given field."""
        field_lower = field_name.lower()
        for schema_field in self.fields.values():
            if schema_field.name.lower() == field_lower or field_lower in [
                a.lower() for a in schema_field.aliases
            ]:
                return [schema_field.name, *schema_field.aliases]
        return []

    def find_field_by_name(self, field_name: str) -> FieldSchema | None:
        """Find a field schema by its name or alias."""
        field_lower = field_name.lower()
        for schema_field in self.fields.values():
            if schema_field.name.lower() == field_lower:
                return schema_field
            if field_lower in [a.lower() for a in schema_field.aliases]:
                return schema_field
        return None


# Use the same limit for content length as file size for consistency
# This ensures that whether content comes from a file or direct string,
# the same memory limits apply
MAX_SCHEMA_CONTENT_LENGTH = MAX_SCHEMA_FILE_SIZE_BYTES

ALLOWED_SCHEMA_SUFFIXES: tuple[str, ...] = (
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".text",
    ".json",
    ".yaml",
    ".yml",
)


class SchemaParser:
    """Parse documentation files to extract test data schema."""

    # Patterns to identify field definitions
    FIELD_HEADER_PATTERN: re.Pattern[str] = re.compile(
        r"^([A-Z][A-Za-z\s]+)$|^([A-Z][A-Za-z\s]+):?\s*$", re.MULTILINE
    )

    # Patterns for field descriptions.
    # Order matters:
    #   1. Zephyr-style prose: The "Field" section should contain ...
    #   2. Markdown bullet syntax: "Field" - description
    #   3. Generic colon form: Field: description
    # More specific expressions are ordered first to ensure they are matched
    # before simpler, more general patterns.

    DESCRIPTION_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        # Example: The "Objective" section should describe the test intent.
        re.compile(
            r'\s*The\s+"([^"]+)"\s+(?:section|field|portion)\s+'
            r"(?:of\s+the\s+)?(?:test\s+case\s+)?should\s+(.+?)(?:\.|\n|$)",
            re.IGNORECASE,
        ),
        # Example: "Expected Result" - What should happen after execution.
        re.compile(r'\s*"([^"]+)"\s+-\s+(.+?)(?:\.|\n|$)', re.IGNORECASE),
        # Example: Precondition: Environment must be online.
        re.compile(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*(.+?)(?:\n|$)",
            re.IGNORECASE,
        ),
    ]

    # Patterns for examples
    # Patterns for example extraction. The explicit prose form is prioritised
    # over fenced code blocks so we keep short inline samples before grabbing
    # entire snippets.
    EXAMPLE_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"(?:Ex|Example|e\.g\.|For example):\s*(.+?)(?:\n|$)",
            re.IGNORECASE,
        ),
        re.compile(r"```\s*(.+?)\s*```", re.DOTALL),
    ]

    def parse_file(self, file_path: str | Path) -> SchemaDocument:
        """Parse a documentation file to extract schema information."""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Schema file not found: {file_path}")
            return SchemaDocument(source_file=str(file_path))

        try:
            if path.is_symlink():
                logger.warning("Refusing to follow schema symlink %s", file_path)
                return SchemaDocument(source_file=str(file_path))
            resolved = path.resolve(strict=False)
            if not resolved.is_file():
                logger.warning("Schema path %s is not a regular file", file_path)
                return SchemaDocument(source_file=str(file_path))
            if not self._is_allowed_schema_file(resolved):
                logger.warning("Schema file %s has disallowed extension", file_path)
                return SchemaDocument(source_file=str(file_path))
            if resolved.stat().st_size > MAX_SCHEMA_FILE_SIZE_BYTES:
                logger.warning(
                    "Schema file %s exceeds size limit (%d bytes). "
                    "Consider splitting into multiple files and registering each one. "
                    "The SchemaRegistry merges fields from all registered files.",
                    file_path,
                    MAX_SCHEMA_FILE_SIZE_BYTES,
                )
                return SchemaDocument(source_file=str(file_path))
            content = resolved.read_text(encoding="utf-8")
            return self.parse_content(content, source_file=str(file_path))
        except Exception as e:
            logger.warning(f"Failed to parse schema file {file_path}: {e}")
            return SchemaDocument(source_file=str(file_path))

    def parse_content(self, content: str, source_file: str = "") -> SchemaDocument:
        """Parse documentation content to extract schema information.

        Args:
            content: The documentation content to parse.
            source_file: An optional source file path for tracking.

        Returns:
            The parsed schema document.

        Raises:
            `ValidationError`: If the content exceeds reasonable security limits.

        Note:
            Content is automatically sanitized and truncated if necessary. However,
            extremely large inputs (exceeding 10 times the limit) are rejected
            outright to prevent memory exhaustion attacks.
        """
        # Reject pathologically large inputs before any processing
        if len(content) > MAX_SCHEMA_FILE_SIZE_BYTES * 10:
            raise exceptions.ValidationError(
                f"Schema content ({len(content)} bytes) exceeds maximum "
                f"reasonable size ({MAX_SCHEMA_FILE_SIZE_BYTES * 10} bytes)"
            )

        doc = SchemaDocument(source_file=source_file)

        sanitized = self._sanitize_content(content)
        sections = self._split_into_sections(sanitized)
        for index, (section_title, section_content) in enumerate(sections.items()):
            if index >= MAX_SCHEMA_SECTIONS:
                logger.warning(
                    "Schema content exceeded section limit (%d); remaining sections "
                    "truncated",
                    MAX_SCHEMA_SECTIONS,
                )
                break
            field_schema = self._parse_section(section_title, section_content)
            if field_schema:
                doc.fields[field_schema.name] = field_schema

        return doc

    def _sanitize_content(self, content: str) -> str:
        """Sanitizes raw content to mitigate malicious inputs."""
        if len(content) > MAX_SCHEMA_CONTENT_LENGTH:
            logger.warning(
                "Schema content exceeds max length (%d bytes); truncating",
                MAX_SCHEMA_CONTENT_LENGTH,
            )
            content = content[:MAX_SCHEMA_CONTENT_LENGTH]

        sanitized = content.replace("\ufeff", "")
        sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")

        allowed_control = {"\n", "\t"}
        return "".join(
            ch for ch in sanitized if ch in allowed_control or ch.isprintable()
        )

    def _is_allowed_schema_file(self, path: Path) -> bool:
        """Check if the file has an allowed schema extension or appears text-like."""
        suffix = path.suffix.lower()
        if suffix in ALLOWED_SCHEMA_SUFFIXES:
            return True
        # Allow files without extension if they appear text-like by sampling bytes
        if suffix == "":
            try:
                with path.open("rb") as handle:
                    sample = handle.read(1024)
            except OSError:
                return False
            return self._looks_textual(sample)
        return False

    @staticmethod
    def _looks_textual(sample: bytes) -> bool:
        """Determine if a byte sample appears to be text."""
        if not sample:
            return True
        control_bytes = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
        return control_bytes / len(sample) < 0.05

    def _split_into_sections(self, content: str) -> dict[str, str]:
        """Split content into sections based on identified headers."""
        sections: dict[str, str] = {}
        current_section = "Overview"
        current_content: list[str] = []

        for line in content.splitlines():
            # Check if this is a section header
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith((" ", "\t"))
                and self._is_likely_header(stripped)
            ):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                # Start new section
                current_section = stripped.rstrip(":")
                current_content = []
                continue

            current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _is_likely_header(self, text: str) -> bool:
        """Check if the provided text is likely a section header."""
        # Skip common non-header patterns
        if text.startswith(("Ex:", "Example:", "e.g.", "For example")):
            return False
        if ":" in text:
            header, remainder = text.split(":", 1)
            header = header.strip()
            remainder = remainder.strip()
            if header and len(header) < 15 and remainder:
                # Likely an inline "Key: value" pattern, not a header
                return False

        # Short lines that start with capital letter
        if len(text) < 50 and text[0].isupper():
            # Not a sentence if no lowercase words
            words = text.split()
            if len(words) <= 5:
                # Check if it looks like a field name (mostly capital words)
                capital_words = sum(1 for w in words if w and w[0].isupper())
                if capital_words >= len(words) * 0.5:
                    return True
        return False

    def _parse_section(
        self, section_title: str, section_content: str
    ) -> FieldSchema | None:
        """Parse a section to extract field schema information."""
        # Clean section title
        field_name = section_title.strip().rstrip(":")

        # Skip general sections
        skip_sections = {
            "overview",
            "introduction",
            "table of contents",
            "more information",
            "details",
        }
        if field_name.lower() in skip_sections:
            return None

        field_schema = FieldSchema(name=field_name)

        # Extract description
        description = self._extract_description(section_content)
        if description:
            field_schema.description = description

        # Extract examples
        examples = self._extract_examples(section_content)
        if examples:
            field_schema.examples = examples

        # Determine if required
        if "required" in section_content.lower() or "must" in section_content.lower():
            field_schema.required = True

        # Extract aliases from content
        aliases = self._extract_aliases(field_name, section_content)
        if aliases:
            field_schema.aliases = aliases

        return field_schema

    def _extract_description(self, content: str) -> str:
        """Extract the field description from the provided content."""
        for pattern in self.DESCRIPTION_PATTERNS:
            match = pattern.search(content)
            if match:
                # Get the description part
                desc = match.group(2) if len(match.groups()) > 1 else match.group(1)
                return desc.strip()

        # Default behavior: take first non-empty, non-example line
        for line in content.splitlines():
            stripped = line.strip()
            is_example = re.match(
                r"^(Ex|Example|e\.g\.|For example)\s*:",
                stripped,
                re.IGNORECASE,
            )
            if (
                stripped
                and not stripped.startswith(("#", "*", "-", "Ex:", "Example:"))
                and not is_example
            ):
                return stripped
        return ""

    def _extract_examples(self, content: str) -> list[str]:
        """Extract examples from the provided content."""
        examples: list[str] = []

        # Look for "Ex:" or "Example:" patterns
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            # Check if line starts with example indicator
            example_pattern = r"^(Ex|Example|e\.g\.|For example)\s*:"
            if re.match(example_pattern, stripped, re.IGNORECASE):
                # Extract the example text
                example_text = re.sub(
                    example_pattern,
                    "",
                    stripped,
                    flags=re.IGNORECASE,
                ).strip()
                if example_text and len(example_text) < 200:
                    examples.append(example_text)

        # Also try the regex patterns for inline examples
        for pattern in self.EXAMPLE_PATTERNS:
            for match in pattern.finditer(content):
                example = match.group(1).strip()
                # Reasonable example length and avoid duplicates
                if example and len(example) < 200 and example not in examples:
                    examples.append(example)

        return examples[:5]  # Limit to 5 examples

    def _extract_aliases(self, field_name: str, content: str) -> list[str]:
        """Extract field name aliases from the provided content."""
        aliases: list[str] = []

        # Common alias patterns
        escaped_name = re.escape(field_name)
        alias_patterns = [
            re.compile(
                rf"{escaped_name}\s+(?:is\s+)?(?:also\s+)?"
                r'(?:known\s+as|called)\s+"?([^".\n]+)"?',
                re.IGNORECASE,
            ),
            re.compile(r'(?:Also|Or)\s+"([^"]+)"', re.IGNORECASE),
        ]

        for pattern in alias_patterns:
            for match in pattern.finditer(content):
                alias = match.group(1).strip()
                if alias and alias.lower() != field_name.lower():
                    aliases.append(alias)

        return aliases


class SchemaRegistry:
    """A registry for storing and retrieving schema information."""

    def __init__(self) -> None:
        """Initialize a new schema registry."""
        self._schemas: list[SchemaDocument] = []
        self._field_index: dict[str, FieldSchema] = {}

    def register(self, schema: SchemaDocument) -> None:
        """Register a schema document."""
        self._schemas.append(schema)
        # Update field index
        for field_schema in schema.fields.values():
            self._field_index[field_schema.name.lower()] = field_schema
            for alias in field_schema.aliases:
                self._field_index[alias.lower()] = field_schema

    def find_field(self, field_name: str) -> FieldSchema | None:
        """Find field schema by name or alias."""
        return self._field_index.get(field_name.lower())

    def get_field_aliases(self, field_name: str) -> list[str]:
        """Get all known aliases for a field."""
        field_schema = self.find_field(field_name)
        if field_schema:
            return [field_schema.name, *field_schema.aliases]
        return []

    def get_all_fields(self) -> list[FieldSchema]:
        """Get all registered field schemas."""
        return list(self._field_index.values())

    def clear(self) -> None:
        """Clear all registered schemas."""
        self._schemas.clear()
        self._field_index.clear()


# Global registry instance
_SCHEMA_REGISTRY = SchemaRegistry()


def register_schema_file(file_path: str | Path) -> SchemaDocument:
    """Parse and register a schema documentation file."""
    parser = SchemaParser()
    schema = parser.parse_file(file_path)
    _SCHEMA_REGISTRY.register(schema)
    logger.info(f"Registered input schema from {file_path}")
    logger.debug(f"Found {len(schema.fields)} field definitions")
    return schema


def get_schema_registry() -> SchemaRegistry:
    """Get the global schema registry."""
    return _SCHEMA_REGISTRY


def find_field_schema(field_name: str) -> FieldSchema | None:
    """Find field schema by name or alias."""
    return _SCHEMA_REGISTRY.find_field(field_name)


__all__ = [
    "MAX_SCHEMA_SECTIONS",
    "FieldSchema",
    "SchemaDocument",
    "SchemaParser",
    "SchemaRegistry",
    "find_field_schema",
    "get_schema_registry",
    "register_schema_file",
]
