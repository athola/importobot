"""Custom exception classes for Importobot."""


class ImportobotError(Exception):
    """Base exception class for all Importobot-related errors."""


class ConfigurationError(ImportobotError):
    """Raised when there are configuration-related issues."""


class ValidationError(ImportobotError):
    """Raised when input validation fails."""


class ConversionError(ImportobotError):
    """Raised when conversion process encounters an error."""


class FileNotFound(ImportobotError):
    """Raised when a required file is not found."""


class FileAccessError(ImportobotError):
    """Raised when there are issues accessing a file."""


class ParseError(ImportobotError):
    """Raised when parsing JSON or other data fails."""


class SuggestionError(ImportobotError):
    """Raised when suggestion generation or application fails."""
