"""Test framework converter.

Entry point for importobot CLI. Handles argument parsing and dispatches
to appropriate conversion functions.
"""

import json
import sys

from importobot import exceptions
from importobot.cli.handlers import (
    handle_directory_conversion,
    handle_files_conversion,
    handle_positional_args,
)
from importobot.cli.parser import create_parser
from importobot.utils.logging import log_exception, setup_logger

logger = setup_logger("importobot-cli")


def main() -> None:
    """Entry point for the CLI tool."""
    parser = create_parser()
    args = parser.parse_args()

    try:
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

    except exceptions.ImportobotError as e:
        logger.error(str(e))
        sys.exit(1)
    except json.JSONDecodeError as e:
        # User-friendly error for corrupted JSON files
        logger.error(str(e))  # This now contains our enhanced message
        sys.exit(1)
    except (FileNotFoundError, ValueError, IOError) as e:
        logger.error(
            str(e)
        )  # Remove "Error:" prefix since our messages are now descriptive
        sys.exit(1)
    except Exception as e:
        log_exception(logger, e, "Unexpected error in main CLI")
        print(f"An unexpected error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
