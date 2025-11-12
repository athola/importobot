"""
Logging and error reporting for Importobot interactive demo.

This module provides logging, error handling, and reporting
for the demo script.
"""

import json
import logging
import sys
import time
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


class ColoredConsoleFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages and removes prefixes."""

    # ANSI color codes
    COLORS = {
        "ERROR": "\033[91m",  # Red
        "WARNING": "\033[93m",  # Yellow
        "INFO": "",  # No color (default)
        "DEBUG": "\033[96m",  # Cyan
        "RESET": "\033[0m",  # Reset to default
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with color coding."""
        # Get the color for this log level
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"] if color else ""

        # Format the message without the level prefix
        message = super().format(record)

        # For ERROR and WARNING, add color; for INFO, no prefix or color
        if record.levelname in ["ERROR", "WARNING"]:
            return f"{color}{message}{reset}"
        # For INFO and DEBUG, just return the message without prefix
        return message


class DemoLogger:
    """Logger for demo operations."""

    def __init__(self, name: str = "importobot_demo", log_level: int = logging.INFO):
        """Initialize the demo logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

        self.session_start = time.time()
        self.events: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.performance_metrics: dict[str, dict[str, Any]] = {}

    def _setup_handlers(self) -> None:
        """Set up logging handlers for console and file output."""
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # File handler for detailed logs
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatters
        console_format = ColoredConsoleFormatter(
            "%(message)s"
        )  # No prefix, just message
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler.setFormatter(console_format)
        file_handler.setFormatter(file_format)

        # Set up handlers for the main logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        # Also set up handlers for the security logger to prevent
        # duplicate configuration
        security_logger = logging.getLogger("demo_security")
        if not security_logger.handlers:
            security_logger.addHandler(console_handler)
            security_logger.addHandler(file_handler)
            security_logger.setLevel(self.logger.level)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with optional structured data."""
        self.logger.info(message)
        self._log_event("info", message, kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with optional structured data."""
        self.logger.warning(message)
        self._log_event("warning", message, kwargs)

    def error(
        self, message: str, exception: Exception | None = None, **kwargs: Any
    ) -> None:
        """Log error message with optional exception details."""
        if exception:
            self.logger.error("%s: %s", message, exception)
            self.errors.append(
                {
                    "message": message,
                    "exception": str(exception),
                    "traceback": traceback.format_exc(),
                    "timestamp": time.time(),
                    "context": kwargs,
                }
            )
        else:
            self.logger.error(message)
        self._log_event("error", message, kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with optional structured data."""
        self.logger.debug(message)
        self._log_event("debug", message, kwargs)

    def _log_event(self, level: str, message: str, context: dict[str, Any]) -> None:
        """Log structured event data."""
        event = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "context": context,
        }
        self.events.append(event)

    def log_performance(self, operation: str, duration: float, **metrics: Any) -> None:
        """Log performance metrics for an operation."""
        self.performance_metrics[operation] = {
            "duration_seconds": duration,
            "timestamp": time.time(),
            **metrics,
        }
        self.info(f"Performance: {operation} completed in {duration:.2f}s", **metrics)

    def log_business_impact(self, scenario: str, metrics: dict[str, float]) -> None:
        """Log business impact calculations."""
        self.info(f"Business impact calculated for {scenario}")
        self.debug(f"Business metrics: {metrics}")

    @contextmanager
    def operation_timer(self, operation_name: str) -> Iterator[None]:
        """Context manager to time operations."""
        start_time = time.time()
        self.debug(f"Starting operation: {operation_name}")
        try:
            yield
            duration = time.time() - start_time
            self.log_performance(operation_name, duration)
        except Exception as e:
            duration = time.time() - start_time
            self.error(f"Operation failed: {operation_name}", e, duration=duration)
            raise

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of the current logging session."""
        session_duration = time.time() - self.session_start

        return {
            "session_duration": session_duration,
            "total_events": len(self.events),
            "errors_count": len(self.errors),
            "performance_operations": len(self.performance_metrics),
            "event_breakdown": self._get_event_breakdown(),
            "performance_summary": self._get_performance_summary(),
        }

    def _get_event_breakdown(self) -> dict[str, int]:
        """Get breakdown of events by level."""
        breakdown: dict[str, int] = {}
        for event in self.events:
            level = event["level"]
            breakdown[level] = breakdown.get(level, 0) + 1
        return breakdown

    def _get_performance_summary(self) -> dict[str, dict[str, float]]:
        """Get summary of performance metrics."""
        summary = {}
        for operation, metrics in self.performance_metrics.items():
            summary[operation] = {
                "duration": metrics["duration_seconds"],
                "timestamp": metrics["timestamp"],
            }
        return summary

    def export_session_report(self, output_file: str | None = None) -> str:
        """Export detailed session report to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"demo_report_{timestamp}.json"

        report = {
            "session_info": {
                "start_time": self.session_start,
                "end_time": time.time(),
                "duration": time.time() - self.session_start,
            },
            "summary": self.get_session_summary(),
            "events": self.events,
            "errors": self.errors,
            "performance_metrics": self.performance_metrics,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            self.info(f"Session report exported to {output_file}")
            return output_file
        except OSError as e:
            self.error("Failed to export session report", e)
            return ""


class ErrorHandler:
    """Manages error handling for demo operations."""

    def __init__(self, logger: DemoLogger):
        """Initialize the ErrorHandler with a logger."""
        self.logger = logger
        self.error_recovery_strategies = {
            "FileNotFoundError": self._handle_file_not_found,
            "subprocess.CalledProcessError": self._handle_command_error,
            "ImportError": self._handle_import_error,
            "PermissionError": self._handle_permission_error,
        }

    def handle_error(self, error: Exception, context: str = "") -> bool:
        """
        Handle an error with appropriate recovery strategy.

        Returns True if error was handled and operation can continue.
        """
        error_type = type(error).__name__

        self.logger.error(f"Error in {context}", error)

        if error_type in self.error_recovery_strategies:
            try:
                return self.error_recovery_strategies[error_type](error, context)
            except Exception as recovery_error:
                self.logger.error(
                    f"Error recovery failed for {error_type}", recovery_error
                )
                return False
        else:
            self.logger.error(f"No recovery strategy for {error_type}")
            return False

    def _handle_file_not_found(self, _error: Exception, context: str) -> bool:
        """Handle file not found errors."""
        self.logger.warning(f"File not found in {context}, using default data")
        return True  # Can continue with sample data

    def _handle_command_error(self, _error: Exception, context: str) -> bool:
        """Handle subprocess command errors."""
        self.logger.warning(f"Command failed in {context}, showing simulated results")
        return True  # Can continue with simulated data

    def _handle_import_error(self, _error: Exception, context: str) -> bool:
        """Handle import errors."""
        self.logger.error(f"Missing dependency in {context}")
        return False  # Cannot continue without required imports

    def _handle_permission_error(self, _error: Exception, context: str) -> bool:
        """Handle permission errors."""
        self.logger.warning(f"Permission denied in {context}, skipping operation")
        return True  # Can continue by skipping the operation


class ProgressReporter:
    """Reports progress of long-running operations."""

    def __init__(
        self, logger: DemoLogger, total_steps: int, operation_name: str = "Operation"
    ):
        """Initialize ProgressReporter with logger, total steps, and operation name."""
        self.logger = logger
        self.total_steps = total_steps
        self.current_step = 0
        self.operation_name = operation_name
        self.start_time = time.time()

    def step(self, description: str = "") -> None:
        """Advance to the next step."""
        self.current_step += 1
        percentage = (self.current_step / self.total_steps) * 100

        elapsed = time.time() - self.start_time
        if self.current_step > 0:
            estimated_total = elapsed * (self.total_steps / self.current_step)
            remaining = estimated_total - elapsed
        else:
            remaining = 0

        progress_msg = (
            f"{self.operation_name}: {self.current_step}/{self.total_steps} "
            f"({percentage:.1f}%)"
        )
        if description:
            progress_msg += f" - {description}"
        if remaining > 0:
            progress_msg += f" (ETA: {remaining:.1f}s)"

        self.logger.info(progress_msg)

    def complete(self) -> None:
        """Mark operation as complete."""
        duration = time.time() - self.start_time
        self.logger.info(f"{self.operation_name} completed in {duration:.2f}s")


class BusinessMetricsReporter:
    """Reporter for business metrics and ROI calculations."""

    def __init__(self, logger: DemoLogger):
        """Initialize the BusinessMetricsReporter with a logger."""
        self.logger = logger

    def report_scenario_analysis(
        self, scenario_name: str, metrics: dict[str, float]
    ) -> None:
        """Report analysis of a business scenario."""
        self.logger.info(f"=== {scenario_name} Analysis ===")

        # Time savings
        time_savings = metrics.get("time_savings_days", 0)
        time_reduction = metrics.get("time_reduction_percent", 0)
        self.logger.info(
            f"Time Savings: {time_savings:.1f} days ({time_reduction:.1f}% reduction)"
        )

        # Cost savings
        cost_savings = metrics.get("cost_savings_usd", 0)
        self.logger.info(f"Cost Savings: ${cost_savings:,.0f}")

        # ROI
        roi = metrics.get("roi_multiplier", 0)
        if roi != float("inf"):
            self.logger.info(f"ROI: {roi:.1f}x return on investment")
        else:
            self.logger.info("ROI: Infinite (near-zero implementation cost)")

        # Speed improvement
        speed_improvement = metrics.get("speed_improvement", 0)
        if speed_improvement != float("inf"):
            self.logger.info(f"Speed Improvement: {speed_improvement:.1f}x faster")
        else:
            self.logger.info("Speed Improvement: Dramatically faster")

    def report_comparative_analysis(self, scenarios: list[dict[str, Any]]) -> None:
        """Report comparative analysis across multiple scenarios."""
        self.logger.info("=== Comparative Business Impact Analysis ===")

        for i, scenario in enumerate(scenarios):
            # Safely extract scenario name
            if (
                "scenario" in scenario
                and hasattr(scenario["scenario"], "name")
                and scenario["scenario"].name
            ):
                scenario_name = scenario["scenario"].name
            else:
                scenario_name = f"Scenario {i + 1}"

            self.logger.info(f"\n{scenario_name}:")
            metrics = scenario.get("metrics", {})

            manual_cost = metrics.get("manual_cost_usd", 0)
            auto_cost = metrics.get("importobot_cost_usd", 0)
            savings = metrics.get("cost_savings_usd", 0)

            self.logger.info(f"  Manual Cost: ${manual_cost:,.0f}")
            self.logger.info(f"  Automated Cost: ${auto_cost:,.0f}")
            self.logger.info(f"  Savings: ${savings:,.0f}")

    def report_risk_analysis(
        self, manual_success_rate: float, auto_success_rate: float, project_value: float
    ) -> None:
        """Report risk analysis comparing manual vs automated approaches."""
        self.logger.info("=== Risk Analysis ===")

        manual_failure_rate = 100 - manual_success_rate
        auto_failure_rate = 100 - auto_success_rate

        manual_risk = (manual_failure_rate / 100) * project_value
        auto_risk = (auto_failure_rate / 100) * project_value
        risk_reduction = manual_risk - auto_risk

        self.logger.info(
            f"Manual Failure Risk: {manual_failure_rate:.1f}% (${manual_risk:,.0f})"
        )
        self.logger.info(
            f"Automated Failure Risk: {auto_failure_rate:.1f}% (${auto_risk:,.0f})"
        )
        self.logger.info(f"Risk Reduction: ${risk_reduction:,.0f}")


# Global logger instance
demo_logger = DemoLogger()
error_handler = ErrorHandler(demo_logger)
metrics_reporter = BusinessMetricsReporter(demo_logger)
