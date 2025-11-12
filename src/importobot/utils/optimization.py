"""Optimization algorithms and mathematical utilities for Importobot.

Provide advanced optimization algorithms for improving test conversion processes.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast


@dataclass
class OptimizerConfig:
    """Configuration for gradient descent optimizer."""

    learning_rate: float = 0.01
    momentum: float = 0.9
    regularization: float = 0.001
    max_iterations: int = 1000
    tolerance: float = 1e-6
    adaptive_learning: bool = True


@dataclass
class AnnealingConfig:
    """Configuration for simulated annealing optimizer."""

    initial_temperature: float = 100.0
    cooling_rate: float = 0.95
    min_temperature: float = 1e-6
    max_iterations: int = 1000


class GradientDescentOptimizer:
    """Gradient descent optimizer for parameter tuning and function optimization.

    This class implements gradient descent with various enhancements including:
    - Adaptive learning rates
    - Momentum-based optimization
    - Regularization to prevent overfitting
    - Convergence detection and early stopping
    """

    def __init__(self, config: OptimizerConfig | None = None):
        """Initialize gradient descent optimizer.

        Args:
            config: Optimizer configuration. If None, uses default config.
        """
        self.config = config or OptimizerConfig()

        # Optimization state
        self.velocity: dict[str, float] = {}
        self.iteration_count = 0
        self.convergence_history: list[float] = []

    def optimize(
        self,
        objective_function: Callable[[dict[str, float]], float],
        initial_parameters: dict[str, float],
        parameter_bounds: dict[str, tuple[float, float]] | None = None,
        gradient_function: Callable[[dict[str, float]], dict[str, float]] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """Optimize parameters using gradient descent.

        Args:
            objective_function: Function to minimize (takes parameters, returns scalar)
            initial_parameters: Starting parameter values
            parameter_bounds: Optional bounds for parameters (min, max)
            gradient_function: Optional function to compute gradients
                (uses numerical if None)

        Returns:
            Tuple of (optimized_parameters, final_value, optimization_metadata)
        """
        # Initialize optimization state
        state = self._initialize_optimization_state(
            initial_parameters, objective_function
        )
        parameter_bounds = parameter_bounds or {}

        # Main optimization loop
        for iteration in range(self.config.max_iterations):
            self.iteration_count = iteration

            # Compute and apply gradients
            gradients = self._compute_gradients(
                objective_function, state.parameters, gradient_function
            )
            self._apply_regularization(gradients, state.parameters)

            # Update parameters using momentum
            self._update_parameters_with_momentum(state, gradients, parameter_bounds)

            # Evaluate and track progress
            current_value = objective_function(state.parameters)
            self.convergence_history.append(current_value)

            # Update best solution if improved
            if current_value < state.best_value:
                state.best_parameters = state.parameters.copy()
                state.best_value = current_value

            # Adaptive learning rate adjustment
            if self.config.adaptive_learning and iteration > 0:
                state.learning_rate = self._adjust_learning_rate(
                    gradients, state.learning_rate, state.prev_gradient_norm
                )
                state.prev_gradient_norm = math.sqrt(
                    sum(g**2 for g in gradients.values())
                )

            # Check for convergence
            if self._check_convergence(iteration):
                break

        return self._create_optimization_result(state)

    def _initialize_optimization_state(
        self,
        initial_parameters: dict[str, float],
        objective_function: Callable[..., float],
    ) -> Any:
        """Initialize optimization state variables."""

        @dataclass
        class OptimizationState:
            """Optimization state tracking for gradient descent."""

            parameters: dict[str, float]
            best_parameters: dict[str, float]
            best_value: float
            learning_rate: float
            prev_gradient_norm: float

        parameters = initial_parameters.copy()
        self.velocity = cast(dict[str, float], dict.fromkeys(parameters, 0.0))
        self.iteration_count = 0
        self.convergence_history = []

        return OptimizationState(
            parameters=parameters,
            best_parameters=parameters.copy(),
            best_value=objective_function(parameters),
            learning_rate=self.config.learning_rate,
            prev_gradient_norm=float("inf"),
        )

    def _compute_gradients(
        self,
        objective_function: Callable[..., float],
        parameters: dict[str, float],
        gradient_function: Callable[..., dict[str, float]] | None,
    ) -> dict[str, float]:
        """Compute gradients using provided function or numerical approximation."""
        if gradient_function:
            return gradient_function(parameters)
        return self._compute_numerical_gradients(objective_function, parameters)

    def _apply_regularization(
        self, gradients: dict[str, float], parameters: dict[str, float]
    ) -> None:
        """Apply L2 regularization to gradients."""
        for param, value in parameters.items():
            if param in gradients:
                gradients[param] += self.config.regularization * value

    def _update_parameters_with_momentum(
        self,
        state: Any,
        gradients: dict[str, float],
        parameter_bounds: dict[str, tuple[float, float]],
    ) -> None:
        """Update parameters using momentum and apply bounds."""
        # Update velocity with momentum
        for param in state.parameters:
            if param in gradients:
                self.velocity[param] = (
                    self.config.momentum * self.velocity[param]
                    - state.learning_rate * gradients[param]
                )

        # Update parameters and apply bounds
        for param in state.parameters:
            if param in self.velocity:
                state.parameters[param] += self.velocity[param]

            # Apply parameter bounds
            if param in parameter_bounds:
                min_val, max_val = parameter_bounds[param]
                state.parameters[param] = max(
                    min_val, min(max_val, state.parameters[param])
                )

    def _adjust_learning_rate(
        self,
        gradients: dict[str, float],
        current_learning_rate: float,
        prev_gradient_norm: float,
    ) -> float:
        """Adjust learning rate based on gradient norm changes."""
        current_gradient_norm = math.sqrt(sum(g**2 for g in gradients.values()))

        if current_gradient_norm > prev_gradient_norm * 1.2:
            return current_learning_rate * 0.5  # Reduce if diverging
        if current_gradient_norm < prev_gradient_norm * 0.8:
            return current_learning_rate * 1.02  # Slightly increase if converging

        return current_learning_rate

    def _check_convergence(self, iteration: int) -> bool:
        """Check if optimization has converged."""
        if iteration > 10:
            recent_values = self.convergence_history[-10:]
            return max(recent_values) - min(recent_values) < self.config.tolerance
        return False

    def _create_optimization_result(
        self, state: Any
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """Create final optimization result."""
        optimization_metadata = {
            "iterations": self.iteration_count + 1,
            "convergence_history": self.convergence_history,
            "final_learning_rate": state.learning_rate,
            "converged": len(self.convergence_history) < self.config.max_iterations,
            "best_value": state.best_value,
        }

        return state.best_parameters, state.best_value, optimization_metadata

    def _compute_numerical_gradients(
        self,
        objective_function: Callable[[dict[str, float]], float],
        parameters: dict[str, float],
    ) -> dict[str, float]:
        """Compute gradients using numerical differentiation.

        Args:
            objective_function: Function to compute gradients for
            parameters: Current parameter values

        Returns:
            Dictionary of parameter gradients
        """
        gradients = {}
        epsilon = 1e-8

        objective_function(parameters)  # Call to establish baseline

        for param in parameters:
            # Compute forward difference
            parameters_plus = parameters.copy()
            parameters_plus[param] += epsilon
            forward_value = objective_function(parameters_plus)

            # Compute backward difference
            parameters_minus = parameters.copy()
            parameters_minus[param] -= epsilon
            backward_value = objective_function(parameters_minus)

            # Central difference for better accuracy
            gradients[param] = (forward_value - backward_value) / (2 * epsilon)

        return gradients


class GeneticAlgorithmOptimizer:  # pylint: disable=too-many-positional-arguments
    """Genetic algorithm optimizer for complex parameter spaces.

    This class implements a genetic algorithm with:
    - Tournament selection
    - Crossover and mutation operations
    - Elitism to preserve best solutions
    - Adaptive mutation rates
    """

    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism_count: int = 2,
        max_generations: int = 100,
        tournament_size: int = 3,
    ):
        """Initialize genetic algorithm optimizer.

        Args:
            population_size: Number of individuals in population
            mutation_rate: Probability of mutation for each gene
            crossover_rate: Probability of crossover between parents
            elitism_count: Number of best individuals to preserve
            max_generations: Maximum number of generations
            tournament_size: Size of tournament for selection
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count
        self.max_generations = max_generations
        self.tournament_size = tournament_size

        # Optimization state
        self.generation_count = 0
        self.fitness_history: list[float] = []

    def optimize(
        self,
        fitness_function: Callable[[dict[str, float]], float],
        parameter_ranges: dict[str, tuple[float, float]],
        initial_population: list[dict[str, float]] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """Optimize parameters using genetic algorithm.

        Args:
            fitness_function: Function to maximize (takes parameters, returns fitness)
            parameter_ranges: Dictionary of parameter ranges (min, max)
            initial_population: Optional starting population

        Returns:
            Tuple of (best_parameters, best_fitness, optimization_metadata)
        """
        # Initialize population and tracking variables
        population = self._initialize_population(parameter_ranges, initial_population)
        best_individual, best_fitness = self._initialize_best_solution(parameter_ranges)
        self.fitness_history = []

        # Evolution loop
        for generation in range(self.max_generations):
            self.generation_count = generation

            # Evaluate fitness and update best solution
            fitness_scores = self._evaluate_population(population, fitness_function)
            best_individual, best_fitness = self._update_best_solution(
                population, fitness_scores, best_individual, best_fitness
            )
            self.fitness_history.append(max(fitness_scores))

            # Check for convergence
            if self._check_genetic_convergence(generation):
                break

            # Create next generation
            population = self._create_next_generation(
                population, fitness_scores, parameter_ranges
            )

        return self._create_genetic_result(best_individual, best_fitness)

    def _initialize_population(
        self,
        parameter_ranges: dict[str, tuple[float, float]],
        initial_population: list[dict[str, float]] | None,
    ) -> list[dict[str, float]]:
        """Initialize the genetic algorithm population."""
        if initial_population:
            population = initial_population[: self.population_size]
            # Fill remaining slots with random individuals
            while len(population) < self.population_size:
                population.append(self._generate_random_individual(parameter_ranges))
            return population

        return [
            self._generate_random_individual(parameter_ranges)
            for _ in range(self.population_size)
        ]

    def _initialize_best_solution(
        self, parameter_ranges: dict[str, tuple[float, float]]
    ) -> tuple[dict[str, float], float]:
        """Initialize best solution tracking."""
        return self._generate_random_individual(parameter_ranges), float("-inf")

    def _evaluate_population(
        self,
        population: list[dict[str, float]],
        fitness_function: Callable[[dict[str, float]], float],
    ) -> list[float]:
        """Evaluate fitness for all individuals in population."""
        return [fitness_function(individual) for individual in population]

    def _update_best_solution(
        self,
        population: list[dict[str, float]],
        fitness_scores: list[float],
        current_best: dict[str, float],
        current_best_fitness: float,
    ) -> tuple[dict[str, float], float]:
        """Update best solution if a better one is found."""
        best_individual = current_best
        best_fitness = current_best_fitness

        for individual, fitness in zip(population, fitness_scores, strict=False):
            if fitness > best_fitness:
                best_fitness = fitness
                best_individual = individual.copy()

        return best_individual, best_fitness

    def _check_genetic_convergence(self, generation: int) -> bool:
        """Check if genetic algorithm has converged."""
        if generation > 20:
            recent_fitness = self.fitness_history[-20:]
            return max(recent_fitness) - min(recent_fitness) < 1e-6
        return False

    def _create_next_generation(
        self,
        population: list[dict[str, float]],
        fitness_scores: list[float],
        parameter_ranges: dict[str, tuple[float, float]],
    ) -> list[dict[str, float]]:
        """Create the next generation through selection, crossover, and mutation."""
        new_population = []

        # Elitism: preserve best individuals
        new_population.extend(self._apply_elitism(population, fitness_scores))

        # Generate remaining individuals
        while len(new_population) < self.population_size:
            child = self._generate_offspring(
                population, fitness_scores, parameter_ranges
            )
            new_population.append(child)

        return new_population

    def _apply_elitism(
        self, population: list[dict[str, float]], fitness_scores: list[float]
    ) -> list[dict[str, float]]:
        """Select elite individuals for next generation."""
        elite_indices = sorted(
            range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True
        )
        return [
            population[elite_indices[i]].copy()
            for i in range(min(self.elitism_count, len(population)))
        ]

    def _generate_offspring(
        self,
        population: list[dict[str, float]],
        fitness_scores: list[float],
        parameter_ranges: dict[str, tuple[float, float]],
    ) -> dict[str, float]:
        """Generate a single offspring through selection, crossover, and mutation."""
        parent1 = self._tournament_selection(population, fitness_scores)
        parent2 = self._tournament_selection(population, fitness_scores)

        # Apply crossover
        if random.random() < self.crossover_rate:
            child = self._crossover(parent1, parent2)
        else:
            child = random.choice([parent1.copy(), parent2.copy()])

        # Apply mutation
        if random.random() < self.mutation_rate:
            child = self._mutate(child, parameter_ranges)

        return child

    def _create_genetic_result(
        self, best_individual: dict[str, float], best_fitness: float
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """Create final genetic algorithm result."""
        optimization_metadata = {
            "generations": self.generation_count + 1,
            "fitness_history": self.fitness_history,
            "converged": len(self.fitness_history) < self.max_generations,
            "best_fitness": best_fitness,
        }

        return best_individual, best_fitness, optimization_metadata

    def _generate_random_individual(
        self, parameter_ranges: dict[str, tuple[float, float]]
    ) -> dict[str, float]:
        """Generate a random individual within parameter ranges."""
        return {
            param: random.uniform(min_val, max_val)
            for param, (min_val, max_val) in parameter_ranges.items()
        }

    def _tournament_selection(
        self, population: list[dict[str, float]], fitness_scores: list[float]
    ) -> dict[str, float]:
        """Select individual using tournament selection."""
        tournament_indices = random.sample(
            range(len(population)), min(self.tournament_size, len(population))
        )
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_index = tournament_indices[
            tournament_fitness.index(max(tournament_fitness))
        ]
        return population[winner_index].copy()

    def _crossover(
        self, parent1: dict[str, float], parent2: dict[str, float]
    ) -> dict[str, float]:
        """Perform crossover between two parents."""
        child: dict[str, float] = {}
        for param, value in parent1.items():
            if param in parent2:
                # Uniform crossover
                child[param] = random.choice([value, parent2[param]])
            else:
                child[param] = value
        return child

    def _mutate(
        self,
        individual: dict[str, float],
        parameter_ranges: dict[str, tuple[float, float]],
    ) -> dict[str, float]:
        """Mutate an individual within parameter ranges."""
        mutated = individual.copy()
        for param in mutated:
            if param in parameter_ranges:
                min_val, max_val = parameter_ranges[param]
                # Gaussian mutation
                mutation_strength = (max_val - min_val) * 0.1
                mutated[param] += random.gauss(0, mutation_strength)
                mutated[param] = max(min_val, min(max_val, mutated[param]))
        return mutated


def simulated_annealing(
    objective_function: Callable[[dict[str, float]], float],
    initial_parameters: dict[str, float],
    parameter_bounds: dict[str, tuple[float, float]] | None = None,
    config: AnnealingConfig | None = None,
) -> tuple[dict[str, float], float, dict[str, Any]]:
    """Perform simulated annealing optimization algorithm.

    Args:
        objective_function: Function to minimize
        initial_parameters: Starting parameter values
        parameter_bounds: Optional parameter bounds
        config: Annealing configuration. If None, uses default config.

    Returns:
        Tuple of (best_parameters, best_value, optimization_metadata)
    """
    config = config or AnnealingConfig()
    current_parameters = initial_parameters.copy()
    parameter_bounds = parameter_bounds or {}

    current_value = objective_function(current_parameters)
    best_parameters = current_parameters.copy()
    best_value = current_value

    temperature = config.initial_temperature
    iteration = 0
    acceptance_history = []

    while temperature > config.min_temperature and iteration < config.max_iterations:
        # Generate neighbor solution
        neighbor_parameters = current_parameters.copy()
        for param in neighbor_parameters:
            if param in parameter_bounds:
                min_val, max_val = parameter_bounds[param]
                step_size = (
                    (max_val - min_val)
                    * 0.1
                    * (temperature / config.initial_temperature)
                )
                neighbor_parameters[param] += random.gauss(0, step_size)
                neighbor_parameters[param] = max(
                    min_val, min(max_val, neighbor_parameters[param])
                )

        neighbor_value = objective_function(neighbor_parameters)

        # Accept or reject neighbor
        delta = neighbor_value - current_value
        if delta < 0 or random.random() < math.exp(-delta / temperature):
            current_parameters = neighbor_parameters
            current_value = neighbor_value
            acceptance_history.append(1)

            if current_value < best_value:
                best_parameters = current_parameters.copy()
                best_value = current_value
        else:
            acceptance_history.append(0)

        # Cool down
        temperature *= config.cooling_rate
        iteration += 1

    optimization_metadata = {
        "iterations": iteration,
        "final_temperature": temperature,
        "acceptance_rate": (
            sum(acceptance_history) / len(acceptance_history)
            if acceptance_history
            else 0
        ),
        "converged": temperature <= config.min_temperature,
        "best_value": best_value,
    }

    return best_parameters, best_value, optimization_metadata
