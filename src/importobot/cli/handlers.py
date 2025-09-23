"""CLI command handlers and processing logic."""

import argparse
import glob
import os
import sys

from importobot import exceptions
from importobot.core.converter import (
    convert_directory,
    convert_file,
    convert_multiple_files,
    get_conversion_suggestions,
)
from importobot.utils.file_operations import (
    display_suggestion_changes,
    load_json_file,
    process_single_file_with_suggestions,
)
from importobot.utils.logging import setup_logger

logger = setup_logger("importobot-cli")


def detect_input_type(input_path: str) -> tuple[str, list[str]]:
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


def requires_output_directory(input_type: str, files_count: int) -> bool:
    """Determine if the input type requires an output directory."""
    if input_type == "directory":
        return True
    if input_type == "wildcard" and files_count > 1:
        return True
    return False


def validate_input_and_output(
    input_type: str,
    detected_files: list,
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    """Validate input and output arguments."""
    if input_type == "error":
        logger.error("No matching files found for '%s'", args.input)
        sys.exit(1)

    requires_output_dir = requires_output_directory(input_type, len(detected_files))

    if requires_output_dir and not args.output_file:
        parser.error("Output directory required for multiple files or directory input")
    elif not requires_output_dir and not args.output_file:
        parser.error("Output file required for single file input")


def collect_suggestions(json_data: object) -> list[tuple[int, int, str]]:
    """Collect suggestions from all test cases in the JSON data."""
    all_suggestions = []
    test_cases = json_data if isinstance(json_data, list) else [json_data]

    for i, test_case in enumerate(test_cases):
        suggestions = get_conversion_suggestions(test_case)
        indexed_suggestions = [(i, j, s) for j, s in enumerate(suggestions)]
        all_suggestions.extend(indexed_suggestions)

    return all_suggestions


def filter_suggestions(suggestions: list[tuple[int, int, str]]) -> list[str]:
    """Filter and deduplicate suggestions."""
    if not suggestions:
        return []

    # Sort by test case index and then by original suggestion order
    suggestions.sort(key=lambda x: (x[0], x[1]))

    # Extract unique suggestion texts
    unique_suggestions = []
    seen = set()
    for _, _, suggestion in suggestions:
        if suggestion not in seen:
            unique_suggestions.append(suggestion)
            seen.add(suggestion)

    # Filter out "No improvements needed" if there are other suggestions
    filtered = [s for s in unique_suggestions if "No improvements needed" not in s]
    return filtered if filtered else unique_suggestions


def print_suggestions(filtered_suggestions: list[str]) -> None:
    """Print suggestions or positive feedback to the user."""
    if not filtered_suggestions:
        return

    if (
        len(filtered_suggestions) == 1
        and "No improvements needed" in filtered_suggestions[0]
    ):
        print("\nYour conversion is already well-structured.")
        print("No suggestions for improvement.")
        return

    print("\n💡 Conversion Suggestions:")
    print("=" * 50)
    for i, suggestion in enumerate(filtered_suggestions, 1):
        print(f"  {i}. {suggestion}")
    print(
        "\nThese suggestions can improve the quality of the "
        "generated Robot Framework code."
    )


def display_suggestions(json_file_path: str, no_suggestions: bool = False) -> None:
    """Display conversion suggestions for a JSON file if not disabled."""
    if no_suggestions:
        return

    try:
        json_data = load_json_file(json_file_path)

        all_suggestions = collect_suggestions(json_data)
        filtered_suggestions = filter_suggestions(all_suggestions)
        print_suggestions(filtered_suggestions)

    except exceptions.ImportobotError as e:
        logger.warning("Could not generate suggestions: %s", str(e))
    except Exception as e:
        logger.warning("Could not generate suggestions: %s", str(e))


def convert_single_file(args: argparse.Namespace) -> None:
    """Convert a single file."""
    convert_file(args.input, args.output_file)
    print(f"Successfully converted {args.input} to {args.output_file}")
    display_suggestions(args.input, args.no_suggestions)


def convert_directory_handler(args: argparse.Namespace) -> None:
    """Convert all files in a directory."""
    convert_directory(args.input, args.output_file)
    print(f"Successfully converted directory {args.input} to {args.output_file}")


def convert_wildcard_files(args: argparse.Namespace, detected_files: list[str]) -> None:
    """Convert files matching wildcard pattern."""
    if len(detected_files) == 1:
        convert_file(detected_files[0], args.output_file)
        print(f"Successfully converted {detected_files[0]} to {args.output_file}")
        display_suggestions(detected_files[0], args.no_suggestions)
    else:
        convert_multiple_files(detected_files, args.output_file)
        print(
            f"Successfully converted {len(detected_files)} files to {args.output_file}"
        )


def apply_suggestions_single_file(args: argparse.Namespace) -> None:
    """Apply suggestions and convert for a single file."""
    process_single_file_with_suggestions(
        args,
        display_changes_func=display_suggestion_changes,
        use_stem_for_basename=False,
    )
    display_suggestions(args.input, args.no_suggestions)


def handle_bulk_conversion_with_suggestions(
    args: argparse.Namespace, input_type: str, detected_files: list
) -> None:
    """Handle conversion for directories or multiple files with suggestions warning."""
    print("Warning: --apply-suggestions is only supported for single file conversion.")
    print("Performing normal conversion instead...")

    if input_type == "directory":
        convert_directory(args.input, args.output_file)
        print(f"Successfully converted directory {args.input} to {args.output_file}")
    elif len(detected_files) == 1:
        convert_file(detected_files[0], args.output_file)
        print(f"Successfully converted {detected_files[0]} to {args.output_file}")
        display_suggestions(detected_files[0], args.no_suggestions)
    else:
        convert_multiple_files(detected_files, args.output_file)
        print(
            f"Successfully converted {len(detected_files)} files to {args.output_file}"
        )


def handle_positional_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Handle positional input arguments."""
    input_type, detected_files = detect_input_type(args.input)

    validate_input_and_output(input_type, detected_files, args, parser)

    if args.apply_suggestions:
        if input_type == "file":
            apply_suggestions_single_file(args)
        else:
            handle_bulk_conversion_with_suggestions(args, input_type, detected_files)
    else:
        # Normal conversion
        if input_type == "file":
            convert_single_file(args)
        elif input_type == "directory":
            convert_directory_handler(args)
        elif input_type == "wildcard":
            convert_wildcard_files(args, detected_files)


def handle_files_conversion(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Handle conversion of files specified with --files flag."""
    if not args.output:
        parser.error("--output is required when using --files")

    if args.apply_suggestions and len(args.files) == 1:
        # Set up args for single file processing
        input_file = args.files[0]
        args.input = input_file
        args.output_file = args.output

        process_single_file_with_suggestions(
            args,
            display_changes_func=display_suggestion_changes,
            use_stem_for_basename=False,
        )
        display_suggestions(input_file, args.no_suggestions)
    elif len(args.files) == 1:
        # Single file conversion - output should be a file
        convert_file(args.files[0], args.output)
        print(f"Successfully converted {args.files[0]} to {args.output}")
        display_suggestions(args.files[0], args.no_suggestions)
    else:
        # Multiple files conversion - output should be a directory
        convert_multiple_files(args.files, args.output)
        print(f"Successfully converted {len(args.files)} files to {args.output}")


def handle_directory_conversion(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Handle directory conversion."""
    if not args.output:
        parser.error("--output is required when using --directory")

    if args.apply_suggestions:
        print(
            "Warning: --apply-suggestions is only supported for single file conversion."
        )
        print("Performing normal directory conversion instead...")

    convert_directory(args.directory, args.output)
    print(f"Successfully converted directory {args.directory} to {args.output}")
