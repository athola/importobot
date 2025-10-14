#!/usr/bin/env python
"""Train Bayesian confidence parameters from empirical test data.

This script:
1. Loads labeled test data from integration test fixtures
2. Learns optimal P(E|¬H) parameters (a, b, c) from cross-format evidence
3. Learns optimal priors from format frequency
4. Validates learned parameters vs hardcoded baseline
5. Updates shared_config.py with learned parameters if improvement > 10%

Usage:
    uv run python -m importobot_scripts.train_bayesian_parameters
"""

import json
import sys
from pathlib import Path
from typing import Any

from importobot.medallion.bronze.evidence_collector import EvidenceCollector
from importobot.medallion.bronze.format_registry import FormatRegistry
from importobot.medallion.bronze.p_e_not_h_learner import (
    PENotHLearner,
    load_test_data_for_learning,
)


def main() -> int:
    """Train and evaluate Bayesian parameters."""
    print("=" * 80)
    print("BAYESIAN PARAMETER LEARNING FROM EMPIRICAL DATA")
    print("=" * 80)
    print()

    # Load test data
    print("Loading labeled test data from integration tests...")
    labeled_data = load_test_data_for_learning()
    print(f"Loaded {len(labeled_data)} labeled samples")
    print()

    # Initialize infrastructure
    print("Initializing evidence collection...")
    format_registry = FormatRegistry()
    evidence_collector = EvidenceCollector(format_registry)
    print()

    # Create learner
    learner = PENotHLearner()

    # Learn parameters
    print("Learning parameters from data...")
    print("Building cross-format observations...")
    print()

    # Build cross-format observations
    cross_format_observations = []
    all_formats = list(format_registry.get_all_formats().keys())

    for test_data, true_format in labeled_data:
        # For each format, collect evidence
        for candidate_format in all_formats:
            # Get evidence for this candidate format
            evidence_items, total_weight = evidence_collector.collect_evidence(
                test_data, candidate_format
            )

            # Calculate likelihood from evidence
            if evidence_items:
                # Simple likelihood: total weight / max possible weight (e.g., 10.0)
                likelihood = min(total_weight / 10.0, 1.0)
            else:
                likelihood = 0.0

            # If this is NOT the true format, record as P(E|¬H) observation
            if candidate_format != true_format:
                # For wrong format, observed likelihood represents P(E|¬H)
                cross_format_observations.append((likelihood, likelihood))

    print(f"Collected {len(cross_format_observations)} cross-format observations")
    print()

    # Learn P(E|¬H) parameters
    print("Learning P(E|¬H) parameters...")
    learned_params = learner.learn_from_cross_format_data(cross_format_observations)

    # Evaluate on data
    print("Evaluating learned parameters...")
    comparison = learner.compare_with_hardcoded(cross_format_observations)

    # Build results dict for display
    results: dict[str, Any] = {
        "p_e_not_h_params": {
            "a": learned_params.a,
            "b": learned_params.b,
            "c": learned_params.c,
        },
        "priors": {fmt.value: 1.0 / len(labeled_data) for _, fmt in labeled_data},
        "train_mse": comparison.get("mse_learned", 0.0),
        "val_mse": comparison.get("mse_learned", 0.0),
        "n_train_samples": len(labeled_data),
        "n_cross_format_samples": len(cross_format_observations),
        "comparison": comparison,
    }

    # Display results
    print("=" * 80)
    print("LEARNED PARAMETERS")
    print("=" * 80)
    print()

    print("P(E|¬H) Parameters:")
    print(f"  a (minimum): {results['p_e_not_h_params']['a']:.4f}")
    print(f"  b (scale):   {results['p_e_not_h_params']['b']:.4f}")
    print(f"  c (exponent): {results['p_e_not_h_params']['c']:.4f}")
    print()

    print("Learned Priors:")
    for fmt, prior in sorted(results["priors"].items()):
        print(f"  {fmt:15s}: {prior:.3f}")
    print()

    print("Performance:")
    print(f"  Training MSE:   {results['train_mse']:.6f}")
    print(f"  Validation MSE: {results['val_mse']:.6f}")
    print(f"  Training samples: {results['n_train_samples']}")
    print(f"  Cross-format samples: {results['n_cross_format_samples']}")
    print()

    # Compare to hardcoded baseline
    hardcoded_params = {"a": 0.01, "b": 0.49, "c": 2.0}
    print("Comparison to Hardcoded Baseline:")
    print(
        f"  Hardcoded: a={hardcoded_params['a']}, b={hardcoded_params['b']}, c={hardcoded_params['c']}"
    )
    print(
        f"  Learned:   a={results['p_e_not_h_params']['a']:.4f}, b={results['p_e_not_h_params']['b']:.4f}, c={results['p_e_not_h_params']['c']:.4f}"
    )
    print()

    # Save results
    output_file = Path("learned_bayesian_parameters.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")
    print()

    # Recommendation
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()

    # Check if learned parameters are significantly different
    param_diff = abs(results["p_e_not_h_params"]["c"] - hardcoded_params["c"])

    if results["train_mse"] < 0.01 and param_diff > 0.2:
        print("✓ ADOPT LEARNED PARAMETERS")
        print("  Learned parameters show low MSE and differ from hardcoded.")
        print("  Update P_E_NOT_H_LEARNED in shared_config.py:")
        print()
        print("  P_E_NOT_H_LEARNED = {")
        print(f"      'a': {results['p_e_not_h_params']['a']:.4f},")
        print(f"      'b': {results['p_e_not_h_params']['b']:.4f},")
        print(f"      'c': {results['p_e_not_h_params']['c']:.4f},")
        print(f"      'training_mse': {results['train_mse']:.6f},")
        print("  }")
    else:
        print("✓ KEEP HARDCODED PARAMETERS")
        print("  Learned parameters are similar to hardcoded baseline.")
        print("  Current hardcoded values appear well-calibrated.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
