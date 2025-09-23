"""Conversion strategies for different input types."""

from abc import ABC, abstractmethod
from typing import Any, cast

from importobot import exceptions
from importobot.core.converter import (
    convert_directory,
    convert_file,
    convert_multiple_files,
    get_conversion_suggestions,
)
from importobot.utils.file_operations import (
    convert_with_temp_file,
    display_suggestion_changes,
    load_json_file,
    process_single_file_with_suggestions,
)
from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)


class ConversionStrategy(ABC):
    """Abstract base class for conversion strategies."""

    @abstractmethod
    def convert(self, args: Any) -> None:
        """Execute the conversion strategy."""

    @abstractmethod
    def validate_args(self, args: Any) -> None:
        """Validate arguments for this strategy."""


class SingleFileConversionStrategy(ConversionStrategy):
    """Strategy for converting a single file."""

    def convert(self, args: Any) -> None:
        """Convert a single file."""
        if args.apply_suggestions:
            self._convert_with_suggestions(args)
        else:
            convert_file(args.input, args.output_file)
            print(f"Successfully converted {args.input} to {args.output_file}")
            self._display_suggestions(args.input, args.no_suggestions)

    def validate_args(self, args: Any) -> None:
        """Validate single file conversion arguments."""
        if not args.output_file:
            raise exceptions.ValidationError(
                "Output file required for single file input"
            )

    def _convert_with_suggestions(self, args: Any) -> None:
        """Apply suggestions and convert a single file."""
        process_single_file_with_suggestions(
            args,
            display_changes_func=display_suggestion_changes,
            use_stem_for_basename=True,
        )
        self._display_suggestions(args.input, args.no_suggestions)

    def _prepare_conversion_data(self, improved_data: Any) -> dict[str, Any]:
        """Prepare data for conversion."""
        if isinstance(improved_data, list) and len(improved_data) > 0:
            return cast(dict[str, Any], improved_data[0])
        return cast(dict[str, Any], improved_data)

    def _convert_with_temp_file(
        self,
        conversion_data: dict[str, Any],
        robot_filename: str,
        changes_made: list[dict[str, Any]],
        args: Any,
    ) -> None:
        """Convert data using a temporary file."""
        convert_with_temp_file(
            conversion_data=conversion_data,
            robot_filename=robot_filename,
            changes_made=changes_made,
            display_changes_func=display_suggestion_changes,
            args=args,
        )

    def _display_suggestions(
        self, json_file_path: str, no_suggestions: bool = False
    ) -> None:
        """Display conversion suggestions for a JSON file."""
        if no_suggestions:
            return

        try:
            json_data = load_json_file(json_file_path)

            suggestions = get_conversion_suggestions(json_data)
            self._print_suggestions(suggestions)

        except exceptions.ImportobotError as e:
            logger.warning("Could not generate suggestions: %s", str(e))
        except Exception as e:
            logger.warning("Could not generate suggestions: %s", str(e))

    def _print_suggestions(self, suggestions: list[str]) -> None:
        """Print suggestions if they are meaningful."""
        if not suggestions:
            return

        # Filter out "No improvements needed" if there are other suggestions
        filtered = [s for s in suggestions if "No improvements needed" not in s]
        if not filtered and len(suggestions) == 1:
            return

        suggestions_to_print = filtered if filtered else suggestions

        print("\n💡 Conversion Suggestions:")
        print("=" * 50)
        for i, suggestion in enumerate(suggestions_to_print, 1):
            print(f"  {i}. {suggestion}")
        print(
            "\nThese suggestions can help improve the quality of the "
            "generated Robot Framework code."
        )


class DirectoryConversionStrategy(ConversionStrategy):
    """Strategy for converting all files in a directory."""

    def convert(self, args: Any) -> None:
        """Convert all files in a directory."""
        if args.apply_suggestions:
            print("Warning: --apply-suggestions only supported for single files.")
            print("Performing normal directory conversion instead...")

        convert_directory(args.input, args.output_file)
        print(f"Successfully converted directory {args.input} to {args.output_file}")

    def validate_args(self, args: Any) -> None:
        """Validate directory conversion arguments."""
        if not args.output_file:
            raise exceptions.ValidationError(
                "Output directory required for directory input"
            )


class MultipleFilesConversionStrategy(ConversionStrategy):
    """Strategy for converting multiple files."""

    def __init__(self, files: list[str]):
        """Initialize with list of files to convert."""
        self.files = files

    def convert(self, args: Any) -> None:
        """Convert multiple files."""
        if args.apply_suggestions and len(self.files) == 1:
            # Special case: single file with suggestions
            strategy = SingleFileConversionStrategy()
            args.input = self.files[0]
            strategy.convert(args)
        elif len(self.files) == 1:
            # Single file without suggestions
            convert_file(self.files[0], args.output_file)
            print(f"Successfully converted {self.files[0]} to {args.output_file}")
            self._display_suggestions(self.files[0], args.no_suggestions)
        else:
            # Multiple files
            if args.apply_suggestions:
                print("Warning: --apply-suggestions only supported for single files.")
                print("Performing normal conversion instead...")

            convert_multiple_files(self.files, args.output_file)
            print(
                f"Successfully converted {len(self.files)} files to {args.output_file}"
            )

    def validate_args(self, args: Any) -> None:
        """Validate multiple files conversion arguments."""
        if not args.output_file:
            if len(self.files) == 1:
                raise exceptions.ValidationError(
                    "Output file required for single file input"
                )
            raise exceptions.ValidationError(
                "Output directory required for multiple files"
            )

    def _display_suggestions(
        self, json_file_path: str, no_suggestions: bool = False
    ) -> None:
        """Display conversion suggestions for a JSON file."""
        if no_suggestions:
            return

        try:
            json_data = load_json_file(json_file_path)

            suggestions = get_conversion_suggestions(json_data)
            if suggestions and not (
                len(suggestions) == 1 and "No improvements needed" in suggestions[0]
            ):
                print("\n💡 Conversion Suggestions:")
                print("=" * 50)
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")
                print(
                    "\nThese suggestions can help improve the quality of the "
                    "generated Robot Framework code."
                )

        except Exception as e:
            logger.warning("Could not generate suggestions: %s", str(e))


class ConversionStrategyFactory:
    """Factory for creating appropriate conversion strategies."""

    @staticmethod
    def create_strategy(
        input_type: str, detected_files: list[str]
    ) -> ConversionStrategy:
        """Create a conversion strategy based on input type.

        Args:
            input_type: Type of input (file, directory, wildcard)
            detected_files: List of detected files

        Returns:
            Appropriate conversion strategy

        Raises:
            ValueError: If input type is unknown
        """
        if input_type == "file":
            return SingleFileConversionStrategy()
        if input_type == "directory":
            return DirectoryConversionStrategy()
        if input_type == "wildcard":
            return MultipleFilesConversionStrategy(detected_files)
        raise ValueError(f"Unknown input type: {input_type}")
