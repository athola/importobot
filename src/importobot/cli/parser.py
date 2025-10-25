"""CLI argument parsing configuration."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import cast

from importobot.cli.constants import FETCHABLE_FORMATS, format_choices


class FetchFormatAction(argparse.Action):
    """Normalize and coerce fetch format arguments."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        """Normalize format input, validate against choices, and store enum."""
        if values is None:
            setattr(namespace, self.dest, None)
            return

        if isinstance(values, Sequence) and not isinstance(values, str):
            parser.error(f"{option_string or '--fetch-format'} expected a single value")

        if not isinstance(values, str):
            parser.error(f"{option_string or '--fetch-format'} expects a string value")
            return

        normalized = values.lower()
        fetch_format = FETCHABLE_FORMATS.get(normalized)
        if fetch_format is None:
            valid = ", ".join(format_choices())
            parser.error(f'Unsupported fetch format "{values}". Choose from: {valid}')

        setattr(namespace, self.dest, fetch_format)


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
        existing = getattr(namespace, self.dest, None)
        if existing is None:
            tokens: list[str] = []
        else:
            tokens = cast(list[str], existing)
            if not isinstance(tokens, list):
                tokens = list(tokens)

        if values is None:
            return

        if isinstance(values, str):
            raw_segments: list[str] = [values]
        else:
            raw_segments = list(values)

        for segment in raw_segments:
            for raw_token in segment.split(","):
                token = raw_token.strip()
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
        action=FetchFormatAction,
        type=str.lower,
        choices=format_choices(),
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
    parser.add_argument(
        "--insecure",
        action="store_true",
        help=(
            "Disable TLS certificate verification for API requests. "
            "Use only when connecting to trusted endpoints."
        ),
    )

    parser.add_argument(
        "--robot-template",
        dest="robot_templates",
        action="append",
        metavar="PATH",
        help=(
            "Robot Framework template file or directory. "
            "Use multiple --robot-template flags to supply additional sources. "
            "Entries can be FILE, DIR, or NAME=PATH to bind a template name."
        ),
    )

    parser.add_argument(
        "--input-schema",
        dest="input_schemas",
        action="append",
        metavar="PATH",
        help=(
            "Documentation file describing input test data format (SOP, README, etc.). "
            "Helps improve parsing quality and conversion suggestions. "
            "Use multiple --input-schema flags for additional documentation sources."
        ),
    )

    return parser
