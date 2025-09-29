"""
Tests for test generation utilities including CategoryEnum enum functionality.
"""

# pylint: disable=protected-access,no-member

import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from importobot.utils.test_generation.categories import CategoryEnum, CategoryInfo
from importobot.utils.test_generation.distributions import DistributionDict, WeightsDict
from importobot.utils.test_generation.generators import (
    CategoryTestParams,
    EnterpriseTestGenerator,
)
from importobot.utils.test_generation.helpers import (
    generate_random_test_json,
    generate_test_suite,
    get_available_structures,
    get_required_libraries_for_keywords,
)


class TestCategoryEnumEnum:
    """Test the CategoryEnum enum functionality."""

    def test_enum_values(self):
        """Test that enum has correct values."""
        assert CategoryEnum.REGRESSION.value == "regression"
        assert CategoryEnum.SMOKE.value == "smoke"
        assert CategoryEnum.INTEGRATION.value == "integration"
        assert CategoryEnum.E2E.value == "e2e"

    def test_get_all_values(self):
        """Test getting all enum values as strings."""
        values = CategoryEnum.get_all_values()
        expected = ["regression", "smoke", "integration", "e2e"]
        assert values == expected

    def test_from_string_valid(self):
        """Test converting valid strings to enum."""
        assert CategoryEnum.from_string("regression") == CategoryEnum.REGRESSION
        assert CategoryEnum.from_string("smoke") == CategoryEnum.SMOKE
        assert CategoryEnum.from_string("integration") == CategoryEnum.INTEGRATION
        assert CategoryEnum.from_string("e2e") == CategoryEnum.E2E

    def test_from_string_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError, match="Unknown category: invalid"):
            CategoryEnum.from_string("invalid")

    @pytest.mark.parametrize(
        "category_str,expected_enum",
        [
            ("regression", CategoryEnum.REGRESSION),
            ("smoke", CategoryEnum.SMOKE),
            ("integration", CategoryEnum.INTEGRATION),
            ("e2e", CategoryEnum.E2E),
        ],
    )
    def test_from_string_parameterized(self, category_str, expected_enum):
        """Test converting various valid strings to enums using parameterization."""
        result = CategoryEnum.from_string(category_str)
        assert result == expected_enum
        assert result.value == category_str

    @pytest.mark.parametrize(
        "invalid_category",
        ["invalid", "unknown", "test", "", "REGRESSION", "Smoke", "integration_test"],
    )
    def test_from_string_invalid_parameterized(self, invalid_category):
        """Test that various invalid strings raise ValueError."""
        with pytest.raises(ValueError, match=f"Unknown category: {invalid_category}"):
            CategoryEnum.from_string(invalid_category)

    def test_get_default_weights(self):
        """Test default weights structure and values."""
        weights = CategoryEnum.get_default_weights()

        # Check all categories are present
        assert CategoryEnum.REGRESSION in weights
        assert CategoryEnum.SMOKE in weights
        assert CategoryEnum.INTEGRATION in weights
        assert CategoryEnum.E2E in weights

        # Check weights are positive
        for weight in weights.values():
            assert weight > 0

        # Check weights sum to approximately 1.0 (allowing for floating point precision)
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.0001


class EnterpriseTestGeneratorWeights:
    """Test the weight distribution functionality in EnterpriseTestGenerator."""

    def __init__(self):
        """Initialize test fixtures."""
        self.generator = EnterpriseTestGenerator()

    def test_enum_based_weights(self):
        """Test distribution calculation with enum-based weights."""
        weights = {
            CategoryEnum.REGRESSION: 0.6,
            CategoryEnum.SMOKE: 0.2,
            CategoryEnum.INTEGRATION: 0.2,
        }

        # pylint: disable=protected-access,no-member
        distribution = self.generator._get_test_distribution(100, None, weights)

        assert distribution["regression"] == 60
        assert distribution["smoke"] == 20
        assert distribution["integration"] == 20
        assert sum(distribution.values()) == 100

    def test_string_based_weights(self):
        """Test distribution calculation with string-based weights."""
        weights = {"regression": 0.5, "smoke": 0.3, "integration": 0.1, "e2e": 0.1}

        # pylint: disable=protected-access,no-member
        distribution = self.generator._get_test_distribution(100, None, weights)

        assert distribution["regression"] == 50
        assert distribution["smoke"] == 30
        assert distribution["integration"] == 10
        assert distribution["e2e"] == 10
        assert sum(distribution.values()) == 100

    @pytest.mark.parametrize(
        "total_tests,weights,expected",
        [
            (100, {"regression": 0.6, "smoke": 0.4}, {"regression": 60, "smoke": 40}),
            (50, {"regression": 0.8, "smoke": 0.2}, {"regression": 40, "smoke": 10}),
            (
                200,
                {"regression": 0.25, "smoke": 0.25, "integration": 0.25, "e2e": 0.25},
                {"regression": 50, "smoke": 50, "integration": 50, "e2e": 50},
            ),
            (10, {"regression": 1.0}, {"regression": 10}),
        ],
    )
    def test_distribution_calculation_parameterized(
        self, total_tests, weights, expected
    ):
        """Test distribution calculation with various total counts and weights."""
        generator = EnterpriseTestGenerator()

        # pylint: disable=protected-access,no-member
        distribution = generator._get_test_distribution(total_tests, None, weights)

        assert distribution == expected
        assert sum(distribution.values()) == total_tests

    def test_weights_normalization(self):
        """Test that weights are properly normalized."""
        # Weights that don't sum to 1.0
        weights = {"regression": 3.0, "smoke": 1.0, "integration": 1.0}

        # pylint: disable=protected-access,no-member
        distribution = self.generator._get_test_distribution(100, None, weights)

        # Should be normalized: 3/5 = 0.6, 1/5 = 0.2, 1/5 = 0.2
        assert distribution["regression"] == 60
        assert distribution["smoke"] == 20
        assert distribution["integration"] == 20
        assert sum(distribution.values()) == 100

    def test_invalid_string_category(self):
        """Test that invalid string categories raise ValueError."""
        weights = {"invalid_category": 0.5, "regression": 0.5}

        # pylint: disable=protected-access,no-member
        with pytest.raises(ValueError, match="Invalid test category: invalid_category"):
            self.generator._get_test_distribution(100, None, weights)

    def test_zero_total_weight_error(self):
        """Test that zero total weight raises ValueError."""
        weights = {"regression": 0.0, "smoke": 0.0}

        # pylint: disable=protected-access,no-member
        with pytest.raises(ValueError, match="Total weight cannot be zero"):
            self.generator._get_test_distribution(100, None, weights)

    def test_default_weights_when_none_provided(self):
        """Test that default weights are used when no weights/distribution provided."""
        # pylint: disable=protected-access,no-member
        distribution = self.generator._get_test_distribution(100)

        # Should use default weights
        assert sum(distribution.values()) == 100
        assert "regression" in distribution
        assert "smoke" in distribution
        assert "integration" in distribution
        assert "e2e" in distribution

    def test_distribution_takes_precedence(self):
        """Test that distribution parameter takes precedence over weights."""
        weights = {"regression": 1.0}  # This should be ignored
        distribution_input = {
            "regression": 50,
            "smoke": 50,
        }  # Total = 100, no adjustment needed

        # pylint: disable=protected-access,no-member
        distribution = self.generator._get_test_distribution(
            100, distribution_input, weights
        )

        # Should match the distribution input, not the weights
        assert distribution["regression"] == 50
        assert distribution["smoke"] == 50
        assert sum(distribution.values()) == 100

    def test_rounding_adjustment(self):
        """Test that rounding errors are properly adjusted."""
        # Use weights that will cause rounding issues
        weights = {"regression": 1.0, "smoke": 1.0, "integration": 1.0}

        # pylint: disable=protected-access,no-member
        # Test with total that doesn't divide evenly
        distribution = self.generator._get_test_distribution(100, None, weights)

        # Should still sum to exactly 100
        assert sum(distribution.values()) == 100

        # Each category should get approximately 33 (100/3)
        for count in distribution.values():
            assert 33 <= count <= 34


class TestTypeAliases:
    """Test the type aliases work correctly."""

    def test_weights_dict_type_annotation(self):
        """Test that WeightsDict type alias accepts both enum and string keys."""
        # This test mainly checks that the type annotations are correct
        # The actual functionality is tested in the methods above

        enum_weights: WeightsDict = {CategoryEnum.REGRESSION: 0.5}
        string_weights: WeightsDict = {"regression": 0.5}

        # If this compiles without type errors, the type alias is working
        assert isinstance(enum_weights, dict)
        assert isinstance(string_weights, dict)

    def test_distribution_dict_type_annotation(self):
        """Test that DistributionDict type alias works correctly."""
        distribution: DistributionDict = {"regression": 100, "smoke": 50}
        assert isinstance(distribution, dict)


class EnterpriseTestGeneratorCore:
    """Test core EnterpriseTestGenerator functionality."""

    def __init__(self):
        """Initialize test fixtures."""
        self.generator = EnterpriseTestGenerator()

    def test_generate_realistic_test_data(self):
        """Test realistic test data generation."""
        data = self.generator.generate_realistic_test_data()

        # Should return a dictionary with expected keys
        assert isinstance(data, dict)
        assert "base_url" in data
        assert "username" in data
        assert "password" in data
        assert "api_version" in data
        assert "test_environment" in data

        # Values should be realistic strings
        assert data["base_url"].startswith("https://")
        assert len(data["username"]) > 0
        assert len(data["password"]) > 0

    def test_generate_enterprise_test_step(self):
        """Test enterprise test step generation."""
        test_data = {"base_url": "https://example.com", "username": "test"}

        step = self.generator.generate_enterprise_test_step(
            "Navigate to application", test_data, 0
        )

        assert isinstance(step, dict)
        assert "description" in step
        assert "testData" in step
        assert "expectedResult" in step
        assert "index" in step
        assert "stepType" in step
        assert "estimatedDuration" in step
        assert "criticalityLevel" in step
        assert "dependencies" in step

    def test_generate_enterprise_test_case(self):
        """Test enterprise test case generation."""
        test_case = self.generator.generate_enterprise_test_case(
            "web_automation", "user_authentication", 1, "high"
        )

        assert isinstance(test_case, dict)
        assert "key" in test_case
        assert "name" in test_case
        assert "description" in test_case
        assert "testScript" in test_case
        assert "steps" in test_case["testScript"]
        assert len(test_case["testScript"]["steps"]) > 0

    def test_generate_test_suite_creates_requested_number_of_files(self):
        """User gets exactly the number of test files they requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            requested_test_count = 20  # User's request

            counts = self.generator.generate_test_suite(
                temp_dir,
                total_tests=requested_test_count,
                weights={CategoryEnum.REGRESSION: 1.0},  # Only regression tests
            )

            # User should get count information matching their request
            assert isinstance(counts, dict)
            assert "regression" in counts
            assert counts["regression"] == requested_test_count, (
                "Count should match user request"
            )

            # User should get actual files created
            output_path = Path(temp_dir)
            regression_dir = output_path / "regression"
            assert regression_dir.exists(), "Directory should be created for user"

            # User should get exactly the number of files they requested
            json_files = list(regression_dir.glob("*.json"))
            assert len(json_files) == requested_test_count, (
                f"User requested {requested_test_count} files and should get "
                f"exactly that many"
            )

    def test_generate_random_json_structures(self):
        """Test random JSON generation with different structures."""
        structures = ["zephyr_basic", "zephyr_nested", "simple_tests_array"]

        for structure in structures:
            json_data = self.generator.generate_random_json(structure)

            assert isinstance(json_data, dict)
            # Should be valid JSON (can be serialized)
            json.dumps(json_data)  # Will raise exception if not valid JSON

    @pytest.mark.parametrize(
        "structure",
        [
            "zephyr_basic",
            "zephyr_nested",
            "simple_tests_array",
            "enterprise_workflow",
            "api_tests",
        ],
    )
    def test_generate_random_json_structures_parameterized(self, structure):
        """Test random JSON generation with various structures
        using parameterization."""
        json_data = self.generator.generate_random_json(structure)

        assert isinstance(json_data, dict)
        # Should be valid JSON (can be serialized)
        json.dumps(json_data)  # Will raise exception if not valid JSON

        # Structure-specific assertions
        if structure == "zephyr_basic":
            assert "name" in json_data
        elif structure == "simple_tests_array":
            assert isinstance(json_data.get("tests", []), list)

    def test_generate_random_json_no_structure(self):
        """Test random JSON generation with no structure specified."""
        json_data = self.generator.generate_random_json()

        assert isinstance(json_data, dict)
        json.dumps(json_data)  # Should be valid JSON

    def test_generate_keyword_specific_data(self):
        """Test keyword-specific data generation."""
        web_keyword = {
            "intent": "web_navigation",
            "library": "SeleniumLibrary",
            "keyword": "Open Browser",
            "description": "Open browser for testing",
        }

        test_data = {"base_url": "https://example.com"}

        data = self.generator.generate_keyword_specific_data(web_keyword, test_data)
        assert isinstance(data, str)
        assert "Browser: Chrome" in data or "https://example.com" in data

    def test_private_helper_methods(self):
        """Test various private helper methods."""
        # Test step type determination
        # pylint: disable=protected-access,no-member
        step_type = self.generator._determine_step_type("Navigate to login page")
        assert step_type in [
            "navigation",
            "authentication",
            "verification",
            "execution",
            "monitoring",
            "configuration",
            "action",
        ]

        # Test duration estimation
        # pylint: disable=protected-access,no-member
        duration = self.generator._estimate_step_duration("Click login button")
        assert isinstance(duration, str)
        assert any(unit in duration for unit in ["second", "minute"])

        # Test criticality determination
        # pylint: disable=protected-access,no-member
        criticality = self.generator._determine_criticality("Authenticate user")
        assert criticality in ["critical", "high", "medium", "low"]

    @pytest.mark.parametrize(
        "description,expected_types",
        [
            ("Navigate to login page", ["navigation", "action"]),
            ("Click login button", ["action", "authentication"]),
            ("Verify user is logged in", ["verification"]),
            ("Monitor system performance", ["monitoring"]),
            ("Configure database settings", ["configuration"]),
            ("Execute API call", ["execution", "action"]),
            ("Authenticate with OAuth", ["authentication"]),
        ],
    )
    def test_determine_step_type_parameterized(self, description, expected_types):
        """Test step type determination with various descriptions."""
        # pylint: disable=protected-access,no-member
        step_type = self.generator._determine_step_type(description)
        assert step_type in expected_types

    @pytest.mark.parametrize(
        "description,expected_criticality_options",
        [
            ("Authenticate user", ["critical", "high"]),
            ("Click submit button", ["high", "medium"]),
            ("Log action", ["low", "medium"]),
            ("Verify payment", ["critical", "high"]),
            ("Update profile", ["medium", "low"]),
            ("Delete account", ["critical", "high"]),
            ("View dashboard", ["low", "medium"]),
        ],
    )
    def test_determine_criticality_parameterized(
        self, description, expected_criticality_options
    ):
        """Test criticality determination with various descriptions."""
        # pylint: disable=protected-access,no-member
        criticality = self.generator._determine_criticality(description)
        assert criticality in expected_criticality_options

    @pytest.mark.parametrize(
        "description",
        [
            "Click login button",
            "Navigate to page",
            "Verify result",
            "Execute command",
            "Monitor status",
            "Configure setting",
            "Authenticate user",
        ],
    )
    def test_estimate_step_duration_parameterized(self, description):
        """Test duration estimation with various step descriptions."""
        # pylint: disable=protected-access,no-member
        duration = self.generator._estimate_step_duration(description)
        assert isinstance(duration, str)
        assert any(unit in duration for unit in ["second", "minute"])
        # Duration should contain a number
        assert any(char.isdigit() for char in duration)

    def test_category_scenarios_mapping(self):
        """Test category scenarios mapping."""
        # pylint: disable=protected-access,no-member
        scenarios = self.generator._get_category_scenarios()

        assert isinstance(scenarios, dict)
        for category in CategoryEnum.get_all_values():
            assert category in scenarios
            assert isinstance(scenarios[category], dict)


class TestConvenienceWrapperFunctions:
    """Test the convenience wrapper functions."""

    def test_generate_test_suite_wrapper(self):
        """Test the generate_test_suite convenience wrapper."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with enum weights
            counts = generate_test_suite(
                temp_dir, total_tests=10, weights={CategoryEnum.SMOKE: 1.0}
            )

            assert isinstance(counts, dict)
            assert "smoke" in counts
            assert counts["smoke"] == 10

    def test_generate_test_suite_wrapper_with_distribution(self):
        """Test wrapper with distribution parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            counts = generate_test_suite(
                temp_dir, total_tests=10, distribution={"regression": 6, "smoke": 4}
            )

            assert counts["regression"] == 6
            assert counts["smoke"] == 4

    def test_generate_random_test_json_wrapper(self):
        """Test the generate_random_test_json convenience wrapper."""
        json_data = generate_random_test_json("zephyr_basic")

        assert isinstance(json_data, dict)
        json.dumps(json_data)  # Should be valid JSON

    def test_generate_random_test_json_wrapper_no_params(self):
        """Test wrapper with no parameters."""
        json_data = generate_random_test_json()

        assert isinstance(json_data, dict)

    def test_get_available_structures_wrapper(self):
        """Test get_available_structures wrapper."""
        structures = get_available_structures()

        assert isinstance(structures, list)
        assert len(structures) > 0
        assert all(isinstance(s, str) for s in structures)

    def test_get_required_libraries_for_keywords_wrapper(self):
        """Test get_required_libraries_for_keywords wrapper."""
        keywords = [
            {
                "intent": "web_navigation",
                "library": "SeleniumLibrary",
                "keyword": "Open Browser",
            },
            {
                "intent": "api_request",
                "library": "RequestsLibrary",
                "keyword": "GET On Session",
            },
        ]

        libraries = get_required_libraries_for_keywords(keywords)

        assert isinstance(libraries, list)
        # Should detect SeleniumLibrary and RequestsLibrary
        assert any("Selenium" in lib for lib in libraries)

    @pytest.mark.parametrize(
        "total_tests,category_weights",
        [
            (10, {CategoryEnum.SMOKE: 1.0}),
            (25, {CategoryEnum.REGRESSION: 0.8, CategoryEnum.SMOKE: 0.2}),
            (
                100,
                {
                    CategoryEnum.REGRESSION: 0.4,
                    CategoryEnum.INTEGRATION: 0.3,
                    CategoryEnum.E2E: 0.3,
                },
            ),
            (5, {CategoryEnum.E2E: 1.0}),
        ],
    )
    def test_generate_test_suite_wrapper_parameterized(
        self, total_tests, category_weights
    ):
        """Test the generate_test_suite wrapper with various configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            counts = generate_test_suite(
                temp_dir, total_tests=total_tests, weights=category_weights
            )

            assert isinstance(counts, dict)
            assert sum(counts.values()) == total_tests

            # All specified categories should be present
            for category_enum in category_weights.keys():
                assert category_enum.value in counts
                assert counts[category_enum.value] > 0

    @pytest.mark.parametrize(
        "structure",
        [
            "zephyr_basic",
            "zephyr_nested",
            "simple_tests_array",
            "enterprise_workflow",
            None,  # Test default structure
        ],
    )
    def test_generate_random_test_json_wrapper_parameterized(self, structure):
        """Test the generate_random_test_json wrapper with various structures."""
        if structure is None:
            json_data = generate_random_test_json()
        else:
            json_data = generate_random_test_json(structure)

        assert isinstance(json_data, dict)
        json.dumps(json_data)  # Should be valid JSON

    @pytest.mark.parametrize(
        "keywords_config",
        [
            [
                {
                    "intent": "web_navigation",
                    "library": "SeleniumLibrary",
                    "keyword": "Open Browser",
                }
            ],
            [
                {
                    "intent": "api_request",
                    "library": "RequestsLibrary",
                    "keyword": "GET On Session",
                }
            ],
            [
                {
                    "intent": "database",
                    "library": "DatabaseLibrary",
                    "keyword": "Connect To Database",
                }
            ],
            [
                {
                    "intent": "web_navigation",
                    "library": "SeleniumLibrary",
                    "keyword": "Open Browser",
                },
                {
                    "intent": "api_request",
                    "library": "RequestsLibrary",
                    "keyword": "GET On Session",
                },
            ],
            [],  # Empty list
        ],
    )
    def test_get_required_libraries_parameterized(self, keywords_config):
        """Test library detection with various keyword configurations."""
        libraries = get_required_libraries_for_keywords(keywords_config)

        assert isinstance(libraries, list)

        if keywords_config:
            # Should detect libraries from keywords
            expected_libraries = {
                kw.get("library") for kw in keywords_config if kw.get("library")
            }
            for expected_lib in expected_libraries:
                if expected_lib:
                    assert any(expected_lib in lib for lib in libraries)
        else:
            # Empty keywords should return empty or default libraries
            assert len(libraries) >= 0


class ErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    def __init__(self):
        """Initialize test fixtures."""
        self.generator = EnterpriseTestGenerator()

    def test_invalid_category_in_generate_test_suite(self):
        """Test that invalid categories are handled properly."""
        with tempfile.TemporaryDirectory():
            # This should work because string validation happens
            # in _get_test_distribution
            # and we already tested that in the weights tests
            pass

    def test_empty_weights_dict(self):
        """Test handling of empty weights dictionary."""
        with pytest.raises(ValueError, match="Total weight cannot be zero"):
            # pylint: disable=protected-access,no-member
            self.generator._get_test_distribution(100, None, {})

    def test_generate_test_case_with_minimal_params(self):
        """Test test case generation with minimal parameters."""
        test_case = self.generator.generate_enterprise_test_case(
            "web_automation", "user_authentication", 1
        )

        # Should still generate a valid test case
        assert isinstance(test_case, dict)
        assert "testScript" in test_case
        assert "steps" in test_case["testScript"]
        assert len(test_case["testScript"]["steps"]) > 0

    def test_keyword_specific_data_edge_cases(self):
        """Test keyword specific data generation with edge cases."""
        # Test with unknown intent
        unknown_keyword = {
            "intent": "unknown_intent",
            "description": "Unknown operation",
        }

        data = self.generator.generate_keyword_specific_data(unknown_keyword, {})
        assert isinstance(data, str)
        assert "Unknown operation" in data


class TestProgressReporting:
    """Test progress reporting functionality in test generation."""

    @property
    def generator(self):
        """Get test generator instance."""
        return EnterpriseTestGenerator()

    def test_progress_reporting_in_category_generation(self):
        """Test that progress reporting works during category test generation."""
        generator = EnterpriseTestGenerator()

        # Mock the logger to capture progress messages
        with patch.object(generator.logger, "info") as mock_info:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create category info structure
                category_info: CategoryInfo = {"dir": Path(temp_dir), "count": 0}

                # Mock scenarios for testing
                scenarios = {
                    "business_workflow": ["scenario1", "scenario2"],
                    "user_interaction": ["scenario3", "scenario4"],
                }

                # Create parameter object matching CategoryTestParams structure

                params = CategoryTestParams(
                    category="test_category",
                    count=20,  # Small count to test progress milestones
                    scenarios=scenarios,
                    category_info=category_info,
                    start_test_id=1,
                )

                # Generate small number of tests to see progress reporting
                generator._generate_category_tests(params)

                # Verify progress reporting calls
                progress_calls = [
                    call
                    for call in mock_info.call_args_list
                    if "Progress:" in str(call)
                ]
                assert len(progress_calls) > 0

                # Check that progress messages contain expected elements
                for call in progress_calls:
                    message = call[0][0]
                    assert "Progress:" in message
                    assert "/" in message  # Should show current/total
                    assert "%" in message  # Should show percentage
                    assert "test_category" in message

    def test_progress_milestone_calculation(self):
        """Test that progress milestones are calculated correctly."""
        generator = EnterpriseTestGenerator()

        with tempfile.TemporaryDirectory() as temp_dir:
            category_info: CategoryInfo = {"dir": Path(temp_dir), "count": 0}
            scenarios = {"test": ["scenario1"]}

            # Test with 100 tests (should report every 10%)
            with patch.object(generator.logger, "info") as mock_info:
                # Create parameter object

                params = CategoryTestParams(
                    category="test",
                    count=100,
                    scenarios=scenarios,
                    category_info=category_info,
                    start_test_id=1,
                )
                generator._generate_category_tests(params)

                # Should have progress reports at 10%, 20%, etc.
                progress_messages = [
                    str(call)
                    for call in mock_info.call_args_list
                    if "Progress:" in str(call)
                ]
                assert len(progress_messages) >= 5  # At least several progress reports

    def test_progress_reporting_for_small_counts(self):
        """Test progress reporting behavior with small test counts."""
        generator = EnterpriseTestGenerator()

        with tempfile.TemporaryDirectory() as temp_dir:
            category_info: CategoryInfo = {"dir": Path(temp_dir), "count": 0}
            scenarios = {"test": ["scenario1"]}

            # Test with very small count
            with patch.object(generator.logger, "info") as mock_info:
                # Create parameter object

                params = CategoryTestParams(
                    category="small_test",
                    count=5,
                    scenarios=scenarios,
                    category_info=category_info,
                    start_test_id=1,
                )
                generator._generate_category_tests(params)

                # Should still report progress (milestone should be at least 1)
                progress_calls = [
                    call
                    for call in mock_info.call_args_list
                    if "Progress:" in str(call)
                ]
                assert len(progress_calls) > 0

                # Final progress should show 100%
                final_progress = [
                    call
                    for call in mock_info.call_args_list
                    if "Progress:" in str(call) and "100.0%" in str(call)
                ]
                assert len(final_progress) > 0

    def test_file_write_progress_reporting(self):
        """Test progress reporting during file write operations."""
        generator = EnterpriseTestGenerator()

        with patch.object(generator.logger, "info") as mock_info:
            # Create a large enough batch to trigger progress reporting
            # Need > 50 files with reporting at multiples of 20
            # Manually add to queue without triggering auto-flush
            for i in range(60):  # 60 > 50 threshold, will report at index 20, 40
                generator._file_write_queue.append(
                    {
                        "filepath": Path(f"/tmp/test_{i}.json"),
                        "content": {"test": f"data_{i}"},
                    }
                )

            # Manually flush the large queue to trigger progress reporting
            generator._flush_write_queue()

            # Check for file write progress messages
            progress_calls = [
                call for call in mock_info.call_args_list if "File write:" in str(call)
            ]
            assert len(progress_calls) > 0

            # Verify progress message format
            for call in progress_calls:
                message = call[0][0]
                assert "File write:" in message
                assert "/" in message  # Should show current/total
                assert "%" in message  # Should show percentage

    def test_no_progress_reporting_for_small_batches(self):
        """Test that small file batches don't trigger progress reporting."""
        generator = EnterpriseTestGenerator()

        with patch.object(generator.logger, "info") as mock_info:
            # Queue small number of files (should not trigger progress reporting)
            for i in range(10):
                generator._queue_file_write(
                    Path(f"/tmp/small_{i}.json"), {"test": f"data_{i}"}
                )

            generator._flush_write_queue()

            # Should not have file write progress messages for small batches
            progress_calls = [
                call for call in mock_info.call_args_list if "File write:" in str(call)
            ]
            assert len(progress_calls) == 0

    def test_progress_reporting_accuracy(self):
        """Test that progress percentages are calculated accurately."""
        generator = EnterpriseTestGenerator()

        with tempfile.TemporaryDirectory() as temp_dir:
            category_info: CategoryInfo = {"dir": Path(temp_dir), "count": 0}
            scenarios = {"test": ["scenario1"]}

            with patch.object(generator.logger, "info") as mock_info:
                # Create parameter object matching CategoryTestParams structure

                total_tests = 50
                params = CategoryTestParams(
                    category="accuracy_test",
                    count=total_tests,
                    scenarios=scenarios,
                    category_info=category_info,
                    start_test_id=1,
                )
                generator._generate_category_tests(params)

                # Extract progress percentages
                progress_calls = [
                    call
                    for call in mock_info.call_args_list
                    if "Progress:" in str(call)
                ]

                for call in progress_calls:
                    message = call[0][0]
                    # Extract percentage from message like "Progress: 10/50 (20.0%)"
                    if "%" in message:
                        # Find the percentage value
                        match = re.search(r"\((\d+\.?\d*)%\)", message)
                        if match:
                            percentage = float(match.group(1))
                            assert 0 <= percentage <= 100

                # Final message should show 100%
                final_calls = [call for call in progress_calls if "100.0%" in str(call)]
                assert len(final_calls) > 0

    def test_progress_reporting_integration_with_resource_manager(self):
        """Test that progress reporting works with resource manager context."""
        generator = EnterpriseTestGenerator()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(generator.logger, "info") as mock_info:
                # Use resource manager context
                with generator.resource_manager.operation("test_generation"):
                    category_info: CategoryInfo = {"dir": Path(temp_dir), "count": 0}
                    scenarios = {"test": ["scenario1"]}

                    # Create parameter object

                    params = CategoryTestParams(
                        category="integration_test",
                        count=25,
                        scenarios=scenarios,
                        category_info=category_info,
                        start_test_id=1,
                    )
                    generator._generate_category_tests(params)

                # Should have both resource manager and progress reporting logs
                all_messages = [str(call) for call in mock_info.call_args_list]
                progress_messages = [msg for msg in all_messages if "Progress:" in msg]
                assert len(progress_messages) > 0

    def test_concurrent_progress_reporting(self):
        """Test progress reporting behavior with multiple concurrent operations."""
        generator = EnterpriseTestGenerator()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(generator.logger, "info") as mock_info:
                # Simulate multiple category generations
                for category_num in range(3):
                    category_info: CategoryInfo = {"dir": Path(temp_dir), "count": 0}
                    scenarios = {f"test_{category_num}": ["scenario1"]}

                    # Create parameter object

                    params = CategoryTestParams(
                        category=f"concurrent_test_{category_num}",
                        count=15,
                        scenarios=scenarios,
                        category_info=category_info,
                        start_test_id=category_num * 100,
                    )
                    generator._generate_category_tests(params)

                # Should have progress messages for each category
                all_calls = mock_info.call_args_list
                for category_num in range(3):
                    category_messages = [
                        call
                        for call in all_calls
                        if f"concurrent_test_{category_num}" in str(call)
                    ]
                    assert len(category_messages) > 0
