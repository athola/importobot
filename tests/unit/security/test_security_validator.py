"""Tests for the SecurityValidator orchestration class.

Covers ``importobot.security.security_validator.SecurityValidator``.
The validator is the public-facing facade over audit logging, pattern
selection by security level, and the various ``check_*`` predicates.
Individual checkers have their own tests; here we verify the facade's
contract: constructor selection, delegation, and the structured result
shape callers depend on.
"""

from __future__ import annotations

import pytest

from importobot.security import security_validator
from importobot.security.patterns import SecurityPatterns
from importobot.security.security_validator import SecurityValidator
from importobot.services.security_types import SecurityLevel


@pytest.fixture(autouse=True)
def _provide_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", "A" * 44)


class TestConstructionAndDefaults:
    """Constructor behaviour around security levels and patterns."""

    def test_default_construction_uses_standard_level(self) -> None:
        validator = SecurityValidator()
        assert validator.security_level == SecurityLevel.STANDARD
        assert validator.enable_audit_logging is True

    def test_strict_level_picks_strict_patterns(self) -> None:
        std = SecurityValidator(security_level=SecurityLevel.STANDARD)
        strict = SecurityValidator(security_level=SecurityLevel.STRICT)
        # Strict should never have fewer dangerous patterns than standard.
        assert len(strict.dangerous_patterns) >= len(std.dangerous_patterns)
        assert len(strict.sensitive_paths) >= len(std.sensitive_paths)

    def test_permissive_level_picks_relaxed_patterns(self) -> None:
        permissive = SecurityValidator(security_level=SecurityLevel.PERMISSIVE)
        # Permissive should not exceed standard's dangerous pattern count.
        std = SecurityValidator(security_level=SecurityLevel.STANDARD)
        assert len(permissive.dangerous_patterns) <= len(std.dangerous_patterns)

    def test_explicit_dangerous_patterns_replace_defaults(self) -> None:
        validator = SecurityValidator(dangerous_patterns=[r"only_mine"])
        # Explicit list replaces, so the default patterns must not appear.
        assert validator.dangerous_patterns == [r"only_mine"]

    def test_additional_patterns_extend_rather_than_replace(self) -> None:
        validator = SecurityValidator(
            additional_dangerous_patterns=[r"extra_pattern"],
        )
        assert "extra_pattern" in validator.dangerous_patterns
        # The defaults remain in place.
        default_count = len(
            SecurityPatterns.get_dangerous_patterns(None, SecurityLevel.STANDARD)
        )
        assert len(validator.dangerous_patterns) == default_count + 1

    def test_explicit_sensitive_paths_replace_defaults(self) -> None:
        validator = SecurityValidator(sensitive_paths=["/tmp/only"])
        assert validator.sensitive_paths == ["/tmp/only"]

    def test_audit_logger_can_be_disabled(self) -> None:
        validator = SecurityValidator(enable_audit_logging=False)
        # The exposed property is the underlying logging.Logger; only the
        # toggle is observable from the public API.
        assert validator.enable_audit_logging is False


class TestValidateSshParameters:
    """Orchestrator returns a flat list of warning strings."""

    def test_clean_params_yield_no_warnings(self) -> None:
        validator = SecurityValidator()
        warnings = validator.validate_ssh_parameters(
            {
                "host": "example.com",
                "username": "user",
                "command": "ls /tmp",
            }
        )
        assert isinstance(warnings, list)
        # No hardcoded credentials, no dangerous commands -> empty.
        assert warnings == []

    def test_dangerous_command_surfaces_warning(self) -> None:
        validator = SecurityValidator()
        warnings = validator.validate_ssh_parameters({"command": "rm -rf /"})
        assert any("rm" in w.lower() or "dangerous" in w.lower() for w in warnings)

    def test_sensitive_path_surfaces_warning(self) -> None:
        validator = SecurityValidator()
        warnings = validator.validate_ssh_parameters({"source_path": "/etc/shadow"})
        # The sensitive path checker emits at least one warning here.
        assert warnings != []


class TestDelegationHelpers:
    """The facade delegates to checkers and recommendation helpers."""

    def test_sanitize_command_parameters_returns_string(self) -> None:
        validator = SecurityValidator()
        out = validator.sanitize_command_parameters("ls -la")
        assert isinstance(out, str)

    def test_validate_file_operations_returns_list(self) -> None:
        validator = SecurityValidator()
        out = validator.validate_file_operations("/etc/passwd", "read")
        assert isinstance(out, list)
        # Sensitive path triggers a warning.
        assert out != []

    def test_validate_file_operations_path_traversal_triggers_warning(self) -> None:
        validator = SecurityValidator()
        out = validator.validate_file_operations("/var/log/../../../etc/shadow", "read")
        assert out != []

    def test_sanitize_error_message_returns_string(self) -> None:
        validator = SecurityValidator()
        out = validator.sanitize_error_message("Error: token=abc123")
        assert isinstance(out, str)

    def test_generate_security_recommendations_returns_list(self) -> None:
        validator = SecurityValidator()
        out = validator.generate_security_recommendations({"step": "ssh root@host"})
        assert isinstance(out, list)
        assert any("ssh" in r.lower() for r in out)

    def test_validate_test_security_result_shape(self) -> None:
        validator = SecurityValidator()
        result = validator.validate_test_security({"steps": []})
        assert set(result.keys()) == {
            "warnings",
            "recommendations",
            "sanitized_errors",
        }


class TestBackwardsCompatibility:
    """Backwards-compat attributes/methods must remain stable."""

    def test_class_constants_match_module_defaults(self) -> None:
        # Callers may still reach for the class-level constants.
        assert (
            SecurityValidator.DEFAULT_DANGEROUS_PATTERNS
            is SecurityPatterns.DEFAULT_DANGEROUS_PATTERNS
        )
        assert (
            SecurityValidator.DEFAULT_SENSITIVE_PATHS
            is SecurityPatterns.DEFAULT_SENSITIVE_PATHS
        )

    def test_audit_logger_property_returns_underlying_logger(self) -> None:
        validator = SecurityValidator()
        # The property exposes the underlying logging.Logger, not the
        # SecurityAuditLogger wrapper, for legacy compatibility.
        assert hasattr(validator.audit_logger, "warning")
        assert hasattr(validator.audit_logger, "error")

    def test_private_pattern_accessors_remain_callable(self) -> None:
        # Older code calls _get_patterns / _get_sensitive_paths; the
        # underscore prefix is documentation, not enforcement.
        validator = SecurityValidator()
        assert isinstance(validator._get_patterns(None, SecurityLevel.STANDARD), list)
        assert isinstance(
            validator._get_sensitive_paths(None, SecurityLevel.STANDARD), list
        )


class TestCredentialManagerInitialization:
    """The validator wires up CredentialManager from env or ephemeral key."""

    def test_env_key_present_uses_env_backed_manager(self) -> None:
        # IMPORTOBOT_ENCRYPTION_KEY is set by the autouse fixture; the
        # manager must initialise without raising.
        validator = SecurityValidator()
        assert validator.credential_manager is not None

    def test_env_key_absent_falls_back_to_ephemeral_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Override the autouse fixture for this test only.
        monkeypatch.delenv("IMPORTOBOT_ENCRYPTION_KEY", raising=False)
        validator = SecurityValidator()
        # No env key, but construction still succeeds via an ephemeral
        # 32-byte key generated with secrets.token_bytes.
        assert validator.credential_manager is not None


class TestModulePrivacy:
    def test_all_is_empty(self) -> None:
        assert security_validator.__all__ == []
