"""CLI argument parsing configuration."""

import argparse


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

    return parser
