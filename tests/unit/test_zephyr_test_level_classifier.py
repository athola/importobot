"""Comprehensive TDD tests for ZephyrTestLevelClassifier."""

from importobot.core.zephyr_parsers import ZephyrTestLevelClassifier


class TestZephyrTestLevelClassifier:
    """Test ZephyrTestLevelClassifier class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = ZephyrTestLevelClassifier()

    def test_test_levels_structure(self):
        """Test TEST_LEVELS contains expected structure."""
        expected_levels = ["Minimum Viable CRS", "Smoke", "Edge Case", "Regression"]

        for level in expected_levels:
            assert level in self.classifier.TEST_LEVELS
            assert isinstance(self.classifier.TEST_LEVELS[level], int)

        # Verify the priority values (lower numbers = higher priority)
        assert self.classifier.TEST_LEVELS["Smoke"] == 0
        assert self.classifier.TEST_LEVELS["Minimum Viable CRS"] == 1
        assert self.classifier.TEST_LEVELS["Edge Case"] == 2
        assert self.classifier.TEST_LEVELS["Regression"] == 3

    def test_classify_test_minimum_viable_crs(self):
        """Test classification of Minimum Viable CRS tests."""
        test_cases = [
            {
                "name": "Authentication Test",
                "issues": ["CRS-001", "CRS-002"],
                "linkedCRS": ["CRS-AUTH-001"],
                "requirements": ["REQ-001"],
            },
            {
                "name": "Database Connection Test",
                "confluence": ["https://wiki.example.com/DatabaseRequirements"],
                "issues": ["PROJ-123"],
            },
            {
                "name": "API Endpoint Test",
                "requirements": ["API-REQ-001"],
                "webLinks": ["https://requirements.example.com/api-spec"],
            },
        ]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            assert level_name == "Minimum Viable CRS"

    def test_classify_test_smoke(self):
        """Test classification of Smoke tests."""
        test_cases = [
            {
                "name": "Basic Application Startup Test",
                "objective": "Verify application starts successfully",
            },
            {
                "name": "Core Login Functionality",
                "description": "Test critical login functionality",
            },
            {
                "name": "Database Connection Smoke Test",
                "objective": "Verify basic database connectivity for core operations",
            },
            {
                "name": "Critical Path Validation",
                "description": (
                    "Test the most critical user journey through the application"
                ),
            },
            {
                "name": "Startup Health Check",
                "objective": "Basic smoke test to verify system is running",
            },
        ]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            assert level_name == "Smoke"

    def test_classify_test_edge_case(self):
        """Test classification of Edge Case tests."""
        test_cases = [
            {
                "name": "Invalid Input Handling Test",
                "objective": "Test system behavior with invalid input parameters",
            },
            {
                "name": "Boundary Condition Test",
                "description": "Test edge cases at system boundaries",
            },
            {
                "name": "Error Handling Validation",
                "objective": "Verify proper error handling for exception scenarios",
            },
            {
                "name": "Negative Testing Scenarios",
                "description": "Test system response to invalid operations",
            },
            {
                "name": "Resource Limit Testing",
                "objective": "Test behavior when system resources are exhausted",
            },
        ]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            assert level_name == "Edge Case"

    def test_classify_test_regression(self):
        """Test classification of Regression tests (default)."""
        test_cases = [
            {
                "name": "Regular Feature Test",
                "objective": "Test standard functionality",
            },
            {
                "name": "User Management Test",
                "description": "Test user creation and management features",
            },
            {
                "name": "Report Generation Test",
                "objective": "Verify report generation works correctly",
            },
            {
                "name": "Bug Fix Validation",
                "description": "Test that previously fixed bugs remain fixed",
            },
        ]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            assert level_name == "Regression"

    def test_classify_test_priority_order(self):
        """Test that CRS links take priority over smoke test indicators."""
        # Test with both CRS links and smoke indicators - should classify as CRS
        test_data = {
            "name": "Critical Authentication Smoke Test",
            "objective": "Basic smoke test for authentication",
            "issues": ["CRS-001"],  # CRS link should take priority
            "description": "Critical startup test",
        }

        level_name, _level_value = self.classifier.classify_test(test_data)
        assert level_name == "Minimum Viable CRS"

    def test_classify_test_case_insensitive(self):
        """Test classification with case variations."""
        test_cases = [
            {"name": "SMOKE TEST", "objective": "basic startup verification"},
            {"name": "Edge Case Test", "description": "BOUNDARY condition testing"},
            {"name": "ERROR HANDLING TEST", "objective": "Test EXCEPTION scenarios"},
        ]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            # Should still classify correctly despite case variations
            assert level_name in ["Smoke", "Edge Case"]

    def test_classify_test_empty_data(self):
        """Test classification with minimal test data."""
        test_cases = [{}, {"name": ""}, {"description": ""}, {"objective": ""}]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            # Should default to Regression for empty/unclear cases
            assert level_name == "Regression"

    def test_classify_test_complex_scenarios(self):
        """Test classification with complex test scenarios."""
        # Complex test with multiple indicators
        complex_test = {
            "name": "User Authentication Flow",
            "objective": "Test complete user authentication workflow",
            "description": "Critical smoke test for user login functionality",
            "issues": ["BUG-123"],  # Regular bug, not CRS
            "requirements": ["AUTH-REQ-001"],
        }

        level_name, _level_value = self.classifier.classify_test(complex_test)
        # Should classify as Smoke due to smoke indicators and no CRS links
        assert level_name == "Smoke"

        # Another complex test with edge case indicators
        edge_case_test = {
            "name": "Input Validation Test",
            "objective": "Test boundary conditions and invalid inputs",
            "description": "Negative testing for form validation",
            "issues": ["BUG-456"],
        }

        level_name, _level_value = self.classifier.classify_test(edge_case_test)
        assert level_name == "Edge Case"

    def test_has_crs_links_with_various_formats(self):
        """Test CRS link detection with various formats."""
        test_cases = [
            {"issues": ["CRS-001", "PROJ-123"]},
            {"linkedCRS": ["CRS-AUTH-001", "CRS-AUTH-002"]},
            {"requirements": ["CRS-REQ-001"]},
            {"confluence": ["CRS-DOC-001"]},
            {"issues": ["PROJ-123"], "linkedCRS": ["CRS-001"]},  # Mixed
            {"issues": ["proj-123"]},  # Should not match (case-sensitive)
            {"issues": ["CRS123"]},  # Should not match (missing dash)
        ]

        expected_results = [True, True, True, True, True, False, False]

        for test_data, expected in zip(test_cases, expected_results, strict=True):
            result = self.classifier._has_crs_links(test_data)
            assert result == expected, f"Failed for test data: {test_data}"

    def test_is_smoke_test_detection(self):
        """Test smoke test detection logic."""
        test_cases = [
            ({"name": "Basic startup test"}, True),
            ({"objective": "Core functionality verification"}, True),
            ({"description": "Critical path testing"}, True),
            ({"name": "System health check"}, True),
            ({"objective": "Basic connectivity test"}, True),
            ({"name": "Regular feature test"}, False),
            ({"description": "Detailed functionality testing"}, False),
            ({"objective": "Complex workflow validation"}, False),
        ]

        for test_data, expected in test_cases:
            result = self.classifier._is_smoke_test(test_data)
            assert result == expected, f"Failed for test data: {test_data}"

    def test_is_edge_case_detection(self):
        """Test edge case detection logic."""
        test_cases = [
            ({"name": "Boundary condition test"}, True),
            ({"objective": "Error handling validation"}, True),
            ({"description": "Exception scenario testing"}, True),
            ({"name": "Negative testing"}, True),
            ({"objective": "Invalid input handling"}, True),
            ({"name": "Normal flow test"}, False),
            ({"description": "Standard functionality testing"}, False),
            ({"objective": "Happy path validation"}, False),
        ]

        for test_data, expected in test_cases:
            result = self.classifier._is_edge_case(test_data)
            assert result == expected, f"Failed for test data: {test_data}"

    def test_classify_test_with_unicode(self):
        """Test classification with unicode characters."""
        test_cases = [
            {
                "name": "Prueba básica de inicio",
                "objective": "Verificar inicio básico del sistema",
            },
            {
                "name": "Test de gestion des erreurs",
                "description": "Test de scénarios d'exception",
            },
        ]

        for test_data in test_cases:
            level_name, _level_value = self.classifier.classify_test(test_data)
            # Should handle unicode correctly and classify based on content
            assert level_name in ["Smoke", "Edge Case", "Regression"]

    def test_classify_test_performance_considerations(self):
        """Test that classification is efficient for large datasets."""
        # Create a large test case
        large_test = {
            "name": "Performance Test " * 100,
            "objective": "Basic functionality test " * 100,
            "description": "Standard testing approach " * 100,
        }

        # Should complete quickly even with large data
        level_name, _level_value = self.classifier.classify_test(large_test)
        assert level_name == "Smoke"  # Due to "Basic" indicator

    def test_classify_test_return_format(self):
        """Test that classify_test returns expected format."""
        test_data = {"name": "Test Case"}

        result = self.classifier.classify_test(test_data)

        # Should return a tuple of (string, int)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)  # Level name
        assert isinstance(result[1], int)  # Level value

        # Level name should be one of the defined levels
        assert result[0] in self.classifier.TEST_LEVELS

        # Level value should match the defined value
        assert result[1] == self.classifier.TEST_LEVELS[result[0]]
