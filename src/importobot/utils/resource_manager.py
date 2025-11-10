"""Resource management and limits for test generation operations."""

import os
import time
from dataclasses import dataclass
from typing import Any

import psutil

from importobot.utils.logging import get_logger


@dataclass
class ResourceLimits:
    """Configuration class for resource limits."""

    max_total_tests: int = 50000
    max_file_size_mb: int = 100
    max_memory_usage_mb: int = 500
    max_disk_usage_gb: int = 10
    max_execution_time_minutes: int = 60
    max_files_per_directory: int = 10000
    max_concurrent_operations: int = 10


class ResourceOperation:
    """Context manager for individual resource-managed operations."""

    def __init__(self, manager: "ResourceManager", operation_name: str):
        """Initialize resource operation context manager."""
        self.manager = manager
        self.operation_name = operation_name
        self.operation_id: str | None = None

    def __enter__(self) -> str:
        """Enter context manager and start operation."""
        self.operation_id = self.manager.start_operation(self.operation_name)
        return self.operation_id

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and finish operation."""
        if self.operation_id:
            self.manager.finish_operation(self.operation_id)


class ResourceManager:
    """Manages and enforces resource limits for test generation operations."""

    _instance = None
    _initialized = False

    def __new__(cls, limits: ResourceLimits | None = None) -> "ResourceManager":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, limits: ResourceLimits | None = None):
        """Initialize resource manager with configurable limits."""
        if self._initialized:
            return

        self.limits = limits or ResourceLimits()
        self.logger = get_logger()
        # Track per-operation baselines for correct time enforcement
        self._operation_start_times: dict[str, float] = {}
        self._operation_counter: int = 0
        self._active_operations = 0
        self._total_files_generated = 0
        self._total_disk_usage_mb: float = 0
        self._current_operation_id: str | None = None
        self._initialized = True

    def __enter__(self) -> "ResourceManager":
        """Enter context manager - start a default operation."""
        self._current_operation_id = self.start_operation("context_managed")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager - finish the current operation."""
        if self._current_operation_id:
            self.finish_operation(self._current_operation_id)
            self._current_operation_id = None

    def operation(self, name: str) -> ResourceOperation:
        """Create a context manager for a named operation."""
        return ResourceOperation(self, name)

    def validate_generation_request(self, total_tests: int, output_dir: str) -> None:
        """Validate a test generation request against resource limits."""
        validation_errors: list[str] = []

        self._validate_test_count(total_tests, validation_errors)
        self._validate_disk_space(total_tests, output_dir, validation_errors)
        self._validate_memory_usage(total_tests, validation_errors)

        if validation_errors:
            raise ValueError(
                f"Resource validation failed: {'; '.join(validation_errors)}"
            )

        self.logger.info("Resource validation passed for %d tests", total_tests)

    def _validate_test_count(
        self, total_tests: int, validation_errors: list[str]
    ) -> None:
        """Validate test count against limits."""
        if total_tests <= 0:
            validation_errors.append("total_tests must be greater than 0")
        elif total_tests > self.limits.max_total_tests:
            validation_errors.append(
                f"Requested {total_tests} tests exceeds maximum allowed "
                f"{self.limits.max_total_tests}"
            )

    def _validate_disk_space(
        self, total_tests: int, output_dir: str, validation_errors: list[str]
    ) -> None:
        """Validate disk space requirements."""
        try:
            disk_usage = psutil.disk_usage(output_dir)
            available_gb = disk_usage.free / (1024**3)
            estimated_usage_gb = (total_tests * 5) / 1024  # 5KB per test

            if estimated_usage_gb > available_gb:
                validation_errors.append(
                    f"Estimated disk usage {estimated_usage_gb:.2f}GB exceeds "
                    f"available space {available_gb:.2f}GB"
                )
            elif estimated_usage_gb > self.limits.max_disk_usage_gb:
                validation_errors.append(
                    f"Estimated disk usage {estimated_usage_gb:.2f}GB exceeds "
                    f"limit {self.limits.max_disk_usage_gb}GB"
                )
        except (OSError, AttributeError) as e:
            self.logger.warning("Could not check disk usage: %s", e)

    def _validate_memory_usage(
        self, total_tests: int, validation_errors: list[str]
    ) -> None:
        """Validate memory usage requirements."""
        try:
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024**2)
            estimated_memory_mb = total_tests * 0.1  # 100KB per test

            if estimated_memory_mb > available_mb:
                validation_errors.append(
                    f"Estimated memory usage {estimated_memory_mb:.2f}MB exceeds "
                    f"available memory {available_mb:.2f}MB"
                )
            elif estimated_memory_mb > self.limits.max_memory_usage_mb:
                validation_errors.append(
                    f"Estimated memory usage {estimated_memory_mb:.2f}MB exceeds "
                    f"limit {self.limits.max_memory_usage_mb}MB"
                )
        except (OSError, AttributeError) as e:
            self.logger.warning("Could not check memory usage: %s", e)

    def start_operation(self, operation_name: str) -> str:
        """Start tracking an operation."""
        if self._active_operations >= self.limits.max_concurrent_operations:
            max_ops = self.limits.max_concurrent_operations
            raise RuntimeError(
                f"Maximum concurrent operations ({max_ops}) already running"
            )

        # Generate a unique, stable operation id
        self._operation_counter += 1
        operation_id = f"{operation_name}_{int(time.time())}_{self._operation_counter}"
        self._active_operations += 1
        # Record a per-operation baseline using wall-clock time (deterministic)
        self._operation_start_times[operation_id] = time.time()

        self.logger.info(
            "Started operation '%s' (%d/%d active)",
            operation_id,
            self._active_operations,
            self.limits.max_concurrent_operations,
        )

        return operation_id

    def check_operation_limits(self, operation_id: str) -> None:
        """Check if operation is within resource limits."""
        start_time = self._operation_start_times.get(operation_id)
        if start_time is None:
            return

        # Check execution time
        now = time.time()
        elapsed_seconds = now - start_time
        # Safety bounds: guard against clock adjustments producing negative elapsed
        if elapsed_seconds < 0:
            # Reset baseline to now to avoid spurious timeouts
            self._operation_start_times[operation_id] = now
            elapsed_seconds = 0
        elapsed_minutes = elapsed_seconds / 60
        if elapsed_minutes > self.limits.max_execution_time_minutes:
            self.finish_operation(operation_id)
            raise RuntimeError(
                f"Operation '{operation_id}' exceeded maximum execution time "
                f"({self.limits.max_execution_time_minutes} minutes)"
            )

        # Check memory usage
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024**2)
            if memory_mb > self.limits.max_memory_usage_mb:
                self.logger.warning(
                    "Operation '%s' memory usage %.2fMB exceeds limit %dMB",
                    operation_id,
                    memory_mb,
                    self.limits.max_memory_usage_mb,
                )
        except (psutil.NoSuchProcess, AttributeError):
            pass

    def finish_operation(self, operation_id: str) -> None:
        """Finish tracking an operation."""
        if self._active_operations > 0:
            self._active_operations -= 1

        elapsed_time: float = 0
        start_time = self._operation_start_times.pop(operation_id, None)
        if start_time is not None:
            now = time.time()
            elapsed_time = max(0.0, now - start_time)

        self.logger.info(
            "Finished operation '%s' in %.2fs (%d active operations remaining)",
            operation_id,
            elapsed_time,
            self._active_operations,
        )

    def validate_file_operation(
        self, file_path: str, estimated_size_mb: float = 0
    ) -> None:
        """Validate a file operation against resource limits."""
        # Check file size limit
        if estimated_size_mb > self.limits.max_file_size_mb:
            raise ValueError(
                f"File size {estimated_size_mb:.2f}MB exceeds limit "
                f"{self.limits.max_file_size_mb}MB"
            )

        # Check directory file count
        try:
            directory = os.path.dirname(file_path)
            if os.path.exists(directory):
                file_count = len(
                    [
                        f
                        for f in os.listdir(directory)
                        if os.path.isfile(os.path.join(directory, f))
                    ]
                )
                if file_count >= self.limits.max_files_per_directory:
                    raise ValueError(
                        f"Directory {directory} has {file_count} files, "
                        f"exceeding limit {self.limits.max_files_per_directory}"
                    )
        except (OSError, PermissionError) as e:
            self.logger.warning("Could not check directory file count: %s", e)

    def track_file_generated(self, file_path: str, size_mb: float) -> None:
        """Track a generated file."""
        self._total_files_generated += 1
        self._total_disk_usage_mb += size_mb

        # Log file path for debugging if needed
        _ = file_path  # Mark as used to avoid lint warning

        if self._total_files_generated % 100 == 0:  # Log every 100 files
            self.logger.info(
                "Generated %d files, total disk usage: %.2fMB",
                self._total_files_generated,
                self._total_disk_usage_mb,
            )

    def get_resource_stats(self) -> dict[str, Any]:
        """Get current resource usage statistics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
        except psutil.AccessDenied as e:
            self.logger.error("Access denied getting system resource info: %s", e)
            return {"error": f"Permission denied accessing system resources: {e}"}
        except FileNotFoundError as e:
            self.logger.error("File system path not found: %s", e)
            return {"error": f"File system error: {e}"}
        except OSError as e:
            self.logger.error("System error getting resource stats: %s", e)
            return {"error": f"System I/O error: {e}"}
        except RuntimeError as e:
            self.logger.error("Runtime error in resource monitoring: %s", e)
            return {"error": f"Resource monitoring unavailable: {e}"}
        except AttributeError as e:
            self.logger.error("psutil object missing expected attributes: %s", e)
            return {"error": f"System monitoring corrupted: {e}"}
        except Exception as e:
            self.logger.error("Unexpected error getting resource stats: %s", e)
            return {"error": f"Unexpected system error: {e}"}

        return {
            "active_operations": self._active_operations,
            "files_generated": self._total_files_generated,
            "disk_usage_mb": self._total_disk_usage_mb,
            "system_memory_percent": memory.percent,
            "system_disk_percent": disk.percent,
            "limits": {
                "max_total_tests": self.limits.max_total_tests,
                "max_file_size_mb": self.limits.max_file_size_mb,
                "max_memory_usage_mb": self.limits.max_memory_usage_mb,
                "max_disk_usage_gb": self.limits.max_disk_usage_gb,
                "max_execution_time_minutes": self.limits.max_execution_time_minutes,
            },
        }

    def reset_stats(self) -> None:
        """Reset internal tracking statistics."""
        self._total_files_generated = 0
        self._total_disk_usage_mb = 0
        self.logger.info("Resource tracking statistics reset")

    def configure_limits(self, **kwargs: Any) -> None:
        """Configure resource limits."""
        self.limits = ResourceLimits(**kwargs)
        self.logger.info("Resource limits configured: %s", self.limits)

    @classmethod
    def _reset_singleton(cls) -> None:
        """Reset singleton instance for testing."""
        cls._instance = None
        cls._initialized = False


def get_resource_manager() -> ResourceManager:
    """Get the singleton resource manager instance."""
    return ResourceManager()


def configure_resource_limits(**kwargs: Any) -> None:
    """Configure resource limits on the singleton instance."""
    manager = ResourceManager()
    manager.configure_limits(**kwargs)
