"""Tests for logging utilities."""

import importlib
import logging
from typing import Any
from unittest.mock import Mock

from importobot.utils.logging import get_logger, log_exception


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_logger_creation(self) -> None:
        """Test that a logger is created with the correct name and level."""
        logger = get_logger("test_logger", level=logging.DEBUG)
        assert logger.name == "test_logger"
        assert logger.level == logging.DEBUG

    def test_handler_added_once(self) -> None:
        """Test that a handler is added only once for the same logger name."""
        # Reset logging to ensure a clean state
        logging.shutdown()
        reload(logging)

        logger1 = get_logger("singleton_logger")
        assert len(logger1.handlers) == 1

        logger2 = get_logger("singleton_logger")
        assert len(logger2.handlers) == 1


class TestLogException:
    """Tests for the log_exception function."""

    def test_log_exception(self) -> None:
        """Test that an exception is logged with the correct message and context."""
        mock_logger = Mock()
        exception = ValueError("Test error")

        log_exception(mock_logger, exception, context="Test context")

        mock_logger.exception.assert_called_once_with(
            "Test context - Exception occurred: ValueError: Test error"
        )

    def test_log_exception_no_context(self) -> None:
        """Test that an exception is logged without context."""
        mock_logger = Mock()
        exception = ValueError("Test error")

        log_exception(mock_logger, exception)

        mock_logger.exception.assert_called_once_with(
            "Exception occurred: ValueError: Test error"
        )


# Helper to reload logging module for test isolation
def reload(module: Any) -> None:
    """Reload a module."""
    importlib.reload(module)
