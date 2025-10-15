import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Assuming these exist based on the plan and common structure
from importobot.formats import SupportedFormat  # New import for the enum
from importobot.medallion.bronze.raw_data_processor import RawDataProcessor
from importobot.core.engine import GenericConversionEngine
from importobot.exceptions import (
    ConversionError,
    FileAccessError,
    ParseError,
    ValidationError,
)
from importobot.config import MAX_JSON_SIZE_MB # Example config import

import logging
logger = logging.getLogger(__name__)

class JsonToRobotConverter:
    """
    Primary interface for converting JSON test cases to Robot Framework format.

    This class orchestrates the conversion process, handling file operations,
    JSON parsing, and delegating to internal components for raw data processing
    and final Robot Framework generation. It supports both automatic source
    format detection and explicit format specification to optimize performance.
    """

    def __init__(self, source_format: Optional[SupportedFormat] = None) -> None:
        """
        Initializes the JsonToRobotConverter.

        Args:
            source_format: An optional default source format (e.g., SupportedFormat.ZEPHYR)
                           to be used for all conversions performed by this instance,
                           unless explicitly overridden by method-level arguments.
                           If `None`, automatic format detection will be performed.
        """
        self._instance_source_format: Optional[SupportedFormat] = source_format
        # RawDataProcessor is identified as the module responsible for format detection
        self._raw_data_processor = RawDataProcessor()
        # GenericConversionEngine handles the actual transformation to Robot
        self._conversion_engine = GenericConversionEngine()
        logger.debug(
            f"JsonToRobotConverter initialized with instance default source_format: "
            f"{self._instance_source_format.value if self._instance_source_format else 'None (auto-detect)'}"
        )

    def _get_effective_source_format(self, method_source_format: Optional[SupportedFormat]) -> Optional[SupportedFormat]:
        """
        Determines the effective source format to use for a conversion operation.

        Args:
            method_source_format: The source format provided directly to a conversion method.
                                  If this is not None, it takes precedence.

        Returns:
            The effective SupportedFormat to use for the current operation. If both
            `method_source_format` and `self._instance_source_format` are None,
            then None is returned, indicating that automatic detection is required.
        """
        return method_source_format if method_source_format is not None else self._instance_source_format

    def _load_and_process_json_data(self, json_content: str, effective_source_format: Optional[SupportedFormat]) -> Dict[str, Any]:
        """
        Loads, validates, and processes JSON content using the RawDataProcessor.

        Args:
            json_content: The raw JSON string content.
            effective_source_format: The determined source format to use. If None,
                                     the RawDataProcessor will perform automatic detection.

        Returns:
            A dictionary containing processed data ready for the conversion engine.

        Raises:
            FileAccessError: If the input JSON exceeds maximum allowed size.
            ParseError: If the input JSON cannot be parsed.
            ValidationError: If the raw data processor detects structural issues.
            ConversionError: If the data processing fails for other reasons.
        """
        json_byte_size = len(json_content.encode('utf-8'))
        json_mb_size = json_byte_size / (1024 * 1024)

        if json_mb_size > MAX_JSON_SIZE_MB:
            logger.error(f"Input JSON ({json_mb_size:.2f}MB) exceeds maximum allowed size of {MAX_JSON_SIZE_MB}MB.")
            raise FileAccessError(f"Input JSON exceeds maximum allowed size of {MAX_JSON_SIZE_MB}MB.")
        elif json_mb_size > (MAX_JSON_SIZE_MB / 2): # Heuristic for large but valid files
            logger.info(f"Processing large JSON input ({json_mb_size:.2f}MB).")

        try:
            raw_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input: {e}", exc_info=True)
            raise ParseError(f"Invalid JSON input: {e}") from e

        log_format_value = effective_source_format.value if effective_source_format else 'auto-detect'
        logger.debug(
            f"Raw data loaded. Passing to RawDataProcessor with effective format: {log_format_value}"
        )
        try:
            # Pass effective_source_format down to the RawDataProcessor.
            # This is where the core logic to bypass auto-detection will reside.
            processed_data = self._raw_data_processor.process_raw_data(
                raw_data, source_format=effective_source_format
            )
            return processed_data
        except (ValidationError, ConversionError) as e:
            logger.error(f"Error during raw data processing: {e}", exc_info=True)
            raise # Re-raise the original exception
        except Exception as e:
            logger.critical(f"An unexpected error occurred during raw data processing: {e}", exc_info=True)
            raise ConversionError(f"An unexpected error occurred during data processing: {e}") from e


    def convert_json_string(self, json_string: str, source_format: Optional[SupportedFormat] = None) -> str:
        """
        Converts a JSON string containing test cases to a Robot Framework string.

        Args:
            json_string: The JSON string content.
            source_format: Optional. Specifies the source format to bypass
                           automatic detection. If provided, it overrides the
                           instance-level `source_format` for this conversion.
                           Pass `None` to force automatic detection (even if an
                           instance-level `source_format` was set).

        Returns:
            A string containing the Robot Framework test suite.

        Raises:
            ValidationError: If the input JSON is structurally invalid.
            ParseError: If the input JSON cannot be parsed.
            ConversionError: If an error occurs during the conversion process.
            FileAccessError: If the input JSON string size exceeds limits.
        """
        effective_source_format = self._get_effective_source_format(source_format)

        log_msg_format = effective_source_format.value if effective_source_format else 'auto-detect'
        logger.info(f"Starting JSON string conversion (effective format: {log_msg_format})")
        
        try:
            # Load and process the JSON data, passing the effective source_format
            processed_data = self._load_and_process_json_data(json_string, effective_source_format)
            
            # Convert the processed data into Robot Framework content.
            # The GenericConversionEngine is assumed to handle the normalized data
            # from RawDataProcessor without needing explicit format information here.
            robot_content = self._conversion_engine.convert(processed_data)
            logger.info(f"JSON string conversion completed successfully.")
            return robot_content
        except (FileAccessError, ParseError, ValidationError, ConversionError) as e:
            logger.error(f"Failed to convert JSON string: {e}", exc_info=True)
            raise # Re-raise the original exception
        except Exception as e:
            logger.critical(f"An unexpected error occurred during JSON string conversion: {e}", exc_info=True)
            raise ConversionError(f"An unexpected error occurred during conversion: {e}") from e


    def convert_file(self, input_path: str, output_path: str, source_format: Optional[SupportedFormat] = None) -> None:
        """
        Converts a single JSON file to a Robot Framework file.

        Args:
            input_path: Path to the input JSON file.
            output_path: Path to the output Robot Framework file.
            source_format: Optional. Specifies the source format to bypass
                           automatic detection. If provided, it overrides the
                           instance-level `source_format` for this conversion.
                           Pass `None` to force automatic detection (even if an
                           instance-level `source_format` was set).

        Raises:
            FileNotFoundError: If the input file does not exist.
            FileAccessError: If there's an issue reading the input or writing the output.
            ValidationError: If the input JSON is structurally invalid.
            ParseError: If the input JSON cannot be parsed.
            ConversionError: If an error occurs during the conversion process.
        """
        input_file_path = Path(input_path)
        output_file_path = Path(output_path)

        if not input_file_path.exists():
            logger.error(f"Input file not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not input_file_path.is_file():
            logger.error(f"Input path '{input_path}' is not a file.")
            raise FileAccessError(f"Input path '{input_path}' is not a file.")

        try:
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create output directory {output_file_path.parent}: {e}", exc_info=True)
            raise FileAccessError(f"Error creating output directory for {output_path}: {e}") from e

        logger.info(f"Reading input file: {input_path}")
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
        except OSError as e:
            logger.error(f"Error reading input file {input_path}: {e}", exc_info=True)
            raise FileAccessError(f"Error reading input file {input_path}: {e}") from e

        effective_source_format = self._get_effective_source_format(source_format)

        log_msg_format = effective_source_format.value if effective_source_format else 'auto-detect'
        logger.info(f"Converting file '{input_path}' to '{output_path}' (effective format: {log_msg_format})")

        try:
            # Call convert_json_string to perform the actual conversion logic
            robot_content = self.convert_json_string(json_content, effective_source_format)

            logger.info(f"Writing output file: {output_path}")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(robot_content)
            logger.info(f"File '{input_path}' converted successfully to '{output_path}'.")
        except (FileNotFoundError, FileAccessError, ParseError, ValidationError, ConversionError) as e:
            logger.error(f"Failed to convert file '{input_path}': {e}", exc_info=True)
            raise # Re-raise the original exception
        except Exception as e:
            logger.critical(f"An unexpected error occurred during file conversion for '{input_path}': {e}", exc_info=True)
            raise ConversionError(f"An unexpected error occurred during file conversion: {e}") from e

        
    def convert_directory(self, input_dir: str, output_dir: str, source_format: Optional[SupportedFormat] = None) -> Dict[str, Any]:
        """
        Converts all JSON files in an input directory (and its subdirectories)
        to Robot Framework files in an output directory, maintaining the original
        directory structure.

        Args:
            input_dir: Path to the input directory containing JSON files.
            output_dir: Path to the output directory for Robot Framework files.
            source_format: Optional. Specifies the source format to bypass
                           automatic detection for all files in the directory.
                           If provided, it overrides the instance-level
                           `source_format` for all conversions in this batch.
                           Pass `None` to force automatic detection (even if an
                           instance-level `source_format` was set).

        Returns:
            A dictionary containing conversion summary (e.g., success_count, error_count, errors).

        Raises:
            FileNotFoundError: If the input directory does not exist.
            FileAccessError: If there's an issue with directory access.
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.exists():
            logger.error(f"Input directory not found: {input_dir}")
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        if not input_path.is_dir():
            logger.error(f"Input path '{input_dir}' is not a directory.")
            raise FileAccessError(f"Input path '{input_dir}' is not a directory.")

        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create output directory {output_path}: {e}", exc_info=True)
            raise FileAccessError(f"Error creating output directory {output_dir}: {e}") from e

        success_count = 0
        error_count = 0
        errors: Dict[str, str] = {}

        # Determine the effective source_format for the batch
        effective_source_format = self._get_effective_source_format(source_format)

        log_msg_format = effective_source_format.value if effective_source_format else 'auto-detect'
        logger.info(
            f"Starting batch conversion from '{input_dir}' to '{output_dir}' "
            f"(effective format: {log_msg_format})"
        )

        json_files = list(input_path.rglob("*.json"))
        if not json_files:
            logger.warning(f"No JSON files found in input directory '{input_dir}' or its subdirectories.")
            return {"success_count": 0, "error_count": 0, "errors": {}, "message": "No JSON files found."}


        for json_file in json_files:
            relative_path = json_file.relative_to(input_path)
            output_file = (output_path / relative_path).with_suffix(".robot")
            
            try:
                # Ensure the parent directory for the output file exists
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Pass the batch-level effective_source_format to convert_file
                self.convert_file(str(json_file), str(output_file), source_format=effective_source_format)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors[str(json_file)] = str(e)
                logger.error(f"Failed to convert '{json_file}': {e}", exc_info=True)

        logger.info(
            f"Batch conversion completed for '{input_dir}': "
            f"{success_count} successful, {error_count} failed."
        )
        return {"success_count": success_count, "error_count": error_count, "errors": errors}