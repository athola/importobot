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
from typing import Any, Dict, List, Mapping, Optional, Pattern, Tuple, TypedDict, Union

from importobot.services.security_types import SecurityLevel
from importobot.services.validation_service import ValidationService
from importobot.utils.logging import setup_logger
from importobot.utils.security import SecurityValidator
from importobot.utils.validation import (
    ValidationError,
    validate_file_path,
    validate_json_dict,
    validate_json_size,
    validate_safe_path,
)

try:
    import bleach  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - bleach is optional at runtime
    bleach = None  # type: ignore[assignment]


INLINE_EVENT_HANDLER_PATTERN = (
    r"on(?:abort|afterprint|beforeprint|beforeunload|blur|change|click|contextmenu|"
    r"copy|cut|dblclick|drag|dragend|dragenter|dragleave|dragover|dragstart|drop|"
    r"error|focus|focusin|focusout|hashchange|input|invalid|keydown|keypress|"
    r"keyup|load|loadeddata|loadedmetadata|loadstart|message|mousedown|mouseenter|"
    r"mouseleave|mousemove|mouseout|mouseover|mouseup|paste|popstate|reset|resize|"
    r"scroll|search|select|storage|submit|toggle|touchcancel|touchend|touchmove|"
    r"touchstart|unload|wheel)\s*="
)

logger = setup_logger(__name__)


class SanitizationResult(TypedDict, total=False):
    """Structured result returned from sanitize_api_input."""

    is_safe: bool
    sanitized_data: Any
    security_issues: List[str]
    validation_issues: List[str]
    security_level: str
    input_type: str
    correlation_id: Optional[str]


class FileOperationResult(TypedDict, total=False):
    """Structured result returned from validate_file_operation."""

    is_safe: bool
    file_path: str
    operation: str
    security_issues: List[str]
    normalized_path: str
    correlation_id: Optional[str]


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
        self._dangerous_patterns = self._build_dangerous_patterns()
        self._dangerous_pattern_strings = [
            pattern.pattern for pattern, _ in self._dangerous_patterns
        ]
        self._suspicious_patterns = self._build_suspicious_patterns()
        self._path_traversal_patterns = self._build_traversal_patterns()
        logger.info(
            "Initialized SecurityGateway with level=%s", self.security_level.value
        )

    @staticmethod
    def _build_dangerous_patterns() -> List[Tuple[re.Pattern[str], str]]:
        """Compile dangerous pattern catalogue with case-insensitive coverage."""
        return [
            (re.compile(r"<\s*script\b", re.IGNORECASE), "Script tag detected"),
            (
                re.compile(r"<\s*iframe\b", re.IGNORECASE),
                "Iframe tag detected",
            ),
            (
                re.compile(INLINE_EVENT_HANDLER_PATTERN, re.IGNORECASE),
                "Inline event handler attribute detected",
            ),
            (
                re.compile(r"javascript\s*:", re.IGNORECASE),
                "JavaScript protocol detected",
            ),
            (
                re.compile(r"vbscript\s*:", re.IGNORECASE),
                "VBScript protocol detected",
            ),
            (
                re.compile(r"data\s*:[^;]+;?base64", re.IGNORECASE),
                "Base64-encoded data URI detected",
            ),
            (
                re.compile(r"file\s*:", re.IGNORECASE),
                "File protocol reference detected",
            ),
            (
                re.compile(r"(?:\.{2}/|\\\.\.)", re.IGNORECASE),
                "Directory traversal sequence detected",
            ),
            (
                re.compile(r"/etc/passwd", re.IGNORECASE),
                "Sensitive system path reference detected",
            ),
            (
                re.compile(r"/proc/", re.IGNORECASE),
                "Process filesystem reference detected",
            ),
            (
                re.compile(r"c:\\windows\\system32", re.IGNORECASE),
                "Windows system directory reference detected",
            ),
            (
                re.compile(r"\brm\s+-rf\s+/", re.IGNORECASE),
                "Dangerous command pattern detected",
            ),
            (
                re.compile(r"\b(?:rm|del|rmdir)\s+-[rf]+\s+", re.IGNORECASE),
                "Dangerous file deletion command detected",
            ),
            (
                re.compile(r";\s*(?:rm|del|format)\s+", re.IGNORECASE),
                "Dangerous chained command detected",
            ),
        ]

    @staticmethod
    def _build_suspicious_patterns() -> List[Tuple[Pattern[str], str]]:
        """Compile universal security checks once for reuse."""
        return [
            (re.compile(r"eval\s*\(", re.IGNORECASE), "JavaScript eval detected"),
            (re.compile(r"exec\s*\(", re.IGNORECASE), "Python exec detected"),
            (re.compile(r"system\s*\(", re.IGNORECASE), "System command detected"),
            (re.compile(r"subprocess", re.IGNORECASE), "Subprocess usage detected"),
            (re.compile(r"__import__", re.IGNORECASE), "Dynamic import detected"),
            (
                re.compile(r"rm\s+-rf", re.IGNORECASE),
                "Dangerous file deletion detected",
            ),
        ]

    @staticmethod
    def _build_traversal_patterns() -> List[Pattern[str]]:
        """Compile common path traversal expressions."""
        return [
            re.compile(r"\.\.[\\/]"),
            re.compile(r"[\\/]\.\.[\\/]"),
            re.compile(r"[\\/]\.\.$"),
            re.compile(r"^\.\.[\\/]"),
        ]

    def sanitize_api_input(
        self,
        data: Any,
        input_type: str = "json",
        context: Optional[Mapping[str, Any]] = None,
    ) -> SanitizationResult:
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
        context_dict: Dict[str, Any] = dict(context or {})
        correlation_id = self._extract_correlation_id(context_dict)
        log_extra = self._build_log_extra(correlation_id)
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
            # Map input types to validation strategies
            # Skip validation for plain strings (they're validated by sanitization)
            if input_type == "file_path":
                validation_result = self.validation_service.validate(
                    sanitized_data, strategy_name="file", context=context_dict
                )
                if not validation_result.is_valid:
                    validation_issues = validation_result.messages
            elif input_type == "json":
                validation_result = self.validation_service.validate(
                    sanitized_data, strategy_name="json", context=context_dict
                )
                if not validation_result.is_valid:
                    validation_issues = validation_result.messages
            # String type doesn't need additional validation beyond sanitization
            # Step 4: Determine if input is safe
            is_safe = len(security_issues) == 0 and len(validation_issues) == 0
            return {
                "is_safe": is_safe,
                "sanitized_data": sanitized_data,
                "security_issues": security_issues,
                "validation_issues": validation_issues,
                "security_level": self.security_level.value,
                "input_type": input_type,
                "correlation_id": correlation_id,
            }
        except Exception as e:
            logger.error("Security gateway error: %s", e, extra=log_extra)
            raise SecurityError(f"Security validation failed: {e}") from e

    def validate_file_operation(
        self,
        file_path: Union[str, Path],
        operation: str = "read",
        *,
        correlation_id: Optional[str] = None,
    ) -> FileOperationResult:
        """Validate file operations with comprehensive security checks.

        Args:
            file_path: Path to validate
            operation: Type of operation (read, write, delete)

        Returns:
            Validation result with security assessment
        """
        path_str = str(file_path)
        log_extra = self._build_log_extra(correlation_id)
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
                "correlation_id": correlation_id,
            }
        except Exception as e:
            logger.error("File operation validation failed: %s", e, extra=log_extra)
            return {
                "is_safe": False,
                "file_path": path_str,
                "operation": operation,
                "security_issues": [f"Validation error: {e}"],
                "normalized_path": path_str,
                "correlation_id": correlation_id,
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
            "forbidden_patterns": self._dangerous_pattern_strings,
            "validate_before_parse": True,
        }

    def _sanitize_json_input(self, data: Any) -> tuple[Any, List[str]]:
        """Sanitize JSON input data."""
        issues = []
        try:
            # If it's a string, parse it first
            if isinstance(data, str):
                # Validate size before parsing to prevent DoS
                validate_json_size(data, max_size_mb=10)
                data = json.loads(data)
            # Check for dangerous content in JSON values
            if isinstance(data, dict):
                validate_json_dict(data)
                data, json_issues = self._sanitize_dict_values(data)
                issues.extend(json_issues)
            elif isinstance(data, list):
                data, json_issues = self._sanitize_list_values(data)
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
            for pattern, description in self._dangerous_patterns:
                if pattern.search(path_str):
                    issues.append(description)
            # Additional path traversal checks
            traversal_issues = self._check_path_traversal(path_str)
            issues.extend(traversal_issues)
            return normalized_path, issues
        except Exception as e:
            issues.append(f"Path normalization failed: {e}")
            return path_str, issues

    def _sanitize_string_input(self, data: str) -> tuple[str, List[str]]:
        """Sanitize string input."""
        issues: List[str] = []
        seen: set[str] = set()
        original = data

        # Apply HTML sanitization using bleach when available, otherwise use a
        # conservative fallback that strips markup.
        if bleach is not None:
            sanitized_string = bleach.clean(
                data,
                tags=[],
                attributes={},
                protocols=[],
                strip=True,
            )
        else:  # pragma: no cover - bleach should be installed via project deps
            sanitized_string = re.sub(r"<[^>]*>", "", data)
            sanitized_string = re.sub(
                INLINE_EVENT_HANDLER_PATTERN,
                "",
                sanitized_string,
                flags=re.IGNORECASE,
            )

        if sanitized_string != original:
            issues.append("HTML content sanitized for security")
            seen.add("HTML content sanitized for security")

        for pattern, description in self._dangerous_patterns:
            if pattern.search(original) and description not in seen:
                issues.append(description)
                seen.add(description)

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
        # Check for suspicious patterns using precompiled regex
        for pattern, message in self._suspicious_patterns:
            if pattern.search(data_str):
                issues.append(message)
        return issues

    def _check_path_traversal(self, path: str) -> List[str]:
        """Check for path traversal attempts."""
        issues = []
        for pattern in self._path_traversal_patterns:
            if pattern.search(path):
                issues.append("Path traversal attempt detected")
                break
        return issues

    @staticmethod
    def _extract_correlation_id(context: Mapping[str, Any]) -> Optional[str]:
        """Return correlation identifier from context if present."""
        value = context.get("correlation_id")
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _build_log_extra(correlation_id: Optional[str]) -> Dict[str, str]:
        """Prepare structured logging extras with correlation metadata."""
        if correlation_id:
            return {"correlation_id": correlation_id}
        return {}


class SecurityError(Exception):
    """Exception raised for security validation failures."""
