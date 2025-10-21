"""Blueprint registry and rendering entry-points."""

from __future__ import annotations

import re
from typing import Any

from .cli import _build_cli_task_suite
from .models import Blueprint

BLUEPRINTS: tuple[Blueprint, ...] = (
    Blueprint(
        name="cli_proc_task",
        trigger_patterns=(
            re.compile(
                r"(?:on\s+)?cli\s*:\s*(?P<command>[a-z0-9_\-]+)"
                r"(?:[\s\S]*?--proc_name\s+(?P<proc_name>[^\s]+))?",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?P<command>touch|rm|ls|cat|mkdir|cp|mv|chmod|chown|echo|grep|find|ps|kill|ping|wget|curl|tar|gzip|gunzip|df|du|free|top|netstat)\s+"
                r"(?:[\s\S]*?--proc_name\s+(?P<proc_name>[^\s]+))?",
                re.IGNORECASE,
            ),
        ),
        builder=_build_cli_task_suite,
    ),
)


def render_with_blueprints(data: Any) -> str | None:
    """Render Robot Framework content using registered blueprints."""
    for blueprint in BLUEPRINTS:
        rendered = blueprint.try_render(data)
        if rendered is not None:
            return rendered
    return None


__all__ = ["BLUEPRINTS", "render_with_blueprints"]
