"""Tests for the optimization service integration layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from importobot.medallion.gold_layer import GoldLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.services.optimization_service import OptimizationService
from importobot.utils.optimization import OptimizerConfig


def test_optimization_service_executes_gradient_descent() -> None:
    """Test that optimization service executes gradient descent algorithm."""
    service = OptimizationService()

    def objective(parameters: dict[str, float]) -> float:
        quality_delta = parameters["quality_weight"] - 1.0
        latency_delta = parameters["latency_weight"] - 0.5
        return quality_delta**2 + latency_delta**2

    service.register_scenario(
        "gradient-descent-preview",
        objective_function=objective,
        initial_parameters={"quality_weight": 0.0, "latency_weight": 1.0},
    )

    outcome = service.execute(
        "gradient-descent-preview",
        gradient_config=OptimizerConfig(max_iterations=6, tolerance=1e-5),
    )

    assert outcome.algorithm == "gradient_descent"
    assert set(outcome.parameters).issuperset({"quality_weight", "latency_weight"})
    assert outcome.score >= 0.0


def test_optimization_service_evicts_old_scenarios() -> None:
    """Test that optimization service evicts old scenarios when limit is reached."""
    service = OptimizationService()

    def objective(parameters: dict[str, float]) -> float:
        return parameters.get("x", 0.0) ** 2

    max_scenarios = service.MAX_REGISTERED_SCENARIOS

    for index in range(max_scenarios + 5):
        service.register_scenario(
            f"scenario-{index}",
            objective_function=objective,
            initial_parameters={"x": float(index)},
        )

    assert not service.has_scenario("scenario-0")
    assert service.has_scenario(f"scenario-{max_scenarios + 4}")


def test_optimization_service_limits_cached_results() -> None:
    """Test that optimization service limits the number of cached results."""
    service = OptimizationService()

    def objective(parameters: dict[str, float]) -> float:
        return parameters.get("x", 0.0) ** 2

    total_runs = service.MAX_RESULT_HISTORY + 10

    for index in range(total_runs):
        name = f"scenario-{index}"
        service.register_scenario(
            name,
            objective_function=objective,
            initial_parameters={"x": float(index)},
        )
        service.execute(name, gradient_config=OptimizerConfig(max_iterations=3))

    # pylint: disable=protected-access
    assert len(service._results) <= service.MAX_RESULT_HISTORY
    assert "scenario-0" not in service._results


def test_gold_layer_optimization_preview_included(tmp_path: Path) -> None:
    """Test that gold layer includes optimization preview in processing results."""
    gold_layer = GoldLayer(optimization_service=OptimizationService())
    metadata = LayerMetadata(
        source_path=tmp_path / "source.json",
        layer_name="gold",
        ingestion_timestamp=datetime.now(),
        custom_metadata={
            "conversion_optimization": {
                "enabled": True,
                "scenario_name": "conversion-preview",
                "preview_max_iterations": 4,
                "baseline_quality_score": 0.74,
                "target_quality_score": 0.9,
                "baseline_latency_ms": 700.0,
                "target_latency_ms": 450.0,
                "suite_complexity": 5,
            }
        },
    )

    result = gold_layer.ingest({"test_cases": [1, 2, 3, 4]}, metadata)

    assert "optimization_preview" in result.details
    preview = result.details["optimization_preview"]
    assert preview["algorithm"] == "gradient_descent"
    assert set(preview["parameters"]).issuperset({"quality_weight", "latency_weight"})
    assert preview["score"] >= 0.0
