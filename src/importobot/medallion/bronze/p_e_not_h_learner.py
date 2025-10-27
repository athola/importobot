"""P(E|¬H) parameter learning from empirical data.

This module implements data-driven estimation of P(E|¬H) parameters
to replace or validate the hardcoded quadratic decay formula.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

# Local imports for test data (moved here to avoid import-outside-toplevel issues)
from importobot.medallion.interfaces.enums import SupportedFormat

try:
    from tests.unit.medallion.bronze.test_format_detection_integration import (
        TestFormatDetectionIntegration,
    )
except ImportError:
    # To handle cases where test modules are not available
    TestFormatDetectionIntegration: Any = None  # type: ignore[no-redef]

try:
    from scipy import optimize  # pyright: ignore[reportMissingModuleSource]

    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False
    optimize = None  # type: ignore[assignment]


@dataclass
class PENotHParameters:
    """Parameters for P(E|¬H) estimation.

    The formula is: P(E|¬H) = a + b * (1 - L) ** c

    where:
        a: minimum P(E|¬H) for perfect evidence (L=1.0)
        b: scale factor
        c: decay exponent (2.0 = quadratic, 1.0 = linear)
    """

    a: float = 0.01  # Minimum for perfect evidence
    b: float = 0.49  # Scale factor
    c: float = 2.0  # Quadratic decay

    def __call__(self, likelihood: float) -> float:
        """Calculate P(E|¬H) for given likelihood."""
        return float(self.a + self.b * (1.0 - likelihood) ** self.c)

    def validate(self) -> bool:
        """Validate parameters satisfy constraints."""
        # a must be positive and small
        if not 0.0 < self.a < 0.1:
            return False

        # b must be positive
        if not 0.0 < self.b < 1.0:
            return False

        # a + b must be <= 1.0 (probability constraint)
        if self.a + self.b > 1.0:
            return False

        # c must be positive (decay exponent)
        return 0.5 <= self.c <= 3.0


class PENotHLearner:
    """Learn P(E|¬H) parameters from cross-format evidence data."""

    def __init__(self) -> None:
        """Initialize learner with default hardcoded parameters."""
        self.parameters = PENotHParameters()
        self.training_data: list[tuple[float, float]] = []

    def learn_from_cross_format_data(
        self, cross_format_observations: list[tuple[float, float]]
    ) -> PENotHParameters:
        """Learn P(E|¬H) parameters from cross-format likelihood observations.

        Args:
            cross_format_observations: List of (likelihood, observed_p_e_not_h) pairs
                - likelihood: Evidence strength for format A when true format is B
                - observed_p_e_not_h: Empirical frequency of this likelihood

        Returns:
            Learned PENotHParameters

        The learning process:
        1. For each test sample with true_format = F_true:
        2. Measure likelihood L for detecting F_target (where F_target != F_true)
        3. This likelihood represents P(E_target|¬F_target) empirically
        4. Fit parameters (a, b, c) to minimize MSE between:
           - Predicted: a + b * (1 - L) ** c
           - Observed: empirical P(E|¬H)
        """
        self.training_data = cross_format_observations

        if not cross_format_observations:
            return self.parameters

        if not _SCIPY_AVAILABLE:
            # Use lightweight heuristic optimization
            return self._learn_with_heuristics(cross_format_observations)

        # Use scipy optimization for advanced parameter fitting
        return self._learn_with_scipy(cross_format_observations)

    def _learn_with_scipy(
        self, observations: list[tuple[float, float]]
    ) -> PENotHParameters:
        """Learn parameters using scipy optimization."""
        assert optimize is not None

        def objective(params: np.ndarray) -> float:
            a, b, c = params
            mse = 0.0
            for likelihood, observed_p in observations:
                predicted = a + b * (1.0 - likelihood) ** c
                mse += (predicted - observed_p) ** 2
            return mse / len(observations)

        # Constraint to ensure a + b <= 1
        sum_constraint = optimize.NonlinearConstraint(
            lambda x: x[0] + x[1], -np.inf, 1.0
        )

        # Bounds
        bounds = [
            (0.001, 0.1),  # a
            (0.1, 0.9),  # b
            (0.5, 3.0),  # c
        ]

        # Initial guess: current hardcoded values
        x0 = np.array([self.parameters.a, self.parameters.b, self.parameters.c])

        result = optimize.minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=(sum_constraint,),
        )

        if result.success:
            learned = PENotHParameters(
                a=float(result.x[0]), b=float(result.x[1]), c=float(result.x[2])
            )
            if learned.validate():
                return learned

        # If optimization fails, return hardcoded
        return self.parameters

    def _learn_with_heuristics(
        self, observations: list[tuple[float, float]]
    ) -> PENotHParameters:
        """Learn parameters using simple heuristics without scipy."""
        likelihoods = np.array([L for L, _ in observations])
        observed_p = np.array([p for _, p in observations])

        # Estimate 'a' from high likelihood samples (L > 0.9)
        high_lik_mask = likelihoods > 0.9
        if high_lik_mask.any():
            a_est = float(np.mean(observed_p[high_lik_mask]))
            a = np.clip(a_est, 0.001, 0.1)
        else:
            a = self.parameters.a

        # Estimate 'b' from low likelihood samples (L < 0.1)
        low_lik_mask = likelihoods < 0.1
        if low_lik_mask.any():
            b_est = float(np.mean(observed_p[low_lik_mask])) - a
            b = np.clip(b_est, 0.1, 0.9)
        else:
            b = self.parameters.b

        # Estimate decay exponent `c` from remaining points.
        eps = 1e-8
        denom = max(b, eps)
        valid_mask = (
            (likelihoods < 0.999)
            & (likelihoods > eps)
            & (observed_p > a + eps)
            & (observed_p < a + b - eps)
        )
        if valid_mask.any():
            ratios = np.clip((observed_p[valid_mask] - a) / denom, eps, 1.0 - eps)
            bases = np.clip(1.0 - likelihoods[valid_mask], eps, 1.0 - eps)
            c_samples = np.log(ratios) / np.log(bases)
            finite_samples = c_samples[np.isfinite(c_samples)]
            if finite_samples.size > 0:
                c_est = float(np.mean(finite_samples))
                c = float(np.clip(c_est, 0.5, 3.0))
                if abs(c - self.parameters.c) < 0.1:
                    c = self.parameters.c
            else:
                c = self.parameters.c
        else:
            c = self.parameters.c

        learned = PENotHParameters(a=a, b=b, c=c)
        if learned.validate():
            return learned

        return self.parameters

    def compare_with_hardcoded(
        self, cross_format_observations: list[tuple[float, float]]
    ) -> dict[str, float]:
        """Compare learned vs hardcoded parameters.

        Returns:
            Dictionary with comparison metrics:
            - mse_hardcoded: MSE of hardcoded formula
            - mse_learned: MSE of learned formula
            - improvement_percent: % improvement
        """
        if not cross_format_observations:
            return {}

        hardcoded = PENotHParameters()  # Default hardcoded values
        learned = self.learn_from_cross_format_data(cross_format_observations)

        mse_hardcoded = 0.0
        mse_learned = 0.0

        for likelihood, observed_p in cross_format_observations:
            pred_hardcoded = hardcoded(likelihood)
            pred_learned = learned(likelihood)

            mse_hardcoded += (pred_hardcoded - observed_p) ** 2
            mse_learned += (pred_learned - observed_p) ** 2

        mse_hardcoded /= len(cross_format_observations)
        mse_learned /= len(cross_format_observations)

        improvement = (
            ((mse_hardcoded - mse_learned) / mse_hardcoded * 100)
            if mse_hardcoded > 0
            else 0.0
        )

        return {
            "mse_hardcoded": mse_hardcoded,
            "mse_learned": mse_learned,
            "improvement_percent": improvement,
            "learned_a": learned.a,
            "learned_b": learned.b,
            "learned_c": learned.c,
        }


def load_test_data_for_learning() -> list[tuple[dict[str, Any], Any]]:
    """Load labeled test data from integration test fixtures.

    Returns:
        List of (test_data, ground_truth_format) tuples
    """
    if SupportedFormat is None or TestFormatDetectionIntegration is None:
        return []

    if TestFormatDetectionIntegration is not None:
        test_instance = TestFormatDetectionIntegration()
        if hasattr(test_instance, "setUp"):
            test_instance.setUp()  # type: ignore[no-untyped-call]

    labeled_samples = []

    # Map test data keys to formats
    format_mapping = {
        "zephyr_complete": SupportedFormat.ZEPHYR,
        "xray_with_jira": SupportedFormat.JIRA_XRAY,
        "testrail_api_response": SupportedFormat.TESTRAIL,
        "testlink_xml_export": SupportedFormat.TESTLINK,
        "generic_unstructured": SupportedFormat.GENERIC,
    }

    for key, true_format in format_mapping.items():
        if key in test_instance.test_data_samples:
            labeled_samples.append((test_instance.test_data_samples[key], true_format))

    return labeled_samples


__all__ = ["PENotHLearner", "PENotHParameters", "load_test_data_for_learning"]
