"""Robot Framework specific validation and formatting utilities."""

import re
from pathlib import Path
from typing import Any

from importobot.core.constants import ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR


def convert_parameters_to_robot_variables(
    text: str, parameters: list[dict[str, Any]] | None = None
) -> str:
    """Convert parameter placeholders {param} to Robot Framework variables ${param}.

    Args:
        text: Text containing parameter placeholders
        parameters: Optional list of parameter definitions to validate against

    Returns:
        Text with parameters converted to Robot Framework variable syntax

    Examples:
        >>> convert_parameters_to_robot_variables("echo {test_file}")
        'echo ${test_file}'
    """
    if not text:
        return text

    # If parameters is None, treat it as an empty list
    if parameters is None:
        parameters = []

    # Find parameter placeholders in {param} format, but exclude those
    # already in ${param} format
    pattern = r"(?<!\$)\{([^}]+)\}"

    def replace_parameter(match: re.Match[str]) -> str:
        param_name = match.group(1).strip()

        # Avoid converting braces that are immediately adjacent to
        # alphanumeric characters (e.g. "foo{bar}") since they're likely
        # literal braces rather than placeholder syntax.
        if match.start() > 0:
            preceding_char = match.string[match.start() - 1]
            if preceding_char.isalnum() or preceding_char == "_":
                return match.group(0)

        # Only convert if it looks like a valid variable name
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", param_name):
            return f"${{{param_name}}}"
        # Keep original if it doesn't look like a variable
        return match.group(0)

    converted_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            converted_lines.append(line)
            continue
        converted_lines.append(re.sub(pattern, replace_parameter, line))

    return "\n".join(converted_lines)


def sanitize_robot_string(text: Any) -> str:
    """Sanitize string for Robot Framework output.

    Removes newlines, carriage returns, and trims whitespace
    to prevent Robot Framework syntax errors.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized string safe for Robot Framework
    """
    if text is None:
        return ""

    # Handle control characters and line endings while preserving intended spacing
    text_str = str(text)
    # Replace Windows line endings first to avoid double spaces
    text_str = text_str.replace("\r\n", " ")
    # Then replace remaining newlines and carriage returns
    text_str = text_str.translate({ord("\n"): " ", ord("\r"): " "})
    # Replace other non-printable control characters with spaces (e.g., form feed)
    text_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text_str)
    # Trim leading/trailing whitespace but preserve internal spacing
    return text_str.strip()


def format_robot_framework_arguments(*args: Any) -> str:
    """Format arguments for Robot Framework keyword calls.

    Joins arguments with 4 spaces as per Robot Framework syntax.

    Args:
        *args: Arguments to format

    Returns:
        Formatted argument string

    Examples:
        >>> format_robot_framework_arguments("Run Process", "echo", "hello")
        'Run Process    echo    hello'
    """
    # Convert all arguments to strings and filter out empty ones
    string_args = [
        str(arg).strip() for arg in args if arg is not None and str(arg).strip()
    ]
    return ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR.join(string_args)


def sanitize_error_message(message: str, file_path: str | None = None) -> str:
    """Sanitize error messages to prevent information disclosure.

    Args:
        message: Original error message
        file_path: Optional file path to sanitize from message

    Returns:
        Sanitized error message
    """
    if not message:
        return "An error occurred"

    sanitized = message

    # Remove full paths, keep only filename
    if file_path:
        filename = Path(file_path).name
        sanitized = sanitized.replace(file_path, f"'{filename}'")

    # Remove system information patterns
    patterns_to_remove = [
        r"[\\/]home[\\/][^\\s\\n]*",  # Home directories
        r"[\\/]usr[\\/][^\\s\\n]*",  # System directories
        r"[\\/]tmp[\\/][^\\s\\n]*",  # Temp directories
        r"C:\\[^\\s\\n]*",  # Windows paths
    ]

    for pattern in patterns_to_remove:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    return sanitized
