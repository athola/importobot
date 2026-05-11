"""Tests for the enterprise compliance engine."""

from __future__ import annotations

from importobot_enterprise.compliance import (
    ComplianceRule,
    EnterpriseComplianceEngine,
)


def test_compliance_engine_scores_rules() -> None:
    rules = [
        ComplianceRule(
            identifier="SOC2.AC-1", description="Access reviews", weight=2.0
        ),
        ComplianceRule(
            identifier="SOC2.AC-2", description="Least privilege", weight=1.0
        ),
    ]
    engine = EnterpriseComplianceEngine(rules)
    report = engine.evaluate({"SOC2.AC-1"})

    assert report.score == 2.0
    assert report.maximum == 3.0
    assert report.percentage == round((2.0 / 3.0) * 100, 2)
    assert len(report.controls) == 2
