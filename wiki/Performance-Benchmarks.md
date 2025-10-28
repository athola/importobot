# Performance Benchmarks

Importobot uses two complementary benchmarking systems:

1. **ASV (Airspeed Velocity)** - Tracks performance across releases with automated visualization
2. **Performance Benchmark Script** - Quick validation during development

## ASV Performance Tracking

[Airspeed Velocity (ASV)](https://asv.readthedocs.io/) is used to track the performance of Importobot over time. It automatically runs benchmarks on each commit and generates detailed reports that can be used to identify performance regressions.

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

A script is provided for running quick performance benchmarks during development. This is useful for validating the performance impact of your changes before submitting a pull request.

### Running the Benchmark Script

```bash
# Run the full benchmark suite
uv run python -m importobot_scripts.benchmarks.performance_benchmark

# Run a specific scenario with a limited number of iterations
uv run python -m importobot_scripts.benchmarks.performance_benchmark --iterations 20 --complexity complex
```

### Key Metrics

The benchmark script captures the following key metrics:

-   **Throughput:** The number of files processed per second.
-   **Latency:** The time it takes to process a single file.
-   **Memory Usage:** The amount of memory used by the process.

Results are printed to the console and saved to `performance_benchmark_results.json`.
