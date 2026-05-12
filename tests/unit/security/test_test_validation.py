"""Tests for high-level test-case security validation.

Covers ``importobot.security.test_validation``. The module orchestrates
SecurityValidator + recommendation generation, so the tests both
verify the result-shape contract and exercise the SSH-parameter
extraction regex helper.
"""

from __future__ import annotations

import pytest

from importobot.security import test_validation
from importobot.security.test_validation import (
    _extract_ssh_parameters,
    validate_test_security,
)


@pytest.fixture(autouse=True)
def _provide_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # SecurityValidator depends on CredentialManager which mandates
    # IMPORTOBOT_ENCRYPTION_KEY. Use the project test pattern.
    monkeypatch.setenv("IMPORTOBOT_ENCRYPTION_KEY", "A" * 44)


class TestValidateTestSecurity:
    """High-level orchestration entrypoint."""

    def test_returns_three_named_result_lists(self) -> None:
        # Callers destructure these three keys; any rename breaks them.
        result = validate_test_security({"name": "noop", "steps": []})
        assert set(result.keys()) == {
            "warnings",
            "recommendations",
            "sanitized_errors",
        }
        assert isinstance(result["warnings"], list)
        assert isinstance(result["recommendations"], list)
        assert isinstance(result["sanitized_errors"], list)

    def test_empty_test_case_produces_no_warnings(self) -> None:
        result = validate_test_security({})
        assert result["warnings"] == []
        assert result["sanitized_errors"] == []

    def test_ssh_step_produces_recommendations(self) -> None:
        test_case = {
            "name": "SSH test",
            "steps": [
                {
                    "library": "SSHLibrary",
                    "test_data": "host: example.com, username: admin",
                }
            ],
        }
        result = validate_test_security(test_case)
        # The recommendation pipeline always runs; SSH-flavoured test
        # cases should surface guidance regardless of the validator's
        # warning output.
        assert any("ssh" in r.lower() for r in result["recommendations"])

    def test_non_ssh_test_case_skips_ssh_validation(self) -> None:
        # A test case without "ssh" anywhere should not trigger the
        # SSH-parameter validation branch; recommendations may still
        # be empty.
        result = validate_test_security(
            {"name": "API check", "steps": [{"library": "RequestsLibrary"}]}
        )
        assert result["warnings"] == []

    def test_steps_count_logged_even_without_steps_key(self) -> None:
        # Regression guard: missing "steps" must not raise.
        result = validate_test_security({"name": "x"})
        assert "warnings" in result


class TestExtractSshParameters:
    """SSH parameter regex extractor (internal but load-bearing)."""

    def test_empty_string_returns_empty_dict(self) -> None:
        assert _extract_ssh_parameters("") == {}

    def test_extracts_password_username_host(self) -> None:
        data = "host: srv.example, username: admin, password: hunter2"
        params = _extract_ssh_parameters(data)
        assert params["host"] == "srv.example"
        assert params["username"] == "admin"
        assert params["password"] == "hunter2"

    def test_extracts_keyfile_and_command(self) -> None:
        data = "keyfile: /root/.ssh/id_rsa, command: uname -a"
        params = _extract_ssh_parameters(data)
        assert params["keyfile"] == "/root/.ssh/id_rsa"
        # Commands may contain spaces; regex captures until comma/newline.
        assert params["command"] == "uname -a"

    def test_extracts_source_and_destination_paths(self) -> None:
        data = "source: /tmp/a.txt, destination: /var/dest/b.txt"
        params = _extract_ssh_parameters(data)
        assert params["source_path"] == "/tmp/a.txt"
        assert params["destination_path"] == "/var/dest/b.txt"

    def test_password_indicator_present_but_value_missing(self) -> None:
        # The contract: a bare "password:" with no value still flags as
        # present so downstream rules can warn about empty passwords.
        params = _extract_ssh_parameters("password:")
        assert params.get("password") is True

    def test_irrelevant_data_yields_empty_result(self) -> None:
        assert _extract_ssh_parameters("just some narrative text") == {}

    def test_multiline_input_handled(self) -> None:
        data = "host: srv\nusername: admin\npassword: secret123"
        params = _extract_ssh_parameters(data)
        assert params["host"] == "srv"
        assert params["password"] == "secret123"


class TestModulePrivacy:
    """Encode the invariant that this module's public surface is empty."""

    def test_all_is_empty(self) -> None:
        assert test_validation.__all__ == []
