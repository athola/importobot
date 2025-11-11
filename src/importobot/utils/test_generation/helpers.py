"""Helper functions for test generation."""

import random
from typing import Any

from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.core.pattern_matcher import LibraryDetector
from importobot.utils.test_generation.distributions import DistributionDict, WeightsDict
from importobot.utils.test_generation.generators import TestSuiteGenerator


def generate_test_suite(
    output_dir: str,
    total_tests: int = 800,
    distribution: DistributionDict | None = None,
    weights: WeightsDict | None = None,
) -> DistributionDict:
    """Generate a test suite.

    Args:
        output_dir: Directory to save generated test files
        total_tests: Total number of tests to generate
        distribution: Absolute test count per category
            (e.g., {"regression": 250, "smoke": 150})
        weights: Relative weights per category. Can use CategoryEnum enum or strings:
                - Enum: {CategoryEnum.REGRESSION: 0.5, CategoryEnum.SMOKE: 0.3}
                - String: {"regression": 0.5, "smoke": 0.3}
                Weights will be normalized to sum to 1.0 automatically.

    Returns:
        Dictionary mapping category names to actual test counts generated

    Example:
        # Generate 1000 tests with default distribution
        counts = generate_test_suite("output", 1000)

        # Generate with custom weights
        weights = {"regression": 0.6, "smoke": 0.4}
        counts = generate_test_suite("output", 500, weights=weights)
    """
    # Validate resource limits to prevent exhaustion
    if total_tests <= 0:
        raise ValueError("total_tests must be greater than 0")
    if total_tests > 50000:  # MAX_TOTAL_TESTS
        raise ValueError(f"total_tests ({total_tests}) exceeds maximum allowed (50000)")

    generator = TestSuiteGenerator()
    result: DistributionDict = generator.generate_test_suite(
        output_dir, total_tests, distribution, weights
    )
    return result


def generate_random_test_json(
    structure: str | None = None, complexity: str | None = None
) -> dict[str, Any]:
    """Generate a random JSON test artifact."""
    generator = TestSuiteGenerator()
    result: dict[str, Any] = generator.generate_random_json(structure, complexity)
    return result


def get_available_structures() -> list[str]:
    """Get list of available test structures for generation."""
    return ["zephyr", "jira", "testlink", "generic"]


def get_required_libraries_for_keywords(keywords: list[dict[str, Any]]) -> set[str]:
    """Get required Robot Framework libraries for given keywords."""
    # Create steps using the same process as the actual test conversion
    generator = TestSuiteGenerator()
    test_data = generator.generate_realistic_test_data()

    steps = []
    for i, kw in enumerate(keywords):
        description = kw.get("description", kw.get("keyword", "action"))
        step = {
            "description": f"Execute {description.lower()}",
            "testData": generator.generate_keyword_specific_data(kw, test_data),
            "expectedResult": f"{description} completes successfully",
            "index": i,
        }
        steps.append(step)

    # Detect libraries from the generated steps (same as conversion process)
    detected_libs = LibraryDetector.detect_libraries_from_steps(steps)
    return {lib.value for lib in detected_libs}


def generate_keyword_list(num_keywords: int) -> list[dict[str, Any]]:
    """Generate a list of random Robot Framework keywords for testing."""
    all_keywords = []

    # Get keywords from all libraries
    keyword_libraries = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES
    for library_name, keywords in keyword_libraries.items():
        for keyword_name, keyword_info in keywords.items():
            all_keywords.append(
                {
                    "keyword": keyword_name,
                    "library": library_name,
                    "description": keyword_info["description"],
                }
            )

    # Return random sample
    return random.sample(all_keywords, min(num_keywords, len(all_keywords)))
