"""Learn P(E|¬H) parameters from empirical cross-format evidence.

Replaces hardcoded quadratic decay with data-driven parameter estimation
based on observed likelihood patterns from test data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

# TODO: Implement proper test data feeding system for learning P(E|¬H) parameters
# Issue: https://github.com/athola/importobot/issues/83
# Production code should load from external data sources, not test modules.

try:
    from scipy import optimize  # pyright: ignore[reportMissingModuleSource]

    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False
    optimize = None  # type: ignore[assignment]


@dataclass
class PENotHParameters:
    """Parameters for P(E|¬H) estimation using formula: P(E|¬H) = a + b * (1 - L) ** c.

    Args:
        a: Minimum P(E|¬H) for perfect evidence (L=1.0)
        b: Scale factor
        c: Decay exponent (2.0 = quadratic, 1.0 = linear)
    """

    a: float = 0.01
    b: float = 0.49
    c: float = 2.0

    def __call__(self, likelihood: float) -> float:
        """Calculate P(E|¬H) for given likelihood."""
        return float(self.a + self.b * (1.0 - likelihood) ** self.c)

    def validate(self) -> bool:
        """Validate parameters satisfy probability and range constraints."""
        if not 0.0 < self.a < 0.1:
            return False
        if not 0.0 < self.b < 1.0:
            return False
        if self.a + self.b > 1.0:
            return False
        return 0.5 <= self.c <= 3.0


class PENotHLearner:
    """Learn P(E|¬H) parameters from cross-format evidence data."""

    def __init__(self) -> None:
        """Initialize learner with default parameters."""
        self.parameters = PENotHParameters()
        self.training_data: list[tuple[float, float]] = []

    def learn_from_cross_format_data(
        self, cross_format_observations: list[tuple[float, float]]
    ) -> PENotHParameters:
        """Learn P(E|¬H) parameters from cross-format likelihood observations.

        Args:
            cross_format_observations: List of (likelihood, observed_p_e_not_h) pairs

        Returns:
            Learned PENotHParameters

        Fits parameters (a, b, c) to minimize MSE between predicted and observed values.
        """
        self.training_data = cross_format_observations

        if not cross_format_observations:
            return self.parameters

        if not _SCIPY_AVAILABLE:
            return self._learn_with_heuristics(cross_format_observations)

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

        sum_constraint = optimize.NonlinearConstraint(
            lambda x: x[0] + x[1], -np.inf, 1.0
        )

        bounds = [
            (0.001, 0.1),  # a
            (0.1, 0.9),  # b
            (0.5, 3.0),  # c
        ]

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

        return self.parameters

    def _learn_with_heuristics(
        self, observations: list[tuple[float, float]]
    ) -> PENotHParameters:
        """Learn parameters using heuristic estimation when scipy unavailable."""
        likelihoods = np.array([L for L, _ in observations])
        observed_p = np.array([p for _, p in observations])

        high_lik_mask = likelihoods > 0.9
        if high_lik_mask.any():
            a_est = float(np.mean(observed_p[high_lik_mask]))
            a = np.clip(a_est, 0.001, 0.1)
        else:
            a = self.parameters.a

        low_lik_mask = likelihoods < 0.1
        if low_lik_mask.any():
            b_est = float(np.mean(observed_p[low_lik_mask])) - a
            b = np.clip(b_est, 0.1, 0.9)
        else:
            b = self.parameters.b

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
            Dictionary with MSE comparison and improvement metrics.
        """
        if not cross_format_observations:
            return {}

        hardcoded = PENotHParameters()
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
    """Load labeled test data for learning P(E|¬H) parameters.

    Returns:
        List of (test_data, ground_truth_format) tuples.

    TODO: Implement proper test data feeding system for learning P(E|¬H) parameters
    Issue: https://github.com/athola/importobot/issues/83
    Production code should load from external data sources, not test modules.
    """
    return []


__all__ = ["PENotHLearner", "PENotHParameters", "load_test_data_for_learning"]
