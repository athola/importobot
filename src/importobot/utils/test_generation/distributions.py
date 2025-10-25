"""Distribution and weight management for test generation."""

from importobot.utils.test_generation.categories import CategoryEnum

# Type aliases for flexibility in weight specification
WeightsDict = dict[CategoryEnum, float] | dict[str, float]
DistributionDict = dict[str, int]


class DistributionManager:
    """Manages test distribution calculations and normalization."""

    @staticmethod
    def get_test_distribution(
        total_tests: int,
        distribution: DistributionDict | None = None,
        weights: WeightsDict | None = None,
    ) -> DistributionDict:
        """Get normalized test distribution from weights or absolute counts."""
        if distribution is not None:
            return DistributionManager.process_absolute_distribution(
                total_tests, distribution
            )

        if weights is not None:
            return DistributionManager.process_weighted_distribution(
                total_tests, weights
            )

        # Use default weights if neither distribution nor weights provided
        default_weights = CategoryEnum.get_default_weights()
        return DistributionManager.get_test_distribution(
            total_tests, weights=default_weights
        )

    @staticmethod
    def process_absolute_distribution(
        total_tests: int, distribution: DistributionDict
    ) -> DistributionDict:
        """Process absolute distribution values."""
        # Create a copy to avoid modifying the input
        distribution_copy: DistributionDict = distribution.copy()

        # Validate distribution has positive values
        if not distribution_copy:
            raise ValueError("Distribution dictionary cannot be empty")

        # Check for non-positive values
        invalid_values = {k: v for k, v in distribution_copy.items() if v <= 0}
        if invalid_values:
            raise ValueError(
                f"Distribution contains non-positive values: {invalid_values}"
            )

        # Ensure distribution adds up to total_tests
        current_total = sum(distribution_copy.values())
        if current_total == 0:
            raise ValueError("Total distribution cannot be zero")

        if current_total != total_tests:
            # Scale proportionally to match total_tests
            scale_factor = total_tests / current_total
            distribution_copy = {
                k: max(1, int(v * scale_factor)) for k, v in distribution_copy.items()
            }
            # Handle rounding errors by adjusting the largest category
            adjusted_total = sum(distribution_copy.values())
            if adjusted_total != total_tests:
                largest_category = max(
                    distribution_copy, key=lambda k: distribution_copy[k]
                )
                distribution_copy[largest_category] += total_tests - adjusted_total
        return distribution_copy

    @staticmethod
    def process_weighted_distribution(
        total_tests: int, weights: WeightsDict
    ) -> DistributionDict:
        """Process weighted distribution values."""
        # Validate weights
        if not weights:
            raise ValueError(
                "Total weight cannot be zero (Weights dictionary cannot be empty)"
            )

        # Check for non-positive weights (negative or zero)
        invalid_weights = {k: v for k, v in weights.items() if v <= 0}
        if invalid_weights:
            raise ValueError(f"Weights contain non-positive values: {invalid_weights}")

        # Convert CategoryEnum keys to strings if necessary
        string_weights: dict[str, float]
        if isinstance(next(iter(weights.keys())), CategoryEnum):
            string_weights = {
                k.value if isinstance(k, CategoryEnum) else str(k): v
                for k, v in weights.items()
            }
        else:
            string_weights = {str(k): v for k, v in weights.items()}

        # Normalize weights to sum to 1.0
        total_weight = sum(string_weights.values())
        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")

        normalized_weights: dict[str, float] = {
            k: v / total_weight for k, v in string_weights.items()
        }
        computed_distribution: DistributionDict = {
            k: int(total_tests * weight) for k, weight in normalized_weights.items()
        }

        # Handle rounding errors by distributing remainder
        distributed_total = sum(computed_distribution.values())
        remainder = total_tests - distributed_total

        # Add remainder to categories with highest fractional parts
        if remainder > 0:
            fractional_parts = [
                (k, (total_tests * normalized_weights[k]) % 1)
                for k in computed_distribution
            ]
            fractional_parts.sort(key=lambda x: x[1], reverse=True)

            for i in range(remainder):
                category = fractional_parts[i % len(fractional_parts)][0]
                computed_distribution[category] += 1

        return computed_distribution


def print_test_distribution(counts: DistributionDict) -> None:
    """Print test distribution summary in a consistent format."""
    total = sum(counts.values())
    print(f"\nTest Distribution Summary (Total: {total} tests)")
    print("=" * 50)

    for category, count in sorted(counts.items()):
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"{category.title():>12}: {count:>4} tests ({percentage:>5.1f}%)")

    print("=" * 50)
