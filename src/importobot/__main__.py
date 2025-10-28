"""Test framework converter.

Entry point for importobot CLI. Handles argument parsing and dispatches
to appropriate conversion functions.
"""

import json
import sys
from typing import Any

from importobot import exceptions
from importobot.cli.handlers import (
    handle_api_ingest,
    handle_directory_conversion,
    handle_files_conversion,
    handle_positional_args,
)
from importobot.cli.parser import create_parser
from importobot.core.schema_parser import register_schema_file
from importobot.core.templates import configure_template_sources
from importobot.utils.logging import get_logger, log_exception

logger = get_logger("importobot-cli")


def _check_conversion_flags(args: Any) -> bool:
    """Check if any conversion-related flags are present."""
    return any(
        [
            bool(getattr(args, "input", None)),
            bool(getattr(args, "files", None)),
            bool(getattr(args, "directory", None)),
            bool(getattr(args, "output_file", None)),
            bool(getattr(args, "output", None)),
        ]
    )


def _handle_api_ingest_logic(
    args: Any, _parser: Any, had_conversion_flags: bool
) -> bool:
    """Handle API ingest logic if needed."""
    saved_payload_path = handle_api_ingest(args)

    if not getattr(args, "input", None):
        args.input = saved_payload_path

    if (
        getattr(args, "output", None)
        and not getattr(args, "output_file", None)
        and not getattr(args, "files", None)
        and not getattr(args, "directory", None)
    ):
        args.output_file = args.output

    conversion_intended = any(
        [
            bool(args.files),
            bool(args.directory),
            bool(getattr(args, "output_file", None)),
            had_conversion_flags,
        ]
    )

    if not conversion_intended:
        print(f"Saved API payload to {saved_payload_path}")
        return True  # Exit flag
    return False  # Continue flag


def _determine_conversion_action(args: Any, parser: Any) -> None:
    """Determine and execute the appropriate conversion action."""
    # Handle positional arguments (input can be file, directory, or wildcard)
    if args.input and not any([args.files, args.directory]):
        handle_positional_args(args, parser)
    # Handle files conversion (single or multiple)
    elif args.files:
        handle_files_conversion(args, parser)
    # Handle directory conversion
    elif args.directory:
        handle_directory_conversion(args, parser)
    else:
        parser.error(
            "Please specify input and output files, or use --files/--directory "
            "with --output"
        )


def _handle_error(e: Exception) -> None:
    """Handle different types of exceptions."""
    if isinstance(e, exceptions.ImportobotError):
        logger.error(str(e))
        sys.exit(1)
    elif isinstance(e, json.JSONDecodeError):
        # User-friendly error for corrupted JSON files
        logger.error(str(e))  # This now contains our enhanced message
        sys.exit(1)
    elif isinstance(e, (FileNotFoundError, ValueError, IOError)):
        logger.error(
            str(e)
        )  # Remove "Error:" prefix since our messages are now descriptive
        sys.exit(1)
    else:
        log_exception(logger, e, "Unexpected error in main CLI")
        print(f"An unexpected error occurred: {e!s}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI tool."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        had_conversion_flags = _check_conversion_flags(args)

        template_sources = getattr(args, "robot_templates", None)
        if template_sources:
            configure_template_sources(template_sources)

        # Load input schema documentation if provided
        schema_sources = getattr(args, "input_schemas", None)
        if schema_sources:
            for schema_path in schema_sources:
                register_schema_file(schema_path)

        if getattr(args, "fetch_format", None):
            should_exit = _handle_api_ingest_logic(args, parser, had_conversion_flags)
            if should_exit:
                return

        _determine_conversion_action(args, parser)

    except Exception as e:
        _handle_error(e)


if __name__ == "__main__":
    main()
