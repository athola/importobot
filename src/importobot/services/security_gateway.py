"""Security gateway service for API input validation and sanitization.

Implements centralized security hardening identified in the staff review:
- Centralized input sanitization at API boundaries
- JSON deserialization with validation
- Unified security checks across file operations
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from importobot.services.security_types import SecurityLevel
from importobot.services.validation_service import ValidationService
from importobot.utils.logging import setup_logger
from importobot.utils.security import SecurityValidator
from importobot.utils.validation import (
    ValidationError,
    validate_file_path,
    validate_json_dict,
    validate_safe_path,
)

logger = setup_logger(__name__)


class SecurityGateway:
    """Centralized security gateway for API input validation and sanitization."""

    def __init__(
        self, security_level: Union[SecurityLevel, str] = SecurityLevel.STANDARD
    ):
        """Initialize security gateway.

        Args:
            security_level: Security level enum or string
        """
        if isinstance(security_level, str):
            self.security_level = SecurityLevel.from_string(security_level)
        else:
            self.security_level = security_level
        self.security_validator = SecurityValidator(
            security_level=self.security_level.value
        )
        self.validation_service = ValidationService(
            security_level=self.security_level.value
        )
        # Dangerous patterns that should be blocked
        self._dangerous_patterns = [
            r"<script.*?>.*?</script>",  # XSS scripts
            r"javascript:",  # JavaScript protocol
            r"data:.*base64",  # Base64 data URIs
            r"vbscript:",  # VBScript protocol
            r"file://",  # File protocol
            r"\.\./",  # Directory traversal
            r"\\.\\.\\",  # Windows directory
            # traversal
            r"/etc/passwd",  # System files
            r"/proc/",  # Process filesystem
            r"C:\\Windows\\System32",  # Windows system directory
        ]
        logger.info(
            "Initialized SecurityGateway with level=%s", self.security_level.value
        )

    def sanitize_api_input(
        self,
        data: Any,
        input_type: str = "json",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sanitize and validate API input data.

        Args:
            data: Input data to sanitize
            input_type: Type of input (json, file_path, string)
            context: Additional context for validation
        Returns:
            Dictionary with sanitized data and validation results
        Raises:
            SecurityError: If input fails security validation
        """
        context = context or {}
        sanitized_data = data
        security_issues = []
        validation_issues = []
        try:
            # Step 1: Input type specific sanitization
            if input_type == "json":
                sanitized_data, json_issues = self._sanitize_json_input(data)
                security_issues.extend(json_issues)
            elif input_type == "file_path":
                sanitized_data, path_issues = self._sanitize_file_path(data)
                security_issues.extend(path_issues)
            elif input_type == "string":
                sanitized_data, string_issues = self._sanitize_string_input(data)
                security_issues.extend(string_issues)
            # Step 2: Universal security checks
            universal_issues = self._perform_universal_security_checks(sanitized_data)
            security_issues.extend(universal_issues)
            # Step 3: Validation service check
            validation_result = self.validation_service.validate(
                sanitized_data, strategy_name=input_type, context=context
            )
            if not validation_result.is_valid:
                validation_issues = validation_result.messages
            # Step 4: Determine if input is safe
            is_safe = len(security_issues) == 0 and len(validation_issues) == 0
            return {
                "is_safe": is_safe,
                "sanitized_data": sanitized_data,
                "security_issues": security_issues,
                "validation_issues": validation_issues,
                "security_level": self.security_level.value,
                "input_type": input_type,
            }
        except Exception as e:
            logger.error("Security gateway error: %s", e)
            raise SecurityError(f"Security validation failed: {e}") from e

    def validate_file_operation(
        self, file_path: Union[str, Path], operation: str = "read"
    ) -> Dict[str, Any]:
        """Validate file operations with comprehensive security checks.

        Args:
            file_path: Path to validate
            operation: Type of operation (read, write, delete)

        Returns:
            Validation result with security assessment
        """
        path_str = str(file_path)
        try:
            # Basic path validation
            validate_file_path(path_str)
            validate_safe_path(path_str)
            # Security validator checks
            file_warnings = self.security_validator.validate_file_operations(
                path_str, operation
            )
            # Additional path traversal checks
            traversal_issues = self._check_path_traversal(path_str)
            all_issues = file_warnings + traversal_issues
            return {
                "is_safe": len(all_issues) == 0,
                "file_path": path_str,
                "operation": operation,
                "security_issues": all_issues,
                "normalized_path": str(Path(path_str).resolve()),
            }
        except Exception as e:
            logger.error("File operation validation failed: %s", e)
            return {
                "is_safe": False,
                "file_path": path_str,
                "operation": operation,
                "security_issues": [f"Validation error: {e}"],
                "normalized_path": None,
            }

    def create_secure_json_parser(self, max_size_mb: int = 10) -> Dict[str, Any]:
        """Create a secure JSON parser configuration.

        Args:
            max_size_mb: Maximum allowed JSON size in MB
        Returns:
            Parser configuration with security settings
        """
        return {
            "max_size_mb": max_size_mb,
            "allow_duplicate_keys": False,
            "strict_mode": self.security_level
            in [SecurityLevel.STRICT, SecurityLevel.STANDARD],
            "forbidden_patterns": self._dangerous_patterns,
            "validate_before_parse": True,
        }

    def _sanitize_json_input(self, data: Any) -> tuple[Any, List[str]]:
        """Sanitize JSON input data."""
        issues = []
        try:
            # If it's a string, parse and validate it
            if isinstance(data, str):
                validate_json_dict(data)
                data = json.loads(data)
            # Check for dangerous content in JSON values
            if isinstance(data, dict):
                data, json_issues = self._sanitize_dict_values(data)
                issues.extend(json_issues)
            return data, issues
        except (json.JSONDecodeError, ValidationError) as e:
            issues.append(f"JSON validation failed: {e}")
            return None, issues

    def _sanitize_file_path(self, path: Union[str, Path]) -> tuple[str, List[str]]:
        """Sanitize file path input."""
        issues = []
        path_str = str(path)
        # Normalize path
        try:
            normalized_path = str(Path(path_str).resolve())
            # Check for dangerous patterns
            for pattern in self._dangerous_patterns:
                if re.search(pattern, path_str, re.IGNORECASE):
                    issues.append(f"Dangerous pattern detected in path: {pattern}")
            # Additional path traversal checks
            traversal_issues = self._check_path_traversal(path_str)
            issues.extend(traversal_issues)
            return normalized_path, issues
        except Exception as e:
            issues.append(f"Path normalization failed: {e}")
            return path_str, issues

    def _sanitize_string_input(self, data: str) -> tuple[str, List[str]]:
        """Sanitize string input."""
        issues = []
        # Check for dangerous patterns
        for pattern in self._dangerous_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                issues.append(f"Dangerous pattern detected: {pattern}")
        # Basic XSS protection
        sanitized_string = data
        if "<" in data and ">" in data:
            # Simple HTML tag removal (for basic protection)
            sanitized_string = re.sub(r"<[^>]*>", "", data)
            if sanitized_string != data:
                issues.append("HTML tags removed for security")
        return sanitized_string, issues

    def _sanitize_dict_values(
        self, data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], List[str]]:
        """Recursively sanitize dictionary values."""
        issues: List[str] = []
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                str_value, string_issues = self._sanitize_string_input(value)
                sanitized[key] = str_value
                issues.extend(string_issues)
            elif isinstance(value, dict):
                dict_value, dict_issues = self._sanitize_dict_values(value)
                sanitized[key] = dict_value
                issues.extend(dict_issues)
            elif isinstance(value, list):
                list_value, list_issues = self._sanitize_list_values(value)
                sanitized[key] = list_value
                issues.extend(list_issues)
            else:
                sanitized[key] = value
        return sanitized, issues

    def _sanitize_list_values(self, data: List[Any]) -> tuple[List[Any], List[str]]:
        """Recursively sanitize list values."""
        issues: List[str] = []
        sanitized: List[Any] = []
        for item in data:
            if isinstance(item, str):
                str_item, string_issues = self._sanitize_string_input(item)
                sanitized.append(str_item)
                issues.extend(string_issues)
            elif isinstance(item, dict):
                dict_item, dict_issues = self._sanitize_dict_values(item)
                sanitized.append(dict_item)
                issues.extend(dict_issues)
            elif isinstance(item, list):
                list_item, list_issues = self._sanitize_list_values(item)
                sanitized.append(list_item)
                issues.extend(list_issues)
            else:
                sanitized.append(item)
        return sanitized, issues

    def _perform_universal_security_checks(self, data: Any) -> List[str]:
        """Perform universal security checks on any data type."""
        issues = []
        # Convert to string for pattern matching
        data_str = str(data)
        # Check for suspicious patterns
        suspicious_patterns = [
            (r"eval\s*\(", "JavaScript eval detected"),
            (r"exec\s*\(", "Python exec detected"),
            (r"system\s*\(", "System command detected"),
            (r"subprocess", "Subprocess usage detected"),
            (r"__import__", "Dynamic import detected"),
            (r"rm\s+-rf", "Dangerous file deletion detected"),
        ]
        for pattern, message in suspicious_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                issues.append(message)
        return issues

    def _check_path_traversal(self, path: str) -> List[str]:
        """Check for path traversal attempts."""
        issues = []
        traversal_patterns = [
            r"\.\.[\\/]",  # ../ or ..\
            r"[\\/]\.\.[\\/]",  # /../ or \..\
            r"[\\/]\.\.$",  # /.. or \..
            r"^\.\.[\\/]",  # ../ or ..\ at start
        ]
        for pattern in traversal_patterns:
            if re.search(pattern, path):
                issues.append("Path traversal attempt detected")
                break
        return issues


class SecurityError(Exception):
    """Exception raised for security validation failures."""
