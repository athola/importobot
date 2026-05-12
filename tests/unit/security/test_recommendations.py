"""Tests for security recommendations.

Covers the recommendation generators in
``importobot.security.recommendations`` that produce contextual guidance
based on detected operation types in test data.
"""

from __future__ import annotations

from importobot.security.recommendations import (
    SSH_SECURITY_GUIDELINES,
    extract_security_warnings,
    generate_security_recommendations,
    get_ssh_security_guidelines,
)


class TestGetSshSecurityGuidelines:
    """SSH guidelines accessor."""

    def test_returns_non_empty_list(self) -> None:
        guidelines = get_ssh_security_guidelines()
        assert isinstance(guidelines, list)
        assert len(guidelines) > 0

    def test_returns_constant_module_value(self) -> None:
        # The accessor is documented to expose the module-level constant;
        # callers may rely on identity for caching, so guard against an
        # accidental copy that would defeat that.
        assert get_ssh_security_guidelines() is SSH_SECURITY_GUIDELINES

    def test_includes_core_security_themes(self) -> None:
        joined = " ".join(get_ssh_security_guidelines()).lower()
        # Each theme is load-bearing for SSH hardening guidance.
        assert "key-based authentication" in joined
        assert "timeout" in joined
        assert "audit" in joined


class TestGenerateSecurityRecommendations:
    """Detection-driven recommendation builder."""

    def test_empty_test_data_yields_no_recommendations(self) -> None:
        assert generate_security_recommendations({}) == []

    def test_unrelated_test_data_yields_no_recommendations(self) -> None:
        data = {"name": "Login flow", "description": "Check the dashboard"}
        assert generate_security_recommendations(data) == []

    def test_ssh_in_value_triggers_ssh_recommendations(self) -> None:
        data = {"step": "Run ssh root@host whoami"}
        recs = generate_security_recommendations(data)
        assert any("key-based authentication" in r for r in recs)
        assert any("timeout" in r.lower() for r in recs)

    def test_ssh_in_key_triggers_ssh_recommendations(self) -> None:
        data = {"ssh_command": "do something"}
        recs = generate_security_recommendations(data)
        assert any("ssh" in r.lower() for r in recs)

    def test_database_keyword_in_value_triggers_db_recommendations(self) -> None:
        data = {"step": "SELECT * FROM users WHERE id=1"}
        recs = generate_security_recommendations(data)
        assert any("parameterized" in r.lower() for r in recs)
        assert any("sql injection" in r.lower() for r in recs)

    def test_database_key_triggers_db_recommendations(self) -> None:
        data = {"query": "list users"}
        recs = generate_security_recommendations(data)
        assert any("parameterized" in r.lower() for r in recs)

    def test_browser_in_value_triggers_web_recommendations(self) -> None:
        data = {"action": "Open browser to dashboard"}
        recs = generate_security_recommendations(data)
        assert any("xss" in r.lower() for r in recs)
        assert any("auth" in r.lower() for r in recs)

    def test_url_key_triggers_web_recommendations(self) -> None:
        data = {"url": "https://example.com"}
        recs = generate_security_recommendations(data)
        assert any("xss" in r.lower() for r in recs)

    def test_combined_categories_produce_all_relevant_recs(self) -> None:
        data = {
            "ssh_cmd": "ssh user@host",
            "query": "select 1",
            "url": "https://x",
        }
        recs = generate_security_recommendations(data)
        joined = " ".join(recs).lower()
        assert "ssh" in joined or "key-based" in joined
        assert "sql" in joined or "parameterized" in joined
        assert "xss" in joined

    def test_match_is_case_insensitive(self) -> None:
        # data_to_lower_cached lowercases the values; the function should
        # therefore not depend on input casing.
        data = {"step": "DATABASE migration via SELECT"}
        assert generate_security_recommendations(data) != []


class TestExtractSecurityWarnings:
    """Warning extraction from keyword metadata."""

    def test_empty_dict_returns_no_warnings(self) -> None:
        assert extract_security_warnings({}) == []

    def test_returns_security_warning_when_present(self) -> None:
        result = extract_security_warnings({"security_warning": "Avoid sudo"})
        assert result == ["Avoid sudo"]

    def test_returns_security_note_when_present(self) -> None:
        result = extract_security_warnings({"security_note": "Read-only OK"})
        assert result == ["Read-only OK"]

    def test_returns_both_warning_and_note_in_order(self) -> None:
        # The function appends warning before note; that ordering is part
        # of the contract for any caller building a single message buffer.
        result = extract_security_warnings(
            {"security_warning": "W", "security_note": "N"}
        )
        assert result == ["W", "N"]

    def test_ignores_unrelated_keys(self) -> None:
        result = extract_security_warnings(
            {"name": "x", "description": "y", "security_warning": "W"}
        )
        assert result == ["W"]
