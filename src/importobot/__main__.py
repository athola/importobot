"""Test framework converter."""

import argparse
import sys

from importobot.core.converter import convert_to_robot


def main():
    """Entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Convert test cases from JSON to Robot Framework format"
    )
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output Robot Framework file")

    args = parser.parse_args()

    try:
        convert_to_robot(args.input, args.output)
        print(f"Successfully converted {args.input} to {args.output}")
    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
