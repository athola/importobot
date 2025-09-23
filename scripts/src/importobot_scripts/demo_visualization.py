"""
Demo visualization module.

Contains classes for chart creation, theming, and dashboard building.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import matplotlib  # type: ignore[import-untyped]
import matplotlib.pyplot as plt  # type: ignore[import-untyped]
from matplotlib import gridspec  # type: ignore[import-untyped]
from matplotlib.axes import Axes  # type: ignore[import-untyped]
from matplotlib.patches import FancyBboxPatch  # type: ignore[import-untyped]


@dataclass
class MetricCardConfig:
    """Configuration for metric card creation."""

    value: float
    title: str
    subtitle: str = ""
    trend: float | None = None
    card_scale: float = 1.0
    color: str | None = None
    format_type: str = "number"


@dataclass
class BarChartConfig:
    """Configuration for bar chart creation."""

    categories: list[str]
    values: list[float]
    title: str
    ylabel: str
    colors: list[str] | None = None
    value_format: str = "{}"


@dataclass
class LineChartConfig:
    """Configuration for line chart creation."""

    x_values: list[float]
    y_values: list[float]
    title: str
    xlabel: str
    ylabel: str
    marker: str = "o"
    show_confidence: bool = False
    confidence_bands: tuple | None = None


def add_data_point_annotations(
    ax: Axes, x_values: Sequence[float], y_values: Sequence[float]
) -> None:
    """Add standardized annotations to data points.

    Args:
        ax: Matplotlib axes object
        x_values: X coordinate values
        y_values: Y coordinate values
    """
    for x, y in zip(x_values, y_values, strict=False):
        ax.annotate(
            f"{y}s",
            (x, y),
            textcoords="offset points",
            xytext=(0, 15),
            ha="center",
            fontsize=10,
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
        )


def remove_chart_spines(ax: Axes) -> None:
    """Remove top and right spines from chart for cleaner look.

    Args:
        ax: Matplotlib axes object
    """
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


class VisualizationTheme:
    """Manages visualization styling and theming."""

    def __init__(self, config: Any) -> None:
        """Initialize the ThemeManager with a config."""
        self.config = config

    def get_colors(self) -> dict[str, str]:
        """Get color scheme from configuration."""
        viz_config = self.config.visualization_config
        colors = viz_config.colors
        return {
            "primary": colors.primary,
            "secondary": colors.secondary,
            "accent": colors.accent,
            "success": colors.success,
            "danger": colors.danger,
            "warning": colors.warning,
            "neutral": colors.neutral,
            "background": colors.background,
        }

    def get_fonts(self) -> dict[str, int]:
        """Get font sizes from configuration."""
        viz_config = self.config.visualization_config
        fonts = viz_config.fonts
        return {
            "title": fonts.title_size,
            "subtitle": fonts.subtitle_size,
            "body": fonts.body_size,
            "caption": fonts.caption_size,
        }


class ChartFactory:
    """Factory for creating different types of charts with consistent styling."""

    def __init__(self, theme: VisualizationTheme):
        """Initialize the ChartFactory with a theme."""
        self.theme = theme
        self.colors = theme.get_colors()
        self.fonts = theme.get_fonts()

    def create_metric_card(
        self,
        ax: Any,
        config: MetricCardConfig,
    ) -> None:
        """Create a metric card showing key numbers."""
        color = config.color or self.colors["primary"]

        ax.clear()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Background card (scaled)
        card_width = 0.9 * config.card_scale
        card_height = 0.8 * config.card_scale
        card_x = 0.05 + (0.9 - card_width) / 2  # Center horizontally
        card_y = 0.1 + (0.8 - card_height) / 2  # Center vertically
        card = FancyBboxPatch(
            (card_x, card_y),
            card_width,
            card_height,
            boxstyle="round,pad=0.02",
            facecolor="white",
            edgecolor=color,
            linewidth=2 * config.card_scale,
            alpha=0.95,
        )
        ax.add_patch(card)
        # Format value
        formatted_value = self._format_value(config.value, config.format_type)

        # Main value
        ax.text(
            0.5,
            0.65,
            formatted_value,
            ha="center",
            va="center",
            fontsize=int(24 * config.card_scale),
            fontweight="bold",
            color=color,
        )

        # Title and subtitle
        ax.text(
            0.5,
            0.45,
            config.title,
            ha="center",
            va="center",
            fontsize=int(14 * config.card_scale),
            fontweight="bold",
            color="#212121",
        )

        if config.subtitle:
            ax.text(
                0.5,
                0.32,
                config.subtitle,
                ha="center",
                va="center",
                fontsize=int(11 * config.card_scale),
                color="#757575",
            )

        # Trend indicator
        if config.trend is not None:
            trend_color = (
                self.colors["success"]
                if config.trend > 0
                else self.colors["danger"]
                if config.trend < 0
                else "#757575"
            )
            trend_symbol = "↗" if config.trend > 0 else "↘" if config.trend < 0 else "→"
            trend_text = f"{trend_symbol} {abs(config.trend):.1f}%"
            ax.text(
                0.5,
                0.2,
                trend_text,
                ha="center",
                va="center",
                fontsize=int(12 * config.card_scale),
                fontweight="bold",
                color=trend_color,
            )

    def create_bar_chart(
        self,
        ax: Any,
        config: BarChartConfig,
    ) -> Any:
        """Create a bar chart with labels."""
        chart_colors = config.colors or [self.colors["primary"]] * len(
            config.categories
        )

        bars = ax.bar(range(len(config.categories)), config.values, color=chart_colors)
        ax.set_xlabel("Approach", fontweight="bold")
        ax.set_ylabel(config.ylabel, fontweight="bold")
        ax.set_title(config.title, fontsize=self.fonts["subtitle"], fontweight="bold")
        ax.set_xticks(range(len(config.categories)))
        ax.set_xticklabels(config.categories, rotation=45, ha="right")

        self._add_value_labels(ax, bars, config.values, config.value_format)

        # Add padding above the highest bar to prevent label overlap
        if config.values:
            max_value = max(config.values)
            current_ylim = ax.get_ylim()
            # Add 15% padding above the highest value
            new_upper_limit = max_value * 1.15
            ax.set_ylim(current_ylim[0], max(current_ylim[1], new_upper_limit))

        return bars

    def create_line_chart(
        self,
        ax: Any,
        config: LineChartConfig,
    ) -> Any:
        """Create a line chart with optional confidence bands."""
        line = ax.plot(
            config.x_values,
            config.y_values,
            marker=config.marker,
            linewidth=3,
            markersize=10,
            color=self.colors["primary"],
            markerfacecolor=self.colors["accent"],
            markeredgecolor="white",
            markeredgewidth=2,
        )

        if config.show_confidence and config.confidence_bands:
            lower_bounds, upper_bounds = config.confidence_bands
            ax.fill_between(
                config.x_values,
                lower_bounds,
                upper_bounds,
                alpha=0.2,
                color=self.colors["primary"],
                label="95% Confidence Interval",
            )
            ax.legend(loc="upper left")

        ax.set_xlabel(config.xlabel, fontsize=12, fontweight="bold")
        ax.set_ylabel(config.ylabel, fontsize=12, fontweight="bold")
        ax.set_title(config.title, fontsize=14, fontweight="bold", pad=20)
        ax.grid(True, alpha=0.3)

        # Value labels
        add_data_point_annotations(ax, config.x_values, config.y_values)
        remove_chart_spines(ax)
        return line

    def _format_value(self, value: float, format_type: str) -> str:
        """Format values based on type."""
        if format_type == "currency":
            return f"${self.format_large_number(value)}"
        if format_type == "percentage":
            return f"{value:.1f}%"
        if format_type == "multiplier":
            return f"{value:.0f}x"
        if format_type == "days":
            return f"{value:.0f} days"

        return self.format_large_number(value)

    def format_large_number(self, value: float) -> str:
        """Format large numbers with K, M, B suffixes."""
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"{value / 1_000:.1f}K"

        return f"{value:,.0f}"

    def _add_value_labels(
        self, ax: Any, bars: Any, values: list[float], format_str: str = "{}"
    ) -> None:
        """Add value labels to bar chart bars."""
        for bar_item, value in zip(bars, values, strict=False):
            height = bar_item.get_height()
            ax.text(
                bar_item.get_x() + bar_item.get_width() / 2,
                height + (height * 0.01),  # Small offset
                format_str.format(value),
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=11,
                color="#212121",
            )


class DashboardBuilder:
    """Builds consistent dashboard layouts."""

    def __init__(self, theme: VisualizationTheme):
        """Initialize the DashboardBuilder with a theme."""
        self.theme = theme
        self.colors = theme.get_colors()

    def setup_dashboard_grid(self, fig: Any, title: str = "Dashboard") -> Any:
        """Set up matplotlib grid for charts."""
        fig.patch.set_facecolor(self.colors["background"])

        fig.suptitle(
            title, fontsize=20, fontweight="bold", color=self.colors["primary"], y=0.95
        )

        gs = gridspec.GridSpec(
            3,
            4,
            figure=fig,
            hspace=0.5,
            wspace=0.5,
            top=0.90,
            bottom=0.06,
            left=0.08,
            right=0.95,
        )
        return gs


class PlotManager:
    """Handles plot display and saving."""

    def __init__(self, config: Any) -> None:
        """Initialize the PlotManager with a config."""
        self.config = config
        self.visualizations_dir = config.ensure_visualization_directory()

    def display_plot(
        self, _plt_figure: Any, plot_name: str = "importobot_plot"
    ) -> None:
        """Display or save a plot based on interactive mode."""
        try:
            if not self.config.non_interactive:
                # Check if we're in an interactive environment before showing

                current_backend = matplotlib.get_backend().lower()
                if current_backend in ["agg", "svg", "pdf", "ps"]:
                    # Non-interactive backends - save instead of show
                    if self.visualizations_dir:
                        filename = (
                            f"{self.visualizations_dir}/"
                            f"{plot_name}_{int(time.time())}.png"
                        )
                        plt.savefig(filename, dpi=150, bbox_inches="tight")
                        print(f"[Plot saved to {filename}]")
                else:
                    # Interactive backends - show the plot
                    plt.show()
            else:
                if self.visualizations_dir:
                    filename = (
                        f"{self.visualizations_dir}/{plot_name}_{int(time.time())}.png"
                    )
                    plt.savefig(filename, dpi=150, bbox_inches="tight")
                    print(f"[Plot saved to {filename}]")
        except Exception as e:
            print(f"Warning: Could not display/save plot {plot_name}: {e}")
        finally:
            plt.close("all")
