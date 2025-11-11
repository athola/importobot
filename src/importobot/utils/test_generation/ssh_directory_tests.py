"""SSH directory test generation module."""

from typing import Any

from .ssh_base import BaseSSHTestGenerator


class SSHDirectoryTestGenerator(BaseSSHTestGenerator):
    """Generate SSH directory test cases."""

    def __init__(self) -> None:
        """Initialize the SSH directory test generator."""

    def generate_directory_listing_tests(self, config: dict[str, Any]) -> list[str]:
        """Generate directory listing test cases.

        Args:
            config: Configuration for test generation

        Returns:
            List of generated test cases
        """
        _ = config  # Unused parameter
        return []
