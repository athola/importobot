"""Test framework converter."""

import argparse
import glob
import os
import sys

from importobot.core.converter import (
    convert_directory,
    convert_file,
    convert_multiple_files,
)


def _detect_input_type(input_path: str) -> tuple[str, list[str]]:
    """Detect input type and return (type, files_list).

    Returns:
        tuple: (input_type, files_list) where input_type is one of:
               'file', 'directory', 'wildcard', 'error'
    """
    # Check if it contains wildcard characters
    if any(char in input_path for char in ["*", "?", "[", "]"]):
        # Handle wildcard pattern
        matched_files = glob.glob(input_path, recursive=True)
        if not matched_files:
            return "error", []
        # Filter for JSON files only
        json_files = [f for f in matched_files if f.lower().endswith(".json")]
        if not json_files:
            return "error", []
        return "wildcard", json_files

    # Check if it's a directory
    if os.path.isdir(input_path):
        return "directory", [input_path]

    # Check if it's a file
    if os.path.isfile(input_path):
        return "file", [input_path]

    # Path doesn't exist
    return "error", []


def _requires_output_directory(input_type: str, files_count: int) -> bool:
    """Determine if the input type requires an output directory."""
    if input_type == "directory":
        return True
    if input_type == "wildcard" and files_count > 1:
        return True
    return False


def _handle_positional_args(args, parser):
    input_type, detected_files = _detect_input_type(args.input)

    if input_type == "error":
        print(
            f"Error: No matching files found for '{args.input}'",
            file=sys.stderr,
        )
        sys.exit(1)

    requires_output_dir = _requires_output_directory(input_type, len(detected_files))

    if requires_output_dir and not args.output_file:
        parser.error("Output directory required for multiple files or directory input")
    elif not requires_output_dir and not args.output_file:
        parser.error("Output file required for single file input")

    if input_type == "file":
        convert_file(args.input, args.output_file)
        print(f"Successfully converted {args.input} to {args.output_file}")

    elif input_type == "directory":
        output_dir = args.output_file
        convert_directory(args.input, output_dir)
        print(f"Successfully converted directory {args.input} to {output_dir}")

    elif input_type == "wildcard":
        if len(detected_files) == 1:
            convert_file(detected_files[0], args.output_file)
            print(f"Successfully converted {detected_files[0]} to {args.output_file}")
        else:
            output_dir = args.output_file
            convert_multiple_files(detected_files, output_dir)
            print(f"Successfully converted {len(detected_files)} files to {output_dir}")


def main():
    """Entry point for the CLI tool."""
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

    # Output for single file or output directory for bulk operations
    parser.add_argument(
        "input", nargs="?", help="Input JSON file or directory/wildcard pattern"
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Output Robot Framework file or output directory",
    )

    # Output for single file or output directory for bulk operations
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Output file (for single file) or output directory "
        "(for multiple files/directory)",
    )

    args = parser.parse_args()

    try:
        # Handle positional arguments (input can be file, directory, or wildcard)
        if args.input and not any([args.files, args.directory]):
            _handle_positional_args(args, parser)

        # Handle files conversion (single or multiple)
        elif args.files:
            if not args.output:
                parser.error("--output is required when using --files")

            if len(args.files) == 1:
                # Single file conversion - output should be a file
                convert_file(args.files[0], args.output)
                print(f"Successfully converted {args.files[0]} to {args.output}")
            else:
                # Multiple files conversion - output should be a directory
                convert_multiple_files(args.files, args.output)
                print(
                    f"Successfully converted {len(args.files)} files to {args.output}"
                )

        # Handle directory conversion
        elif args.directory:
            if not args.output:
                parser.error("--output is required when using --directory")
            convert_directory(args.directory, args.output)
            print(f"Successfully converted directory {args.directory} to {args.output}")

        else:
            parser.error(
                "Please specify input and output files, or use --files/--directory "
                "with --output"
            )

    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
