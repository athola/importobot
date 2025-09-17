"""Logging utilities for Importobot."""

import logging
import sys


def setup_logger(name: str = "importobot", level: int = logging.INFO) -> logging.Logger:
    """Set up and return a logger with consistent formatting.

    Args:
        name: Name for the logger
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers if logger already exists
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_exception(
    logger: logging.Logger, exception: Exception, context: str = ""
) -> None:
    """Log an exception with its traceback.

    Args:
        logger: Logger instance to use
        exception: Exception to log
        context: Additional context information
    """
    message = f"Exception occurred: {type(exception).__name__}: {str(exception)}"
    if context:
        message = f"{context} - {message}"
    logger.exception(message)
