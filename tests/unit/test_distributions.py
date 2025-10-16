"""Tests for distribution and weight management."""

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from importobot.utils.test_generation.categories import CategoryEnum
from importobot.utils.test_generation.distributions import (
    DistributionDict,
    DistributionManager,
    WeightsDict,
    print_test_distribution,
)


class TestDistributionManagerBasicUsage:
    """Test basic DistributionManager usage and get_test_distribution method."""

    def test_get_test_distribution_with_distribution(self):
        """Test get_test_distribution with explicit distribution."""
        distribution = {"category1": 10, "category2": 20, "category3": 30}

        result = DistributionManager.get_test_distribution(
            60, distribution=distribution
        )

        assert result == distribution

    def test_get_test_distribution_with_weights(self):
        """Test get_test_distribution with weights."""
        weights = {"category1": 1.0, "category2": 2.0, "category3": 3.0}

        result = DistributionManager.get_test_distribution(60, weights=weights)

        # Should be normalized and distributed
        assert sum(result.values()) == 60
        assert result["category1"] == 10  # 1/6 * 60
        assert result["category2"] == 20  # 2/6 * 60
        assert result["category3"] == 30  # 3/6 * 60

    def test_get_test_distribution_with_enum_weights(self):
        """Test get_test_distribution with CategoryEnum weights."""
        weights = {CategoryEnum.REGRESSION: 1.0, CategoryEnum.SMOKE: 2.0}

        result = DistributionManager.get_test_distribution(30, weights=weights)

        assert sum(result.values()) == 30
        assert result["regression"] == 10  # 1/3 * 30
        assert result["smoke"] == 20  # 2/3 * 30

    def test_get_test_distribution_default_weights(self):
        """Test get_test_distribution with default weights."""
        result = DistributionManager.get_test_distribution(100)

        assert sum(result.values()) == 100
        assert all(count > 0 for count in result.values())

    def test_get_test_distribution_no_params(self):
        """Test get_test_distribution with no distribution or weights."""
        result = DistributionManager.get_test_distribution(50)

        assert sum(result.values()) == 50
        assert all(count > 0 for count in result.values())


class TestDistributionManagerAbsoluteDistribution:
    """Test DistributionManager absolute distribution processing."""

    def test_process_absolute_distribution_empty(self):
        """Test _process_absolute_distribution with empty distribution."""
        with pytest.raises(ValueError, match="Distribution dictionary cannot be empty"):
            DistributionManager.process_absolute_distribution(10, {})

    def test_process_absolute_distribution_zero_values(self):
        """Test _process_absolute_distribution with zero values."""
        with pytest.raises(ValueError, match="non-positive values"):
            DistributionManager.process_absolute_distribution(
                10, {"cat1": 0, "cat2": 5}
            )

    def test_process_absolute_distribution_negative_values(self):
        """Test _process_absolute_distribution with negative values."""
        with pytest.raises(ValueError, match="non-positive values"):
            DistributionManager.process_absolute_distribution(
                10, {"cat1": -1, "cat2": 5}
            )

    def test_process_absolute_distribution_all_zero(self):
        """Test _process_absolute_distribution with all zero values."""
        with pytest.raises(ValueError, match="non-positive values"):
            DistributionManager.process_absolute_distribution(
                10, {"cat1": 0, "cat2": 0}
            )

    def test_process_absolute_distribution_matches_total(self):
        """Test _process_absolute_distribution when distribution matches total."""
        distribution = {"cat1": 3, "cat2": 7}
        result = DistributionManager.process_absolute_distribution(10, distribution)
        assert result == distribution

    def test_process_absolute_distribution_needs_scaling_up(self):
        """Test _process_absolute_distribution when scaling up."""
        distribution = {"cat1": 1, "cat2": 2}
        result = DistributionManager.process_absolute_distribution(10, distribution)
        assert sum(result.values()) == 10
        assert result["cat1"] == 3  # 1/3 * 10, rounded up
        assert result["cat2"] == 7  # 2/3 * 10, rounded up

    def test_process_absolute_distribution_needs_scaling_down(self):
        """Test _process_absolute_distribution when scaling down."""
        distribution = {"cat1": 10, "cat2": 20}
        result = DistributionManager.process_absolute_distribution(10, distribution)
        assert sum(result.values()) == 10
        assert result["cat1"] == 3  # 10/30 * 10, rounded
        assert result["cat2"] == 7  # 20/30 * 10, rounded

    def test_process_absolute_distribution_rounding_adjustment(self):
        """Test _process_absolute_distribution rounding adjustment."""
        # This should result in rounding errors that need adjustment
        distribution = {"cat1": 1, "cat2": 1, "cat3": 1}
        result = DistributionManager.process_absolute_distribution(4, distribution)
        assert sum(result.values()) == 4
        # All should be at least 1, and one should be 2 to make the total 4


class TestDistributionManagerWeightedDistribution:
    """Test DistributionManager weighted distribution processing."""

    def test_process_weighted_distribution_empty_weights(self):
        """Test _process_weighted_distribution with empty weights."""
        with pytest.raises(ValueError, match="Weights dictionary cannot be empty"):
            DistributionManager.process_weighted_distribution(10, {})

    def test_process_weighted_distribution_zero_weights(self):
        """Test _process_weighted_distribution with zero weights."""
        with pytest.raises(ValueError, match="non-positive values"):
            DistributionManager.process_weighted_distribution(
                10, {"cat1": 0.0, "cat2": 1.0}
            )

    def test_process_weighted_distribution_negative_weights(self):
        """Test _process_weighted_distribution with negative weights."""
        with pytest.raises(ValueError, match="non-positive values"):
            DistributionManager.process_weighted_distribution(
                10, {"cat1": -1.0, "cat2": 1.0}
            )

    def test_process_weighted_distribution_all_zero_weights(self):
        """Test _process_weighted_distribution with all zero weights."""
        with pytest.raises(ValueError, match="non-positive values"):
            DistributionManager.process_weighted_distribution(
                10, {"cat1": 0.0, "cat2": 0.0}
            )

    def test_process_weighted_distribution_enum_keys(self):
        """Test _process_weighted_distribution with CategoryEnum keys."""
        weights = {CategoryEnum.REGRESSION: 1.0, CategoryEnum.SMOKE: 2.0}
        result = DistributionManager.process_weighted_distribution(30, weights)

        assert sum(result.values()) == 30
        assert result["regression"] == 10  # 1/3 * 30
        assert result["smoke"] == 20  # 2/3 * 30

    def test_process_weighted_distribution_string_keys(self):
        """Test _process_weighted_distribution with string keys."""
        weights = {"regression": 1.0, "smoke": 2.0}
        result = DistributionManager.process_weighted_distribution(30, weights)

        assert sum(result.values()) == 30
        assert result["regression"] == 10  # 1/3 * 30
        assert result["smoke"] == 20  # 2/3 * 30

    def test_process_weighted_distribution_mixed_keys(self):
        """Test _process_weighted_distribution with mixed key types."""
        weights: dict[Any, float] = {CategoryEnum.REGRESSION: 1.0, "smoke": 2.0}
        result = DistributionManager.process_weighted_distribution(30, weights)

        assert sum(result.values()) == 30
        assert result["regression"] == 10  # 1/3 * 30
        assert result["smoke"] == 20  # 2/3 * 30

    def test_process_weighted_distribution_remainder_distribution(self):
        """Test _process_weighted_distribution with remainder distribution."""
        # 7 tests with weights that don't divide evenly
        weights = {"cat1": 1.0, "cat2": 1.0, "cat3": 1.0}
        result = DistributionManager.process_weighted_distribution(7, weights)

        assert sum(result.values()) == 7
        # Should distribute remainder to categories with highest fractional parts
        assert all(
            count >= 2 for count in result.values()
        )  # Each should get at least 2 (7/3 ≈ 2.33)

    def test_process_weighted_distribution_large_total(self):
        """Test _process_weighted_distribution with large total."""
        weights = {"cat1": 1.0, "cat2": 2.0, "cat3": 3.0}
        result = DistributionManager.process_weighted_distribution(1000, weights)

        assert sum(result.values()) == 1000
        assert result["cat1"] == 167  # 1/6 * 1000
        assert result["cat2"] == 333  # 2/6 * 1000
        assert result["cat3"] == 500  # 3/6 * 1000

    @settings(max_examples=200, deadline=None)
    @given(
        total_tests=st.integers(min_value=1, max_value=250),
        weight_values=st.lists(
            st.integers(min_value=1, max_value=20), min_size=1, max_size=8
        ),
    )
    def test_fractional_remainder_allocation(
        self, total_tests: int, weight_values: list[int]
    ) -> None:
        """Check that remainder slots favor the largest fractional shares."""
        weights = {
            f"cat_{index}": float(weight) for index, weight in enumerate(weight_values)
        }

        result = DistributionManager.process_weighted_distribution(total_tests, weights)
        assert sum(result.values()) == total_tests

        total_weight = sum(weights.values())
        normalized = {k: v / total_weight for k, v in weights.items()}
        raw_counts = {k: total_tests * normalized[k] for k in weights}
        base_counts = {k: int(raw_counts[k]) for k in weights}
        remainder = total_tests - sum(base_counts.values())

        fractional_parts = [(k, (total_tests * normalized[k]) % 1) for k in weights]
        fractional_parts.sort(key=lambda item: item[1], reverse=True)
        expected_recipients = {k for k, _ in fractional_parts[:remainder]}
        actual_recipients = {k for k in weights if result[k] > base_counts[k]}

        for key in weights:
            delta = result[key] - base_counts[key]
            assert delta in (0, 1)

        assert actual_recipients == expected_recipients


class TestPrintTestDistribution:
    """Test print_test_distribution function."""

    def test_print_test_distribution_empty(self, capsys):
        """Test print_test_distribution with empty distribution."""
        print_test_distribution({})

        captured = capsys.readouterr()
        assert "Test Distribution Summary (Total: 0 tests)" in captured.out

    def test_print_test_distribution_single_category(self, capsys):
        """Test print_test_distribution with single category."""
        distribution = {"web_testing": 10}

        print_test_distribution(distribution)

        captured = capsys.readouterr()
        assert "Test Distribution Summary (Total: 10 tests)" in captured.out
        assert "Web_Testing:   10 tests (100.0%)" in captured.out

    def test_print_test_distribution_multiple_categories(self, capsys):
        """Test print_test_distribution with multiple categories."""
        distribution = {"web_testing": 6, "api_testing": 3, "database_testing": 1}

        print_test_distribution(distribution)

        captured = capsys.readouterr()
        assert "Test Distribution Summary (Total: 10 tests)" in captured.out
        assert "Api_Testing:" in captured.out
        assert "Database_Testing:" in captured.out
        assert "Web_Testing:" in captured.out
        assert "6 tests ( 60.0%)" in captured.out
        assert "3 tests ( 30.0%)" in captured.out
        assert "1 tests ( 10.0%)" in captured.out

    def test_print_test_distribution_sorted_categories(self, capsys):
        """Test print_test_distribution sorts categories alphabetically."""
        distribution = {"zebra": 1, "alpha": 2, "beta": 3}

        print_test_distribution(distribution)

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        # Find the category lines (skip header and separators)
        category_lines = [line for line in lines if ":" in line and "tests (" in line]
        assert len(category_lines) == 3
        assert "Alpha:" in category_lines[0]
        assert "Beta:" in category_lines[1]
        assert "Zebra:" in category_lines[2]

    def test_print_test_distribution_percentage_formatting(self, capsys):
        """Test print_test_distribution percentage formatting."""
        distribution = {"cat1": 1, "cat2": 1, "cat3": 1}  # 33.3% each

        print_test_distribution(distribution)

        captured = capsys.readouterr()
        assert "33.3%" in captured.out

    def test_print_test_distribution_zero_total(self, capsys):
        """Test print_test_distribution with zero total (edge case)."""
        distribution = {"cat1": 0, "cat2": 0}

        print_test_distribution(distribution)

        captured = capsys.readouterr()
        assert "Test Distribution Summary (Total: 0 tests)" in captured.out
        assert "  0.0%" in captured.out


class TestTypeAliases:
    """Test type aliases are properly defined."""

    def test_weights_dict_type_alias(self):
        """Test WeightsDict type alias can be used."""
        weights: WeightsDict = {"cat1": 1.0, "cat2": 2.0}
        assert isinstance(weights, dict)

    def test_distribution_dict_type_alias(self):
        """Test DistributionDict type alias can be used."""
        distribution: DistributionDict = {"cat1": 10, "cat2": 20}
        assert isinstance(distribution, dict)

    def test_weights_dict_with_enum(self):
        """Test WeightsDict with CategoryEnum keys."""
        weights: WeightsDict = {CategoryEnum.REGRESSION: 1.0}
        assert isinstance(weights, dict)
