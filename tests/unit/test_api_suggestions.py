"""Tests for importobot.api.suggestions module.

These tests exercise the public suggestion engine with realistic JSON
fixtures and assert on the improvement guidance it returns.
The goal is to verify business behaviour rather than just the existence
of API shapes.
"""

from typing import Any

from importobot.api import suggestions


def make_step(
    action: str, expected: str | None = None, data: str | None = None
) -> dict[str, Any]:
    """Create a step payload using canonical field names."""
    step: dict[str, str] = {"action": action}
    if expected is not None:
        step["expectedResult"] = expected
    if data is not None:
        step["testData"] = data
    return step


def make_test_case(
    *,
    name: str = "Sample Test",
    description: str | None = "Sample description",
    steps: list[dict[str, Any]] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical test case structure recognised by the engine."""
    payload: dict[str, object] = {
        "name": name,
        "description": description,
        "testScript": {"steps": steps or []},
    }
    if extra_fields:
        payload.update(extra_fields)
    return payload


class TestSuggestionEngine:
    """Test the suggestion engine in the API module."""

    def test_suggestion_engine_instantiation(self) -> None:
        """Engine can be created and exposes the public API."""
        engine = suggestions.GenericSuggestionEngine()
        assert hasattr(engine, "get_suggestions")
        assert hasattr(engine, "apply_suggestions")

    def test_suggestion_engine_with_empty_data(self) -> None:
        """Empty payload returns concrete guidance for missing structure."""
        engine = suggestions.GenericSuggestionEngine()

        result = engine.get_suggestions({})

        assert "Test case 1: Add test case name" in result
        assert "Test case 1: Add test case description" in result
        assert "Test case 1: Add test steps" in result
        assert any(
            suggestion.endswith("Add test steps to define actions")
            for suggestion in result
        )

    def test_suggestion_engine_with_minimal_test_case(self) -> None:
        """Minimal but incomplete test case surfaces actionable prompts."""
        engine = suggestions.GenericSuggestionEngine()

        minimal_test = make_test_case(name="Minimal Test", description=None)

        result = engine.get_suggestions(minimal_test)

        assert "Test case 1: Add test case description" in result
        assert any(
            suggestion.endswith("Add test steps to define actions")
            for suggestion in result
        )

    def test_suggestions_module_exports(self) -> None:
        """Public module re-exports match the documented surface."""
        assert hasattr(suggestions, "__all__")
        assert set(suggestions.__all__) == {"GenericSuggestionEngine"}
        exported_engine = suggestions.GenericSuggestionEngine
        assert exported_engine.__name__ == "GenericSuggestionEngine"


class TestQAWorkflowIntegration:
    """Test suggestion engine integration with QA workflows."""

    def test_ambiguous_test_case_suggestions(self) -> None:
        """Missing step metadata produces the correct per-step guidance."""
        engine = suggestions.GenericSuggestionEngine()

        ambiguous_test = make_test_case(
            name="Login Test",
            steps=[make_step("Do something")],
        )

        result = engine.get_suggestions(ambiguous_test)

        assert any("Add expected result field" in suggestion for suggestion in result)
        assert any("Add test data field" in suggestion for suggestion in result)

    def test_incomplete_test_case_suggestions(self) -> None:
        """Engine highlights every missing field across multiple steps."""
        engine = suggestions.GenericSuggestionEngine()

        incomplete_test = make_test_case(
            name="Database Test",
            steps=[
                make_step("Connect to database"),
                make_step("Run query", data="SELECT * FROM users"),
            ],
        )

        result = engine.get_suggestions(incomplete_test)

        assert any(
            suggestion.startswith("Test case 1, Step 1: Add expected result")
            for suggestion in result
        )
        assert any(
            suggestion.startswith("Test case 1, Step 1: Add test data field")
            for suggestion in result
        )
        assert any(
            suggestion.startswith("Test case 1, Step 2: Add expected result")
            for suggestion in result
        )

    def test_enterprise_test_case_optimization(self) -> None:
        """Well-formed test case returns the success sentinel message."""
        engine = suggestions.GenericSuggestionEngine()

        enterprise_test = make_test_case(
            name="Enterprise User Management Test",
            steps=[
                make_step(
                    "Login to system",
                    expected="Login successful",
                    data="username: admin, password: secret123",
                ),
                make_step(
                    "Navigate to user management",
                    expected="User management page displays",
                    data="section=user-management",
                ),
                make_step(
                    "Create new user",
                    expected="User created successfully",
                    data="name: John Doe, email: john@company.com",
                ),
            ],
        )

        result = engine.get_suggestions(enterprise_test)

        assert result == ["No improvements needed - test data is well-structured"]

    def test_suggestion_consistency_across_calls(self) -> None:
        """Subsequent calls with the same payload stay deterministic."""
        engine = suggestions.GenericSuggestionEngine()

        test_case = make_test_case(
            name="Consistency Test",
            steps=[make_step("Test action", expected="Test result")],
        )

        first = engine.get_suggestions(test_case)
        second = engine.get_suggestions(test_case)

        assert first == second


class TestEnterpriseQARequirements:
    """Test suggestion engine requirements for enterprise QA teams."""

    def test_handles_large_test_suites(self) -> None:
        """Large suites return the success sentinel rather than raising."""
        engine = suggestions.GenericSuggestionEngine()

        large_test_suite = {
            "name": "Enterprise Regression Suite",
            "description": "Large regression suite",
            "tests": [
                make_test_case(
                    name=f"Regression Test {index + 1}",
                    steps=[
                        make_step(
                            f"Execute regression step {index + 1}",
                            expected=f"Regression step {index + 1} passes",
                            data=f"dataset_{index + 1}",
                        )
                    ],
                )
                for index in range(50)
            ],
        }

        result = engine.get_suggestions(large_test_suite)

        assert result == ["No improvements needed - test data is well-structured"]

    def test_suggestion_quality_for_complex_scenarios(self) -> None:
        """Complex scenarios surface parameter mapping suggestions when needed."""
        engine = suggestions.GenericSuggestionEngine()

        complex_test = make_test_case(
            name="Multi-System Integration Test",
            description="Complex test involving multiple systems",
            steps=[
                make_step(
                    "Initialize enterprise environment",
                    expected="Environment initialized",
                    data="config: ${ENTERPRISE_CONFIG}",
                ),
                make_step(
                    "Connect to external API",
                    expected="API connection established",
                    data="endpoint: https://api.partner.com/v1",
                ),
                make_step(
                    "Sync user data across systems",
                    expected="User data synchronized",
                    data="users: batch_001.json",
                ),
                make_step(
                    "Verify data consistency",
                    expected="Data consistency verified across all systems",
                ),
            ],
        )

        result = engine.get_suggestions(complex_test)

        assert any(
            "Consider adding Robot Framework variable mappings" in item
            for item in result
        )
        assert any("Add parameter definition" in item for item in result)

    def test_security_suggestions_for_enterprise(self) -> None:
        """Placeholder parameters trigger explicit variable mapping guidance."""
        engine = suggestions.GenericSuggestionEngine()

        security_test = make_test_case(
            name="Authentication Test",
            steps=[
                make_step(
                    "Login with credentials",
                    expected="Login successful",
                    data="username: ${ADMIN_USER}, password: ${ADMIN_PASSWORD}",
                ),
                make_step(
                    "Access sensitive data",
                    expected="Data retrieved",
                    data="token=<API_TOKEN> query: ${QUERY_ID}",
                ),
            ],
        )

        result = engine.get_suggestions(security_test)

        assert any("ADMIN_PASSWORD" in suggestion for suggestion in result)
        assert any("API_TOKEN" in suggestion for suggestion in result)

    def test_performance_with_enterprise_workloads(self) -> None:
        """Massive step lists yield a single success message, not errors."""
        engine = suggestions.GenericSuggestionEngine()

        steps = [
            make_step(
                f"Enterprise operation {index + 1}",
                expected=f"Operation {index + 1} completes within SLA",
                data=f"operation_data_{index + 1}: {'x' * 50}",
            )
            for index in range(1000)
        ]
        enterprise_workload = make_test_case(
            name="Enterprise Performance Test",
            description="Large test case for performance validation",
            steps=steps,
        )

        result = engine.get_suggestions(enterprise_workload)

        assert result == ["No improvements needed - test data is well-structured"]

    def test_internationalization_support(self) -> None:
        """International characters survive analysis and still succeed."""
        engine = suggestions.GenericSuggestionEngine()

        international_test = make_test_case(
            name="Test Internacionalización (çãé)",
            description="Test with international characters: åäöüß",
            steps=[
                make_step(
                    "Introducir datos especiales: éñü",
                    expected="Caracteres especiales manejados correctamente",
                    data="datos con ñ y ç caracteres",
                )
            ],
        )

        result = engine.get_suggestions(international_test)

        assert result == ["No improvements needed - test data is well-structured"]
