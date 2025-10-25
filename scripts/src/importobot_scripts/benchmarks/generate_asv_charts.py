#!/usr/bin/env python3
"""Generate static PNG charts from ASV benchmark results.

This script reads ASV benchmark data and generates static images suitable
for embedding in GitHub wiki pages. It creates trend charts showing
performance across releases and commits.
"""

import json
from pathlib import Path
from typing import Any

try:
    import matplotlib

    matplotlib.use("Agg")  # Non-interactive backend
    from datetime import datetime

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, cannot generate charts")


def load_asv_results(results_dir: Path) -> dict[str, Any]:
    """Load ASV benchmark results from JSON files.

    Args:
        results_dir: Path to .asv/results directory

    Returns:
        Dictionary mapping benchmark names to their results over time
    """
    benchmarks_file = results_dir / "benchmarks.json"
    if not benchmarks_file.exists():
        raise FileNotFoundError(f"No benchmarks.json found at {benchmarks_file}")

    with open(benchmarks_file) as f:
        benchmarks_meta = json.load(f)

    # Find machine results directory
    machine_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
    if not machine_dirs:
        raise FileNotFoundError(f"No machine results found in {results_dir}")

    # Load all result files
    all_results = {}
    for machine_dir in machine_dirs:
        for result_file in machine_dir.glob("*.json"):
            with open(result_file) as f:
                result_data = json.load(f)
                commit_hash = result_data.get("commit_hash", "unknown")
                if commit_hash not in all_results:
                    all_results[commit_hash] = result_data

    return {"metadata": benchmarks_meta, "results": all_results}


def generate_conversion_performance_chart(
    data: dict[str, Any], output_path: Path
) -> None:
    """Generate chart showing conversion performance trends.

    Args:
        data: ASV results data
        output_path: Path to save PNG file
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    # Extract benchmark data for ZephyrConversionSuite
    benchmark_names = [
        "ZephyrConversionSuite.time_convert_simple_single_test",
        "ZephyrConversionSuite.time_convert_moderate_multiple_tests",
        "ZephyrConversionSuite.time_convert_large_complex_suite",
    ]

    colors = ["#2ecc71", "#3498db", "#e74c3c"]
    labels = ["Simple (1 test)", "Moderate (20 tests)", "Large (100 tests)"]

    results = data["results"]
    commits = sorted(results.keys(), key=lambda c: results[c].get("date", 0))

    for idx, benchmark_name in enumerate(benchmark_names):
        times = []
        commit_dates = []

        for commit in commits:
            result = results[commit]
            if "results" in result and benchmark_name in result["results"]:
                value = result["results"][benchmark_name]
                if value and isinstance(value, int | float):
                    times.append(value)
                    # Convert timestamp to datetime if available
                    timestamp = result.get("date", 0)
                    if timestamp:
                        commit_dates.append(datetime.fromtimestamp(timestamp / 1000))

        if times and commit_dates:
            # Convert datetime objects to matplotlib date format
            mdates = matplotlib.dates
            date_nums = mdates.date2num(commit_dates)
            ax.plot(date_nums, times, marker="o", label=labels[idx], color=colors[idx])

    ax.set_xlabel("Commit Date", fontsize=12)
    ax.set_ylabel("Time (seconds)", fontsize=12)
    ax.set_title(
        "Conversion Performance Across Releases", fontsize=14, fontweight="bold"
    )
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Generated: {output_path}")


def generate_memory_usage_chart(data: dict[str, Any], output_path: Path) -> None:
    """Generate chart showing memory usage trends.

    Args:
        data: ASV results data
        output_path: Path to save PNG file
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, ax = plt.subplots(figsize=(10, 5))

    benchmark_name = "ZephyrConversionSuite.peakmem_convert_large_suite"
    results = data["results"]
    commits = sorted(results.keys(), key=lambda c: results[c].get("date", 0))

    memory_values = []
    commit_dates = []

    for commit in commits:
        result = results[commit]
        if "results" in result and benchmark_name in result["results"]:
            value = result["results"][benchmark_name]
            if value and isinstance(value, int | float):
                # Convert to MB
                memory_values.append(value / (1024 * 1024))
                timestamp = result.get("date", 0)
                if timestamp:
                    commit_dates.append(datetime.fromtimestamp(timestamp / 1000))

    if memory_values and commit_dates:
        # Convert datetime objects to matplotlib date format
        date_nums = mdates.date2num(commit_dates)
        ax.plot(date_nums, memory_values, marker="s", color="#9b59b6", linewidth=2)
        ax.fill_between(date_nums, memory_values, alpha=0.3, color="#9b59b6")

    ax.set_xlabel("Commit Date", fontsize=12)
    ax.set_ylabel("Peak Memory (MB)", fontsize=12)
    ax.set_title(
        "Memory Usage for Large Suite Conversion", fontsize=14, fontweight="bold"
    )
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Generated: {output_path}")


def generate_bulk_conversion_chart(data: dict[str, Any], output_path: Path) -> None:
    """Generate chart showing bulk conversion performance.

    Args:
        data: ASV results data
        output_path: Path to save PNG file
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # DirectoryConversionSuite parameterized benchmarks
    params = ["5", "10", "25"]
    colors = ["#1abc9c", "#f39c12", "#e67e22"]

    results = data["results"]
    commits = sorted(results.keys(), key=lambda c: results[c].get("date", 0))

    for idx, param in enumerate(params):
        benchmark_name = "DirectoryConversionSuite.time_convert_directory"
        times = []
        commit_dates = []

        for commit in commits:
            result = results[commit]
            if "results" in result:
                # Look for parameterized results
                param_key = f"{benchmark_name}({param})"
                if param_key in result["results"]:
                    value = result["results"][param_key]
                    if value and isinstance(value, int | float):
                        times.append(value)
                        timestamp = result.get("date", 0)
                        if timestamp:
                            commit_dates.append(
                                datetime.fromtimestamp(timestamp / 1000)
                            )

        if times and commit_dates:
            # Convert datetime objects to matplotlib date format
            date_nums = mdates.date2num(commit_dates)
            ax.plot(
                date_nums,
                times,
                marker="^",
                label=f"{param} files",
                color=colors[idx],
            )

    ax.set_xlabel("Commit Date", fontsize=12)
    ax.set_ylabel("Time (seconds)", fontsize=12)
    ax.set_title(
        "Bulk Directory Conversion Performance", fontsize=14, fontweight="bold"
    )
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Generated: {output_path}")


def main() -> None:
    """Generate all ASV benchmark charts."""
    if not MATPLOTLIB_AVAILABLE:
        print("Error: matplotlib is required to generate charts")
        print("Install with: uv pip install matplotlib")
        return

    project_root = Path(__file__).parent.parent.parent.parent.parent
    results_dir = project_root / ".asv" / "results"
    output_dir = project_root / "wiki" / "images"

    if not results_dir.exists():
        print(f"Error: ASV results not found at {results_dir}")
        print("Run 'uv run asv run' first to generate benchmark data")
        return

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    print("Loading ASV results...")
    data = load_asv_results(results_dir)

    print(f"Found {len(data['results'])} commits with benchmark data")

    # Generate charts
    print("\nGenerating benchmark charts...")
    generate_conversion_performance_chart(
        data, output_dir / "asv-conversion-performance.png"
    )
    generate_memory_usage_chart(data, output_dir / "asv-memory-usage.png")
    generate_bulk_conversion_chart(data, output_dir / "asv-bulk-conversion.png")

    print(f"\n✓ Charts saved to {output_dir}/")
    print("  - asv-conversion-performance.png")
    print("  - asv-memory-usage.png")
    print("  - asv-bulk-conversion.png")


if __name__ == "__main__":
    main()
