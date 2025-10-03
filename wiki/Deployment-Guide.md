# Deployment Guide

This guide explains how to ship Importobot in different environments.

## Prerequisites

- Python 3.10+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Access to target format exports (Zephyr/JIRA/etc.)

## Local Development

```bash
git clone https://github.com/athola/importobot.git
cd importobot
uv sync
uv run python -m pytest
```

## Container Deployment

1. Build the image

   ```bash
   docker build -t importobot:latest .
   ```

2. Run conversions

   ```bash
   docker run --rm -v $PWD/data:/data importobot:latest \
       uv run importobot /data/input.json /data/output.robot
   ```

## CI/CD Integration

- Use the Python API (`importobot.api.converters`) inside CI jobs for bulk conversions.
- Run `uv run python scripts/src/importobot_scripts/performance_benchmark.py --parallel`
  in nightly jobs to catch performance regressions.
- Publish `performance_benchmark_results.json` as a build artifact.

## Production Checklist

- Configure medallion storage paths in `importobot.config`.
- Enable strict security level for ingestion services.
- Set up log aggregation for medallion layer warnings/errors.
- Monitor cache stats + memory via benchmark harness.
