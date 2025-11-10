"""Logging utilities for Importobot."""

from __future__ import annotations

import inspect
import logging
import sys
from functools import cache

_LOGGER_CACHE: dict[str, logging.Logger] = {}


def _configure_logger(name: str, level: int) -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


@cache
def _detect_caller_module(depth: int = 2) -> str:
    """Detect the name of the calling module."""
    frame = inspect.currentframe()
    for _ in range(depth):
        if frame is None:
            break
        frame = frame.f_back
    module_name = "importobot"
    if frame and frame.f_globals.get("__name__"):
        module_name = frame.f_globals["__name__"]
    return module_name


def get_logger(name: str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with optional automatic module detection."""
    resolved_name = name or _detect_caller_module()
    cached = _LOGGER_CACHE.get(resolved_name)
    if cached is not None and cached.level == level:
        return cached

    logger = _configure_logger(resolved_name, level)
    _LOGGER_CACHE[resolved_name] = logger
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
    message = f"Exception occurred: {type(exception).__name__}: {exception!s}"
    if context:
        message = f"{context} - {message}"
    logger.exception(message)


# Exported helpers
__all__ = ["get_logger", "log_exception"]
