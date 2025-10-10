"""Performance-oriented tests for Weighted Evidence Bayesian confidence calculations."""

from __future__ import annotations

import time

import pytest

from importobot.medallion.bronze.weighted_evidence_bayesian_confidence import (
    EvidenceMetrics,
    WeightedEvidenceBayesianScorer,
)

# Check for scipy availability
try:
    import scipy  # noqa: F401  # pylint: disable=unused-import

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@pytest.mark.skipif(not HAS_SCIPY, reason="scipy required for uncertainty calculations")
def test_weighted_evidence_confidence_performance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabling uncertainty sampling should deliver a clear speedup."""
    scorer = WeightedEvidenceBayesianScorer()
    metrics = EvidenceMetrics(
        completeness=0.8,
        quality=0.75,
        uniqueness=0.7,
        evidence_count=120,
        unique_count=60,
    )

    # Ensure uncertainty branch executes when enabled
    scorer.parameter_confidence_intervals = {"completeness_weight": (0.2, 0.4)}

    def slow_bounds(_metrics, _format_name):  # type: ignore[override]
        time.sleep(0.002)
        return {
            "confidence_lower_95": 0.1,
            "confidence_upper_95": 0.9,
            "confidence_std": 0.2,
        }

    monkeypatch.setattr(
        scorer,
        "_calculate_confidence_bounds",
        slow_bounds,
        raising=False,
    )

    iterations = 50

    start = time.perf_counter()
    for _ in range(iterations):
        scorer.calculate_confidence(metrics, "Zephyr", use_uncertainty=False)
    elapsed_no_uncertainty = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        scorer.calculate_confidence(metrics, "Zephyr", use_uncertainty=True)
    elapsed_with_uncertainty = time.perf_counter() - start

    assert elapsed_with_uncertainty > elapsed_no_uncertainty
    speedup = elapsed_with_uncertainty / max(elapsed_no_uncertainty, 1e-9)
    assert speedup > 10.0
