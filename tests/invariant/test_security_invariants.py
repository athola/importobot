"""Security-oriented invariant tests powered by Hypothesis.

These tests exercise the security gateway and validator surface with property-
based inputs to make sure sanitization never fails catastrophically and that
dangerous patterns are consistently flagged.
"""

# pylint: disable=missing-function-docstring

from __future__ import annotations

from typing import Any, Dict

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
        self, payload: Dict[str, Any]
    ) -> None:
        gateway = _security_gateway(SecurityLevel.STRICT)

        try:
            result = gateway.sanitize_api_input(payload, "json")
        except SecurityError as exc:  # pragma: no cover - should not happen
            msg = f"Security gateway should not raise for JSON payloads: {exc}"
            pytest.fail(msg)

        assert result["input_type"] == "json"
        assert isinstance(result["is_safe"], bool)
        assert isinstance(result["security_issues"], list)
        assert isinstance(result["sanitized_data"], dict)

        if result["is_safe"]:
            assert not result["security_issues"]

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

        assert result["is_safe"] is False
        assert any("sanit" in issue.lower() for issue in result["security_issues"])
        sanitized = result["sanitized_data"]
        lowered = sanitized.lower()
        assert "<script" not in lowered and "</script" not in lowered

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

        assert result["is_safe"] is False
        msg = "Dangerous command must surface issues"
        assert result["security_issues"], msg
        assert any(
            "danger" in issue.lower() or "command" in issue.lower()
            for issue in result["security_issues"]
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

        assert result["is_safe"] is False
        msg = "Traversal attempt must yield issues"
        assert result["security_issues"], msg
        keywords = ("path", "traversal", "danger")
        assert any(
            any(keyword in issue.lower() for keyword in keywords)
            for issue in result["security_issues"]
        )
