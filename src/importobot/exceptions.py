"""Custom exception classes for Importobot."""


class ImportobotError(Exception):
    """Base exception for all errors raised by Importobot."""


class ConfigurationError(ImportobotError):
    """Indicate an error in the application's configuration."""


class ValidationError(ImportobotError):
    """Indicate that input data failed a validation check."""


class ConversionError(ImportobotError):
    """Indicate an error during the conversion process."""


class FileNotFound(ImportobotError):
    """Indicate that a required file could not be found."""


class FileAccessError(ImportobotError):
    """Indicate an error accessing a file, such as a permissions issue."""


class ParseError(ImportobotError):
    """Indicate an error parsing a file, such as a malformed JSON document."""


class SuggestionError(ImportobotError):
    """Indicate an error generating or applying a code suggestion."""


class SecurityError(ImportobotError):
    """Indicate a security validation failure, such as an invalid credential."""
