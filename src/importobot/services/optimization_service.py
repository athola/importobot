"""Gateway service for optimization algorithms.

This service provides a thin integration layer between the mathematical
optimization utilities in :mod:`importobot.utils.optimization` and the rest of
Importobot's architecture. It will be used by the upcoming Gold layer to tune
conversion heuristics and performance levers while keeping the optimizer
implementations decoupled from business logic.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from importobot.config import OPTIMIZATION_CACHE_TTL_SECONDS
from importobot.utils.optimization import (
    AnnealingConfig,
    GeneticAlgorithmOptimizer,
    GradientDescentOptimizer,
    OptimizerConfig,
    simulated_annealing,
)

AlgorithmName = str


@dataclass
class OptimizationScenario:
    """Container describing an optimization problem instance."""

    objective_function: Callable[[dict[str, float]], float]
    initial_parameters: dict[str, float]
    parameter_bounds: dict[str, tuple[float, float]] | None = None
    algorithm: AlgorithmName = "gradient_descent"
    maximize: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationOutcome:
    """Normalized representation of an optimization result."""

    algorithm: AlgorithmName
    parameters: dict[str, float]
    score: float
    details: dict[str, Any] = field(default_factory=dict)


class OptimizationService:
    """Expose Importobot's optimization utilities through a cohesive service.

    The near-term consumer is the Gold layer optimization pipeline. The service
    keeps algorithm selection, optimizer configuration, and metadata collection
    centralized so downstream features can request optimization without knowing
    the implementation details of each algorithm.
    """

    SUPPORTED_ALGORITHMS: ClassVar[set[AlgorithmName]] = {
        "gradient_descent",
        "genetic_algorithm",
        "simulated_annealing",
    }

    MAX_REGISTERED_SCENARIOS: ClassVar[int] = 32
    MAX_RESULT_HISTORY: ClassVar[int] = 64

    def __init__(
        self,
        default_algorithm: AlgorithmName = "gradient_descent",
        *,
        cache_ttl_seconds: int | None = None,
    ) -> None:
        """Initialize optimization service with default algorithm."""
        self.default_algorithm = default_algorithm
        self._scenarios: OrderedDict[str, OptimizationScenario] = OrderedDict()
        self._results: OrderedDict[str, OptimizationOutcome] = OrderedDict()
        resolved_ttl = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else OPTIMIZATION_CACHE_TTL_SECONDS
        )
        self._ttl_seconds: int | None = resolved_ttl if resolved_ttl > 0 else None
        # TTL derives from `IMPORTOBOT_OPTIMIZATION_CACHE_TTL_SECONDS` to ensure
        # scenarios/results expire in long-running processes.
        self._scenario_expiry: dict[str, float] = {}
        self._result_expiry: dict[str, float] = {}

    def register_scenario(
        self,
        name: str,
        objective_function: Callable[[dict[str, float]], float],
        initial_parameters: dict[str, float],
        *,
        parameter_bounds: dict[str, tuple[float, float]] | None = None,
        algorithm: AlgorithmName | None = None,
        maximize: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register an optimization scenario for later execution."""
        self._purge_expired_entries()
        chosen_algorithm = algorithm or self.default_algorithm
        if chosen_algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f'Unsupported algorithm "{chosen_algorithm}". Supported algorithms: '
                f"{sorted(self.SUPPORTED_ALGORITHMS)}"
            )
        scenario = OptimizationScenario(
            objective_function=objective_function,
            initial_parameters=initial_parameters,
            parameter_bounds=parameter_bounds,
            algorithm=chosen_algorithm,
            maximize=maximize,
            metadata=metadata or {},
        )

        if name in self._scenarios:
            self._scenarios.move_to_end(name)
        self._scenarios[name] = scenario
        self._touch_scenario(name)

        if len(self._scenarios) > self.MAX_REGISTERED_SCENARIOS:
            evicted_name, _ = self._scenarios.popitem(last=False)
            self._scenario_expiry.pop(evicted_name, None)
            self._results.pop(evicted_name, None)
            self._result_expiry.pop(evicted_name, None)

    def has_scenario(self, name: str) -> bool:
        """Return True if a scenario has been registered."""
        self._purge_expired_entries()
        return name in self._scenarios

    def execute(
        self,
        name: str,
        *,
        algorithm: AlgorithmName | None = None,
        gradient_config: OptimizerConfig | None = None,
        annealing_config: AnnealingConfig | None = None,
        genetic_optimizer: GeneticAlgorithmOptimizer | None = None,
    ) -> OptimizationOutcome:
        """Execute a registered optimization scenario and return the outcome."""
        self._purge_expired_entries()
        if name not in self._scenarios:
            raise KeyError(f'Unknown optimization scenario "{name}"')

        scenario = self._scenarios[name]
        self._scenarios.move_to_end(name)
        chosen_algorithm = algorithm or scenario.algorithm
        self._touch_scenario(name)

        if chosen_algorithm == "gradient_descent":
            return self._run_gradient_descent(name, scenario, gradient_config)
        if chosen_algorithm == "simulated_annealing":
            return self._run_simulated_annealing(name, scenario, annealing_config)
        if chosen_algorithm == "genetic_algorithm":
            return self._run_genetic_algorithm(name, scenario, genetic_optimizer)

        raise ValueError(
            f'Unsupported algorithm "{chosen_algorithm}". Supported algorithms: '
            f"{sorted(self.SUPPORTED_ALGORITHMS)}"
        )

    def last_result(self, name: str) -> OptimizationOutcome | None:
        """Return the last cached result for a scenario, if any."""
        self._purge_expired_entries()
        return self._results.get(name)

    def clear(self) -> None:
        """Remove all registered scenarios and cached results."""
        self._scenarios.clear()
        self._results.clear()
        self._scenario_expiry.clear()
        self._result_expiry.clear()

    # Internal helpers
    def _cache_result(
        self, name: str, outcome: OptimizationOutcome
    ) -> OptimizationOutcome:
        """Cache an optimization outcome."""
        if name in self._results:
            self._results.move_to_end(name)
        self._results[name] = outcome
        self._touch_result(name)
        if len(self._results) > self.MAX_RESULT_HISTORY:
            evicted_name, _ = self._results.popitem(last=False)
            self._result_expiry.pop(evicted_name, None)
        return outcome

    def _run_gradient_descent(
        self,
        name: str,
        scenario: OptimizationScenario,
        gradient_config: OptimizerConfig | None,
    ) -> OptimizationOutcome:
        """Run gradient descent optimization for a scenario."""
        optimizer = GradientDescentOptimizer(gradient_config)
        parameters, value, metadata = optimizer.optimize(
            scenario.objective_function,
            scenario.initial_parameters,
            scenario.parameter_bounds,
        )
        outcome = OptimizationOutcome(
            algorithm="gradient_descent",
            parameters=parameters,
            score=value,
            details={"metadata": metadata, "maximize": scenario.maximize},
        )
        return self._cache_result(name, outcome)

    def _run_simulated_annealing(
        self,
        name: str,
        scenario: OptimizationScenario,
        annealing_config: AnnealingConfig | None,
    ) -> OptimizationOutcome:
        """Run simulated annealing optimization for a scenario."""
        parameters, value, metadata = simulated_annealing(
            scenario.objective_function,
            scenario.initial_parameters,
            scenario.parameter_bounds,
            config=annealing_config,
        )
        outcome = OptimizationOutcome(
            algorithm="simulated_annealing",
            parameters=parameters,
            score=value,
            details={"metadata": metadata, "maximize": scenario.maximize},
        )
        return self._cache_result(name, outcome)

    def _run_genetic_algorithm(
        self,
        name: str,
        scenario: OptimizationScenario,
        genetic_optimizer: GeneticAlgorithmOptimizer | None,
    ) -> OptimizationOutcome:
        """Run genetic algorithm optimization for a scenario."""
        optimizer = genetic_optimizer or GeneticAlgorithmOptimizer()
        parameter_ranges = self._ensure_parameter_ranges(
            scenario.initial_parameters,
            scenario.parameter_bounds,
        )

        def fitness(individual: dict[str, float]) -> float:
            score = scenario.objective_function(individual)
            return score if scenario.maximize else -score

        best_parameters, best_fitness, metadata = optimizer.optimize(
            fitness_function=fitness,
            parameter_ranges=parameter_ranges,
            initial_population=[scenario.initial_parameters],
        )
        score = best_fitness if scenario.maximize else -best_fitness
        outcome = OptimizationOutcome(
            algorithm="genetic_algorithm",
            parameters=best_parameters,
            score=score,
            details={"metadata": metadata, "maximize": scenario.maximize},
        )
        return self._cache_result(name, outcome)

    # Cache bookkeeping helpers -------------------------------------------------

    def _current_time(self) -> float:
        """Provide current time (extracted for easier testing)."""
        return time.time()

    def _touch_scenario(self, name: str) -> None:
        """Update the last access time for a scenario."""
        if self._ttl_seconds is None:
            return
        self._scenario_expiry[name] = self._current_time()

    def _touch_result(self, name: str) -> None:
        """Update the last access time for a result."""
        if self._ttl_seconds is None:
            return
        self._result_expiry[name] = self._current_time()

    def _purge_expired_entries(self) -> None:
        """Remove expired scenarios and results from the cache."""
        if self._ttl_seconds is None:
            return

        now = self._current_time()

        expired_scenarios = [
            name
            for name, timestamp in list(self._scenario_expiry.items())
            if now - timestamp > self._ttl_seconds
        ]
        for name in expired_scenarios:
            self._scenario_expiry.pop(name, None)
            self._scenarios.pop(name, None)
            self._results.pop(name, None)
            self._result_expiry.pop(name, None)

        expired_results = [
            name
            for name, timestamp in list(self._result_expiry.items())
            if now - timestamp > self._ttl_seconds
        ]
        for name in expired_results:
            self._result_expiry.pop(name, None)
            self._results.pop(name, None)

    @staticmethod
    def _ensure_parameter_ranges(
        initial_parameters: dict[str, float],
        parameter_bounds: dict[str, tuple[float, float]] | None,
    ) -> dict[str, tuple[float, float]]:
        """Ensure parameter ranges are defined for optimization."""
        if parameter_bounds:
            return parameter_bounds

        parameter_ranges: dict[str, tuple[float, float]] = {}
        for name, value in initial_parameters.items():
            if value == 0:
                parameter_ranges[name] = (-1.0, 1.0)
            else:
                span = abs(value) * 0.5
                parameter_ranges[name] = (value - span, value + span)
        return parameter_ranges


__all__ = [
    "OptimizationOutcome",
    "OptimizationScenario",
    "OptimizationService",
]
