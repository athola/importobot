"""Shared file operation utilities for consistent file handling."""

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Union

from importobot.utils.json_utils import load_json_file

# Conversion functions have been moved to importobot.core.converter
# to avoid circular import issues. Import directly from there.


@contextmanager
def temporary_json_file(
    data: Union[dict[str, Any], list[Any]],
) -> Generator[str, None, None]:
    """Create a temporary JSON file with the given data."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as temp_file:
        json.dump(data, temp_file, indent=2, ensure_ascii=False)
        temp_filename = temp_file.name

    try:
        yield temp_filename
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
        except (OSError, Exception):
            # Ignore cleanup errors
            pass


def convert_with_temp_file(
    conversion_data: Union[dict[str, Any], list[Any]],
    robot_filename: str,
    changes_made: list[dict[str, Any]] | None = None,
    display_changes_func: Callable | None = None,
    args: Any | None = None,
) -> None:
    """Convert data using a temporary file and optionally display changes."""
    with temporary_json_file(conversion_data) as temp_filename:
        if display_changes_func and changes_made and args:
            display_changes_func(changes_made, args)
        from importobot.core.converter import (  # pylint: disable=import-outside-toplevel  # noqa: E501
            convert_file,
        )

        convert_file(temp_filename, robot_filename)
        print(f"Successfully converted improved JSON to {robot_filename}")


def save_improved_json_and_convert(
    improved_data: Union[dict[str, Any], list[Any]],
    base_name: str,
    args: Any,
    changes_made: list[dict[str, Any]] | None = None,
    display_changes_func: Callable | None = None,
) -> None:
    """Save improved JSON and convert to Robot Framework format."""
    improved_filename = f"{base_name}_improved.json"
    robot_filename = args.output_file or f"{base_name}_improved.robot"

    # Create backup of original file if it exists
    original_input = getattr(args, "input", None)
    if (
        original_input
        and isinstance(original_input, str)
        and os.path.exists(original_input)
    ):
        backup_filename = f"{original_input}.bak"
        try:
            shutil.copy2(original_input, backup_filename)
            print(f"Created backup file: {backup_filename}")
        except (OSError, IOError) as e:
            print(f"Warning: Could not create backup file {backup_filename}: {e}")

    # Save improved JSON
    with open(improved_filename, "w", encoding="utf-8") as f:
        json.dump(improved_data, f, indent=2, ensure_ascii=False)

    print(f"Generated improved JSON file: {improved_filename}")

    convert_with_temp_file(
        conversion_data=improved_data,
        robot_filename=robot_filename,
        changes_made=changes_made,
        display_changes_func=display_changes_func,
        args=args,
    )


def display_suggestion_changes(changes_made: list[dict[str, Any]], args: Any) -> None:
    """Display detailed changes if any were made."""
    if changes_made:
        # Sort changes by test case and step index
        changes_made.sort(
            key=lambda x: (
                x.get("test_case_index", 0),
                x.get("step_index", 0),
            )
        )

        print("\n📋 Applied Suggestions:")
        print("=" * 60)
        for i, change in enumerate(changes_made, 1):
            test_case_num = change.get("test_case_index", 0) + 1
            step_num = change.get("step_index", 0) + 1
            field_name = change.get("field", "unknown")

            print(f"  {i}. Test Case {test_case_num}, Step {step_num} - {field_name}")
            print(f"     Before: {change['original']}")
            print(f"     After:  {change['improved']}")
            print(f"     Reason: {change['reason']}")
            print()
    elif not args.no_suggestions:
        print("\nℹ️  No automatic improvements could be applied.")
        print("   The JSON data is already in good shape!")


def process_single_file_with_suggestions(
    args: Any,
    display_changes_func: Callable | None = None,
    use_stem_for_basename: bool = False,
) -> None:
    """Process a single file with suggestions and conversion.

    Args:
        args: Command line arguments with input and output_file attributes
        display_changes_func: Function to display changes made
        use_stem_for_basename: If True, use Path.stem, else os.path.splitext
    """
    # Load the JSON data
    json_data = load_json_file(args.input)

    # Apply suggestions
    from importobot.core.converter import (  # pylint: disable=import-outside-toplevel
        apply_conversion_suggestions,
    )

    improved_data, changes_made = apply_conversion_suggestions(json_data)

    # Generate base name using appropriate method
    if use_stem_for_basename:
        base_name = Path(args.input).stem
    else:
        base_name = os.path.splitext(args.input)[0]

    save_improved_json_and_convert(
        improved_data=improved_data,
        base_name=base_name,
        args=args,
        changes_made=changes_made,
        display_changes_func=display_changes_func,
    )
