#!/usr/bin/env python
"""Analyze empirical P(E|¬H) from existing test data.

This script collects cross-format evidence from existing test fixtures
to determine if the hardcoded quadratic decay formula P(E|¬H) = 0.01 + 0.49×(1-L)²
matches empirical observations.

Usage:
    uv run python -m importobot_scripts.analyze_empirical_p_e_not_h
"""

from __future__ import annotations

import sys
from typing import Any

from importobot.medallion.bronze.evidence_accumulator import EvidenceAccumulator
from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.interfaces.enums import SupportedFormat


def get_test_data_samples() -> list[tuple[dict[str, Any], SupportedFormat]]:
    """Extract labeled test data samples from integration tests.

    Returns:
        List of (test_data, ground_truth_format) pairs
    """
    # Import test data
    from tests.unit.medallion.bronze.test_format_detection_integration import (  # type: ignore[import-untyped]
        TestFormatDetectionIntegration,
    )

    test_instance = TestFormatDetectionIntegration()
    test_instance.setUp()

    samples = []

    # Map test data keys to their true formats
    format_mapping = {
        "zephyr_complete": SupportedFormat.ZEPHYR,
        "xray_with_jira": SupportedFormat.JIRA_XRAY,
        "testrail_api_response": SupportedFormat.TESTRAIL,
        "testlink_xml_export": SupportedFormat.TESTLINK,
        "generic_unstructured": SupportedFormat.GENERIC,
    }

    for key, true_format in format_mapping.items():
        if key in test_instance.test_data_samples:
            samples.append((test_instance.test_data_samples[key], true_format))

    return samples


def collect_cross_format_evidence(
    samples: list[tuple[dict[str, Any], SupportedFormat]],
    detector: FormatDetector,
) -> dict[SupportedFormat, list[tuple[float, SupportedFormat]]]:
    """Collect evidence for each format across all test samples.

    Args:
        samples: List of (test_data, ground_truth_format) pairs
        detector: Format detector instance

    Returns:
        Dictionary mapping target_format to list of (likelihood, true_format) pairs
        where true_format != target_format (cross-format evidence)
    """
    cross_format_evidence: dict[
        SupportedFormat, list[tuple[float, SupportedFormat]]
    ] = {fmt: [] for fmt in SupportedFormat}

    # Get the bayesian scorer from evidence accumulator
    bayesian_scorer = detector.evidence_accumulator.bayesian_scorer

    for test_data, true_format in samples:
        # For each format, collect evidence from this test sample
        for target_format in SupportedFormat:
            # Create accumulator for this detection attempt
            accumulator = EvidenceAccumulator()

            # Collect evidence as if we're detecting target_format
            evidence_items, total_weight = detector.evidence_collector.collect_evidence(
                test_data, target_format
            )

            # Build evidence profile
            for item in evidence_items:
                accumulator.add_evidence(target_format.name, item)
            accumulator.set_total_possible_weight(target_format.name, total_weight)

            # Get the profile and convert to metrics
            profile = accumulator.evidence_profiles[target_format.name]
            metrics = accumulator._profile_to_metrics(profile)

            # Calculate likelihood using current parameters
            likelihood = bayesian_scorer.calculate_likelihood(metrics)

            # Store as cross-format evidence if true format != target format
            if true_format != target_format:
                cross_format_evidence[target_format].append((likelihood, true_format))

    return cross_format_evidence


def analyze_p_e_not_h(
    cross_format_evidence: dict[SupportedFormat, list[tuple[float, SupportedFormat]]],
) -> None:
    """Analyze and compare empirical vs hardcoded P(E|¬H).

    Args:
        cross_format_evidence: Cross-format likelihood observations
    """
    import numpy as np

    print("=" * 80)
    print("EMPIRICAL P(E|¬H) ANALYSIS")
    print("=" * 80)
    print()
    print("Comparing hardcoded quadratic formula vs observed cross-format evidence")
    print("Formula: P(E|¬H) = 0.01 + 0.49 × (1-L)²")
    print()

    for target_format, observations in cross_format_evidence.items():
        if not observations:
            continue

        likelihoods = [lik for lik, _ in observations]

        print(f"\n{target_format.name}")
        print("-" * 40)
        print(f"  Samples from other formats: {len(observations)}")
        print(f"  Likelihood range: [{min(likelihoods):.3f}, {max(likelihoods):.3f}]")
        print(f"  Mean likelihood: {np.mean(likelihoods):.3f}")
        print(f"  Median likelihood: {np.median(likelihoods):.3f}")

        # Calculate empirical P(E|¬H) using hardcoded formula
        empirical_p_e_not_h = [0.01 + 0.49 * (1 - L) ** 2 for L in likelihoods]
        print(
            f"  Hardcoded P(E|¬H) range: [{min(empirical_p_e_not_h):.3f},"
            f" {max(empirical_p_e_not_h):.3f}]"
        )
        print(f"  Mean P(E|¬H): {np.mean(empirical_p_e_not_h):.3f}")

        # Show breakdown by source format
        format_breakdown: dict[SupportedFormat, list[float]] = {}
        for lik, source_fmt in observations:
            if source_fmt not in format_breakdown:
                format_breakdown[source_fmt] = []
            format_breakdown[source_fmt].append(lik)

        print("  Breakdown by source format:")
        for source_fmt, source_liks in format_breakdown.items():
            print(
                f"    {source_fmt.name}: {len(source_liks)} samples,"
                f" mean L={np.mean(source_liks):.3f}"
            )


def calculate_posterior_with_current_formula(
    samples: list[tuple[dict[str, Any], SupportedFormat]], detector: FormatDetector
) -> None:
    """Validate that current formula produces >0.8 confidence for strong evidence.

    Args:
        samples: Test data samples
        detector: Format detector instance
    """
    print("\n" + "=" * 80)
    print("VALIDATION: Strong Evidence → Confidence >0.8")
    print("=" * 80)
    print()

    bayesian_scorer = detector.evidence_accumulator.bayesian_scorer

    for test_data, true_format in samples:
        # Create accumulator
        accumulator = EvidenceAccumulator()

        # Collect evidence for the TRUE format
        evidence_items, total_weight = detector.evidence_collector.collect_evidence(
            test_data, true_format
        )

        # Build profile
        for item in evidence_items:
            accumulator.add_evidence(true_format.name, item)
        accumulator.set_total_possible_weight(true_format.name, total_weight)

        profile = accumulator.evidence_profiles[true_format.name]
        metrics = accumulator._profile_to_metrics(profile)

        # Calculate confidence
        result = bayesian_scorer.calculate_confidence(
            metrics, true_format.name, use_uncertainty=False
        )

        likelihood = result["likelihood"]
        confidence = result["confidence"]

        # Calculate what P(E|¬H) was used
        p_e_not_h = 0.01 + 0.49 * (1 - likelihood) ** 2

        status = "✓ PASS" if confidence > 0.8 else "✗ FAIL"
        if likelihood > 0.9:
            print(
                f"{status} {true_format.name:15s} L={likelihood:.3f}"
                f" P(E|¬H)={p_e_not_h:.3f} → Conf={confidence:.3f}"
            )


def main() -> int:
    """Main analysis routine."""
    print("Loading test data samples...")
    samples = get_test_data_samples()
    print(f"Loaded {len(samples)} labeled test samples")
    print()

    print("Initializing format detector...")
    detector = FormatDetector()
    print()

    print("Collecting cross-format evidence...")
    cross_format_evidence = collect_cross_format_evidence(samples, detector)
    print()

    # Analysis
    analyze_p_e_not_h(cross_format_evidence)

    # Validation
    calculate_posterior_with_current_formula(samples, detector)

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    print("1. If empirical P(E|¬H) closely matches hardcoded formula:")
    print("   → Current formula is adequate, no change needed")
    print()
    print("2. If empirical P(E|¬H) differs significantly (>10% MSE):")
    print("   → Consider learning parameters (a, b, c) from data")
    print()
    print("3. If cross-format likelihoods are highly variable:")
    print("   → Consider format-specific P(E|¬H) models")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
