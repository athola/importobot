"""CLI command handlers and processing logic."""

from __future__ import annotations

import argparse
import datetime as dt
import enum
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

from importobot import exceptions
from importobot.config import resolve_api_ingest_config
from importobot.core.converter import (
    convert_directory,
    convert_file,
    convert_multiple_files,
    get_conversion_suggestions,
)
from importobot.integrations.clients import get_api_client
from importobot.utils.file_operations import (
    display_suggestion_changes,
    process_single_file_with_suggestions,
)
from importobot.utils.json_utils import load_json_file
from importobot.utils.logging import setup_logger


class InputType(enum.Enum):
    """Input type enumeration for CLI processing."""

    FILE = "file"
    DIRECTORY = "directory"
    WILDCARD = "wildcard"
    ERROR = "error"


logger = setup_logger("importobot-cli")


def detect_input_type(input_path: str) -> tuple[InputType, list[str]]:
    """Detect input type and return (type, files_list).

    Returns:
        tuple: (input_type, files_list) where input_type is an InputType enum
    """
    # Check if it contains wildcard characters
    if any(char in input_path for char in ["*", "?", "[", "]"]):
        # Handle wildcard pattern
        matched_files = glob.glob(input_path, recursive=True)
        if not matched_files:
            return InputType.ERROR, []
        # Filter for JSON files only
        json_files = [f for f in matched_files if f.lower().endswith(".json")]
        if not json_files:
            return InputType.ERROR, []
        return InputType.WILDCARD, json_files

    # Check if it's a directory
    if os.path.isdir(input_path):
        return InputType.DIRECTORY, [input_path]

    # Check if it's a file
    if os.path.isfile(input_path):
        return InputType.FILE, [input_path]

    # Path doesn't exist
    return InputType.ERROR, []


def requires_output_directory(input_type: InputType, files_count: int) -> bool:
    """Determine if the input type requires an output directory."""
    if input_type == InputType.DIRECTORY:
        return True
    return bool(input_type == InputType.WILDCARD and files_count > 1)


def validate_input_and_output(
    input_type: InputType,
    detected_files: list,
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    """Validate input and output arguments."""
    if input_type == InputType.ERROR:
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

    print("\nConversion Suggestions:")
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
        args=args,
        convert_file_func=convert_file,
        display_changes_func=display_suggestion_changes,
        use_stem_for_basename=False,
    )
    display_suggestions(args.input, args.no_suggestions)


def handle_bulk_conversion_with_suggestions(
    args: argparse.Namespace, input_type: InputType, detected_files: list
) -> None:
    """Handle conversion for directories or multiple files with suggestions warning."""
    print("Warning: --apply-suggestions only supported for single files.")
    print("Performing normal conversion instead...")

    if input_type == InputType.DIRECTORY:
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


def _build_payload_filename(config: Any) -> Path:
    """Generate deterministic filename for downloaded payload."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_parts = [config.fetch_format.value]
    if config.project_name:
        base_parts.append(config.project_name.lower())
    elif config.project_id is not None:
        base_parts.append(str(config.project_id))
    filename = "-".join(base_parts) + f"-{timestamp}.json"
    return Path(config.output_dir) / filename


def handle_api_ingest(args: argparse.Namespace) -> str:
    """Fetch suites from a remote API and persist them to disk."""
    config = resolve_api_ingest_config(args)
    client = get_api_client(
        config.fetch_format,
        api_url=config.api_url,
        tokens=config.tokens,
        user=config.user,
        project_name=config.project_name,
        project_id=config.project_id,
        max_concurrency=config.max_concurrency,
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = _build_payload_filename(config)
    metadata_path = payload_path.with_suffix(".meta.json")

    totals = {"progress_events": 0, "items": 0}

    def progress_cb(**info: Any) -> None:
        totals["progress_events"] += 1
        totals["items"] += int(info.get("items") or 0)
        total_items = info.get("total")
        if total_items:
            logger.debug(
                "Fetched page %s (%s/%s items)",
                info.get("page"),
                totals["items"],
                total_items,
            )
        else:
            logger.debug(
                "Fetched page %s (%s items)",
                info.get("page"),
                totals["items"],
            )

    payloads: list[dict[str, Any]] = list(client.fetch_all(progress_cb))

    page_count = len(payloads)

    if not payloads:
        logger.warning(
            "No data returned from %s for %s",
            config.api_url,
            config.fetch_format.value,
        )

    with open(payload_path, "w", encoding="utf-8") as handle:
        serialisable = payloads if len(payloads) != 1 else payloads[0]
        json.dump(serialisable, handle, indent=2)

    saved_at = dt.datetime.now(dt.timezone.utc)
    metadata = {
        "format": config.fetch_format.value,
        "source": config.api_url,
        "project": config.project_name or config.project_id,
        "project_name": config.project_name,
        "project_id": config.project_id,
        "saved_at": saved_at.isoformat().replace("+00:00", "Z"),
        "pages": page_count,
        "items": totals["items"],
    }

    with open(metadata_path, "w", encoding="utf-8") as meta_handle:
        json.dump(metadata, meta_handle, indent=2)

    args.input = str(payload_path)
    args.input_dir = str(config.output_dir)
    args.fetched_payload_path = str(payload_path)

    logger.info(
        "Saved API payload to %s (pages=%s, items=%s, progress_events=%s)",
        payload_path,
        page_count,
        totals["items"],
        totals["progress_events"],
    )

    return str(payload_path)


def handle_positional_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Handle positional input arguments."""
    input_type, detected_files = detect_input_type(args.input)

    validate_input_and_output(input_type, detected_files, args, parser)

    if args.apply_suggestions:
        if input_type == InputType.FILE:
            apply_suggestions_single_file(args)
        else:
            handle_bulk_conversion_with_suggestions(args, input_type, detected_files)
    # Normal conversion
    elif input_type == InputType.FILE:
        convert_single_file(args)
    elif input_type == InputType.DIRECTORY:
        convert_directory_handler(args)
    elif input_type == InputType.WILDCARD:
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
            args=args,
            convert_file_func=convert_file,
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


__all__ = [
    "InputType",
    "apply_suggestions_single_file",
    "collect_suggestions",
    "convert_directory_handler",
    "convert_single_file",
    "convert_wildcard_files",
    "detect_input_type",
    "display_suggestions",
    "filter_suggestions",
    "handle_api_ingest",
    "handle_bulk_conversion_with_suggestions",
    "handle_directory_conversion",
    "handle_files_conversion",
    "handle_positional_args",
    "print_suggestions",
    "requires_output_directory",
    "validate_input_and_output",
]
