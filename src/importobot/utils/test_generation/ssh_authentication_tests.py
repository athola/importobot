"""SSH authentication test generation module."""

import random
from typing import Any

from .ssh_base import BaseSSHTestGenerator


class SSHAuthenticationTestGenerator(BaseSSHTestGenerator):
    """Generate SSH authentication test cases."""

    def __init__(self) -> None:
        """Initialize the SSH authentication test generator."""
        # No initialization needed for base class

    def generate_login_test(self) -> dict[str, Any]:
        """Generate test for Login keyword."""
        usernames = ["admin", "deploy", "testuser", "developer"]
        passwords = ["secure123", "password", "admin", "test123"]

        username = random.choice(usernames)
        password = random.choice(passwords)

        return {
            "test_case": {
                "name": f"SSH Login Test - User {username}",
                "description": "Test SSH authentication with username and password",
                "steps": [
                    {
                        "step": "Login with SSH credentials",
                        "test_data": f"username: {username} password: {password}",
                        "expected": "Login successful",
                    }
                ],
            }
        }

    def generate_login_with_public_key_test(self) -> dict[str, Any]:
        """Generate test for Login With Public Key keyword."""
        usernames = ["admin", "deploy", "testuser", "developer"]
        key_files = [
            "/home/user/.ssh/id_rsa",
            "/home/user/.ssh/deploy_key",
            "/home/user/.ssh/production_key",
            "/home/user/.ssh/test_key",
        ]

        username = random.choice(usernames)
        keyfile = random.choice(key_files)

        return {
            "test_case": {
                "name": f"SSH Public Key Login Test - {username}",
                "description": "Test SSH authentication using public key",
                "steps": [
                    {
                        "step": "Login with public key",
                        "test_data": f"username: {username} keyfile: {keyfile}",
                        "expected": "Public key authentication successful",
                    }
                ],
            }
        }
