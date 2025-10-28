"""Unit tests for resource manager functionality."""

# pylint: disable=protected-access

import tempfile
from functools import wraps
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from importobot.utils.resource_manager import (
    ResourceLimits,
    ResourceManager,
    ResourceOperation,
    configure_resource_limits,
    get_resource_manager,
)


def reset_resource_manager_singleton(func):
    """Decorator to reset ResourceManager singleton before test execution."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        ResourceManager._reset_singleton()
        return func(*args, **kwargs)

    return wrapper


class TestResourceLimits:
    """Test ResourceLimits dataclass."""

    def test_default_limits(self):
        """Test default resource limits."""
        limits = ResourceLimits()
        assert limits.max_total_tests == 50000
        assert limits.max_file_size_mb == 100
        assert limits.max_memory_usage_mb == 500
        assert limits.max_disk_usage_gb == 10
        assert limits.max_execution_time_minutes == 60
        assert limits.max_files_per_directory == 10000
        assert limits.max_concurrent_operations == 10

    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_total_tests=1000, max_file_size_mb=50, max_memory_usage_mb=200
        )
        assert limits.max_total_tests == 1000
        assert limits.max_file_size_mb == 50
        assert limits.max_memory_usage_mb == 200
        # Other values should remain default
        assert limits.max_disk_usage_gb == 10


class TestResourceManager:
    """Test ResourceManager functionality."""

    def setup_method(self):
        """Reset singleton before each test."""
        ResourceManager._reset_singleton()

    def test_initialization(self):
        """Test ResourceManager initialization."""
        manager = ResourceManager()
        assert manager.limits is not None
        assert manager._active_operations == 0
        assert manager._total_files_generated == 0
        assert manager._total_disk_usage_mb == 0
        assert manager._current_operation_id is None

    @reset_resource_manager_singleton
    def test_initialization_with_custom_limits(self):
        """Test ResourceManager initialization with custom limits."""
        custom_limits = ResourceLimits(max_total_tests=1000)
        manager = ResourceManager(custom_limits)
        assert manager.limits.max_total_tests == 1000

    def test_context_manager_basic(self):
        """Test basic context manager functionality."""
        manager = ResourceManager()

        with manager as ctx_manager:
            assert ctx_manager is manager
            assert manager._current_operation_id is not None
            assert manager._active_operations == 1

        # After exiting context, operation should be finished
        assert manager._current_operation_id is None
        assert manager._active_operations == 0

    def test_context_manager_with_exception(self):
        """Test context manager handles exceptions properly."""
        manager = ResourceManager()

        with pytest.raises(ValueError), manager as _ctx_manager:
            assert manager._active_operations == 1
            raise ValueError("Test exception")

        # Even with exception, cleanup should occur
        assert manager._current_operation_id is None
        assert manager._active_operations == 0

    def test_named_operation_context_manager(self):
        """Test named operation context manager."""
        manager = ResourceManager()

        with manager.operation("test_operation") as operation_id:
            assert isinstance(operation_id, str)
            assert "test_operation" in operation_id
            assert manager._active_operations == 1

        assert manager._active_operations == 0

    def test_start_and_finish_operation(self):
        """Test manual operation start and finish."""
        manager = ResourceManager()

        operation_id = manager.start_operation("manual_test")
        assert operation_id is not None
        assert manager._active_operations == 1

        manager.finish_operation(operation_id)
        assert manager._active_operations == 0

    @reset_resource_manager_singleton
    def test_concurrent_operations_limit(self):
        """Test concurrent operations limit enforcement."""
        limits = ResourceLimits(max_concurrent_operations=2)
        manager = ResourceManager(limits)

        # Start two operations (should work)
        op1 = manager.start_operation("op1")
        op2 = manager.start_operation("op2")
        assert manager._active_operations == 2

        # Third operation should raise error
        with pytest.raises(RuntimeError, match="Maximum concurrent operations"):
            manager.start_operation("op3")

        # Clean up
        manager.finish_operation(op1)
        manager.finish_operation(op2)

    @patch("psutil.disk_usage")
    def test_validate_generation_request_disk_space(self, mock_disk_usage):
        """Test validation of generation request for disk space."""
        # Mock disk usage to show limited space
        mock_disk_usage.return_value = MagicMock(free=1024**3)  # 1GB free

        manager = ResourceManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Request that would exceed available space
            with pytest.raises(ValueError, match="exceeds available space"):
                manager.validate_generation_request(1000000, temp_dir)

    @patch("psutil.virtual_memory")
    def test_validate_generation_request_memory(self, mock_memory):
        """Test validation of generation request for memory."""
        # Mock memory to show limited available memory
        mock_memory.return_value = MagicMock(available=50 * 1024**2)  # 50MB available

        manager = ResourceManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Request that would exceed available memory
            with pytest.raises(ValueError, match="exceeds available memory"):
                manager.validate_generation_request(1000000, temp_dir)

    @reset_resource_manager_singleton
    def test_validate_generation_request_total_tests_limit(self):
        """Test validation of total tests limit."""
        limits = ResourceLimits(max_total_tests=100)
        manager = ResourceManager(limits)

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="exceeds maximum allowed"):
                manager.validate_generation_request(200, temp_dir)

    def test_validate_generation_request_invalid_count(self):
        """Test validation with invalid test count."""
        manager = ResourceManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="must be greater than 0"):
                manager.validate_generation_request(0, temp_dir)

            with pytest.raises(ValueError, match="must be greater than 0"):
                manager.validate_generation_request(-5, temp_dir)

    @reset_resource_manager_singleton
    def test_validate_file_operation_size_limit(self):
        """Test file operation validation for size limits."""
        limits = ResourceLimits(max_file_size_mb=10)
        manager = ResourceManager(limits)

        with pytest.raises(ValueError, match=r"File size.*exceeds limit"):
            manager.validate_file_operation("/tmp/test.txt", 20)

    @reset_resource_manager_singleton
    def test_validate_file_operation_directory_limit(self):
        """Test file operation validation for directory file count."""
        limits = ResourceLimits(max_files_per_directory=2)
        manager = ResourceManager(limits)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files to exceed limit
            for i in range(3):
                (Path(temp_dir) / f"file{i}.txt").write_text("test")

            test_file = Path(temp_dir) / "new_file.txt"
            with pytest.raises(ValueError, match="exceeding limit"):
                manager.validate_file_operation(str(test_file))

    def test_track_file_generated(self):
        """Test file generation tracking."""
        manager = ResourceManager()

        manager.track_file_generated("/tmp/test1.txt", 5.0)
        assert manager._total_files_generated == 1
        assert manager._total_disk_usage_mb == 5.0

        manager.track_file_generated("/tmp/test2.txt", 3.5)
        assert manager._total_files_generated == 2
        assert manager._total_disk_usage_mb == 8.5

    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_get_resource_stats(self, mock_disk_usage, mock_memory):
        """Test resource statistics retrieval."""
        mock_memory.return_value = MagicMock(percent=75.5)
        mock_disk_usage.return_value = MagicMock(percent=45.2)

        manager = ResourceManager()
        manager.track_file_generated("/tmp/test.txt", 10.0)

        stats = manager.get_resource_stats()

        assert stats["active_operations"] == 0
        assert stats["files_generated"] == 1
        assert stats["disk_usage_mb"] == 10.0
        assert stats["system_memory_percent"] == 75.5
        assert stats["system_disk_percent"] == 45.2
        assert "limits" in stats

    def test_reset_stats(self):
        """Test statistics reset functionality."""
        manager = ResourceManager()

        manager.track_file_generated("/tmp/test.txt", 5.0)
        assert manager._total_files_generated == 1
        assert manager._total_disk_usage_mb == 5.0

        manager.reset_stats()
        assert manager._total_files_generated == 0
        assert manager._total_disk_usage_mb == 0

    @reset_resource_manager_singleton
    @patch("time.time")
    def test_check_operation_limits_timeout(self, mock_time):
        """Test operation timeout checking."""
        limits = ResourceLimits(max_execution_time_minutes=1)  # 1 minute timeout
        manager = ResourceManager(limits)

        # Start operation
        mock_time.return_value = 1000
        operation_id = manager.start_operation("timeout_test")

        # Simulate time passing beyond limit
        mock_time.return_value = 1000 + 70  # 70 seconds = over 1 minute

        with pytest.raises(RuntimeError, match="exceeded maximum execution time"):
            manager.check_operation_limits(operation_id)

    @reset_resource_manager_singleton
    @patch("psutil.Process")
    def test_check_operation_limits_memory(self, mock_process_class):
        """Test operation memory limit checking."""
        limits = ResourceLimits(max_memory_usage_mb=100)
        manager = ResourceManager(limits)

        # Mock process memory usage exceeding limit
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=200 * 1024**2)  # 200MB
        mock_process_class.return_value = mock_process

        operation_id = manager.start_operation("memory_test")

        # Should log warning but not raise exception for memory
        manager.check_operation_limits(operation_id)

        manager.finish_operation(operation_id)


class TestResourceOperation:
    """Test ResourceOperation context manager."""

    def test_resource_operation_basic(self):
        """Test basic ResourceOperation functionality."""
        manager = ResourceManager()
        operation = ResourceOperation(manager, "test_op")

        with operation as operation_id:
            assert isinstance(operation_id, str)
            assert "test_op" in operation_id
            assert manager._active_operations == 1

        assert manager._active_operations == 0

    def test_resource_operation_exception_handling(self):
        """Test ResourceOperation handles exceptions properly."""
        manager = ResourceManager()
        operation = ResourceOperation(manager, "test_op")

        with pytest.raises(ValueError), operation as _operation_id:
            assert manager._active_operations == 1
            raise ValueError("Test exception")

        # Should still clean up after exception
        assert manager._active_operations == 0


class TestGlobalResourceManager:
    """Test global resource manager functions."""

    def test_get_resource_manager_singleton(self):
        """Test global resource manager is singleton."""
        manager1 = get_resource_manager()
        manager2 = get_resource_manager()
        assert manager1 is manager2

    def test_configure_resource_limits(self):
        """Test global resource limits configuration."""
        configure_resource_limits(max_total_tests=5000, max_file_size_mb=25)
        manager = get_resource_manager()
        assert manager.limits.max_total_tests == 5000
        assert manager.limits.max_file_size_mb == 25


class TestResourceManagerIntegration:
    """Integration tests for ResourceManager."""

    def test_real_file_operations(self):
        """Test ResourceManager with real file operations."""
        manager = ResourceManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"

            # Should pass validation
            manager.validate_file_operation(str(test_file), 1.0)

            # Create file and track it
            test_file.write_text("test content")
            file_size_mb = test_file.stat().st_size / (1024**2)
            manager.track_file_generated(str(test_file), file_size_mb)

            assert manager._total_files_generated == 1
            assert manager._total_disk_usage_mb > 0

    def test_context_manager_with_real_operations(self):
        """Test context manager with real operations."""
        manager = ResourceManager()

        with manager.operation("integration_test") as operation_id:
            # Simulate some work
            with tempfile.NamedTemporaryFile() as temp_file:
                manager.validate_file_operation(temp_file.name, 0.1)
                manager.track_file_generated(temp_file.name, 0.1)

            # Check that operation is active
            assert manager._active_operations == 1

            # Check operation limits (should not raise)
            manager.check_operation_limits(operation_id)

        # After context exit, should be cleaned up
        assert manager._active_operations == 0
