"""Expectation rendering helpers for CLI templates."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .default_builder import RenderState

__all__ = ["extract_literal", "extract_step_reference", "render_expectation"]


def render_expectation(
    expected: str | None,
    var_token: str | None,
    *,
    step_index: int,
    state: RenderState,
) -> list[str]:
    """Render expectation assertions for a step."""
    if not expected:
        return []

    expectation = expected.strip()
    if not expectation:
        return []

    lowered = expectation.lower()
    lines: list[str] = [f"    Log    Expected: {expectation}"]

    target_step = extract_step_reference(lowered)
    if target_step is not None and var_token:
        ref_var = state.outputs.get(target_step)
        if ref_var:
            lines.append(f"    Should Be Equal As Strings    {var_token}    {ref_var}")

    literal_match = extract_literal(lowered, ["should include", "contains"])
    if var_token and literal_match:
        lines.append(
            f"    Should Contain    {var_token}    {_normalise_literal(literal_match)}"
        )

    if var_token:
        state.outputs.setdefault(step_index, var_token)

    return lines


def extract_step_reference(text: str) -> int | None:
    """Parse explicit references to previous steps."""
    match = re.search(r"step\s*(\d+)", text)
    if match:
        try:
            return max(int(match.group(1)) - 1, 0)
        except ValueError:
            return None
    if "step1" in text:
        return 0
    if "step2" in text:
        return 1
    return None


def extract_literal(text: str, triggers: list[str]) -> str | None:
    """Extract literal fragments following recognised trigger phrases."""
    for trigger in triggers:
        if trigger in text:
            start = text.find(trigger) + len(trigger)
            literal = text[start:].strip().strip(". ")
            if literal:
                return literal
    return None


def _normalise_literal(literal: str) -> str:
    cleaned = literal.replace("their type", "type")
    cleaned = cleaned.replace("mac address", "mac")
    return cleaned
