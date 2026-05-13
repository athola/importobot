"""Lightweight compliance scoring helpers for enterprise deployments."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from importobot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComplianceRule:
    """Represents a single compliance control with a weight."""

    identifier: str
    description: str
    weight: float = 1.0


@dataclass
class ComplianceControl:
    """Evaluation result for a specific rule."""

    rule: ComplianceRule
    passed: bool
    evidence: str | None = None


@dataclass
class ComplianceReport:
    """Aggregated compliance report for enterprise customers."""

    controls: list[ComplianceControl]
    score: float
    maximum: float

    @property
    def percentage(self) -> float:
        """Return the overall compliance percentage rounded to two decimals."""
        return 0.0 if self.maximum == 0 else round((self.score / self.maximum) * 100, 2)


class EnterpriseComplianceEngine:
    """Evaluates compliance controls and produces deterministic reports."""

    def __init__(self, rules: Iterable[ComplianceRule]) -> None:
        """Initialize the engine with the available compliance rules."""
        self.rules = list(rules)

    def evaluate(self, passed_ids: set[str]) -> ComplianceReport:
        """Produce a ComplianceReport for the given rule identifiers."""
        controls: list[ComplianceControl] = []
        score = 0.0
        maximum = 0.0
        for rule in self.rules:
            maximum += rule.weight
            passed = rule.identifier in passed_ids
            if passed:
                score += rule.weight
            controls.append(ComplianceControl(rule=rule, passed=passed))
        logger.info(
            "Generated compliance report for %d rules (score %.2f/%0.2f)",
            len(controls),
            score,
            maximum,
        )
        return ComplianceReport(controls=controls, score=score, maximum=maximum)
