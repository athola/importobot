"""
Validation and security utilities for Importobot interactive demo.

This module provides input validation, command sanitization, and security
measures to ensure safe execution of the demo script.
"""

import importlib.util
import logging
import os
import re
import subprocess
import time
from pathlib import Path

# Get logger for security events (configured by DemoLogger)
security_logger = logging.getLogger("demo_security")


class ValidationError(Exception):
    """Raised when validation fails."""


class SecurityError(Exception):
    """Raised when a security check fails."""


def validate_file_path(
    file_path: str,
    must_exist: bool = False,
    allowed_extensions: list[str] | None = None,
) -> bool:
    """
    Validate a file path for security and correctness.

    Args:
        file_path: Path to validate
        must_exist: Whether the file must already exist
        allowed_extensions: List of allowed file extensions (e.g., ['.json', '.robot'])

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not file_path or not isinstance(file_path, str):
        raise ValidationError("File path must be a non-empty string")

    # Check for path traversal attempts
    if ".." in file_path or file_path.startswith("/"):
        if not file_path.startswith("/tmp/"):  # Allow /tmp/ for temporary files
            raise SecurityError(f"Potentially unsafe path detected: {file_path}")

    # Validate path format
    try:
        path_obj = Path(file_path)
    except (ValueError, OSError) as e:
        raise ValidationError(f"Invalid path format: {e}") from e

    # Check extension if specified
    if allowed_extensions:
        if not any(file_path.endswith(ext) for ext in allowed_extensions):
            raise ValidationError(
                f"File must have one of these extensions: {allowed_extensions}"
            )

    # Check existence if required
    if must_exist and not path_obj.exists():
        raise ValidationError(f"File does not exist: {file_path}")

    return True


def sanitize_command(command: str, allowed_commands: list[str] | None = None) -> str:
    """
    Sanitize and validate a shell command for safe execution.

    Args:
        command: Command to sanitize
        allowed_commands: List of allowed command prefixes

    Returns:
        Sanitized command

    Raises:
        SecurityError: If command is deemed unsafe
    """
    if not command or not isinstance(command, str):
        raise ValidationError("Command must be a non-empty string")

    # Default allowed commands for this demo
    if allowed_commands is None:
        allowed_commands = [
            "uv run importobot",
            "make enterprise-demo",
            "python -m importobot",
            "ls",
            "cat",
        ]

    # Check against allowed commands
    command_allowed = False
    for allowed in allowed_commands:
        if command.strip().startswith(allowed):
            command_allowed = True
            break

    if not command_allowed:
        raise SecurityError(f"Command not allowed: {command}")

    # Check for dangerous patterns
    dangerous_patterns = [
        r"[;&|`$()]",  # Shell injection characters
        r"rm\s+-rf",  # Dangerous deletion
        r"sudo",  # Privilege escalation
        r"curl|wget",  # Network access
        r">.*\.sh",  # Writing shell scripts
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise SecurityError(
                f"Potentially dangerous command pattern detected: {command}"
            )

    # Log the command for security audit
    security_logger.info("Executing command: %s", command)

    return command.strip()


def validate_json_structure(data: dict, required_keys: list[str] | None = None) -> bool:
    """
    Validate JSON data structure.

    Args:
        data: JSON data to validate
        required_keys: List of required top-level keys

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValidationError("JSON data must be a dictionary")

    if required_keys:
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise ValidationError(f"Missing required keys: {missing_keys}")

    return True


def validate_numeric_range(
    value: int | float,
    min_val: float | None = None,
    max_val: float | None = None,
    name: str = "value",
) -> bool:
    """
    Validate that a numeric value is within acceptable range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        name: Name of the value for error messages

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, int | float):
        raise ValidationError(f"{name} must be a number")

    if min_val is not None and value < min_val:
        raise ValidationError(f"{name} must be at least {min_val}")

    if max_val is not None and value > max_val:
        raise ValidationError(f"{name} must be at most {max_val}")

    return True


def validate_business_metrics(metrics: dict) -> tuple[bool, list[str]]:
    """
    Validate business metrics for reasonableness.

    Args:
        metrics: Dictionary of business metrics

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    try:
        # Required keys for business metrics
        required_keys = ["test_cases", "manual_time_per_test_days", "daily_cost_usd"]
        validate_json_structure(metrics, required_keys)

        # Validate individual metrics
        validate_numeric_range(metrics["test_cases"], 1, 100000, "test_cases")
        validate_numeric_range(
            metrics["manual_time_per_test_days"], 0.1, 30, "manual_time_per_test_days"
        )
        validate_numeric_range(metrics["daily_cost_usd"], 100, 10000, "daily_cost_usd")

        if "manual_success_rate" in metrics:
            validate_numeric_range(
                metrics["manual_success_rate"], 0, 100, "manual_success_rate"
            )

        if "importobot_success_rate" in metrics:
            validate_numeric_range(
                metrics["importobot_success_rate"], 0, 100, "importobot_success_rate"
            )

    except ValidationError as e:
        errors.append(str(e))

    return len(errors) == 0, errors


def safe_remove_file(file_path: str) -> None:
    """
    Safely remove a file with validation.

    Args:
        file_path: Path to the file to remove.
    """
    try:
        validate_file_path(file_path, must_exist=True)
        Path(file_path).unlink()
        security_logger.info("Removed file: %s", file_path)
    except (ValidationError, SecurityError, OSError) as e:
        security_logger.warning("Could not remove file %s: %s", file_path, e)


def read_and_display_file(file_path: str, title: str = "") -> None:
    """
    Read and display a file's content with a title.

    Args:
        file_path: Path to the file to read.
        title: Title to display before the content.
    """
    try:
        validate_file_path(file_path, must_exist=True)
        content = Path(file_path).read_text(encoding="utf-8")
        if title:
            print(f"\n{title}:")
        print(content)
    except (ValidationError, SecurityError, OSError) as e:
        security_logger.warning("Could not read file %s: %s", file_path, e)


def safe_execute_command(
    command: str, cwd: str | None = None, timeout: int = 60
) -> tuple[bool, str, str]:
    """
    Safely execute a shell command with proper validation and error handling.

    Args:
        command: Command to execute
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        # Sanitize the command
        safe_command = sanitize_command(command)

        # Validate working directory if provided
        if cwd:
            validate_file_path(cwd, must_exist=True)

        # Execute with timeout and security measures
        result = subprocess.run(
            safe_command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Don't raise exception on non-zero exit
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after {timeout} seconds: {command}"
        security_logger.warning(error_msg)
        return False, "", error_msg

    except (SecurityError, ValidationError) as e:
        error_msg = f"Security/Validation error: {e}"
        security_logger.error(error_msg)
        return False, "", error_msg

    except Exception as e:
        error_msg = f"Unexpected error executing command: {e}"
        security_logger.error(error_msg)
        return False, "", error_msg


def validate_demo_environment() -> tuple[bool, list[str]]:
    """
    Validate that the demo environment is properly set up.

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Check for required dependencies
    required_deps = ["matplotlib", "numpy", "pandas", "seaborn"]
    for dep in required_deps:
        if importlib.util.find_spec(dep) is None:
            issues.append(f"Missing required dependency: {dep}")

    # Check for importobot availability
    success, _stdout, _stderr = safe_execute_command("uv run importobot --help")
    if not success:
        issues.append("Importobot command not available or not working")

    # Check for example files directory
    examples_dir = Path("examples/json")
    if not examples_dir.exists():
        issues.append(f"Examples directory not found: {examples_dir}")

    # Check write permissions for temporary files
    try:
        test_file = Path("/tmp/demo_permission_test")
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
    except (PermissionError, OSError):
        issues.append("Cannot write to /tmp directory")

    return len(issues) == 0, issues


def log_demo_session(session_info: dict) -> None:
    """
    Log demo session information for audit purposes.

    Args:
        session_info: Dictionary containing session information
    """
    session_data = {
        "timestamp": time.time(),
        "user": os.getenv("USER", "unknown"),
        "mode": session_info.get("mode", "unknown"),
        "demos_run": session_info.get("demos_run", []),
        "errors_encountered": session_info.get("errors", []),
    }

    security_logger.info("Demo session: %s", session_data)


class DemoSecurityManager:
    """Manages security aspects of the demo execution."""

    def __init__(self) -> None:
        """Initialize the DemoSecurityManager."""
        self.session_start_time: float | None = None
        self.commands_executed: list[dict[str, str | bool | float]] = []
        self.files_accessed: list[dict[str, str | float]] = []
        self.errors_encountered: list[dict[str, str | float]] = []

    def start_session(self) -> None:
        """Start a new demo session."""
        self.session_start_time = time.time()
        security_logger.info("Demo session started")

    def log_command(self, command: str, success: bool) -> None:
        """Log a command execution."""
        self.commands_executed.append(
            {"command": command, "success": success, "timestamp": time.time()}
        )

    def log_file_access(self, file_path: str, operation: str) -> None:
        """Log file access."""
        self.files_accessed.append(
            {"file": file_path, "operation": operation, "timestamp": time.time()}
        )

    def log_error(self, error: str) -> None:
        """Log an error."""
        self.errors_encountered.append({"error": error, "timestamp": time.time()})
        security_logger.error("Demo error: %s", error)

    def end_session(self) -> dict[str, int | float]:
        """End the demo session and return summary."""
        session_duration = (
            time.time() - self.session_start_time if self.session_start_time else 0
        )

        summary = {
            "duration_seconds": session_duration,
            "commands_executed": len(self.commands_executed),
            "files_accessed": len(self.files_accessed),
            "errors_encountered": len(self.errors_encountered),
            "successful_commands": sum(
                1 for cmd in self.commands_executed if cmd["success"]
            ),
        }

        security_logger.info("Demo session ended: %s", summary)
        return summary


# Global security manager instance
SECURITY_MANAGER = DemoSecurityManager()
