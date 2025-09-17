#!/usr/bin/env python3
"""
Command-line interface for the consolidated enterprise test generation utility.

This script provides a CLI wrapper around the internal test generation utilities,
allowing for dynamic test count specification and various output options.
"""

import argparse
import json
import sys

from importobot.utils.test_generation.categories import CategoryEnum
from importobot.utils.test_generation.distributions import print_test_distribution
from importobot.utils.test_generation.helpers import generate_test_suite


def main() -> int:
    """Generate enterprise test suite using consolidated utilities."""
    args = _parse_arguments()
    distribution, weights = _parse_custom_parameters(args)

    # Check for conflicting parameters
    if distribution is not None and weights is not None:
        print(
            "Warning: Both --distribution and --weights provided. "
            "Using --distribution and ignoring --weights.",
            file=sys.stderr,
        )

    _print_generation_info(args)

    try:
        # Generate the test suite using the consolidated utility
        counts = generate_test_suite(args.output_dir, args.count, distribution, weights)
        _print_results(args, counts)
        return 0
    except Exception as e:
        print(f"Error generating test suite: {e}", file=sys.stderr)
        return 1


def _parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive enterprise test cases "
        "using consolidated utilities"
    )
    parser.add_argument(
        "--output-dir",
        default="zephyr-tests",
        help="Output directory for generated tests (default: zephyr-tests)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=800,
        help="Total number of tests to generate (default: 800)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed progress information",
    )
    parser.add_argument(
        "--distribution",
        help=(
            "Custom distribution as JSON string, e.g., "
            '"{"regression": 300, "smoke": 100, "integration": 200, "e2e": 200}"'
        ),
    )
    parser.add_argument(
        "--weights",
        help=(
            "Custom test distribution weights as JSON string, e.g., "
            '"{"regression": 0.5, "smoke": 0.2, "integration": 0.2, "e2e": 0.1}". '
            "Weights will be normalized automatically. Use this for percentage-based "
            "distribution instead of absolute counts. "
            "Valid categories: regression, smoke, integration, e2e"
        ),
    )
    return parser.parse_args()


def _parse_custom_parameters(
    args: argparse.Namespace,
) -> tuple[dict[str, int] | None, dict[str, float] | None]:
    """Parse custom distribution or weights parameters."""
    # Parse custom distribution if provided
    distribution: dict[str, int] | None = None
    if args.distribution:
        try:
            parsed_distribution = json.loads(args.distribution)
            # Ensure values are integers for distribution
            distribution = {k: int(v) for k, v in parsed_distribution.items()}
            if args.verbose:
                print(f"Using custom distribution: {distribution}")
        except json.JSONDecodeError as e:
            print(f"Error parsing distribution JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Parse custom weights if provided
    weights: dict[str, float] | None = None
    if args.weights:
        try:
            weights = json.loads(args.weights)
            # Validate weight categories
            valid_categories = CategoryEnum.get_all_values()
            for category in weights.keys():
                if category not in valid_categories:
                    print(
                        f"Error: Invalid category '{category}'. "
                        f"Valid categories: {valid_categories}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            if args.verbose:
                print(f"Using custom weights: {weights}")
        except json.JSONDecodeError as e:
            print(f"Error parsing weights JSON: {e}", file=sys.stderr)
            sys.exit(1)

    return distribution, weights


def _print_generation_info(args: argparse.Namespace) -> None:
    """Print information about the test generation process."""
    if args.verbose:
        print(f"Generating {args.count} enterprise test cases in {args.output_dir}/")
        print(
            "Using consolidated test generation utility with "
            "enhanced enterprise scenarios"
        )
        print("")


def _print_results(args: argparse.Namespace, counts: dict[str, int]) -> None:
    """Print the results of test generation."""
    if args.verbose:
        print_test_distribution(counts)
        print("")
        print("Test categories include:")
        print("  • Web automation with enterprise authentication workflows")
        print("  • API testing with microservices integration")
        print("  • Database testing with enterprise data operations")
        print("  • Infrastructure testing with cloud-native operations")
        print("  • Security testing with comprehensive validation")
        print("")

    total_generated = sum(counts.values())
    print(f"Successfully generated {total_generated} enterprise test cases")

    if args.verbose:
        print("Output structure:")
        for category, count in counts.items():
            print(f"  {args.output_dir}/{category}/: {count} .json files")


if __name__ == "__main__":
    sys.exit(main())
