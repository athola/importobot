"""Test case security validation utilities.

Provides high-level test case validation that orchestrates
the various security checks for test automation scenarios.
"""

import re
import time
from typing import Any

from importobot.security.recommendations import generate_security_recommendations
from importobot.services.security_types import SecurityLevel
from importobot.utils.logging import get_logger
from importobot.utils.string_cache import data_to_lower_cached

logger = get_logger()


def validate_test_security(test_case: dict[str, Any]) -> dict[str, list[str]]:
    """Security validation for test cases.

    Creates a SecurityValidator with standard security level and performs validation.

    Args:
        test_case: Test case dictionary containing steps and test data

    Returns:
        Dictionary with validation results:
        - 'warnings': List of security warnings found
        - 'recommendations': List of security recommendations
        - 'sanitized_errors': List of sanitized error messages

    Note:
        Uses standard security level by default. For custom security levels,
        create a SecurityValidator instance directly with the desired level.
    """
    from importobot.security.security_validator import (  # noqa: PLC0415
        SecurityValidator,
    )

    start_time = time.time()
    validator = SecurityValidator(security_level=SecurityLevel.STANDARD)

    validator.log_validation_start(
        "TEST_CASE_SECURITY",
        {
            "test_case_keys": list(test_case.keys()),
            "has_steps": "steps" in test_case,
            "steps_count": len(test_case.get("steps", [])),
        },
    )

    results: dict[str, list[str]] = {
        "warnings": [],
        "recommendations": [],
        "sanitized_errors": [],
    }

    # Validate SSH operations
    if "ssh" in data_to_lower_cached(test_case):
        for step in test_case.get("steps", []):
            if (
                "ssh" in data_to_lower_cached(step)
                or step.get("library") == "SSHLibrary"
            ):
                test_data = step.get("test_data", "")
                ssh_params = _extract_ssh_parameters(test_data)

                ssh_warnings = validator.validate_ssh_parameters(ssh_params)
                results["warnings"].extend(ssh_warnings)

    # Generate security recommendations
    recommendations = generate_security_recommendations(test_case)
    results["recommendations"].extend(recommendations)

    # Log security analysis
    if results["warnings"]:
        logger.warning(
            "Security warnings for test case: %d issues found", len(results["warnings"])
        )

    duration_ms = (time.time() - start_time) * 1000
    validator.log_validation_complete(
        "TEST_CASE_SECURITY", len(results["warnings"]), duration_ms
    )

    return results


def _extract_ssh_parameters(test_data: str) -> dict[str, Any]:
    """Extract SSH parameters from test data string.

    Args:
        test_data: Test data string containing SSH parameters

    Returns:
        Dictionary of extracted SSH parameters
    """
    ssh_params: dict[str, Any] = {}

    parameter_patterns = {
        "password": r"password:\s*([^,\n\s]+)",
        "username": r"username:\s*([^,\n\s]+)",
        "keyfile": r"keyfile:\s*([^,\n\s]+)",
        "command": r"command:\s*([^,\n]+)",
        "host": r"host:\s*([^,\n\s]+)",
        "source_path": r"source:\s*([^,\n]+)",
        "destination_path": r"destination:\s*([^,\n]+)",
        "parameter": r"parameter:\s*([^,\n]+)",
    }

    for param_name, pattern in parameter_patterns.items():
        match = re.search(pattern, test_data)
        if match:
            ssh_params[param_name] = match.group(1).strip()

    # Ensure password detection includes the value for pattern matching
    if "password:" in test_data and "password" not in ssh_params:
        ssh_params["password"] = True

    return ssh_params


# Internal utility - not part of public API
__all__: list[str] = []
