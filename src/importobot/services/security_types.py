"""Security types and enums for the services package."""

from __future__ import annotations

from enum import Enum


class SecurityLevel(Enum):
    """Security levels for input validation and sanitization.

    Attributes:
        STRICT: Maximum security for enterprise/production environments.
            - Additional dangerous patterns: proc filesystem access, network
              process enumeration, user enumeration, external network requests
            - Additional sensitive paths: /proc/, /sys/, Kubernetes configs, Docker
              configs, system logs, Windows ProgramData
            - Recommended for: Production systems, enterprise environments,
              compliance scenarios

        STANDARD: Balanced security for general development and testing.
            - Default dangerous patterns: rm -rf, sudo, chmod 777, command substitution,
              eval/exec, fork bombs, system file access, disk operations
            - Default sensitive paths: system files, SSH keys, AWS credentials, root
              access, Windows system directories
            - Recommended for: Most development environments, CI/CD pipelines, testing

        PERMISSIVE: Relaxed security for trusted development environments.
            - Reduced dangerous patterns: removes curl, wget, and /dev/null redirection
            - Standard sensitive paths: maintains basic system protection
            - Recommended for: Local development, trusted environments,
              educational purposes
    """

    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"

    @classmethod
    def from_string(cls, value: str) -> SecurityLevel:
        """Convert string to SecurityLevel enum.

        Args:
            value: String value to convert

        Returns:
            SecurityLevel enum value

        Raises:
            ValueError: If value is not a valid security level
        """
        try:
            return cls(value.lower())
        except ValueError as err:
            valid_levels = [level.value for level in cls]
            raise ValueError(
                f"Invalid security level '{value}'. "
                f"Valid levels are: {', '.join(valid_levels)}"
            ) from err

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def description(self) -> str:
        """Get human-readable description of the security level."""
        descriptions = {
            SecurityLevel.STRICT: "Maximum security for production environments",
            SecurityLevel.STANDARD: "Balanced security for development and testing",
            SecurityLevel.PERMISSIVE: "Relaxed security for trusted environments",
        }
        return descriptions[self]

    @property
    def is_strict(self) -> bool:
        """Check if this is strict security level."""
        return self == SecurityLevel.STRICT

    @property
    def is_standard(self) -> bool:
        """Check if this is standard security level."""
        return self == SecurityLevel.STANDARD

    @property
    def is_permissive(self) -> bool:
        """Check if this is permissive security level."""
        return self == SecurityLevel.PERMISSIVE
