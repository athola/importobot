"""SSH test data generation module."""

from typing import Any


class SSHTestDataGenerator:
    """Generate SSH test data."""

    def __init__(self) -> None:
        """Initialize the SSH test data generator."""

    def generate_test_credentials(self, config: dict[str, Any]) -> dict[str, str]:
        """Generate test credentials.

        Args:
            config: Configuration for test generation

        Returns:
            Dictionary of test credentials
        """
        _ = config  # Unused parameter
        return {}

    def generate_test_hosts(self, config: dict[str, Any]) -> list[str]:
        """Generate test host configurations.

        Args:
            config: Configuration for test generation

        Returns:
            List of test host configurations
        """
        _ = config  # Unused parameter
        return []

    def generate_test_commands(self, config: dict[str, Any]) -> list[str]:
        """Generate test commands.

        Args:
            config: Configuration for test generation

        Returns:
            List of test commands
        """
        _ = config  # Unused parameter
        return []
