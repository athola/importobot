"""Security-oriented invariant tests powered by Hypothesis.

These tests exercise the security gateway and validator surface with property-
based inputs to make sure sanitization never fails catastrophically and that
dangerous patterns are consistently flagged.
"""

# pylint: disable=missing-function-docstring

from __future__ import annotations

from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from importobot.services.security_gateway import SecurityError, SecurityGateway
from importobot.services.security_types import SecurityLevel


def _security_gateway(level: SecurityLevel = SecurityLevel.STRICT) -> SecurityGateway:
    """Helper to create a gateway per test without leaking state."""

    return SecurityGateway(level)


class TestSecurityInvariants:
    """Security invariants spanning JSON, string, and file-path sanitization."""

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=32),
            st.recursive(
                st.one_of(
                    st.none(),
                    st.booleans(),
                    st.integers(min_value=-10_000, max_value=10_000),
                    st.floats(allow_nan=False, allow_infinity=False, width=32),
                    st.text(max_size=64),
                ),
                lambda children: st.one_of(
                    st.lists(children, max_size=6),
                    st.dictionaries(
                        st.text(min_size=1, max_size=16), children, max_size=6
                    ),
                ),
                max_leaves=15,
            ),
            max_size=10,
        )
    )
    @settings(max_examples=40)
    def test_json_sanitization_never_raises_and_returns_schema(
        self, payload: dict[str, Any]
    ) -> None:
        gateway = _security_gateway(SecurityLevel.STRICT)

        try:
            result = gateway.sanitize_api_input(payload, "json")
        except SecurityError as exc:  # pragma: no cover - should not happen
            msg = f"Security gateway should not raise for JSON payloads: {exc}"
            pytest.fail(msg)

        assert result.get("input_type") == "json"
        is_safe = bool(result.get("is_safe", False))
        issues = result.get("security_issues", [])
        sanitized_payload = cast(dict[str, Any], result.get("sanitized_data", {}))
        assert isinstance(issues, list)
        assert isinstance(sanitized_payload, dict)

        if is_safe:
            assert not issues

    @given(
        st.text(max_size=40),
        st.text(max_size=40),
        st.text(max_size=40),
    )
    @settings(max_examples=35)
    def test_html_content_is_stripped_and_flagged(
        self, prefix: str, script_body: str, suffix: str
    ) -> None:
        payload = f"{prefix}<script>{script_body}</script>{suffix}"
        gateway = _security_gateway(SecurityLevel.STRICT)

        result = gateway.sanitize_api_input(payload, "string")

        assert bool(result.get("is_safe", False)) is False
        issues = result.get("security_issues", [])
        assert any("sanit" in issue.lower() for issue in issues)
        sanitized = cast(str, result.get("sanitized_data", ""))
        lowered = sanitized.lower()
        assert "<script" not in lowered
        assert "</script" not in lowered

    @given(
        st.text(min_size=1, max_size=40),
        st.text(min_size=0, max_size=40),
    )
    @settings(max_examples=35)
    def test_dangerous_command_patterns_always_trigger_alerts(
        self, prefix: str, suffix: str
    ) -> None:
        # Embed a representative dangerous shell pattern
        payload = f"{prefix} rm -rf / {suffix}"
        gateway = _security_gateway(SecurityLevel.STRICT)

        result = gateway.sanitize_api_input(payload, "string")

        assert bool(result.get("is_safe", False)) is False
        msg = "Dangerous command must surface issues"
        issues = result.get("security_issues", [])
        assert issues, msg
        assert any(
            "danger" in issue.lower() or "command" in issue.lower() for issue in issues
        )

    @given(
        st.text(min_size=0, max_size=10),
        st.text(min_size=0, max_size=10),
        st.text(min_size=0, max_size=10),
    )
    @settings(max_examples=35)
    def test_path_traversal_sequences_never_marked_safe(
        self, segment_a: str, segment_b: str, segment_c: str
    ) -> None:
        path = f"/{segment_a}/../{segment_b}/../{segment_c}/secret.txt"
        gateway = _security_gateway(SecurityLevel.STRICT)

        result = gateway.sanitize_api_input(path, "file_path")

        assert bool(result.get("is_safe", False)) is False
        msg = "Traversal attempt must yield issues"
        issues = result.get("security_issues", [])
        assert issues, msg
        keywords = ("path", "traversal", "danger")
        assert any(
            any(keyword in issue.lower() for keyword in keywords) for issue in issues
        )
