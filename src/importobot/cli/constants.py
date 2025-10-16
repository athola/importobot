"""Shared CLI constants."""

from __future__ import annotations

from importobot.medallion.interfaces.enums import SupportedFormat

# Supported API fetch formats for CLI and configuration.
SUPPORTED_FETCH_FORMATS: tuple[SupportedFormat, ...] = (
    SupportedFormat.JIRA_XRAY,
    SupportedFormat.ZEPHYR,
    SupportedFormat.TESTRAIL,
    SupportedFormat.TESTLINK,
)


# Mapping of lower-case names to enum values for argument parsing.
FETCHABLE_FORMATS: dict[str, SupportedFormat] = {
    fmt.value: fmt for fmt in SUPPORTED_FETCH_FORMATS
}


def format_choices() -> list[str]:
    """Return sorted list of supported fetch formats for help text."""
    return sorted(FETCHABLE_FORMATS)
