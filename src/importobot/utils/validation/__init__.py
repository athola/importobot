"""Unified validation utilities for the Importobot project.

This module consolidates all validation functionality previously spread across:
- utils/validation.py (security and safety validation)
- utils/validators.py (type and input validation)
- core/suggestions/field_validator.py (field-specific validation)

The unified approach provides:
- Consistent validation patterns across the codebase
- Reduced code duplication
- Centralized error handling and messaging
- Better testability and maintainability
"""

from .core import (
    ValidationContext,
    ValidationError,
    require_valid_input,
    validate_json_dict,
    validate_json_size,
    validate_not_empty,
    validate_string_content,
    validate_type,
)
from .field_validation import FieldValidator
from .path_validation import (
    validate_directory_path,
    validate_file_path,
    validate_safe_path,
)
from .robot_validation import (
    convert_parameters_to_robot_variables,
    format_robot_framework_arguments,
    sanitize_error_message,
    sanitize_robot_string,
)

__all__ = [
    # Core validation functions
    "validate_type",
    "validate_not_empty",
    "validate_json_dict",
    "validate_string_content",
    "validate_json_size",
    "ValidationContext",
    "ValidationError",
    "require_valid_input",
    # Path validation
    "validate_safe_path",
    "validate_file_path",
    "validate_directory_path",
    # Robot Framework specific
    "sanitize_robot_string",
    "format_robot_framework_arguments",
    "sanitize_error_message",
    "convert_parameters_to_robot_variables",
    # Field validation
    "FieldValidator",
]
