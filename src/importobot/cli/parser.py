"""CLI argument parsing configuration."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from importobot.medallion.interfaces.enums import SupportedFormat

FETCHABLE_FORMATS: dict[str, SupportedFormat] = {
    SupportedFormat.JIRA_XRAY.value: SupportedFormat.JIRA_XRAY,
    SupportedFormat.ZEPHYR.value: SupportedFormat.ZEPHYR,
    SupportedFormat.TESTRAIL.value: SupportedFormat.TESTRAIL,
    SupportedFormat.TESTLINK.value: SupportedFormat.TESTLINK,
}


def _parse_fetch_format(value: str) -> SupportedFormat:
    """Coerce string value into SupportedFormat."""
    normalized = value.lower()
    if normalized not in FETCHABLE_FORMATS:
        valid = ", ".join(sorted(FETCHABLE_FORMATS))
        raise argparse.ArgumentTypeError(
            f"Unsupported fetch format '{value}'. Choose from: {valid}"
        )
    return FETCHABLE_FORMATS[normalized]


class TokenListAction(argparse.Action):
    """Accumulate tokens from repeated and comma-delimited flags."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        """Accumulate tokens from repeated and comma-delimited flags."""
        tokens = getattr(namespace, self.dest, None)
        if tokens is None:
            tokens = []

        if values is None:
            return

        raw_segments = values if isinstance(values, list) else [values]

        for segment in raw_segments:
            for token in segment.split(","):
                token = token.strip()
                if token:
                    tokens.append(token)

        setattr(namespace, self.dest, tokens)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert test cases from JSON to Robot Framework format"
    )

    # Create mutually exclusive group for different conversion modes
    group = parser.add_mutually_exclusive_group(required=False)

    # Files conversion (single or multiple)
    group.add_argument(
        "--files",
        nargs="+",
        metavar="FILE",
        help="Convert one or more JSON files to Robot Framework files",
    )

    # Directory conversion
    group.add_argument(
        "--directory",
        metavar="DIR",
        help="Convert all JSON files in directory to Robot Framework files",
    )

    # Input file or directory/wildcard pattern (positional)
    parser.add_argument(
        "input", nargs="?", help="Input JSON file or directory/wildcard pattern"
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Output Robot Framework file or output directory",
    )

    # Output path for bulk operations
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Output file (for single file) or output directory "
        "(for multiple files/directory)",
    )

    # Options to disable or apply suggestions
    suggestions_group = parser.add_mutually_exclusive_group()

    suggestions_group.add_argument(
        "--no-suggestions",
        action="store_true",
        help="Disable conversion suggestions to improve performance",
    )

    suggestions_group.add_argument(
        "--apply-suggestions",
        action="store_true",
        help="Automatically apply suggestions and generate improved JSON file",
    )

    # API retrieval options (can be combined with conversion flags)
    parser.add_argument(
        "--fetch-format",
        type=_parse_fetch_format,
        metavar="FORMAT",
        help="Fetch test cases via platform API before converting "
        "(supported: jira_xray, zephyr, testrail, testlink)",
    )
    parser.add_argument(
        "--api-url",
        dest="api_url",
        help="Base API URL for fetching test cases",
    )
    parser.add_argument(
        "--tokens",
        dest="api_tokens",
        action=TokenListAction,
        help="Authentication tokens for API access (repeatable or comma-separated)",
    )
    parser.add_argument(
        "--api-user",
        dest="api_user",
        help="API user identifier where required (e.g., TestRail email)",
    )
    parser.add_argument(
        "--project",
        dest="project",
        help="Project key, ID, or name used by the upstream platform",
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dir",
        help="Directory to store fetched API payloads (defaults to current directory)",
    )
    parser.add_argument(
        "--max-concurrency",
        dest="max_concurrency",
        type=int,
        help="Maximum number of concurrent API requests (experimental)",
    )

    return parser
