"""
Configuration management for Importobot interactive demo.

This module provides centralized configuration for business metrics,
performance benchmarks, and demo scenarios.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BusinessMetrics:
    """Business metrics for ROI calculations."""

    test_cases: int = 800
    manual_time_per_test_days: float = 2.0
    daily_cost_usd: int = 400
    team_size_options: list[int] | None = None
    importobot_time_days: float = 21.0  # 20 work days + 1 execution day
    importobot_development_cost_usd: int = 8000  # 20 work days * $400/day
    manual_success_rate: float = 75.0
    importobot_success_rate: float = 99.8

    def __post_init__(self) -> None:
        """Initialize default values after dataclass initialization."""
        if self.team_size_options is None:
            self.team_size_options = [1, 10]


@dataclass
class PerformanceBenchmarks:
    """Performance benchmarks for scalability demonstration."""

    # Test count -> conversion time mapping
    benchmarks: dict[int, float] | None = None

    def __post_init__(self) -> None:
        """Initialize default benchmarks after dataclass initialization."""
        if self.benchmarks is None:
            self.benchmarks = {
                10: 0.5,
                50: 2.5,
                100: 5.0,
                200: 10.0,
                500: 25.0,
                800: 47.3,
                1000: 60.0,
            }

    @property
    def test_counts(self) -> list[int]:
        """Get sorted list of test counts."""
        if self.benchmarks is None:
            return []
        return sorted(self.benchmarks.keys())

    @property
    def conversion_times(self) -> list[float]:
        """Get conversion times in order of test counts."""
        if self.benchmarks is None:
            return []
        return [self.benchmarks[count] for count in self.test_counts]


@dataclass
class EnterpriseScenario:
    """Enterprise scenario for modeling different business cases."""

    name: str
    test_cases: int
    team_size: int
    urgency_multiplier: float = 1.0  # For rush projects
    complexity_factor: float = 1.0  # For complex test cases

    def calculate_metrics(self, base_metrics: BusinessMetrics) -> dict[str, float]:
        """Calculate business metrics for this scenario."""
        # Manual approach calculations
        manual_time_single = (
            self.test_cases
            * base_metrics.manual_time_per_test_days
            * self.complexity_factor
        )
        manual_time_team = manual_time_single / self.team_size
        manual_cost = manual_time_team * base_metrics.daily_cost_usd * self.team_size

        # Importobot approach calculations
        importobot_time = base_metrics.importobot_time_days * self.complexity_factor
        # Execution cost is only for the 1-day runtime, not the 20 development days
        importobot_execution_cost = (
            1.0 * base_metrics.daily_cost_usd * self.complexity_factor
        )
        importobot_total_cost_usd = (
            importobot_execution_cost + base_metrics.importobot_development_cost_usd
        )

        # Business impact calculations
        time_savings = manual_time_team - importobot_time
        cost_savings = manual_cost - importobot_total_cost_usd
        time_reduction_percent = (time_savings / manual_time_team) * 100
        roi = (
            cost_savings / importobot_total_cost_usd
            if importobot_total_cost_usd > 0
            else float("inf")
        )

        return {
            "manual_time_days": manual_time_team,
            "importobot_time_days": importobot_time,
            "manual_cost_usd": manual_cost,
            "importobot_cost_usd": importobot_execution_cost,
            "importobot_total_cost_usd": importobot_total_cost_usd,
            "importobot_development_cost_usd": (
                base_metrics.importobot_development_cost_usd
            ),
            "importobot_execution_cost_usd": importobot_execution_cost,
            "time_savings_days": time_savings,
            "cost_savings_usd": cost_savings,
            "time_reduction_percent": time_reduction_percent,
            "roi_multiplier": roi,
            "speed_improvement": (
                manual_time_team / importobot_time
                if importobot_time > 0
                else float("inf")
            ),
        }


@dataclass
class ColorPalette:
    """Color configuration for charts."""

    primary: str = "#27ae60"
    secondary: str = "#8e44ad"
    accent: str = "#3498db"
    success: str = "#27ae60"
    danger: str = "#e74c3c"
    warning: str = "#f39c12"
    neutral: str = "#95a5a6"
    background: str = "#f0f0f0"


@dataclass
class FigureSizes:
    """Figure size configurations."""

    single: tuple[int, int] = (12, 8)
    double: tuple[int, int] = (15, 6)
    quad: tuple[int, int] = (15, 12)


@dataclass
class FontSettings:
    """Font size configurations."""

    title_size: int = 14
    subtitle_size: int = 12
    body_size: int = 12
    caption_size: int = 10


@dataclass
class VisualizationConfig:
    """Configuration for chart appearance and behavior."""

    colors: ColorPalette
    figure_sizes: FigureSizes
    fonts: FontSettings
    chart_style: str = "seaborn-v0_8"

    def __post_init__(self) -> None:
        """Initialize default values after dataclass initialization."""
        if not hasattr(self, "colors") or self.colors is None:
            self.colors = ColorPalette()
        if not hasattr(self, "figure_sizes") or self.figure_sizes is None:
            self.figure_sizes = FigureSizes()
        if not hasattr(self, "fonts") or self.fonts is None:
            self.fonts = FontSettings()


class DemoConfig:
    """Main configuration class for the interactive demo."""

    def __init__(self, config_file: str | None = None):
        """Initialize configuration, optionally from a file."""
        self.business_metrics = BusinessMetrics()
        self.performance_benchmarks = PerformanceBenchmarks()
        self.visualization_config = VisualizationConfig(
            colors=ColorPalette(), figure_sizes=FigureSizes(), fonts=FontSettings()
        )
        self.enterprise_scenarios = self._create_default_scenarios()

        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)

    def _create_default_scenarios(self) -> list[EnterpriseScenario]:
        """Create default enterprise scenarios."""
        return [
            EnterpriseScenario(
                name="Small Team",
                test_cases=100,
                team_size=2,
                complexity_factor=0.8,  # Simpler tests
            ),
            EnterpriseScenario(
                name="Medium Enterprise",
                test_cases=500,
                team_size=5,
                complexity_factor=1.0,  # Standard complexity
            ),
            EnterpriseScenario(
                name="Large Enterprise",
                test_cases=2000,
                team_size=15,
                complexity_factor=1.2,  # More complex integration tests
            ),
            EnterpriseScenario(
                name="Rush Project",
                test_cases=800,
                team_size=10,
                urgency_multiplier=2.0,  # Tight deadline increases pressure
                complexity_factor=1.1,
            ),
        ]

    def load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_file, encoding="utf-8") as f:
                config_data = json.load(f)

            # Update business metrics if provided
            if "business_metrics" in config_data:
                metrics_data = config_data["business_metrics"]
                for key, value in metrics_data.items():
                    if hasattr(self.business_metrics, key):
                        setattr(self.business_metrics, key, value)

            # Update performance benchmarks if provided
            if "performance_benchmarks" in config_data:
                bench_data = config_data["performance_benchmarks"]
                if "benchmarks" in bench_data:
                    # Convert string keys to integers
                    benchmarks = {
                        int(k): v for k, v in bench_data["benchmarks"].items()
                    }
                    self.performance_benchmarks.benchmarks = benchmarks

            print(f"Configuration loaded from {config_file}")

        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config from {config_file}: {e}")
            print("Using default configuration.")

    def save_to_file(self, config_file: str) -> None:
        """Save current configuration to JSON file."""
        config_data = {
            "business_metrics": {
                "test_cases": self.business_metrics.test_cases,
                "manual_time_per_test_days": (
                    self.business_metrics.manual_time_per_test_days
                ),
                "daily_cost_usd": self.business_metrics.daily_cost_usd,
                "team_size_options": self.business_metrics.team_size_options,
                "importobot_time_days": self.business_metrics.importobot_time_days,
                "manual_success_rate": self.business_metrics.manual_success_rate,
                "importobot_success_rate": (
                    self.business_metrics.importobot_success_rate
                ),
            },
            "performance_benchmarks": {
                "benchmarks": self.performance_benchmarks.benchmarks
            },
        }

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            print(f"Configuration saved to {config_file}")
        except OSError as e:
            print(f"Error saving configuration to {config_file}: {e}")

    def _validate_business_metrics(self, errors: list[str]) -> None:
        """Validate business metrics configuration."""
        bm = self.business_metrics
        if bm.test_cases <= 0:
            errors.append("test_cases must be positive")
        if bm.manual_time_per_test_days <= 0:
            errors.append("manual_time_per_test_days must be positive")
        if bm.daily_cost_usd <= 0:
            errors.append("daily_cost_usd must be positive")
        if bm.importobot_time_days <= 0:
            errors.append("importobot_time_days must be positive")
        if not 0 <= bm.manual_success_rate <= 100:
            errors.append("manual_success_rate must be between 0 and 100")
        if not 0 <= bm.importobot_success_rate <= 100:
            errors.append("importobot_success_rate must be between 0 and 100")

    def _validate_performance_benchmarks(self, errors: list[str]) -> None:
        """Validate performance benchmarks configuration."""
        pb = self.performance_benchmarks
        if not pb.benchmarks:
            errors.append("performance benchmarks cannot be empty")
        else:
            for test_count, time in pb.benchmarks.items():
                if test_count <= 0:
                    errors.append(f"test count {test_count} must be positive")
                if time <= 0:
                    errors.append(f"conversion time {time} must be positive")

    def _validate_enterprise_scenarios(self, errors: list[str]) -> None:
        """Validate enterprise scenarios configuration."""
        for scenario in self.enterprise_scenarios:
            if scenario.test_cases <= 0:
                errors.append(
                    f"Scenario '{scenario.name}': test_cases must be positive"
                )
            if scenario.team_size <= 0:
                errors.append(f"Scenario '{scenario.name}': team_size must be positive")

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration for reasonableness."""
        errors: list[str] = []

        # Validate different configuration sections
        self._validate_business_metrics(errors)
        self._validate_performance_benchmarks(errors)
        self._validate_enterprise_scenarios(errors)

        return len(errors) == 0, errors

    def get_scenario_by_name(self, name: str) -> EnterpriseScenario | None:
        """Get enterprise scenario by name."""
        for scenario in self.enterprise_scenarios:
            if scenario.name.lower() == name.lower():
                return scenario
        return None


# Create default configuration instance
DEFAULT_CONFIG = DemoConfig()
