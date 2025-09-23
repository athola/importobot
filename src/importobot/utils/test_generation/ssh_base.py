"""Base class for SSH test generators to eliminate code duplication."""

from typing import Any, Dict, List


class BaseSSHTestGenerator:
    """Base class for SSH test generators with common placeholder methods."""

    def _generate_placeholder_method(self, config: Dict[str, Any]) -> List[str]:
        """Generate placeholder test cases (to be overridden by subclasses).

        Args:
            config: Configuration for test generation

        Returns:
            List of generated test cases
        """
        _ = config  # Unused parameter
        return []

    def generate_connection_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate connection test cases."""
        return self._generate_placeholder_method(config)

    def generate_disconnection_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate disconnection test cases."""
        return self._generate_placeholder_method(config)

    def generate_connection_timeout_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate connection timeout test cases."""
        return self._generate_placeholder_method(config)

    def generate_command_output_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate command output verification test cases."""
        return self._generate_placeholder_method(config)

    def generate_command_error_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate command error handling test cases."""
        return self._generate_placeholder_method(config)

    def generate_key_based_auth_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate key-based authentication test cases."""
        return self._generate_placeholder_method(config)

    def generate_password_auth_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate password-based authentication test cases."""
        return self._generate_placeholder_method(config)

    def generate_prompt_response_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate prompt-response test cases."""
        return self._generate_placeholder_method(config)

    def generate_menu_navigation_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate menu navigation test cases."""
        return self._generate_placeholder_method(config)

    def generate_file_upload_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate file upload test cases."""
        return self._generate_placeholder_method(config)

    def generate_file_download_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate file download test cases."""
        return self._generate_placeholder_method(config)

    def generate_file_verification_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate file verification test cases."""
        return self._generate_placeholder_method(config)

    def generate_directory_creation_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate directory creation test cases."""
        return self._generate_placeholder_method(config)

    def generate_directory_deletion_tests(self, config: Dict[str, Any]) -> List[str]:
        """Generate directory deletion test cases."""
        return self._generate_placeholder_method(config)
