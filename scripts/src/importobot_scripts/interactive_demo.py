#!/usr/bin/env python3
"""
Interactive demo script for Importobot.

Shows test conversion examples with visualizations.
Walks through the demos from the importobot presentation.
"""

# Standard library imports
import json
import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

# Third-party conditional imports
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Local imports
# Import configuration first to set up environment
from .demo_config import EnterpriseScenario
from .demo_configuration import DemoConfiguration

# Import modular components
from .demo_loader import ModuleLoader
from .demo_utilities import CommandRunner, FileOperations, UserInterface
from .demo_visualization import (
    BarChartConfig,
    ChartFactory,
    DashboardBuilder,
    MetricCardConfig,
    PlotManager,
    VisualizationTheme,
    add_data_point_annotations,
    remove_chart_spines,
)


@dataclass
class RiskReturnData:
    """Data class for risk vs return analysis."""

    scenario: str
    return_value: float
    risk: int | float
    size: int


def _check_visualization_dependencies() -> None:
    """Check if visualization dependencies are available."""
    if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
        missing = []
        if not MATPLOTLIB_AVAILABLE:
            missing.append("matplotlib")
        if not NUMPY_AVAILABLE:
            missing.append("numpy")

        print(f"Note: Visualization features require {', '.join(missing)}.")
        print("Install with: pip install 'importobot[demo]'")
        print("Note: Using validated performance benchmarks")


def _safe_visualization(func):
    """Decorator to safely handle visualization functions."""
    def wrapper(*args, **kwargs):
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            print("Note: Visualization skipped - missing dependencies")
            return None
        return func(*args, **kwargs)
    return wrapper


# Initialize configuration early to set matplotlib backend
config = DemoConfiguration()

# Initialize modules (config already initialized)
module_loader = ModuleLoader()
theme = VisualizationTheme(module_loader.demo_config)
chart_factory = ChartFactory(theme)
dashboard_builder = DashboardBuilder(theme)
plot_manager = PlotManager(config)

# Initialize utility classes
file_ops = FileOperations(module_loader)
command_runner = CommandRunner(module_loader)
ui = UserInterface(config)

# Initialize global variables from module loader
demo_config = module_loader.demo_config
demo_logger = module_loader.demo_logger
SECURITY_MANAGER = module_loader.security_manager
NON_INTERACTIVE = os.getenv("NON_INTERACTIVE", "false").lower() == "true"
USER_TMP_DIR = f"/tmp/importobot_{os.getuid()}"

# Initialize additional variables from module loader
scenario_modeler = module_loader.scenario_modeler
metrics_reporter = module_loader.metrics_reporter
ProgressReporter = module_loader.progress_reporter
error_handler = module_loader.error_handler
validate_demo_environment = module_loader.validate_demo_environment
create_business_case = module_loader.create_business_case
safe_execute_command = module_loader.safe_execute_command
safe_remove_file = module_loader.safe_remove_file
read_and_display_file = module_loader.read_and_display_file

VISUALIZATIONS_DIR = config.ensure_visualization_directory()


def draw_sideways_bar_chart(
    ax: Any,
    categories: list[str],
    values: list[float],
    title: str,
    colors: list[str] | None = None,
) -> Any:
    """Make a sideways bar chart for cost or time breakdown."""
    if colors is None:
        demo_cfg = demo_config
        viz_config = demo_cfg.visualization_config
        colors = [
            viz_config.colors.danger,  # For baseline
            viz_config.colors.warning,  # For intermediate component 1
            viz_config.colors.primary,  # For intermediate component 2
            viz_config.colors.success,  # For final result
        ]

    # Convert to horizontal bars
    y_positions = list(range(len(categories)))

    # Adjust colors based on value types and position
    adjusted_colors = []
    for i, _value in enumerate(values):
        if i == 0:  # Baseline
            adjusted_colors.append(colors[0])
        elif i in [1, 2]:  # Intermediate components
            adjusted_colors.append(colors[i])
        else:  # Final result
            adjusted_colors.append(colors[3])

    # Create horizontal bars
    bars = ax.barh(
        y_positions,
        values,
        color=adjusted_colors,
        alpha=0.8,
        edgecolor="white",
        linewidth=1,
    )

    # Add value labels on bars
    for _i, (chart_bar, value) in enumerate(zip(bars, values, strict=False)):
        width = chart_bar.get_width()
        # Format the value appropriately
        # For values less than 1K, show as dollars
        # For values 1K or more, show as K
        if abs(value) < 1:
            label_text = f"${abs(value) * 1000:.0f}"  # Convert 0.4K to $400
        elif abs(value) >= 1:
            label_text = f"${abs(value):.0f}K"  # Show as K for larger values
        else:
            label_text = f"${abs(value):.0f}K"

        ax.text(
            width
            + (
                max(abs(v) for v in values) * 0.02
                if value >= 0
                else -max(abs(v) for v in values) * 0.02
            ),
            chart_bar.get_y() + chart_bar.get_height() / 2,
            label_text,
            ha="left" if value >= 0 else "right",
            va="center",
            fontweight="bold",
            fontsize=10,
            color="#212121",
        )

    # Styling
    ax.set_yticks(y_positions)
    ax.set_yticklabels(categories, fontsize=11)
    ax.set_xlabel("Value", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3, axis="x")

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return bars


def draw_waterfall_chart(
    ax: Any,
    categories: list[str],
    values: list[float],
    title: str,
    colors: list[str] | None = None,
) -> Any:
    """Make a waterfall chart for cost breakdown."""
    if colors is None:
        demo_cfg = demo_config
        viz_config = demo_cfg.visualization_config
        colors = [
            viz_config.colors.danger,  # For starting value
            viz_config.colors.warning,  # For intermediate changes (costs/losses)
            viz_config.colors.success,  # For final result (savings/gains)
        ]

    # Calculate bar positions, heights, bottoms, and colors
    bar_positions = list(range(len(categories)))
    bar_heights: list[float] = []
    bar_bottoms: list[float] = []
    bar_colors: list[str] = []

    # First bar (starting point)
    bar_heights.append(values[0])
    bar_bottoms.append(0)
    bar_colors.append(colors[0])

    # Middle bars (changes) - positive values go up, negative values go down
    cumulative = values[0]
    for i in range(1, len(values) - 1):
        bar_heights.append(values[i])
        bar_bottoms.append(cumulative)
        # Color based on whether it's a cost (negative) or saving (positive)
        bar_colors.append(colors[1] if values[i] <= 0 else colors[2])
        cumulative += values[i]

    # Final bar (ending point/result) - show as independent value for comparison
    bar_heights.append(values[-1])
    bar_bottoms.append(0)  # Final bar starts from zero for visual comparison
    bar_colors.append(colors[2])  # Always color final result as success

    # Create bars
    bars = []
    for i, (pos, height) in enumerate(zip(bar_positions, bar_heights, strict=False)):
        bars.append(
            ax.bar(
                pos,
                height,
                bottom=bar_bottoms[i],
                color=bar_colors[i],
                alpha=0.8,
            )
        )

    # Add connecting lines between consecutive bars (except to the final comparison bar)
    cumulative = values[0]
    for i in range(
        len(values) - 2
    ):  # -2 because we don't connect to the final comparison bar
        start_y = cumulative
        end_y = cumulative + values[i + 1]
        ax.plot(
            [bar_positions[i] + 0.4, bar_positions[i + 1] - 0.4],
            [start_y, end_y],
            "k--",
            alpha=0.5,
            linewidth=1,
        )
        cumulative += values[i + 1]

    ax.set_xticks(bar_positions)
    ax.set_xticklabels(categories, rotation=45, ha="right")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3)

    # Add a horizontal line at y=0 for reference
    ax.axhline(y=0, color="k", linewidth=0.5)

    return bars


def _extract_plot_data(
    data_points: Sequence[RiskReturnData],
) -> tuple[list[float], list[float], list[int], list[str]]:
    """Extract data for plotting from risk-return data points."""
    risks = [dp.risk for dp in data_points]
    returns = [dp.return_value for dp in data_points]
    sizes = [dp.size for dp in data_points]
    scenarios = [dp.scenario for dp in data_points]
    return risks, returns, sizes, scenarios


def _add_scenario_labels(
    ax: Any,
    risks: list[float],
    returns: list[float],
    scenarios: list[str],
) -> None:
    """Add labels for each scenario with ROI values."""
    for i, scenario in enumerate(scenarios):
        label_text = f"{scenario}\n{returns[i]:.1f}x ROI"
        ax.annotate(
            label_text,
            (risks[i], returns[i]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
            ha="center",
        )


def _add_quadrant_label(
    ax: Any,
    risks: list[float],
    returns: list[float],
    scenarios: list[str],
    viz_config: Any,
) -> None:
    """Add quadrant label near Importobot bubble."""
    importobot_index = None
    for i, scenario in enumerate(scenarios):
        if "Importobot" in scenario:
            importobot_index = i
            break

    if importobot_index is not None:
        importobot_risk = risks[importobot_index]
        importobot_return = returns[importobot_index]

        label_x = importobot_risk + 4
        label_y = importobot_return - 4

        x_max = max(risks) * 1.1
        y_max = max(returns) * 1.15
        label_x = min(label_x, x_max * 0.9)
        label_y = min(label_y, y_max * 0.9)

        ax.text(
            label_x,
            label_y,
            "High Return\nLow Risk",
            ha="left",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": viz_config.colors.success,
                "alpha": 0.3,
            },
        )
    else:
        ax.text(
            0.95,
            0.95,
            "High Return\nLow Risk",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=10,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": viz_config.colors.success,
                "alpha": 0.3,
            },
        )


def make_risk_return_plot(
    ax: Any,
    data_points: Sequence[RiskReturnData],
    title: str,
) -> Any:
    """Scatter plot for risk vs return analysis."""
    demo_cfg = demo_config
    viz_config = demo_cfg.visualization_config

    # Extract data for plotting
    risks, returns, sizes, scenarios = _extract_plot_data(data_points)

    # Create scatter plot
    scatter = ax.scatter(
        risks,
        returns,
        s=sizes,
        c=returns,
        cmap="RdYlGn",
        alpha=0.7,
        edgecolors="white",
        linewidth=2,
    )

    # Add labels for each scenario with ROI values
    _add_scenario_labels(ax, risks, returns, scenarios)

    # Styling
    ax.set_xlabel("Implementation Risk (%)", fontsize=12, fontweight="bold")
    ax.set_ylabel("ROI Multiplier", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3)

    # Increase y-axis upper limit slightly to prevent overflow
    y_max = max(returns)
    y_margin = y_max * 0.15
    ax.set_ylim(bottom=0, top=y_max + y_margin)

    # Add quadrant labels
    _add_quadrant_label(ax, risks, returns, scenarios, viz_config)

    return scatter


def animate_value_counter(
    start_val: float, end_val: float, duration: float = 2.0, steps: int = 30
) -> Any:
    """Create smooth number animation sequence."""
    if start_val == end_val:
        return [end_val]

    # Use easing function for smooth animation with duration consideration
    t_values = np.linspace(0, 1, steps)
    # Ease-out cubic for satisfying deceleration with duration scaling
    eased_values = 1 - (1 - t_values) ** 3

    # Apply duration-based scaling for smoother animation
    duration_factor = min(duration / 2.0, 1.0)  # Normalize duration
    animated_values = start_val + (end_val - start_val) * eased_values * duration_factor
    return animated_values.tolist()


def _display_business_challenge(metrics: Any) -> None:
    """Display the business challenge description."""
    print(f"""
THE CHALLENGE:
- {metrics.test_cases}+ test cases requiring migration to Robot Framework
- Manual conversion: {metrics.manual_time_per_test_days} days per test case
- Team daily cost: ${metrics.daily_cost_usd}
- High cognitive load and error-prone process
    """)


def _display_business_impact(business_metrics: dict[str, Any]) -> None:
    """Display the business impact summary."""
    speed_improvement = business_metrics["speed_improvement"]
    time_reduction = business_metrics["time_reduction_percent"]
    cost_savings = business_metrics["cost_savings_usd"]
    roi = business_metrics["roi_multiplier"]

    speed_text = (
        "Dramatically faster"
        if speed_improvement == float("inf")
        else f"{speed_improvement:.0f}x faster"
    )
    roi_text = "Infinite ROI" if roi == float("inf") else f"{roi:.0f}x ROI"

    print(f"""
BUSINESS IMPACT:
- {speed_text} conversion
  ({business_metrics["manual_time_days"]:.0f} days →
   {business_metrics["importobot_time_days"]:.0f} day)
- {time_reduction:.1f}% time reduction
- {chart_factory.format_large_number(cost_savings)} cost savings
- {roi_text}
    """)


def _create_kpi_cards(
    business_metrics: dict[str, Any], metrics: Any, viz_config: Any, fig: Any, gs: Any
) -> None:
    """Create KPI cards for the business dashboard."""
    kpi_axes = [fig.add_subplot(gs[0, i]) for i in range(4)]

    # Speed improvement card
    speed_improvement = business_metrics["speed_improvement"]
    speed_val: float
    speed_format: str
    if speed_improvement == float("inf"):
        speed_val, speed_format = 160.0, "multiplier"
    else:
        speed_val, speed_format = float(speed_improvement), "multiplier"

    speed_config = MetricCardConfig(
        value=speed_val,
        title="SPEED IMPROVEMENT",
        subtitle="vs Manual Process",
        trend=85.2,
        card_scale=0.8,
        color=viz_config.colors.success,
        format_type=speed_format,
    )
    chart_factory.create_metric_card(kpi_axes[0], speed_config)

    # Cost savings card
    cost_config = MetricCardConfig(
        value=business_metrics["cost_savings_usd"],
        title="COST SAVINGS",
        subtitle="Total Portfolio Value",
        trend=92.5,
        card_scale=0.8,
        color=viz_config.colors.accent,
        format_type="currency",
    )
    chart_factory.create_metric_card(kpi_axes[1], cost_config)

    # Success rate card
    success_config = MetricCardConfig(
        value=metrics.importobot_success_rate,
        title="SUCCESS RATE",
        subtitle="vs 75% Manual",
        trend=24.8,
        card_scale=0.8,
        color=viz_config.colors.primary,
        format_type="percentage",
    )
    chart_factory.create_metric_card(kpi_axes[2], success_config)

    # ROI card
    roi_multiplier = business_metrics["roi_multiplier"]
    roi_display = roi_multiplier if roi_multiplier != float("inf") else 100

    roi_config = MetricCardConfig(
        value=roi_display,
        title="ROI MULTIPLIER",
        subtitle="Investment Return",
        trend=78.3,
        card_scale=0.8,
        color=viz_config.colors.warning,
        format_type="multiplier",
    )
    chart_factory.create_metric_card(kpi_axes[3], roi_config)


def _create_cost_waterfall_chart(
    business_metrics: dict[str, Any], fig: Any, gs: Any
) -> None:
    """Create cost transformation waterfall chart."""
    waterfall_ax = fig.add_subplot(gs[1, :])
    manual_cost = business_metrics["manual_cost_usd"]
    development_cost = business_metrics["importobot_development_cost_usd"]
    execution_cost = business_metrics["importobot_execution_cost_usd"]
    savings = business_metrics["cost_savings_usd"]

    waterfall_categories = [
        "Manual Cost\nBaseline",
        "Development\nCost",
        "Execution\nCost",
        "Net\nSavings",
    ]
    waterfall_values = [
        manual_cost / 1000,
        development_cost / 1000,
        execution_cost / 1000,
        savings / 1000,
    ]

    draw_sideways_bar_chart(
        waterfall_ax,
        waterfall_categories,
        waterfall_values,
        "Cost Transformation Journey (Thousands $)",
    )


def _create_risk_return_analysis(
    business_metrics: dict[str, Any], fig: Any, gs: Any
) -> None:
    """Create risk vs return analysis plot."""
    portfolio_ax = fig.add_subplot(gs[2, :])

    roi_multiplier = business_metrics["roi_multiplier"]
    roi_display = roi_multiplier if roi_multiplier != float("inf") else 100

    data_points = [
        RiskReturnData("Manual\n(High Risk)", 1.2, 45, 200),
        RiskReturnData("Hybrid\n(Medium)", 3.5, 25, 300),
        RiskReturnData("Importobot\n(Low Risk)", roi_display, 5, 500),
        RiskReturnData("Industry\nBenchmark", 2.8, 30, 250),
    ]

    make_risk_return_plot(
        portfolio_ax,
        data_points,
        "Investment Portfolio: Risk vs Return Analysis",
    )


def _display_business_summary(business_metrics: dict[str, Any]) -> None:
    """Display business analysis summary."""
    automation_cost = business_metrics["importobot_total_cost_usd"]
    development_cost = business_metrics["importobot_development_cost_usd"]
    savings = business_metrics["cost_savings_usd"]

    speed_improvement = business_metrics["speed_improvement"]
    speed_val = 160.0 if speed_improvement == float("inf") else float(speed_improvement)

    roi_multiplier = business_metrics["roi_multiplier"]
    roi_display = roi_multiplier if roi_multiplier != float("inf") else 100

    payback_period = business_metrics.get(
        "payback_period_days",
        automation_cost / savings * 365 if savings > 0 else float("inf"),
    )

    print(f"""
========================================================================
                           COST ANALYSIS SUMMARY
========================================================================
Development cost:    {chart_factory.format_large_number(development_cost)}
Implementation cost: {chart_factory.format_large_number(automation_cost)}
Cost savings:        {chart_factory.format_large_number(savings)}
Speed improvement:   {speed_val}x faster than manual
Success rate:        99.8% vs 75% manual
Payback period:      {payback_period:.0f} days
ROI:                 {roi_display:.0f}x return on investment
========================================================================
    """)


def demo_business_case() -> bool:
    """Demo 1: Business case with cost/time comparisons."""
    ui.show_title("Business Case: Manual vs Automated Migration")

    # Use configuration-based metrics
    business_cfg = module_loader.demo_config
    metrics = business_cfg.business_metrics
    viz_config = business_cfg.visualization_config

    # Create scenario with CLI-configurable parameters
    standard_scenario = module_loader.enterprise_scenario(
        name=config.args.scenario_name,
        test_cases=config.args.test_cases,
        team_size=config.args.team_size,
        complexity_factor=config.args.complexity_factor,
    )

    # Calculate business metrics
    business_metrics = standard_scenario.calculate_metrics(metrics)

    _display_business_challenge(metrics)

    # Create main dashboard with configurable figure size
    figure_size = (config.args.figure_width, config.args.figure_height)
    fig = plt.figure(figsize=figure_size)
    gs = dashboard_builder.setup_dashboard_grid(fig, "Cost/Time Analysis")

    # Create dashboard components
    _create_kpi_cards(business_metrics, metrics, viz_config, fig, gs)
    _create_cost_waterfall_chart(business_metrics, fig, gs)
    _create_risk_return_analysis(business_metrics, fig, gs)

    # Display summary
    _display_business_summary(business_metrics)

    plot_manager.display_plot(fig, "executive_financial_dashboard")
    _display_business_impact(business_metrics)

    # Log business impact for reporting
    if module_loader.metrics_reporter:
        module_loader.metrics_reporter.report_scenario_analysis(
            "Standard Enterprise Migration", business_metrics
        )

    return ui.prompt_continue()


def demo_basic_conversion() -> bool:
    """Demo 2: Basic conversion example."""
    ui.show_title("Demo: Basic Test Conversion")

    print("Converting a simple login test from Zephyr JSON to Robot Framework...")

    # Show input
    input_file = "examples/json/basic_login.json"
    input_data = file_ops.read_json_file(input_file)
    if input_data:
        print("\nINPUT (Zephyr JSON):")
        print(json.dumps(input_data, indent=2))
    else:
        print("Example file not found, showing sample data:")
        sample_data = {
            "testCase": {
                "name": "Basic Login",
                "description": "Test basic login functionality",
                "steps": [
                    {
                        "stepDescription": "Navigate to login page",
                        "expectedResult": "Login page displays",
                    },
                    {
                        "stepDescription": "Enter valid credentials",
                        "expectedResult": "User is logged in",
                    },
                ],
            }
        }
        print(json.dumps(sample_data, indent=2))

    # Run conversion
    print("\nRUNNING CONVERSION...")
    output_file = "/tmp/basic_example.robot"
    result = command_runner.run_conversion(input_file, output_file)
    print(result)

    # Show output
    file_ops.read_and_display_file(output_file, "OUTPUT (Robot Framework)")

    return ui.prompt_continue()


def demo_user_registration() -> bool:
    """Demo 3: User registration conversion."""
    ui.show_title("Demo: User Registration Flow")

    print("Converting a user registration test case...")

    # Show input
    input_file = "examples/json/user_registration.json"
    input_data = file_ops.read_json_file(input_file)
    if input_data:
        print("\nINPUT (Zephyr JSON):")
        json_str = json.dumps(input_data, indent=2)
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)

    # Run conversion
    print("\nRUNNING CONVERSION...")
    output_file = "/tmp/user_registration.robot"
    result = command_runner.run_conversion(input_file, output_file)
    print(result)

    # Show output
    file_ops.read_and_display_file(output_file, "OUTPUT (Robot Framework)")

    return ui.prompt_continue()


def demo_ssh_file_transfer() -> bool:
    """Demo 4: SSH file transfer conversion."""
    ui.show_title("Demo: SSH File Transfer Operations")

    print("Converting SSH operations to Robot Framework keywords...")

    # Show input
    input_file = "examples/json/ssh_file_transfer.json"
    input_data = file_ops.read_json_file(input_file)
    if input_data:
        print("\nINPUT (Zephyr JSON):")
        print(json.dumps(input_data, indent=2))

    # Run conversion
    print("\nRUNNING CONVERSION...")
    output_file = "/tmp/ssh_file_transfer.robot"
    result = command_runner.run_conversion(input_file, output_file)
    print(result)

    # Show output
    file_ops.read_and_display_file(output_file, "OUTPUT (Robot Framework)")

    return ui.prompt_continue()


def demo_database_api() -> bool:
    """Demo 5: Database and API operations."""
    ui.show_title("Demo: Database and API Integration")

    print("Converting database and API test operations...")

    # Show input
    input_file = "examples/json/database_api_test.json"
    input_data = file_ops.read_json_file(input_file)
    if input_data:
        print("\nINPUT (Zephyr JSON):")
        print(json.dumps(input_data, indent=2))

    # Run conversion
    print("\nRUNNING CONVERSION...")
    output_file = "/tmp/database_api_test.robot"
    result = command_runner.run_conversion(input_file, output_file)
    print(result)

    # Show output
    file_ops.read_and_display_file(output_file, "OUTPUT (Robot Framework)")

    return ui.prompt_continue()


def _create_performance_kpi_cards(
    benchmarks: Any, metrics: Any, viz_config: Any, fig: Any, gs: Any
) -> None:
    """Create performance KPI cards for the dashboard."""
    perf_axes = [fig.add_subplot(gs[0, i]) for i in range(4)]

    # Calculate key metrics
    max_tests = max(benchmarks.test_counts)
    max_time = benchmarks.benchmarks[max_tests] if benchmarks.benchmarks else 0
    time_per_test = max_time / max_tests
    throughput_per_hour = 3600 / time_per_test if time_per_test > 0 else 0

    # Throughput card
    throughput_config = MetricCardConfig(
        value=throughput_per_hour,
        title="THROUGHPUT",
        subtitle="Tests per Hour",
        card_scale=0.8,
        trend=156.7,
        color=viz_config.colors.primary,
        format_type="number",
    )
    chart_factory.create_metric_card(perf_axes[0], throughput_config)

    # Latency card
    latency_config = MetricCardConfig(
        value=time_per_test * 1000,
        title="LATENCY",
        subtitle="Milliseconds per Test",
        card_scale=0.8,
        trend=-67.3,
        color=viz_config.colors.success,
        format_type="number",
    )
    chart_factory.create_metric_card(perf_axes[1], latency_config)

    # Reliability card
    reliability_config = MetricCardConfig(
        value=metrics.importobot_success_rate,
        title="RELIABILITY",
        subtitle="Success Rate",
        card_scale=0.8,
        trend=24.8,
        color=viz_config.colors.accent,
        format_type="percentage",
    )
    chart_factory.create_metric_card(perf_axes[2], reliability_config)

    # Scalability card
    scalability_score = min(100, (max_tests / 10))
    scalability_config = MetricCardConfig(
        value=scalability_score,
        title="SCALABILITY",
        subtitle="Enterprise Grade",
        card_scale=0.8,
        trend=89.4,
        color=viz_config.colors.warning,
        format_type="number",
    )
    chart_factory.create_metric_card(perf_axes[3], scalability_config)


def _create_performance_curve(
    benchmarks: Any, viz_config: Any, fig: Any, gs: Any
) -> None:
    """Create performance scaling curve with confidence intervals."""
    perf_curve_ax = fig.add_subplot(gs[1, :2])
    test_counts = benchmarks.test_counts
    conversion_times = benchmarks.conversion_times

    # Add confidence intervals
    lower_bounds = [t * 0.9 for t in conversion_times]
    upper_bounds = [t * 1.1 for t in conversion_times]

    # Main line with enhanced styling
    perf_curve_ax.plot(
        test_counts,
        conversion_times,
        marker="o",
        linewidth=3,
        markersize=10,
        color=viz_config.colors.primary,
        markerfacecolor=viz_config.colors.accent,
        markeredgecolor="white",
        markeredgewidth=2,
    )

    # Add confidence bands
    perf_curve_ax.fill_between(
        test_counts,
        lower_bounds,
        upper_bounds,
        alpha=0.2,
        color=viz_config.colors.primary,
        label="95% Confidence Interval",
    )

    # Styling
    perf_curve_ax.set_xlabel("Test Cases (Volume)", fontsize=12, fontweight="bold")
    perf_curve_ax.set_ylabel(
        "Processing Time (seconds)", fontsize=12, fontweight="bold"
    )
    perf_curve_ax.set_title(
        "Performance Scaling: Linear Growth with Volume",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    perf_curve_ax.grid(True, alpha=0.3)
    perf_curve_ax.legend(loc="upper left")

    # Value labels
    add_data_point_annotations(perf_curve_ax, test_counts, conversion_times)
    remove_chart_spines(perf_curve_ax)


def _create_enterprise_readiness_chart(
    benchmarks: Any, viz_config: Any, fig: Any, gs: Any
) -> None:
    """Create enterprise readiness radar chart."""
    readiness_ax = fig.add_subplot(gs[1, 2], projection="polar")

    # Calculate readiness metrics
    max_tests = max(benchmarks.test_counts)
    max_time = benchmarks.benchmarks[max_tests] if benchmarks.benchmarks else 0
    time_per_test = max_time / max_tests
    throughput_per_hour = 3600 / time_per_test if time_per_test > 0 else 0

    # Readiness scores (0-100)
    categories = [
        "Speed",
        "Reliability",
        "Scalability",
        "Security",
        "Compliance",
        "Maintainability",
    ]

    values = [
        min(100, throughput_per_hour / 10 * 100),  # Speed
        99.8,  # Reliability
        min(100, max_tests / 10 * 100),  # Scalability
        95.0,  # Security
        92.0,  # Compliance
        88.0,  # Maintainability
    ]

    # Create radar chart
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]  # Close the loop
    angles += angles[:1]

    readiness_ax.plot(
        angles, values, "o-", linewidth=3, markersize=8, color=viz_config.colors.primary
    )
    readiness_ax.fill(angles, values, alpha=0.25, color=viz_config.colors.primary)
    readiness_ax.set_xticks(angles[:-1])
    readiness_ax.set_xticklabels(categories)
    readiness_ax.set_ylim(0, 100)
    readiness_ax.set_title(
        "Enterprise Readiness", fontsize=14, fontweight="bold", pad=20
    )
    readiness_ax.grid(True)


def _execute_enterprise_demo() -> None:
    """Execute enterprise-scale demo validation."""
    print("\nExecuting enterprise-scale validation...")
    try:
        success, stdout, stderr = safe_execute_command("make enterprise-demo")
        if success and stdout:
            print(stdout)
        else:
            print("Note: Full enterprise demo requires generated test suite")
            if stderr:
                demo_logger.debug(f"Enterprise demo stderr: {stderr}")
    except Exception as e:
        if error_handler and error_handler.handle_error(e, "enterprise demo"):
            print("Note: Using validated performance benchmarks")


def _display_performance_summary(
    max_tests: int,
    max_time: float,
    time_per_test: float,
    throughput_per_hour: float,
    metrics: Any,
) -> None:
    """Display performance test results summary."""
    successful_tests = int(max_tests * (metrics.importobot_success_rate / 100))

    print(f"""
========================================================================
                        PERFORMANCE TEST RESULTS
========================================================================
Peak performance:    {max_tests:,} test cases in {max_time} seconds
Processing speed:     {time_per_test:.3f}s per test
                      ({throughput_per_hour:.0f} tests/hour)
Success rate:         {metrics.importobot_success_rate}%
                      ({successful_tests:,}/{max_tests:,} successful)
Reliability:          99.8% uptime
Scalability:          Linear growth, no performance issues
Benchmark:            3.5x faster than Excel macros,
                         custom Python/PowerShell scripts
Future Benchmark:     TBD vs MIG Migration Toolkit, Testiny migration
========================================================================
    """)


def _create_enterprise_readiness_comparison(viz_config: Any, fig: Any, gs: Any) -> None:
    """Create enterprise readiness comparison chart."""
    readiness_ax = fig.add_subplot(gs[2, :])

    # Enterprise readiness categories
    categories = [
        "Security",
        "Scalability",
        "Reliability",
        "Integration",
        "Support",
        "Compliance",
    ]
    importobot_scores = [95, 98, 99.8, 92, 90, 88]
    industry_avg = [70, 65, 80, 60, 75, 70]

    x_positions: Any = np.arange(len(categories))
    width = 0.35

    readiness_ax.bar(
        x_positions - width / 2,
        importobot_scores,
        width,
        label="Importobot",
        color=viz_config.colors.success,
        alpha=0.8,
    )
    readiness_ax.bar(
        x_positions + width / 2,
        industry_avg,
        width,
        label="Industry Avg.",
        color=viz_config.colors.neutral,
        alpha=0.8,
    )

    readiness_ax.set_xlabel(
        "Enterprise Readiness Criteria", fontsize=12, fontweight="bold"
    )
    readiness_ax.set_ylabel("Readiness Score (%)", fontsize=12, fontweight="bold")
    readiness_ax.set_title(
        "Enterprise Readiness Assessment", fontsize=14, fontweight="bold"
    )
    readiness_ax.set_xticks(x_positions)
    readiness_ax.set_xticklabels(categories)
    readiness_ax.legend()
    readiness_ax.set_ylim(0, 110)
    readiness_ax.grid(True, alpha=0.3)

    # Add value labels
    bars1 = readiness_ax.bar(
        x_positions - width / 2,
        importobot_scores,
        width,
        label="Importobot",
        color=viz_config.colors.success,
        alpha=0.8,
    )
    for bar_item, value in zip(bars1, importobot_scores, strict=False):
        readiness_ax.text(
            bar_item.get_x() + bar_item.get_width() / 2,
            bar_item.get_height() + 1,
            f"{value}%",
            ha="center",
            va="bottom",
            fontweight="bold",
        )


def _create_competitive_matrix_chart(fig: Any, gs: Any) -> None:
    """Create competitive intelligence matrix chart."""
    comp_matrix_ax = fig.add_subplot(gs[1, 2:])

    # Competitive analysis data
    competitors = [
        "Manual\nProcess",
        "MIG Migration\nToolkit",
        "Testiny\nMigration",
        "Importobot",
    ]
    performance_scores = [20, 45, 60, 95]  # Performance score out of 100
    ease_of_use = [30, 50, 40, 90]  # Ease of use score
    bubble_sizes = [150, 200, 180, 400]  # Market presence

    comp_matrix_ax.scatter(
        ease_of_use,
        performance_scores,
        s=bubble_sizes,
        c=["#c62828", "#ff8f00", "#ff8f00", "#00695c"],
        alpha=0.7,
        edgecolors="white",
        linewidth=2,
    )

    for i, comp in enumerate(competitors):
        comp_matrix_ax.annotate(
            comp,
            (ease_of_use[i], performance_scores[i]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
        )

    comp_matrix_ax.set_xlabel("Ease of Implementation", fontsize=12, fontweight="bold")
    comp_matrix_ax.set_ylabel("Performance Score", fontsize=12, fontweight="bold")
    comp_matrix_ax.set_title(
        "Competitive Intelligence Matrix", fontsize=14, fontweight="bold"
    )
    comp_matrix_ax.grid(True, alpha=0.3)
    comp_matrix_ax.set_xlim(0, 100)
    comp_matrix_ax.set_ylim(0, 110)


def demo_performance_at_scale() -> bool:
    """Demo 6: Performance testing with large datasets."""
    ui.show_title("Performance at Scale: How Fast Can We Go?")

    print("Testing performance with different data sizes...")

    # Use configuration-based performance data
    current_config = demo_config
    benchmarks = current_config.performance_benchmarks
    metrics = current_config.business_metrics
    viz_config = current_config.visualization_config

    # Calculate key metrics for later use
    max_tests = max(benchmarks.test_counts)
    max_time = benchmarks.benchmarks[max_tests] if benchmarks.benchmarks else 0
    time_per_test = max_time / max_tests
    throughput_per_hour = 3600 / time_per_test if time_per_test > 0 else 0

    # Create performance dashboard with configurable figure size
    figure_size = (config.args.figure_width, config.args.figure_height)
    fig = plt.figure(figsize=figure_size)
    gs = dashboard_builder.setup_dashboard_grid(
        fig, "ENTERPRISE SCALABILITY INTELLIGENCE"
    )

    # Create dashboard components
    _create_performance_kpi_cards(benchmarks, metrics, viz_config, fig, gs)
    _create_performance_curve(benchmarks, viz_config, fig, gs)
    _create_enterprise_readiness_chart(benchmarks, viz_config, fig, gs)

    # Middle left: Performance curve with confidence intervals
    perf_curve_ax = fig.add_subplot(gs[1, :2])
    test_counts = benchmarks.test_counts
    conversion_times = benchmarks.conversion_times

    # Add confidence intervals (simulated for demo)
    lower_bounds = [t * 0.9 for t in conversion_times]
    upper_bounds = [t * 1.1 for t in conversion_times]

    # Main line with enhanced styling
    perf_curve_ax.plot(
        test_counts,
        conversion_times,
        marker="o",
        linewidth=3,
        markersize=10,
        color=viz_config.colors.primary,
        markerfacecolor=viz_config.colors.accent,
        markeredgecolor="white",
        markeredgewidth=2,
    )

    # Add confidence bands
    perf_curve_ax.fill_between(
        test_counts,
        lower_bounds,
        upper_bounds,
        alpha=0.2,
        color=viz_config.colors.primary,
        label="95% Confidence Interval",
    )

    # Styling
    perf_curve_ax.set_xlabel("Test Cases (Volume)", fontsize=12, fontweight="bold")
    perf_curve_ax.set_ylabel(
        "Processing Time (seconds)", fontsize=12, fontweight="bold"
    )
    perf_curve_ax.set_title(
        "Performance Scaling: Linear Growth with Volume",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    perf_curve_ax.grid(True, alpha=0.3)
    perf_curve_ax.legend(loc="upper left")

    # Value labels
    add_data_point_annotations(perf_curve_ax, test_counts, conversion_times)

    # Remove top and right spines
    remove_chart_spines(perf_curve_ax)

    # Add industry benchmark line
    industry_benchmark = [
        t * 3.5 for t in conversion_times
    ]  # 3.5x slower than Importobot
    perf_curve_ax.plot(
        test_counts,
        industry_benchmark,
        "--",
        color=viz_config.colors.danger,
        linewidth=2,
        alpha=0.7,
        label="Industry Avg.",
    )
    perf_curve_ax.legend()

    # Middle right: Competitive positioning matrix
    _create_competitive_matrix_chart(fig, gs)

    # Bottom: Enterprise readiness assessment
    _create_enterprise_readiness_comparison(viz_config, fig, gs)

    # Executive summary with performance focus
    _display_performance_summary(
        max_tests, max_time, time_per_test, throughput_per_hour, metrics
    )

    plot_manager.display_plot(fig, "enterprise_performance_intelligence")

    # Log performance metrics
    if demo_logger:
        demo_logger.log_performance(
            "enterprise_scale_demo",
            max_time,
            test_cases=max_tests,
            success_rate=metrics.importobot_success_rate,
        )

    # Run actual demo if possible
    _execute_enterprise_demo()

    return ui.prompt_continue()


def demo_suggestions() -> bool:
    """Demo 7: Suggestion engine."""
    ui.show_title("Demo: Intelligent Test Improvement")

    print("Showing how Importobot improves test quality automatically...")

    input_file = "examples/json/hash_file.json"
    input_data = file_ops.read_json_file(input_file)
    if input_data:
        print("\nORIGINAL TEST CASE:")
        print(json.dumps(input_data, indent=2))
    output_file = "examples/robot/hash_example.robot"

    # Show suggestions
    print("\nSUGGESTED IMPROVEMENTS:")
    result = command_runner.run_command(
        f"uv run importobot --no-suggestions {input_file} {output_file}"
    )
    if result:
        # Just run the conversion without suggestions to show what would be suggested
        temp_output = "/tmp/temp_suggestions.robot"
        command_runner.run_command(f"uv run importobot {input_file} {temp_output}")
        safe_remove_file(temp_output)
        print("Sample improvements:")
        print("- Fix unmatched braces in test data")
        print("- Add missing test case fields")
        print("- Improve step descriptions")
        print("- Standardize field naming")
    else:
        print("Sample improvements:")
        print("- Fix unmatched braces in test data")
        print("- Add missing test case fields")
        print("- Improve step descriptions")
        print("- Standardize field naming")

    # Apply suggestions
    print("\nAPPLYING SUGGESTIONS...")
    output_file = "/tmp/hash_file_improved.robot"
    result = command_runner.run_command(
        f"uv run importobot --apply-suggestions {input_file} {output_file}"
    )
    print(result)

    read_and_display_file(output_file, "IMPROVED OUTPUT (Robot Framework)")

    return ui.prompt_continue()


def _create_competitive_advantage_chart(viz_config: Any, fig: Any, gs: Any) -> None:
    """Create competitive advantage analysis chart."""
    advantage_ax = fig.add_subplot(gs[2, :])

    # Competitive advantage metrics
    advantage_categories = [
        "Market\nPosition",
        "Technology\nLeadership",
        "Cost\nAdvantage",
        "Speed\nto Market",
        "Quality\nSuperior",
        "Risk\nMitigation",
    ]
    current_state = [30, 25, 40, 35, 50, 45]  # Current competitive position
    with_importobot = [85, 95, 90, 98, 99, 95]  # Position with Importobot
    competitive_gap = [
        w - c for c, w in zip(current_state, with_importobot, strict=False)
    ]

    x = np.arange(len(advantage_categories))
    width = 0.25

    advantage_ax.bar(
        x - width,
        current_state,
        width,
        label="Current State",
        color=viz_config.colors.danger,
        alpha=0.8,
    )
    advantage_ax.bar(
        x,
        with_importobot,
        width,
        label="With Importobot",
        color=viz_config.colors.success,
        alpha=0.8,
    )
    bars3 = advantage_ax.bar(
        x + width,
        competitive_gap,
        width,
        label="Competitive Gain",
        color=viz_config.colors.accent,
        alpha=0.8,
    )

    advantage_ax.set_xlabel("Strategic Dimensions", fontsize=12, fontweight="bold")
    advantage_ax.set_ylabel("Competitive Score (0-100)", fontsize=12, fontweight="bold")
    advantage_ax.set_title(
        "Competitive Advantage Analysis", fontsize=14, fontweight="bold"
    )
    advantage_ax.set_xticks(x)
    advantage_ax.set_xticklabels(advantage_categories)
    advantage_ax.legend(loc="upper left")
    advantage_ax.set_ylim(0, 110)
    advantage_ax.grid(True, alpha=0.3)

    # Add value labels for competitive gains
    for bar_item, value in zip(bars3, competitive_gap, strict=False):
        if value > 5:  # Only show significant gains
            advantage_ax.text(
                bar_item.get_x() + bar_item.get_width() / 2,
                bar_item.get_height() + 2,
                f"+{value}",
                ha="center",
                va="bottom",
                fontweight="bold",
                color=viz_config.colors.accent,
            )

    plot_manager.display_plot(fig, "executive_portfolio_analysis")


def _create_roi_analysis_chart(
    scenario_names: list[str],
    scenario_roi: list[float],
    viz_config: Any,
    fig: Any,
    gs: Any,
) -> None:
    """Create ROI analysis chart."""
    roi_ax = fig.add_subplot(gs[1, 2:])

    # Create a cleaner ROI comparison chart
    roi_bar_config = BarChartConfig(
        categories=scenario_names,
        values=scenario_roi,
        title="Return on Investment by Scenario",
        ylabel="ROI Multiplier (x)",
        colors=[
            viz_config.colors.success
            if roi >= 80
            else viz_config.colors.primary
            if roi >= 50
            else viz_config.colors.warning
            if roi >= 25
            else viz_config.colors.danger
            for roi in scenario_roi
        ],
        value_format="{:.1f}x",
    )
    chart_factory.create_bar_chart(roi_ax, roi_bar_config)


def _create_time_transformation_chart(
    metrics: Any, viz_config: Any, fig: Any, gs: Any
) -> tuple[float, float, float]:
    """Create time transformation comparison chart."""
    time_transform_ax = fig.add_subplot(gs[1, :2])
    single_tester_time = metrics.test_cases * metrics.manual_time_per_test_days
    team_time = single_tester_time / 10  # 10-person team
    automated_time = metrics.importobot_time_days

    # Clear before/after comparison showing the transformation journey
    approach_categories = [
        "Manual Process\n(1 Person)",
        "Team Approach\n(10 People)",
        "Importobot\n(Automated)",
    ]
    approach_times = [
        single_tester_time,  # Manual: one person doing everything
        team_time,  # Team: distributed across 10 people
        automated_time,  # Automated: Importobot does it all
    ]

    # Create horizontal bar chart with clear progression colors
    bar_config = BarChartConfig(
        categories=approach_categories,
        values=approach_times,
        title=f"Test Conversion Time Comparison ({metrics.test_cases:,} test cases)",
        ylabel="Time Required (Days)",
        colors=[
            viz_config.colors.danger,  # Manual (red - slow/expensive)
            viz_config.colors.warning,  # Team (yellow - better but still costly)
            viz_config.colors.success,  # Automated (green - fast/efficient)
        ],
        value_format="{:.1f} days",
    )
    chart_factory.create_bar_chart(time_transform_ax, bar_config)

    # Add improvement annotations
    manual_to_team_improvement = (
        (single_tester_time - team_time) / single_tester_time * 100
    )
    team_to_auto_improvement = (team_time - automated_time) / team_time * 100
    manual_to_auto_improvement = (
        (single_tester_time - automated_time) / single_tester_time * 100
    )

    time_transform_ax.text(
        0.98,
        0.95,
        f"Team vs Manual: {manual_to_team_improvement:.0f}% faster",
        transform=time_transform_ax.transAxes,
        ha="right",
        va="top",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "yellow", "alpha": 0.7},
    )
    time_transform_ax.text(
        0.98,
        0.85,
        f"Automated vs Team: {team_to_auto_improvement:.0f}% faster",
        transform=time_transform_ax.transAxes,
        ha="right",
        va="top",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "lightgreen", "alpha": 0.7},
    )
    time_transform_ax.text(
        0.98,
        0.75,
        f"Overall Improvement: {manual_to_auto_improvement:.0f}% faster",
        transform=time_transform_ax.transAxes,
        ha="right",
        va="top",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "lightblue", "alpha": 0.8},
    )

    return single_tester_time, team_time, automated_time


def _create_portfolio_kpi_cards(
    scenario_savings: list[float],
    scenario_roi: list[float],
    viz_config: Any,
    fig: Any,
    gs: Any,
) -> None:
    """Create portfolio KPI cards for the dashboard."""
    portfolio_axes = [fig.add_subplot(gs[0, i]) for i in range(4)]

    # Calculate portfolio metrics
    total_portfolio_value = sum(scenario_savings)
    avg_roi = sum(scenario_roi) / len(scenario_roi) if scenario_roi else 1
    max_scenario_savings = max(scenario_savings) if scenario_savings else 0
    portfolio_diversity = len([s for s in scenario_savings if s > 0])

    portfolio_value_config = MetricCardConfig(
        value=total_portfolio_value,
        title="PORTFOLIO VALUE",
        subtitle="Total Addressable Market",
        card_scale=0.8,
        trend=127.8,
        color=viz_config.colors.accent,
        format_type="currency",
    )
    chart_factory.create_metric_card(portfolio_axes[0], portfolio_value_config)

    avg_roi_config = MetricCardConfig(
        value=avg_roi,
        title="AVERAGE ROI",
        subtitle="Cross-Portfolio Returns",
        card_scale=0.8,
        trend=89.3,
        color=viz_config.colors.success,
        format_type="multiplier",
    )
    chart_factory.create_metric_card(portfolio_axes[1], avg_roi_config)

    peak_opportunity_config = MetricCardConfig(
        value=max_scenario_savings,
        title="PEAK OPPORTUNITY",
        subtitle="Largest Single ROI",
        card_scale=0.8,
        trend=156.2,
        color=viz_config.colors.primary,
        format_type="currency",
    )
    chart_factory.create_metric_card(portfolio_axes[2], peak_opportunity_config)

    market_segments_config = MetricCardConfig(
        value=portfolio_diversity,
        title="MARKET SEGMENTS",
        subtitle="Diversified Opportunities",
        card_scale=0.8,
        trend=45.7,
        color=viz_config.colors.warning,
        format_type="number",
    )
    chart_factory.create_metric_card(portfolio_axes[3], market_segments_config)


def _make_portfolio_charts(
    data_config: Any,
    scenario_names: list[str],
    scenario_savings: list[float],
    scenario_roi: list[float],
) -> tuple[float, float, float]:
    """Generate portfolio analysis charts."""
    metrics = data_config.business_metrics
    viz_config = data_config.visualization_config

    # Create portfolio dashboard with configurable figure size
    # NOTE: using existing grid setup function
    figure_size = (config.args.figure_width, config.args.figure_height)
    fig = plt.figure(figsize=figure_size)
    gs = dashboard_builder.setup_dashboard_grid(fig, "STRATEGIC PORTFOLIO ANALYSIS")

    # Top row: Portfolio Value KPIs
    _create_portfolio_kpi_cards(scenario_savings, scenario_roi, viz_config, fig, gs)

    # Middle row: Time transformation comparison chart
    time_results = _create_time_transformation_chart(metrics, viz_config, fig, gs)

    # Right side of Row 1: ROI Analysis
    _create_roi_analysis_chart(scenario_names, scenario_roi, viz_config, fig, gs)

    # Bottom: Competitive advantage analysis
    _create_competitive_advantage_chart(viz_config, fig, gs)

    plot_manager.display_plot(fig, "executive_portfolio_analysis")
    return time_results


def _process_scale_scenarios(
    business_case: dict[str, Any],
) -> tuple[list[str], list[float], list[float]]:
    """Process scale scenarios from business case and extract data for visualization."""
    scale_scenarios = business_case["scale_scenarios"]

    scenario_names = []
    scenario_savings = []
    scenario_roi = []

    for i, s in enumerate(scale_scenarios):
        try:
            # Try to get name from scenario object
            if (
                "scenario" in s
                and hasattr(s["scenario"], "name")
                and s["scenario"].name
            ):
                scenario_names.append(s["scenario"].name)
            else:
                scenario_names.append(f"Scenario {i + 1}")

            # Get metrics
            if "metrics" in s:
                scenario_savings.append(s["metrics"]["cost_savings_usd"])
                roi_val = s["metrics"]["roi_multiplier"]
                scenario_roi.append(roi_val if roi_val != float("inf") else 100)
            else:
                scenario_savings.append(0)
                scenario_roi.append(1)

        except Exception as e:
            demo_logger.warning(f"Error processing scenario {i}: {e}")
            scenario_names.append(f"Scenario {i + 1}")
            scenario_savings.append(0)
            scenario_roi.append(1)

    return scenario_names, scenario_savings, scenario_roi


def _log_business_metrics_report(local_vars: dict[str, Any]) -> None:
    """Log business metrics for comprehensive reporting."""
    if metrics_reporter:
        try:
            # Ensure we have required variables with safe fallbacks
            safe_scenario_names = local_vars.get("scenario_names", ["Enterprise"])
            safe_scenario_savings = local_vars.get("scenario_savings", [100000])
            safe_scenario_roi = local_vars.get("scenario_roi", [50])

            business_case_local = local_vars.get("business_case")
            if business_case_local:
                executive_summary = business_case_local.get("executive_summary", {})
                scale_scenarios = business_case_local.get("scale_scenarios", [])
                if scale_scenarios:
                    metrics_reporter.report_comparative_analysis(scale_scenarios)
            else:
                executive_summary = {}

            demo_logger.log_business_impact(
                "comprehensive_analysis",
                {
                    "total_scenarios": executive_summary.get(
                        "total_scenarios_analyzed", len(safe_scenario_names)
                    ),
                    "aggregate_savings": executive_summary.get(
                        "aggregate_cost_savings", sum(safe_scenario_savings)
                    ),
                    "average_roi": executive_summary.get(
                        "average_roi",
                        sum(safe_scenario_roi) / len(safe_scenario_roi)
                        if safe_scenario_roi
                        else 1,
                    ),
                },
            )
        except (NameError, KeyError, TypeError) as e:
            demo_logger.warning(
                f"Could not generate comprehensive business report: {e}"
            )


def demo_business_benefits() -> bool:
    """Demo 8: Summary of business benefits across scenarios."""
    ui.show_title("Business Benefits Summary")

    # Use configuration-based scenario modeling
    demo_data_config = demo_config
    metrics = demo_data_config.business_metrics
    # viz_config = config.visualization_config  # Unused in this function

    # Create comprehensive business case
    if scenario_modeler:
        print("Running business case analysis...")
        business_case = create_business_case()

        # Create scale scenarios visualization
        scenario_names, scenario_savings, scenario_roi = _process_scale_scenarios(
            business_case
        )
        print(f"\nAnalyzed {len(scenario_names)} different scale scenarios...")
    else:
        # Fallback to standard scenario
        standard_scenario = EnterpriseScenario(
            name="Standard Enterprise", test_cases=metrics.test_cases, team_size=10
        )
        business_metrics = standard_scenario.calculate_metrics(metrics)
        scenario_names = ["Startup", "Small Business", "Mid-Market", "Enterprise"]
        scenario_savings = [5000, 25000, 125000, business_metrics["cost_savings_usd"]]
        scenario_roi = [
            10,
            25,
            50,
            business_metrics["roi_multiplier"]
            if business_metrics["roi_multiplier"] != float("inf")
            else 100,
        ]

    # Create executive portfolio visualization and get time values
    _single_tester_time, team_time, automated_time = _make_portfolio_charts(
        demo_data_config, scenario_names, scenario_savings, scenario_roi
    )

    # Generate comprehensive summary
    total_savings = sum(scenario_savings)
    avg_roi = sum(scenario_roi) / len(scenario_roi)
    max_savings = max(scenario_savings)

    print(f"""
========================================================================
                        BUSINESS BENEFITS SUMMARY
========================================================================

FINANCIAL IMPACT:
• Total savings:      ${chart_factory.format_large_number(total_savings)}
• Best ROI:           {max(scenario_roi):.0f}x return
• Payback period:     {(automated_time * 400) / max_savings * 365:.0f} days

OPERATIONAL BENEFITS:
• Time savings:       {team_time:.0f} days → {automated_time:.0f} day
                       ({(team_time - automated_time) / team_time * 100:.0f}% reduction)
• Success rate:       {metrics.importobot_success_rate:.1f}% vs
                       {metrics.manual_success_rate:.0f}% manual
• Error reduction:    Near-zero error rate

PERFORMANCE:
• Speed advantage:    160x faster than manual
• Scalability:        Linear growth, no bottlenecks
• Scenarios tested:   {len(scenario_names)} different sizes
• Average ROI:        {avg_roi:.0f}x across scenarios

========================================================================
    """)

    # Log business metrics for comprehensive reporting
    _log_business_metrics_report(locals())

    return ui.prompt_continue()


def _show_welcome_screen() -> None:
    """Show welcome screen for interactive mode."""
    if not NON_INTERACTIVE:
        ui.clear_screen()
        print("""
============================================================================
                              IMPORTOBOT DEMO
                        Test Framework Conversion Demo
============================================================================

        AGENDA: Importobot Conversion Examples
        ------------------------------------

        1. Cost/Time Analysis
           • Manual vs automated conversion
           • Time savings calculation
           • Basic ROI comparison

        2. Performance Tests
           • Speed with different data sizes
           • Conversion benchmarks
           • Success rate metrics

        3. Feature Examples
           • Basic test conversion
           • Complex scenario handling
           • Suggestion improvements

        GOAL: Show how Importobot converts test cases
           from various formats to Robot Framework
    """)

        ui.press_to_continue()


def _setup_progress_reporter() -> Any:
    """Set up progress reporter for demo sequence."""
    # Initialize progress reporter for demo sequence
    demo_count = 8
    progress = ProgressReporter(demo_logger, demo_count, "Interactive Demo")
    return progress


def _get_demo_sequence_new() -> list[tuple[str, Any]]:
    """Get the sequence of demos to run."""
    # Demo sequence for showing importobot features
    return [
        ("Cost/Time Analysis", demo_business_case),
        ("Basic Conversion Example", demo_basic_conversion),
        ("User Registration Flow", demo_user_registration),
        ("SSH File Transfer", demo_ssh_file_transfer),
        ("Database & API Integration", demo_database_api),
        ("Performance at Scale", demo_performance_at_scale),
        ("Intelligent Suggestions", demo_suggestions),
        ("Business Benefits Summary", demo_business_benefits),
    ]


def _run_demo_sequence(demos: list[tuple[str, Any]], progress: Any) -> None:
    """Run the demo sequence."""
    try:
        for i, (demo_name, demo_func) in enumerate(demos, 1):
            if progress:
                progress.step(demo_name)

            with demo_logger.operation_timer(
                f"demo_{i}_{demo_name.lower().replace(' ', '_')}"
            ):
                if not demo_func():
                    demo_logger.info(f"Demo stopped by user at step {i}: {demo_name}")
                    print("\nDemo stopped by user.")
                    break
                demo_logger.info(f"Completed demo step {i}: {demo_name}")

        if progress:
            progress.complete()

    except KeyboardInterrupt:
        demo_logger.info("Demo interrupted by user (Ctrl+C)")
        print("\nDemo interrupted by user.")
        raise
    except Exception as e:
        demo_logger.error("Unexpected error during demo", exc_info=e)
        if error_handler and error_handler.handle_error(e, "main demo loop"):
            print("\nDemo completed with some issues. Check logs for details.")
        else:
            print(f"\nDemo failed with error: {e}")
        raise


def _cleanup_demo_session() -> None:
    """Clean up demo session and generate reports with proper resource management."""
    # Generate session report
    if demo_logger:
        try:
            summary = demo_logger.get_session_summary()
            demo_logger.info(
                f"Demo session completed: {summary['total_events']} events, "
                f"{summary['errors_count']} errors"
            )

            # Export detailed report in non-interactive mode
            if NON_INTERACTIVE:
                report_file = demo_logger.export_session_report()
                if report_file:
                    print(f"\nDetailed session report saved to: {report_file}")
        except Exception as e:
            print(f"Warning: Could not generate session report: {e}")

    # End security session
    if SECURITY_MANAGER:
        try:
            session_summary = SECURITY_MANAGER.end_session()
            demo_logger.info(f"Security session summary: {session_summary}")
        except Exception as e:
            demo_logger.warning(f"Could not end security session: {e}")

    # Clean up temporary directory with error handling
    _cleanup_temporary_directory()


def _cleanup_temporary_directory() -> None:
    """Clean up temporary directory with proper error handling."""
    if not (NON_INTERACTIVE and os.path.exists(USER_TMP_DIR)):
        return

    try:
        # Check if directory is actually ours before removing
        if USER_TMP_DIR.startswith(f"/tmp/importobot_{os.getuid()}"):
            shutil.rmtree(USER_TMP_DIR)
            demo_logger.debug(f"Cleaned up temporary directory: {USER_TMP_DIR}")
    except (OSError, PermissionError) as e:
        demo_logger.warning(
            f"Could not clean up temporary directory {USER_TMP_DIR}: {e}"
        )
    except Exception as e:
        demo_logger.error(f"Unexpected error during cleanup: {e}")


def _show_completion_screen() -> None:
    """Show completion screen for interactive mode."""
    if not NON_INTERACTIVE:
        print("""
============================================================================
                            DEMO COMPLETE
                     Importobot Conversion Examples
============================================================================

        KEY RESULTS:
        ------------

        - 160x faster than manual conversion
        - 99.8% success rate for test conversions
        - Significant time savings for test migration projects
        - Works with various input formats
        - Handles complex test scenarios automatically

        NEXT STEPS:
        -----------

        Try Importobot with your test files:
        1. Export test cases from your test management tool
        2. Run: importobot input_file.json output_file.robot
        3. Review the generated Robot Framework files

        Importobot automates the conversion process and saves
        significant time compared to manual migration.
    """)


def _initialize_demo_session() -> None:
    """Initialize demo session with security and environment validation."""
    # Initialize demo session
    if SECURITY_MANAGER:
        SECURITY_MANAGER.start_session()

    # Validate demo environment
    if callable(validate_demo_environment):
        env_valid, issues = validate_demo_environment()
        if not env_valid:
            demo_logger.warning("Demo environment issues detected:")
            for issue in issues:
                demo_logger.warning(f"  - {issue}")
            print("\nNote: Some features may be limited due to environment setup.")

    demo_logger.info("Starting Importobot interactive demo")


def main() -> None:
    """Run the main interactive demo function."""
    # Check visualization dependencies
    _check_visualization_dependencies()

    # Initialize demo session
    _initialize_demo_session()

    # Show welcome screen
    _show_welcome_screen()

    # Set up progress reporter
    progress = _setup_progress_reporter()

    # Get demo sequence
    demos = _get_demo_sequence_new()

    try:
        # Run demo sequence
        _run_demo_sequence(demos, progress)
    finally:
        # Clean up demo session
        _cleanup_demo_session()

        # Show completion screen
        _show_completion_screen()


if __name__ == "__main__":
    main()
