"""Tests for progress reporting utilities."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from importobot.utils.progress_reporter import (
    BatchProgressReporter,
    ProgressReporter,
    create_progress_callback,
    with_progress_reporting,
)


class TestProgressReporter:
    """Test ProgressReporter class."""

    def test_initialization_with_default_logger(self) -> None:
        """Test initialization with default logger."""
        reporter = ProgressReporter()

        assert reporter.operation_name == "operation"
        assert reporter.logger is not None
        assert reporter.total_items == 0
        assert reporter.completed_items == 0
        assert reporter.last_reported_milestone == 0

    def test_initialization_with_custom_logger_and_name(self) -> None:
        """Test initialization with custom logger and operation name."""
        custom_logger = logging.getLogger("custom")
        reporter = ProgressReporter(custom_logger, "custom_operation")

        assert reporter.operation_name == "custom_operation"
        assert reporter.logger == custom_logger

    def test_initialize_with_basic_params(self) -> None:
        """Test initialize method with basic parameters."""
        reporter = ProgressReporter()
        reporter.initialize(100)

        assert reporter.total_items == 100
        assert reporter.completed_items == 0
        assert reporter.last_reported_milestone == 0

    def test_initialize_with_custom_milestone(self) -> None:
        """Test initialize method with custom milestone percentage."""
        reporter = ProgressReporter()
        reporter.initialize(100, milestone_percentage=25)

        assert reporter.milestone_percentage == 25

    def test_initialize_logs_start_message(self) -> None:
        """Test that initialize logs the start message."""
        reporter = ProgressReporter()
        with patch.object(reporter.logger, "info") as mock_info:
            reporter.initialize(50, milestone_percentage=20)

            mock_info.assert_called_once_with("Starting operation: 50 items to process")

    def test_update_single_item(self) -> None:
        """Test update method with single item increment."""
        reporter = ProgressReporter()
        reporter.initialize(10)

        reporter.update(1)

        assert reporter.completed_items == 1

    def test_update_multiple_items(self) -> None:
        """Test update method with multiple item increment."""
        reporter = ProgressReporter()
        reporter.initialize(10)

        reporter.update(3)

        assert reporter.completed_items == 3

    def test_update_progress_reporting_at_milestones(self) -> None:
        """Test that progress is reported at milestone percentages."""
        reporter = ProgressReporter()
        reporter.initialize(100, milestone_percentage=25)

        with patch.object(reporter.logger, "info") as mock_info:
            # Update to 25% (25 items)
            for _ in range(25):
                reporter.update(1)

            # Update to 50% (25 more items)
            for _ in range(25):
                reporter.update(1)

            # Update to 75% (25 more items)
            for _ in range(25):
                reporter.update(1)

            # Update to 100% (25 more items)
            for _ in range(25):
                reporter.update(1)

            progress_calls = [
                call for call in mock_info.call_args_list if "Progress:" in str(call)
            ]
            assert len(progress_calls) == 4  # 25%, 50%, 75%, 100%

    def test_complete_logs_completion_message(self) -> None:
        """Test that complete logs the completion message."""
        reporter = ProgressReporter()
        reporter.initialize(50)
        reporter.update(50)

        with patch.object(reporter.logger, "info") as mock_info:
            reporter.complete()

            mock_info.assert_called_once_with(
                "Completed operation: 50/50 items processed"
            )

    def test_complete_no_message_for_zero_total(self) -> None:
        """Test that complete doesn't log for zero total items."""
        reporter = ProgressReporter()
        reporter.initialize(0)

        with patch.object(reporter.logger, "info") as mock_info:
            reporter.complete()

            mock_info.assert_not_called()


class TestBatchProgressReporter:
    """Test BatchProgressReporter class."""

    def test_initialization_inherits_from_progress_reporter(self) -> None:
        """Test that BatchProgressReporter inherits from ProgressReporter."""
        reporter = BatchProgressReporter()

        assert isinstance(reporter, ProgressReporter)
        assert hasattr(reporter, "batch_threshold")
        assert hasattr(reporter, "batch_interval")

    def test_should_report_batch_progress_large_batch_at_interval(self) -> None:
        """Test should_report_batch_progress for large batch at interval."""
        reporter = BatchProgressReporter()

        # Large batch (100 > threshold), at interval (20 % 20 == 0)
        result = reporter.should_report_batch_progress(100, 20)

        assert result is True

    def test_should_report_batch_progress_small_batch(self) -> None:
        """Test should_report_batch_progress for small batch."""
        reporter = BatchProgressReporter()

        # Small batch (5 < threshold)
        result = reporter.should_report_batch_progress(5, 5)

        assert result is False

    def test_should_report_batch_progress_not_at_interval(self) -> None:
        """Test should_report_batch_progress not at interval."""
        reporter = BatchProgressReporter()

        # Large batch but not at interval (47 % 10 != 0)
        result = reporter.should_report_batch_progress(100, 47)

        assert result is False

    def test_report_batch_progress_logs_message(self) -> None:
        """Test report_batch_progress logs the correct message."""
        reporter = BatchProgressReporter(operation_name="file_processing")

        with patch.object(reporter.logger, "info") as mock_info:
            reporter.report_batch_progress(20, 100)  # 20 % 20 == 0, so it should report

            mock_info.assert_called_once_with("file_processing: 20/100 (20.0%)")

    def test_report_batch_progress_no_message_when_not_should_report(self) -> None:
        """Test report_batch_progress doesn't log when "
        "should_report_batch_progress is False."""
        reporter = BatchProgressReporter()

        with (
            patch.object(reporter, "should_report_batch_progress", return_value=False),
            patch.object(reporter.logger, "info") as mock_info,
        ):
            reporter.report_batch_progress(5, 10)

            mock_info.assert_not_called()


class TestWithProgressReporting:
    """Test with_progress_reporting decorator."""

    def test_decorator_successful_execution(self) -> None:
        """Test decorator with successful function execution."""

        @with_progress_reporting(total_items=10, operation_name="test_op")
        def test_function(reporter, x, y) -> None:
            for _ in range(10):
                reporter.update(1)
            return x + y

        with patch(
            "importobot.utils.progress_reporter.ProgressReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter_class.return_value = mock_reporter

            result = test_function(
                reporter=mock_reporter,
                x=3,
                y=4,
            )

            assert result == 7
            mock_reporter.initialize.assert_called_once_with(10, None)
            mock_reporter.complete.assert_called_once()

    def test_decorator_with_exception(self) -> None:
        """Test decorator handles exceptions properly."""

        @with_progress_reporting(total_items=5, operation_name="failing_op")
        def failing_function(reporter):
            raise ValueError("Test error")

        with patch(
            "importobot.utils.progress_reporter.ProgressReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter_class.return_value = mock_reporter

            with pytest.raises(ValueError, match="Test error"):
                failing_function(
                    reporter=mock_reporter,
                )

            mock_reporter.initialize.assert_called_once()
            mock_reporter.logger.error.assert_called_once()
            args = mock_reporter.logger.error.call_args[0]
            assert args[0] == "Error in %s: %s"
            assert args[1] == "failing_op"
            assert isinstance(args[2], ValueError)
            assert str(args[2]) == "Test error"

    def test_decorator_with_custom_logger_and_milestone(self) -> None:
        """Test decorator with custom logger and milestone percentage."""
        custom_logger = logging.getLogger("custom")

        @with_progress_reporting(
            total_items=20,
            operation_name="custom_op",
            logger=custom_logger,
            milestone_percentage=25,
        )
        def custom_function(reporter):
            _ = reporter  # Mark as used
            return "done"

        with patch(
            "importobot.utils.progress_reporter.ProgressReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter_class.return_value = mock_reporter

            result = custom_function(
                reporter=mock_reporter,
            )

            assert result == "done"
            mock_reporter.initialize.assert_called_once_with(20, 25)


class TestCreateProgressCallback:
    """Test create_progress_callback function."""

    def test_create_progress_callback_returns_callable(self) -> None:
        """Test create_progress_callback returns a callable."""
        reporter = ProgressReporter()
        callback = create_progress_callback(reporter)

        assert callable(callback)

    def test_create_progress_callback_calls_update(self) -> None:
        """Test that the callback calls reporter.update."""
        reporter = ProgressReporter()
        callback = create_progress_callback(reporter)

        callback(5)

        # Check that update was called with the increment
        # Since update is a method, we need to check it was called
        assert reporter.completed_items == 5

    def test_create_progress_callback_with_custom_increment(self) -> None:
        """Test callback with custom increment value."""
        reporter = ProgressReporter()
        callback = create_progress_callback(reporter)

        callback(3)

        assert reporter.completed_items == 3
