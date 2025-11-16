"""Conversion strategies for different input types."""

import json
from abc import ABC, abstractmethod
from typing import Any

from importobot import exceptions
from importobot.core.converter import (
    apply_conversion_suggestions,
    convert_directory,
    convert_file,
    convert_multiple_files,
    get_conversion_suggestions,
)
from importobot.utils.file_operations import (
    ConversionContext,
    convert_with_temp_file,
    display_suggestion_changes,
    process_single_file_with_suggestions,
)
from importobot.utils.json_utils import load_json_file
from importobot.utils.logging import get_logger


class ConversionStrategy(ABC):
    """Abstract base class for conversion strategies."""

    @abstractmethod
    def validate_args(self, args: Any) -> None:
        """Validate conversion arguments."""
        raise NotImplementedError("validate_args must be implemented")

    @abstractmethod
    def convert(self, args: Any) -> None:
        """Perform the conversion."""
        raise NotImplementedError("convert must be implemented")


class SingleFileStrategy(ConversionStrategy):
    """Strategy for converting a single file."""

    def validate_args(self, args: Any) -> None:
        """Validate single file conversion arguments."""
        if not args.output_file:
            raise exceptions.ValidationError(
                "Output file required for single file input"
            )

    def _convert_with_suggestions(self, args: Any) -> None:
        """Apply suggestions and convert a single file."""
        process_single_file_with_suggestions(
            args=args,
            convert_file_func=convert_file,
            display_changes_func=display_suggestion_changes,
            use_stem_for_basename=True,
        )
        self._display_suggestions(args.input, args.no_suggestions)

    def _convert_directly(self, args: Any) -> None:
        """Convert a single file directly without suggestions."""
        convert_file(args.input, args.output_file)

    def convert(self, args: Any) -> None:
        """Convert a single file."""
        apply_attr = getattr(args, "apply_suggestions", False)
        should_apply = apply_attr if isinstance(apply_attr, bool) else False

        if should_apply:
            self._convert_with_suggestions(args)
        else:
            self._convert_directly(args)

    def _display_suggestions(self, input_file: str, no_suggestions: bool) -> None:
        """Display suggestions for the input file."""
        if no_suggestions:
            return

        try:
            json_data = load_json_file(input_file)
            suggestions = get_conversion_suggestions(json_data)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Cannot read input file for suggestions.")
            return
        except exceptions.ImportobotError as error:
            print(f"Could not generate suggestions: {error}")
            return
        except Exception as error:  # pragma: no cover - defensive logging
            print(f"Could not generate suggestions: {error}")
            return

        if suggestions:
            print("Conversion Suggestions:")
            for index, suggestion in enumerate(suggestions, start=1):
                print(f"{index}. {suggestion}")


class MultipleFileStrategy(ConversionStrategy):
    """Strategy for converting multiple files."""

    def validate_args(self, args: Any) -> None:
        """Validate multiple file conversion arguments."""
        if not args.output_file:
            raise exceptions.ValidationError(
                "Output file required for multiple file input"
            )

    def convert(self, args: Any) -> None:
        """Convert multiple files to a single output file."""
        convert_multiple_files(args.files, args.output_file)


class DirectoryStrategy(ConversionStrategy):
    """Strategy for converting a directory of files."""

    def validate_args(self, args: Any) -> None:
        """Validate directory conversion arguments."""
        output_dir = getattr(args, "output_dir", None)
        if not isinstance(output_dir, str) or not output_dir:
            output_dir = None

        output_file = getattr(args, "output_file", None)
        if not isinstance(output_file, str) or not output_file:
            output_file = None

        output_target = output_dir or output_file
        if not output_target:
            raise exceptions.ValidationError(
                "Output directory required for directory input"
            )

    def convert(self, args: Any) -> None:
        """Convert a directory of files."""
        output_dir = getattr(args, "output_dir", None)
        if not isinstance(output_dir, str) or not output_dir:
            output_dir = None

        output_file = getattr(args, "output_file", None)
        if not isinstance(output_file, str) or not output_file:
            output_file = None

        output_target = output_dir or output_file

        apply_attr = getattr(args, "apply_suggestions", False)
        should_warn = apply_attr if isinstance(apply_attr, bool) else False

        if should_warn:
            print("Warning: --apply-suggestions only supported for single files.")

        if output_target is None:
            raise exceptions.ValidationError(
                "Output directory required for directory input"
            )

        convert_directory(args.input, output_target)


class SuggestionsOnlyStrategy(ConversionStrategy):
    """Strategy for showing suggestions only."""

    def validate_args(self, args: Any) -> None:
        """Validate suggestions-only arguments.

        No validation needed for suggestions-only mode.
        """

    def convert(self, args: Any) -> None:
        """Show suggestions for input files."""
        for input_file in args.files:
            self._display_suggestions_for_file(input_file)

    def _display_suggestions_for_file(self, input_file: str) -> None:
        """Load a file and print suggestion details."""
        try:
            json_data = load_json_file(input_file)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Cannot read {input_file} for suggestions.")
            return

        suggestions = get_conversion_suggestions(json_data)
        if suggestions:
            print(f"Suggestions for {input_file}:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
        else:
            print(f"No suggestions for {input_file}.")


class ImprovedConversionStrategy(ConversionStrategy):
    """Strategy for converting with improvements applied."""

    def validate_args(self, args: Any) -> None:
        """Validate improved conversion arguments."""
        if not args.output_file:
            raise exceptions.ValidationError(
                "Output file required for improved conversion"
            )

    def convert(self, args: Any) -> None:
        """Convert with improvements applied."""
        # Apply suggestions
        json_data = load_json_file(args.input)
        improved_data, changes = apply_conversion_suggestions(json_data)

        # Convert using temporary file
        context = ConversionContext(
            changes_made=[{"description": str(c)} for c in changes],
            display_changes_func=display_suggestion_changes,
            args=args,
        )
        convert_with_temp_file(
            conversion_data=improved_data,
            robot_filename=args.output_file,
            convert_file_func=convert_file,
            context=context,
        )

    def _convert_with_temp_file(
        self,
        conversion_data: dict[str, Any],
        robot_filename: str,
        changes_made: list[dict[str, Any]],
        args: Any,
    ) -> None:
        """Convert data using a temporary file."""
        context = ConversionContext(
            changes_made=changes_made,
            display_changes_func=display_suggestion_changes,
            args=args,
        )
        convert_with_temp_file(
            conversion_data=conversion_data,
            robot_filename=robot_filename,
            convert_file_func=convert_file,
            context=context,
        )

    def _display_suggestions(self, input_file: str, no_suggestions: bool) -> None:
        """Display suggestions for the input file."""
        if not no_suggestions:
            try:
                json_data = load_json_file(input_file)
                suggestions = get_conversion_suggestions(json_data)
                if suggestions:
                    print("Suggestions for improvement:")
                    for suggestion in suggestions:
                        print(f"  - {suggestion}")
                else:
                    print("No suggestions for improvement.")
            except (FileNotFoundError, json.JSONDecodeError):
                print("Cannot read input file for suggestions.")


def get_strategy(args: Any) -> ConversionStrategy:
    """Get the appropriate conversion strategy based on arguments."""
    if args.suggestions_only:
        return SuggestionsOnlyStrategy()
    if args.improved:
        return ImprovedConversionStrategy()
    if args.input and hasattr(args, "output_file") and args.output_file:
        # Single file with output file specified
        return SingleFileStrategy()
    if len(args.files) > 1:
        return MultipleFileStrategy()
    if args.input and hasattr(args, "output_dir") and args.output_dir:
        return DirectoryStrategy()
    # Default to single file strategy
    return SingleFileStrategy()


def convert_with_strategy(args: Any) -> None:
    """Convert input using the appropriate strategy."""
    logger = get_logger()
    strategy = get_strategy(args)

    try:
        strategy.validate_args(args)
        strategy.convert(args)
        logger.info("Conversion completed successfully")
    except Exception as e:
        logger.error("Conversion failed: %s", e)
        raise
