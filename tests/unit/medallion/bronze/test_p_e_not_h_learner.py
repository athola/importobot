"""Tests for P(E|¬H) parameter learning."""

from __future__ import annotations

import numpy as np
import pytest

import importobot.medallion.bronze.p_e_not_h_learner as learner_module
from importobot.medallion.bronze.p_e_not_h_learner import (
    PENotHLearner,
    PENotHParameters,
)


class TestPENotHParameters:
    """Test suite for P(E|¬H) parameters."""

    def test_default_parameters_validate(self):
        """Default hardcoded parameters should validate."""
        params = PENotHParameters()
        assert params.validate() is True
        assert params.a == 0.01
        assert params.b == 0.49
        assert params.c == 2.0

    def test_call_with_zero_likelihood(self):
        """P(E|¬H) at L=0 should be a + b."""
        params = PENotHParameters()
        result = params(0.0)
        # 0.01 + 0.49 * (1-0)^2 = 0.01 + 0.49 = 0.50
        assert result == pytest.approx(0.50, abs=1e-6)

    def test_call_with_perfect_likelihood(self):
        """P(E|¬H) at L=1 should be a."""
        params = PENotHParameters()
        result = params(1.0)
        # 0.01 + 0.49 * (1-1)^2 = 0.01
        assert result == pytest.approx(0.01, abs=1e-6)

    def test_call_with_mid_likelihood(self):
        """P(E|¬H) at L=0.5."""
        params = PENotHParameters()
        result = params(0.5)
        # 0.01 + 0.49 * 0.5^2 = 0.01 + 0.1225 = 0.1325
        assert result == pytest.approx(0.1325, abs=1e-4)

    def test_invalid_a_too_large(self):
        """'a' must be < 0.1."""
        params = PENotHParameters(a=0.5, b=0.3, c=2.0)
        assert params.validate() is False

    def test_invalid_b_negative(self):
        """'b' must be positive."""
        params = PENotHParameters(a=0.01, b=-0.1, c=2.0)
        assert params.validate() is False

    def test_invalid_sum_exceeds_one(self):
        """a + b must be <= 1.0."""
        params = PENotHParameters(a=0.6, b=0.5, c=2.0)
        assert params.validate() is False

    def test_invalid_c_too_small(self):
        """c must be >= 0.5."""
        params = PENotHParameters(a=0.01, b=0.49, c=0.1)
        assert params.validate() is False


class TestPENotHLearner:
    """Test suite for P(E|¬H) learner."""

    def test_initialization(self):
        """Learner initializes with hardcoded parameters."""
        learner = PENotHLearner()
        assert learner.parameters.a == 0.01
        assert learner.parameters.b == 0.49
        assert learner.parameters.c == 2.0
        assert len(learner.training_data) == 0

    def test_learn_from_empty_data(self):
        """Learning from empty data returns hardcoded params."""
        learner = PENotHLearner()
        learned = learner.learn_from_cross_format_data([])
        assert learned.a == 0.01
        assert learned.b == 0.49
        assert learned.c == 2.0

    def test_learn_from_perfect_quadratic_data(self):
        """If data exactly matches quadratic formula, should learn same params."""
        learner = PENotHLearner()

        # Generate synthetic data from hardcoded formula
        hardcoded = PENotHParameters()
        synthetic_data = [
            (likelihood, hardcoded(likelihood))
            for likelihood in [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]
        ]

        learned = learner.learn_from_cross_format_data(synthetic_data)

        # Should learn similar parameters
        assert learned.a == pytest.approx(hardcoded.a, abs=0.01)
        assert learned.b == pytest.approx(hardcoded.b, abs=0.01)
        assert learned.c == pytest.approx(hardcoded.c, abs=0.1)

    def test_learn_from_linear_decay_data(self):
        """If data is linear, should learn c ≈ 1.0."""
        learner = PENotHLearner()

        # Generate linear decay data: P(E|¬H) = 0.02 + 0.48 * (1-likelihood)
        linear_params = PENotHParameters(a=0.02, b=0.48, c=1.0)
        synthetic_data = [
            (likelihood, linear_params(likelihood))
            for likelihood in [0.0, 0.3, 0.6, 0.9, 1.0]
        ]

        learned = learner.learn_from_cross_format_data(synthetic_data)

        # Should learn linear decay (c close to 1.0)
        assert learned.validate() is True
        assert learned.c < 1.5  # Closer to linear than quadratic

    def test_compare_with_hardcoded(self):
        """Comparison metrics should be computed correctly."""
        learner = PENotHLearner()

        # Data that exactly matches hardcoded formula
        hardcoded = PENotHParameters()
        perfect_data = [
            (likelihood, hardcoded(likelihood)) for likelihood in [0.0, 0.5, 1.0]
        ]

        comparison = learner.compare_with_hardcoded(perfect_data)

        assert "mse_hardcoded" in comparison
        assert "mse_learned" in comparison
        assert "improvement_percent" in comparison

        # For perfect data, MSE should be near zero
        assert comparison["mse_hardcoded"] < 1e-6
        assert comparison["mse_learned"] < 1e-6

    def test_heuristic_fallback_when_scipy_unavailable(self, monkeypatch):
        """Should use heuristics when scipy is not available."""
        monkeypatch.setattr(learner_module, "_SCIPY_AVAILABLE", False)
        monkeypatch.setattr(learner_module, "optimize", None)

        learner = learner_module.PENotHLearner()

        # Generate test data
        test_data = [
            (0.0, 0.5),  # Low likelihood → high P(E|¬H)
            (0.5, 0.13),  # Mid
            (1.0, 0.01),  # High likelihood → low P(E|¬H)
        ]

        learned = learner.learn_from_cross_format_data(test_data)

        # Should produce valid parameters
        assert learned.validate() is True
        # Heuristic keeps quadratic decay
        assert learned.c == 2.0

    def test_learned_parameters_maintain_monotonicity(self):
        """Learned P(E|¬H) should be monotonically decreasing in likelihood."""
        learner = PENotHLearner()

        # Generate noisy data
        np.random.seed(42)
        test_data = []
        for likelihood in [0.1, 0.3, 0.5, 0.7, 0.9]:
            # Add some noise to hardcoded formula
            noise = np.random.normal(0, 0.02)
            p_base = 0.01 + 0.49 * (1 - likelihood) ** 2
            test_data.append((likelihood, max(0.01, min(0.5, p_base + noise))))

        learned = learner.learn_from_cross_format_data(test_data)

        # Check monotonicity
        for i in range(100):
            likelihood1 = i / 100
            likelihood2 = (i + 1) / 100
            assert learned(likelihood1) >= learned(likelihood2) - 1e-6  # Allow error


class TestPENotHIntegration:
    """Integration tests for P(E|¬H) learning."""

    def test_improvement_detection(self):
        """Should detect when learned params improve over hardcoded."""
        learner = PENotHLearner()

        # Generate data with different decay (cubic instead of quadratic)
        cubic_params = PENotHParameters(a=0.01, b=0.49, c=3.0)
        cubic_data = [
            (likelihood, cubic_params(likelihood))
            for likelihood in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        ]

        comparison = learner.compare_with_hardcoded(cubic_data)

        # Learned should be better than hardcoded for cubic data
        assert comparison["mse_learned"] < comparison["mse_hardcoded"]
        assert comparison["improvement_percent"] > 0

    def test_no_degradation_on_perfect_match(self):
        """Learned params should not degrade on data matching hardcoded."""
        learner = PENotHLearner()

        hardcoded = PENotHParameters()
        perfect_data = [
            (likelihood, hardcoded(likelihood))
            for likelihood in [0.0, 0.25, 0.5, 0.75, 1.0]
        ]

        comparison = learner.compare_with_hardcoded(perfect_data)

        # Should be near zero improvement (both near perfect)
        assert abs(comparison["improvement_percent"]) < 5.0  # Within 5%
