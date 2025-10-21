"""Blueprint data models and orchestration primitives."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .registry import get_template
from .utils import Step, extract_test_cases, get_steps, iter_step_text

MatchContext = dict[str, str]


@dataclass
class BlueprintResult:
    """Result returned by blueprint builders."""

    template_candidates: list[str]
    substitutions: dict[str, str]
    default_rendering: str | None = None
    prefer_template: bool = False


@dataclass
class Blueprint:
    """Data-driven blueprint definition."""

    name: str
    trigger_patterns: tuple[re.Pattern[str], ...]
    builder: Callable[
        [list[dict[str, Any]], list[list[Step]], list[MatchContext]],
        BlueprintResult | None,
    ]

    def _prepare_inputs(
        self, data: Any
    ) -> tuple[list[dict[str, Any]], list[list[Step]], list[MatchContext]] | None:
        test_cases = extract_test_cases(data)
        if not test_cases:
            return None

        step_groups: list[list[Step]] = []
        contexts: list[MatchContext] = []
        context_found = False

        for test_case in test_cases:
            steps = get_steps(test_case)
            if not steps:
                return None
            step_groups.append(steps)

            context = self._build_match_context(steps)
            if context:
                context_found = True
            contexts.append(context)

        if not context_found:
            return None

        return test_cases, step_groups, contexts

    def try_render(self, data: Any) -> str | None:
        """Attempt to render a blueprint using prepared test case data."""
        prepared = self._prepare_inputs(data)
        if prepared is None:
            return None

        test_cases, step_groups, contexts = prepared

        result = self.builder(test_cases, step_groups, contexts)
        if not result:
            return None

        if result.default_rendering and not result.prefer_template:
            return result.default_rendering

        for candidate in result.template_candidates:
            template = get_template(candidate)
            if template is not None:
                if hasattr(template, "render_safe"):
                    return template.render_safe(result.substitutions)
                return template.safe_substitute(result.substitutions)

        if result.default_rendering:
            return result.default_rendering
        return None

    def _build_match_context(self, steps: list[Step]) -> MatchContext:
        context: MatchContext = {}
        for step in steps:
            aggregate = " ".join(iter_step_text(step))
            for pattern in self.trigger_patterns:
                match = pattern.search(aggregate)
                if match:
                    for key, value in match.groupdict().items():
                        if value:
                            context[key] = value
        return context


__all__ = ["Blueprint", "BlueprintResult", "MatchContext", "Step"]
