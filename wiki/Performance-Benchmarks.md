# Performance Benchmarks

Importobot utilizes two complementary benchmarking systems:

1.  **ASV (Airspeed Velocity)**: Tracks performance across releases with automated visualization.
2.  **Development Benchmark Script**: Provides quick validation during development.

## ASV Performance Tracking

[Airspeed Velocity (ASV)](https://asv.readthedocs.io/) tracks Importobot's performance over time. It automatically runs benchmarks on each commit and generates detailed reports to identify performance regressions.

### Running ASV Benchmarks

```bash
# Run all benchmarks
asv run

# Compare the current commit to the previous one
asv continuous HEAD HEAD~1

# Generate an HTML report
asv publish
asv preview
```

## Development Benchmark Script

A dedicated script facilitates quick performance benchmarks during development. This script helps validate the performance impact of changes before submitting a pull request.

### Running the Benchmark Script

```bash
# Run the full benchmark suite
uv run python -m importobot_scripts.benchmarks.performance_benchmark

# Run a specific scenario with a limited number of iterations
uv run python -m importobot_scripts.benchmarks.performance_benchmark --iterations 20 --complexity complex
```

### Key Metrics

The development benchmark script captures the following key metrics:

-   **Throughput**: The number of files processed per second.
-   **Latency**: The time required to process a single file.
-   **Memory Usage**: The amount of memory consumed by the process.

Results are printed to the console and saved to `performance_benchmark_results.json`.
