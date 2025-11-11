"""SSH file test generation module."""

from typing import Any

from .ssh_base import BaseSSHTestGenerator


class SSHFileTestGenerator(BaseSSHTestGenerator):
    """Generate SSH file test cases."""

    def __init__(self) -> None:
        """Initialize the SSH file test generator."""

    def generate_file_upload_tests(self, config: dict[str, Any]) -> list[str]:
        """Generate file upload test cases.

        Args:
            config: Configuration for test generation

        Returns:
            List of generated test cases
        """
        _ = config  # Unused parameter
        return []
