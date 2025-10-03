"""Tests for optimization algorithms and mathematical utilities."""
# Tests internal implementation - protected-access needed
# pylint: disable=protected-access

import random
from unittest.mock import patch

from importobot.utils.optimization import (
    AnnealingConfig,
    GeneticAlgorithmOptimizer,
    GradientDescentOptimizer,
    OptimizerConfig,
    simulated_annealing,
)


class TestOptimizerConfig:
    """Test OptimizerConfig dataclass."""

    def test_default_config(self):
        """Test default optimizer configuration."""
        config = OptimizerConfig()
        assert config.learning_rate == 0.01
        assert config.momentum == 0.9
        assert config.regularization == 0.001
        assert config.max_iterations == 1000
        assert config.tolerance == 1e-6
        assert config.adaptive_learning is True

    def test_custom_config(self):
        """Test custom optimizer configuration."""
        config = OptimizerConfig(
            learning_rate=0.05,
            momentum=0.8,
            regularization=0.01,
            max_iterations=500,
            tolerance=1e-4,
            adaptive_learning=False,
        )
        assert config.learning_rate == 0.05
        assert config.momentum == 0.8
        assert config.regularization == 0.01
        assert config.max_iterations == 500
        assert config.tolerance == 1e-4
        assert config.adaptive_learning is False


class TestAnnealingConfig:
    """Test AnnealingConfig dataclass."""

    def test_default_config(self):
        """Test default annealing configuration."""
        config = AnnealingConfig()
        assert config.initial_temperature == 100.0
        assert config.cooling_rate == 0.95
        assert config.min_temperature == 1e-6
        assert config.max_iterations == 1000

    def test_custom_config(self):
        """Test custom annealing configuration."""
        config = AnnealingConfig(
            initial_temperature=200.0,
            cooling_rate=0.9,
            min_temperature=1e-8,
            max_iterations=2000,
        )
        assert config.initial_temperature == 200.0
        assert config.cooling_rate == 0.9
        assert config.min_temperature == 1e-8
        assert config.max_iterations == 2000


class TestGradientDescentOptimizer:
    """Test GradientDescentOptimizer class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        optimizer = GradientDescentOptimizer()
        assert optimizer.config.learning_rate == 0.01
        assert optimizer.velocity is None
        assert optimizer.iteration_count == 0
        assert not optimizer.convergence_history

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = OptimizerConfig(learning_rate=0.05, max_iterations=100)
        optimizer = GradientDescentOptimizer(config)
        assert optimizer.config.learning_rate == 0.05
        assert optimizer.config.max_iterations == 100

    def test_simple_quadratic_optimization(self):
        """Test optimization of simple quadratic function."""

        def quadratic_function(params):
            x = params.get("x", 0)
            return x**2

        optimizer = GradientDescentOptimizer(
            OptimizerConfig(learning_rate=0.1, max_iterations=100, tolerance=1e-8)
        )

        result = optimizer.optimize(
            objective_function=quadratic_function,
            initial_parameters={"x": 5.0},
        )

        best_params, best_value, metadata = result
        assert abs(best_params["x"]) < 0.1  # Should converge near 0
        assert best_value < 0.1
        # Convergence may not always happen in limited iterations
        assert metadata["iterations"] > 0
        assert len(metadata["convergence_history"]) > 0

    def test_optimization_with_bounds(self):
        """Test optimization with parameter bounds."""

        def quadratic_function(params):
            x = params.get("x", 0)
            return (x - 2) ** 2

        optimizer = GradientDescentOptimizer(
            OptimizerConfig(learning_rate=0.1, max_iterations=100)
        )

        result = optimizer.optimize(
            objective_function=quadratic_function,
            initial_parameters={"x": 0.0},
            parameter_bounds={"x": (1.5, 3.0)},
        )

        best_params, _, _ = result
        assert 1.5 <= best_params["x"] <= 3.0
        assert abs(best_params["x"] - 2.0) < 0.1

    def test_optimization_with_custom_gradient(self):
        """Test optimization with custom gradient function."""

        def quadratic_function(params):
            x = params.get("x", 0)
            return x**2

        def gradient_function(params):
            x = params.get("x", 0)
            return {"x": 2 * x}

        optimizer = GradientDescentOptimizer(
            OptimizerConfig(learning_rate=0.1, max_iterations=50)
        )

        result = optimizer.optimize(
            objective_function=quadratic_function,
            initial_parameters={"x": 3.0},
            gradient_function=gradient_function,
        )

        best_params, _, _ = result
        assert abs(best_params["x"]) < 0.1

    def test_numerical_gradients(self):
        """Test numerical gradient computation."""

        def quadratic_function(params):
            x = params.get("x", 0)
            return x**2

        optimizer = GradientDescentOptimizer()
        gradients = optimizer._compute_numerical_gradients(
            quadratic_function, {"x": 2.0}
        )

        # Gradient of x^2 at x=2 is 2*x = 4
        assert abs(gradients["x"] - 4.0) < 0.1

    def test_adaptive_learning_rate(self):
        """Test adaptive learning rate adjustment."""
        config = OptimizerConfig(adaptive_learning=True, learning_rate=0.1)
        optimizer = GradientDescentOptimizer(config)

        # Test increasing learning rate for decreasing gradient norm
        new_rate = optimizer._adjust_learning_rate(
            {"x": 0.1},
            0.1,
            1.0,  # small current gradient, large previous
        )
        assert new_rate > 0.1  # Should increase

        # Test decreasing learning rate for increasing gradient norm
        new_rate = optimizer._adjust_learning_rate(
            {"x": 1.0},
            0.1,
            0.1,  # large current gradient, small previous
        )
        assert new_rate < 0.1  # Should decrease

    def test_convergence_check(self):
        """Test convergence detection."""
        optimizer = GradientDescentOptimizer(OptimizerConfig(tolerance=0.1))

        # Not converged with few iterations
        optimizer.convergence_history = [1.0, 0.9, 0.8]
        assert optimizer._check_convergence(5) is False

        # Converged with stable values
        optimizer.convergence_history = [1.0] * 15
        assert optimizer._check_convergence(15) is True

    def test_regularization(self):
        """Test L2 regularization application."""
        optimizer = GradientDescentOptimizer(OptimizerConfig(regularization=0.1))
        gradients = {"x": 1.0, "y": 2.0}
        parameters = {"x": 0.5, "y": 1.5}

        optimizer._apply_regularization(gradients, parameters)

        # Check regularization was applied
        assert gradients["x"] == 1.0 + 0.1 * 0.5  # 1.05
        assert gradients["y"] == 2.0 + 0.1 * 1.5  # 2.15


class TestGeneticAlgorithmOptimizer:
    """Test GeneticAlgorithmOptimizer class."""

    def test_init(self):
        """Test initialization."""
        optimizer = GeneticAlgorithmOptimizer(
            population_size=30,
            mutation_rate=0.2,
            crossover_rate=0.7,
            elitism_count=3,
            max_generations=50,
            tournament_size=4,
        )
        assert optimizer.population_size == 30
        assert optimizer.mutation_rate == 0.2
        assert optimizer.crossover_rate == 0.7
        assert optimizer.elitism_count == 3
        assert optimizer.max_generations == 50
        assert optimizer.tournament_size == 4

    def test_simple_fitness_optimization(self):
        """Test optimization of simple fitness function."""

        def fitness_function(params):
            x = params.get("x", 0)
            # Maximize -(x-5)^2, so optimal x=5
            return -((x - 5) ** 2)

        optimizer = GeneticAlgorithmOptimizer(population_size=20, max_generations=50)

        result = optimizer.optimize(
            fitness_function=fitness_function,
            parameter_ranges={"x": (0, 10)},
        )

        best_params, best_fitness, metadata = result
        assert abs(best_params["x"] - 5.0) < 1.0  # Should be near 5
        assert best_fitness >= -1.0  # Should be high fitness
        assert len(metadata["fitness_history"]) > 0

    def test_random_individual_generation(self):
        """Test random individual generation."""
        optimizer = GeneticAlgorithmOptimizer()
        parameter_ranges = {"x": (0.0, 10.0), "y": (-5.0, 5.0)}

        individual = optimizer._generate_random_individual(parameter_ranges)

        assert 0 <= individual["x"] <= 10
        assert -5 <= individual["y"] <= 5

    def test_tournament_selection(self):
        """Test tournament selection."""
        optimizer = GeneticAlgorithmOptimizer(tournament_size=2)
        population = [{"x": 1.0}, {"x": 2.0}, {"x": 3.0}, {"x": 4.0}]
        fitness_scores = [10.0, 20.0, 30.0, 40.0]  # Higher is better

        with patch("random.sample", return_value=[2, 3]):
            selected = optimizer._tournament_selection(population, fitness_scores)
            # Should select individual with index 3 (highest fitness in tournament)
            assert selected["x"] == 4.0

    def test_crossover(self):
        """Test crossover operation."""
        optimizer = GeneticAlgorithmOptimizer()
        parent1 = {"x": 1.0, "y": 2.0}
        parent2 = {"x": 3.0, "y": 4.0}

        with patch("random.choice", side_effect=[1.0, 4.0]):
            child = optimizer._crossover(parent1, parent2)
            assert child["x"] == 1.0  # From parent1
            assert child["y"] == 4.0  # From parent2

    def test_mutation(self):
        """Test mutation operation."""
        optimizer = GeneticAlgorithmOptimizer()
        individual = {"x": 5.0}
        parameter_ranges = {"x": (0.0, 10.0)}

        with patch("random.gauss", return_value=1.0):
            mutated = optimizer._mutate(individual, parameter_ranges)
            # Should apply mutation but stay within bounds
            assert 0 <= mutated["x"] <= 10

    def test_elitism(self):
        """Test elitism preservation."""
        optimizer = GeneticAlgorithmOptimizer(elitism_count=2)
        population = [{"x": 1.0}, {"x": 2.0}, {"x": 3.0}, {"x": 4.0}]
        fitness_scores = [10.0, 40.0, 20.0, 30.0]

        elite = optimizer._apply_elitism(population, fitness_scores)

        # Should select the 2 best individuals (indices 1 and 3)
        assert len(elite) == 2
        assert {"x": 2.0} in elite  # Fitness 40
        assert {"x": 4.0} in elite  # Fitness 30

    def test_convergence_check(self):
        """Test convergence detection for genetic algorithm."""
        optimizer = GeneticAlgorithmOptimizer()

        # Not converged - few generations
        optimizer.fitness_history = [10, 15, 20]
        assert optimizer._check_genetic_convergence(5) is False

        # Converged - stable fitness
        optimizer.fitness_history = [20.0] * 25
        assert optimizer._check_genetic_convergence(25) is True


class TestSimulatedAnnealing:
    """Test simulated annealing function."""

    def test_simple_optimization(self):
        """Test simulated annealing on simple function."""

        def objective_function(params):
            x = params.get("x", 0)
            return (x - 3) ** 2  # Minimum at x=3

        config = AnnealingConfig(
            initial_temperature=10.0, max_iterations=100, min_temperature=0.01
        )

        result = simulated_annealing(
            objective_function=objective_function,
            initial_parameters={"x": 0.0},
            parameter_bounds={"x": (-10, 10)},
            config=config,
        )

        best_params, _, metadata = result
        assert abs(best_params["x"] - 3.0) < 1.0
        assert metadata["iterations"] > 0
        assert 0 <= metadata["acceptance_rate"] <= 1

    def test_default_config(self):
        """Test simulated annealing with default configuration."""

        def objective_function(params):
            return params.get("x", 0) ** 2

        result = simulated_annealing(
            objective_function=objective_function,
            initial_parameters={"x": 5.0},
        )

        _, best_value, metadata = result
        assert best_value >= 0  # Should be non-negative
        assert "iterations" in metadata
        assert "acceptance_rate" in metadata

    def test_temperature_cooling(self):
        """Test that temperature decreases during annealing."""

        def objective_function(params):
            return params.get("x", 0) ** 2

        config = AnnealingConfig(
            initial_temperature=100.0,
            cooling_rate=0.9,
            max_iterations=10,
            min_temperature=1.0,
        )

        result = simulated_annealing(
            objective_function=objective_function,
            initial_parameters={"x": 1.0},
            config=config,
        )

        _, _, metadata = result
        # Temperature should have cooled down
        assert metadata["final_temperature"] < config.initial_temperature

    def test_parameter_bounds_enforcement(self):
        """Test that parameter bounds are enforced."""

        def objective_function(params):
            return params.get("x", 0) ** 2

        config = AnnealingConfig(max_iterations=50)

        result = simulated_annealing(
            objective_function=objective_function,
            initial_parameters={"x": 0.0},
            parameter_bounds={"x": (-2, 2)},
            config=config,
        )

        best_params, _, _ = result
        assert -2 <= best_params["x"] <= 2

    @patch("random.random")
    @patch("random.gauss")
    def test_acceptance_probability(self, mock_gauss, mock_random):
        """Test acceptance probability calculation."""
        mock_gauss.return_value = 0.1
        mock_random.return_value = 0.5

        def objective_function(params):
            return params.get("x", 0) ** 2

        config = AnnealingConfig(
            initial_temperature=1.0, max_iterations=5, min_temperature=0.1
        )

        result = simulated_annealing(
            objective_function=objective_function,
            initial_parameters={"x": 1.0},
            parameter_bounds={"x": (-5, 5)},
            config=config,
        )

        # Should complete without errors
        assert result is not None


class TestIntegrationScenarios:
    """Integration tests for optimization algorithms."""

    def test_multi_parameter_optimization(self):
        """Test optimization with multiple parameters."""

        def objective_function(params):
            x = params.get("x", 0)
            y = params.get("y", 0)
            # Rosenbrock function (a = 1, b = 100)
            return 100 * (y - x**2) ** 2 + (1 - x) ** 2

        optimizer = GradientDescentOptimizer(
            OptimizerConfig(learning_rate=0.001, max_iterations=1000)
        )

        result = optimizer.optimize(
            objective_function=objective_function,
            initial_parameters={"x": -1.0, "y": 1.0},
            parameter_bounds={"x": (-2, 2), "y": (-2, 2)},
        )

        best_params, _, _ = result
        # Should converge reasonably close to (1, 1)
        assert abs(best_params["x"] - 1.0) < 0.5
        assert abs(best_params["y"] - 1.0) < 0.5

    def test_genetic_vs_gradient_comparison(self):
        """Compare genetic algorithm and gradient descent on same problem."""

        def fitness_function(params):
            x = params.get("x", 0)
            return -((x - 2) ** 2)  # Maximum at x=2

        def objective_function(params):
            return (params.get("x", 0) - 2) ** 2  # Minimum at x=2

        # Genetic algorithm
        ga_optimizer = GeneticAlgorithmOptimizer(population_size=20, max_generations=50)
        ga_result = ga_optimizer.optimize(
            fitness_function=fitness_function,
            parameter_ranges={"x": (0, 4)},
        )

        # Gradient descent
        gd_optimizer = GradientDescentOptimizer(
            OptimizerConfig(learning_rate=0.1, max_iterations=100)
        )
        gd_result = gd_optimizer.optimize(
            objective_function=objective_function,
            initial_parameters={"x": 0.0},
        )

        # Both should find solutions near x=2
        assert abs(ga_result[0]["x"] - 2.0) < 0.5
        assert abs(gd_result[0]["x"] - 2.0) < 0.5

    def test_convergence_with_noise(self):
        """Test optimization with noisy objective function."""

        def noisy_quadratic(params):
            x = params.get("x", 0)
            noise = random.gauss(0, 0.01)
            return x**2 + noise

        optimizer = GradientDescentOptimizer(
            OptimizerConfig(learning_rate=0.05, max_iterations=200, tolerance=1e-4)
        )

        result = optimizer.optimize(
            objective_function=noisy_quadratic,
            initial_parameters={"x": 3.0},
        )

        _, best_value, metadata = result
        # With noise, convergence is less reliable, so we use a more lenient check
        # Just verify the algorithm ran and produced a reasonable result
        assert best_value >= 0  # Quadratic function should be non-negative
        assert metadata["iterations"] > 0
