"""Blueprint registry and rendering entry-points."""

from __future__ import annotations

import os
import re
from typing import Any

from .default_builder import _build_command_suite
from .models import Blueprint
from .registry import TEMPLATE_STATE

# Generic blueprint for command execution tests
# Detects patterns like "remote: ls -la" or "local: echo test"
# No hard-coded command lists or customer-specific flags
BLUEPRINTS: tuple[Blueprint, ...] = (
    Blueprint(
        name="command_execution",
        trigger_patterns=(
            # Pattern 1: Explicit context (remote:, local:, etc.)
            re.compile(
                r"(?:on\s+)?(?P<context>[a-z_]+)\s*:\s*(?P<command>.+)",
                re.IGNORECASE,
            ),
            # Pattern 2: Generic command pattern (any word followed by args)
            re.compile(
                r"(?P<command>[a-z0-9_\-/]+(?:\s+[^\n]+)?)",
                re.IGNORECASE,
            ),
        ),
        builder=_build_command_suite,
    ),
)


def render_with_blueprints(data: Any) -> str | None:
    """Render Robot Framework content using registered blueprints."""
    forced = os.getenv("IMPORTOBOT_FORCE_BLUEPRINTS", "0").lower() in {
        "1",
        "true",
        "yes",
    }
    if os.getenv("IMPORTOBOT_DISABLE_BLUEPRINTS", "0").lower() in {
        "1",
        "true",
        "yes",
    }:
        return None
    if not forced and not TEMPLATE_STATE.get("enabled", False):
        return None
    for blueprint in BLUEPRINTS:
        rendered = blueprint.try_render(data)
        if rendered is not None:
            return rendered
    return None


__all__ = ["BLUEPRINTS", "render_with_blueprints"]
