"""Reusable progress reporting utilities."""

import logging
from collections.abc import Callable
from typing import Any

from importobot.utils.defaults import PROGRESS_CONFIG
from importobot.utils.logging import get_logger


class ProgressReporter:
    """Utility class for consistent progress reporting across operations."""

    def __init__(
        self, logger: logging.Logger | None = None, operation_name: str = "operation"
    ):
        """Initialize progress reporter.

        Args:
            logger: Logger instance to use for reporting. If None, creates default.
            operation_name: Name of the operation being tracked.
        """
        self.logger = logger or get_logger()
        self.operation_name = operation_name
        self.total_items = 0
        self.completed_items = 0
        self.milestone_percentage = PROGRESS_CONFIG.progress_report_percentage
        self.last_reported_milestone = 0

    def initialize(
        self, total_items: int, milestone_percentage: int | None = None
    ) -> None:
        """Initialize progress tracking for a new operation.

        Args:
            total_items: Total number of items to process
            milestone_percentage: Progress report percentage interval (default: config)
        """
        self.total_items = total_items
        self.completed_items = 0
        self.last_reported_milestone = 0
        if milestone_percentage is not None:
            self.milestone_percentage = milestone_percentage

        self.logger.info(
            f"Starting {self.operation_name}: {total_items} items to process"
        )

    def update(self, increment: int = 1) -> None:
        """Update progress and report if milestone reached.

        Args:
            increment: Number of items completed in this update
        """
        self.completed_items += increment

        if self.total_items > 0:
            progress_percent = (self.completed_items / self.total_items) * 100
            milestone = (
                int(progress_percent // self.milestone_percentage)
                * self.milestone_percentage
            )

            # Report progress at milestones or completion
            if (
                milestone > self.last_reported_milestone and milestone > 0
            ) or self.completed_items == self.total_items:
                self.logger.info(
                    f"Progress: {self.completed_items}/{self.total_items} "
                    f"({progress_percent:.1f}%) for {self.operation_name}"
                )
                self.last_reported_milestone = milestone

    def complete(self) -> None:
        """Mark operation as complete."""
        if self.total_items > 0:
            self.logger.info(
                f"Completed {self.operation_name}: {self.completed_items}/"
                f"{self.total_items} items processed"
            )


class BatchProgressReporter(ProgressReporter):
    """Specialized progress reporter for batch operations like file writing."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        operation_name: str = "batch_operation",
    ):
        """Initialize batch progress reporter."""
        super().__init__(logger, operation_name)
        self.batch_threshold = PROGRESS_CONFIG.file_write_progress_threshold
        self.batch_interval = PROGRESS_CONFIG.file_write_progress_interval

    def should_report_batch_progress(self, batch_size: int, current_index: int) -> bool:
        """Determine if batch progress should be reported.

        Args:
            batch_size: Total size of the batch
            current_index: Current index in the batch (1-based)

        Returns:
            True if progress should be reported
        """
        return (
            batch_size > self.batch_threshold
            and current_index % self.batch_interval == 0
        )

    def report_batch_progress(self, current_index: int, batch_size: int) -> None:
        """Report progress for batch operations.

        Args:
            current_index: Current index in the batch (1-based)
            batch_size: Total size of the batch
        """
        if self.should_report_batch_progress(batch_size, current_index):
            progress_percent = (current_index / batch_size) * 100
            self.logger.info(
                f"{self.operation_name}: {current_index}/{batch_size} "
                f"({progress_percent:.1f}%)"
            )


def with_progress_reporting(
    total_items: int,
    operation_name: str = "operation",
    logger: logging.Logger | None = None,
    milestone_percentage: int | None = None,
) -> Callable[..., Any]:
    """Add progress reporting to functions.

    Args:
        total_items: Total number of items to process
        operation_name: Name of the operation
        logger: Logger instance to use
        milestone_percentage: Progress reporting interval

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            injected_reporter = kwargs.pop("reporter", None)
            reporter = injected_reporter or ProgressReporter(logger, operation_name)
            reporter.initialize(total_items, milestone_percentage)

            try:
                result = func(reporter, *args, **kwargs)
                reporter.complete()
                return result
            except Exception as e:
                reporter.logger.error("Error in %s: %s", operation_name, e)
                raise

        return wrapper

    return decorator


def create_progress_callback(reporter: ProgressReporter) -> Callable[[int], None]:
    """Create a progress callback function for use with other functions.

    Args:
        reporter: ProgressReporter instance

    Returns:
        Callback function that accepts increment value
    """
    return reporter.update
