"""Format registry for managing pluggable format definitions."""

from __future__ import annotations

from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import get_logger

from .format_models import FormatDefinition
from .formats import (
    create_generic_format,
    create_testlink_format,
    create_testrail_format,
    create_unknown_format,
    create_xray_format,
    create_zephyr_format,
)

logger = get_logger()


class FormatRegistry:
    """Registry for managing pluggable format definitions."""

    def __init__(self) -> None:
        """Initialize format registry with built-in formats."""
        self._formats: dict[SupportedFormat, FormatDefinition] = {}
        self._load_built_in_formats()

    def register_format(self, format_def: FormatDefinition) -> None:
        """Register a new format definition."""
        validation_issues = format_def.validate()
        if validation_issues:
            raise ValueError(
                f"Invalid format definition: {'; '.join(validation_issues)}"
            )

        self._formats[format_def.format_type] = format_def
        logger.debug(
            "Registered format: %s (%s)", format_def.name, format_def.format_type.value
        )

    def get_format(self, format_type: SupportedFormat) -> FormatDefinition | None:
        """Get format definition by type."""
        return self._formats.get(format_type)

    def get_all_formats(self) -> dict[SupportedFormat, FormatDefinition]:
        """Get all registered format definitions."""
        return self._formats.copy()

    def _load_built_in_formats(self) -> None:
        """Load built-in format definitions from separate files."""
        # Load all built-in format definitions
        formats_to_load = [
            create_zephyr_format,
            create_xray_format,
            create_testrail_format,
            create_testlink_format,
            create_generic_format,
            create_unknown_format,
        ]

        for format_creator in formats_to_load:
            if format_creator is None:
                continue
            try:
                format_def = format_creator()
                self._formats[format_def.format_type] = format_def
                logger.debug("Loaded format definition: %s", format_def.name)
            except Exception as e:
                logger.error(
                    "Failed to load format from %s: %s", format_creator.__name__, e
                )

        logger.debug("Successfully loaded %s format definitions", len(self._formats))


__all__ = ["FormatRegistry"]
