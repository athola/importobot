"""Shared file operation utilities for consistent file handling."""

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from importobot.core import converter as core_converter
from importobot.utils.json_utils import load_json_file


@dataclass
class ConversionContext:
    """Context for file conversion operations."""

    changes_made: list[dict[str, Any]] | None = None
    display_changes_func: Callable[[list[dict[str, Any]], Any], None] | None = None
    args: Any | None = None


def process_single_file_with_suggestions(
    args: Any,
    convert_file_func: Callable[[str, str], None] | None = None,
    apply_suggestions_func: (
        Callable[
            [dict[str, Any] | list[Any]],
            tuple[dict[str, Any] | list[Any], list[dict[str, Any]]],
        ]
        | None
    ) = None,
    display_changes_func: Callable[[list[dict[str, Any]], Any], None] | None = None,
    use_stem_for_basename: bool = False,
) -> None:
    """Process a single file with suggestions and conversion."""
    json_data = load_json_file(args.input)

    apply_func = apply_suggestions_func or core_converter.apply_conversion_suggestions
    improved_data: dict[str, Any] | list[Any]
    changes_made: list[dict[str, Any]]

    no_suggestions_attr = getattr(args, "no_suggestions", False)
    no_suggestions_flag = (
        bool(no_suggestions_attr) if isinstance(no_suggestions_attr, bool) else False
    )

    if no_suggestions_flag:
        improved_data, changes_made = json_data, []
    else:
        improved_data, changes_made = apply_func(json_data)

    base_name = (
        Path(args.input).stem
        if use_stem_for_basename
        else os.path.splitext(args.input)[0]
    )

    context = ConversionContext(
        changes_made=changes_made,
        display_changes_func=display_changes_func,
        args=args,
    )

    convert_func = convert_file_func or core_converter.convert_file
    save_improved_json_and_convert(
        improved_data=improved_data,
        base_name=base_name,
        convert_file_func=convert_func,
        context=context,
    )


def display_suggestion_changes(changes_made: list[dict[str, Any]], args: Any) -> None:
    """Display detailed changes if any were made."""
    if getattr(args, "no_suggestions", False):
        return

    if changes_made:
        sorted_changes = sorted(
            changes_made,
            key=lambda change: (
                change.get("test_case_index", 0),
                change.get("step_index", 0),
            ),
        )

        print("\nApplied Suggestions:")
        print("=" * 60)
        for index, change in enumerate(sorted_changes, start=1):
            test_case_num = change.get("test_case_index", 0) + 1
            step_num = change.get("step_index", 0) + 1
            field_name = change.get("field", "unknown")

            print(
                f"  {index}. Test Case {test_case_num}, Step {step_num} - {field_name}"
            )
            print(f"     Before: {change.get('original', '')}")
            print(f"     After:  {change.get('improved', '')}")
            print(f"     Reason: {change.get('reason', '')}")
            print()
    else:
        print("\nINFO: No automatic improvements could be applied.")
        print("   The JSON data is already in good shape!")


# Conversion functions have been moved to importobot.core.converter
# to avoid circular import issues. Import directly from there.


@contextmanager
def temporary_json_file(
    data: dict[str, Any] | list[Any],
) -> Generator[str, None, None]:
    """Create a temporary JSON file with the given data.

    Security: Sets restrictive permissions (0600 - owner read/write only)
    to prevent unauthorized access to potentially sensitive test data.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as temp_file:
        json.dump(data, temp_file, indent=2, ensure_ascii=False)
        temp_filename = temp_file.name

    # Set restrictive permissions: owner read/write only (0600)
    os.chmod(temp_filename, 0o600)

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
    conversion_data: dict[str, Any] | list[Any],
    robot_filename: str,
    convert_file_func: Callable[[str, str], None],
    context: ConversionContext | None = None,
) -> None:
    """Convert data using a temporary file and optionally display changes.

    Args:
        conversion_data: Data to convert
        robot_filename: Output Robot Framework filename
        convert_file_func: Function to convert file (avoids circular import)
    """
    if context is None:
        context = ConversionContext()

    with temporary_json_file(conversion_data) as temp_filename:
        if context.display_changes_func and context.changes_made and context.args:
            context.display_changes_func(context.changes_made, context.args)
        convert_file_func(temp_filename, robot_filename)
        print(f"Successfully converted improved JSON to {robot_filename}")


def save_improved_json_and_convert(
    improved_data: dict[str, Any] | list[Any],
    base_name: str,
    convert_file_func: Callable[[str, str], None],
    context: ConversionContext | None = None,
    *,
    args: Any | None = None,
    changes_made: list[dict[str, Any]] | None = None,
    display_changes_func: Callable[[list[dict[str, Any]], Any], None] | None = None,
) -> None:
    """Save improved JSON and convert to Robot Framework format.

    Args:
        improved_data: Improved JSON data
        base_name: Base name for output files
        convert_file_func: Function to convert file (avoids circular import)
        context: Optional conversion context
        args: Optional command-line arguments (for compatibility)
        changes_made: Optional list of changes made (for compatibility)
        display_changes_func: Optional display function (for compatibility)
    """
    if context is None:
        context = ConversionContext()

    if args is not None:
        context.args = args
    if changes_made is not None:
        context.changes_made = changes_made
    if display_changes_func is not None:
        context.display_changes_func = display_changes_func

    improved_filename = f"{base_name}_improved.json"
    with open(improved_filename, "w", encoding="utf-8") as json_file:
        json.dump(improved_data, json_file, indent=2, ensure_ascii=False)

    print(f"Generated improved JSON file: {improved_filename}")

    input_path = getattr(context.args, "input", None) if context.args else None
    if isinstance(input_path, str) and os.path.exists(input_path):
        backup_filename = f"{input_path}.bak"
        try:
            shutil.copy2(input_path, backup_filename)
            print(f"Created backup file: {backup_filename}")
        except OSError as exc:
            print(f"Warning: Could not create backup file {backup_filename}: {exc}")

    robot_filename = (
        getattr(context.args, "output_file", None) if context.args is not None else None
    ) or f"{base_name}_improved.robot"

    convert_with_temp_file(
        conversion_data=improved_data,
        robot_filename=robot_filename,
        convert_file_func=convert_file_func,
        context=context,
    )


def save_improved_json_file(
    improved_data: dict[str, Any] | list[Any],
    base_name: str,
) -> str:
    """Save improved JSON data to a file.

    Args:
        improved_data: Improved JSON data
        base_name: Base name for output file

    Returns:
        Path to the saved file
    """
    improved_filename = f"{base_name}_improved.json"
    with open(improved_filename, "w", encoding="utf-8") as f:
        json.dump(improved_data, f, indent=2, ensure_ascii=False)
    return improved_filename


def backup_file(file_path: str | Path) -> str:
    """Create a backup of the given file.

    Args:
        file_path: Path to the file to backup

    Returns:
        Path to the backup file
    """
    file_path = Path(file_path)
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
    shutil.copy2(file_path, backup_path)
    return str(backup_path)


def restore_file(backup_path: str | Path, original_path: str | Path) -> None:
    """Restore a file from backup.

    Args:
        backup_path: Path to the backup file
        original_path: Path where to restore the file
    """
    shutil.copy2(backup_path, original_path)


def load_json_with_default(file_path: str | Path) -> dict[str, Any] | list[Any]:
    """Load JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Loaded JSON data or empty dict if file doesn't exist
    """
    try:
        return load_json_file(str(file_path))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


__all__ = [
    "ConversionContext",
    "backup_file",
    "convert_with_temp_file",
    "display_suggestion_changes",
    "load_json_file",  # Re-exported from json_utils
    "load_json_with_default",
    "process_single_file_with_suggestions",
    "restore_file",
    "save_improved_json_and_convert",
    "save_improved_json_file",
    "temporary_json_file",
]
