# Deployment Guide

This guide covers several common methods for deploying and running Importobot.

## Running from Source

For local development or testing, you can run Importobot directly from a clone of the repository. This setup is covered in detail in the [Getting Started](Getting-Started.md) guide.

```bash
git clone https://github.com/athola/importobot.git
cd importobot
uv sync --dev
uv run pytest
```

## Containerized Deployment

For production and CI/CD environments, we recommend deploying Importobot as a Docker container.

### Building the Docker Image

```bash
docker build -t importobot:latest .
```

### Running Basic Conversions

```bash
# --rm: Automatically remove the container when it exits
# -v: Mount the local ./data directory into the container at /data
docker run --rm -v $PWD/data:/data importobot:latest \
    uv run importobot /data/input.json /data/output.robot
```

### Deployment with API Integration

When using API integration, you can provide credentials to the container using environment variables or an environment file.

#### Using Environment Variables

```bash
docker run --rm \
  -v $PWD/data:/data \
  -e IMPORTOBOT_ZEPHYR_API_URL="https://zephyr.example.com" \
  -e IMPORTOBOT_ZEPHYR_TOKENS="secure-token" \
  importobot:latest \
  uv run importobot --fetch-format zephyr --project PROJ --output /data/converted.robot
```

#### Using an Environment File

Create a `.env` file with your API credentials:

```
IMPORTOBOT_ZEPHYR_API_URL=https://zephyr.example.com
IMPORTOBOT_ZEPHYR_TOKENS=secure-token
IMPORTOBOT_ZEPHYR_PROJECT=PROJECT_KEY
```

Then, run the container with the `--env-file` flag:

```bash
docker run --rm \
  --env-file .env \
  -v $PWD/data:/data \
  importobot:latest \
  uv run importobot --fetch-format zephyr --output /data/converted.robot
```

### Kubernetes Deployment

For large-scale or scheduled tasks, you can run Importobot as a one-off task in Kubernetes using a Job.

First, ensure your API credentials are stored in a Kubernetes Secret named `importobot-secrets`. Then, you can apply the following Job definition:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: importobot-job
spec:
  template:
    spec:
      containers:
      - name: importobot
        image: importobot:latest
        command: ["uv", "run", "importobot"]
        args:
          - "--fetch-format"
          - "zephyr"
          - "--project"
          - "PROJECT_KEY"
          - "--output"
          - "/data/converted.robot"
        env:
        - name: IMPORTOBOT_ZEPHYR_API_URL
          valueFrom:
            secretKeyRef:
              name: importobot-secrets
              key: zephyr-api-url
        - name: IMPORTOBOT_ZEPHYR_TOKENS
          valueFrom:
            secretKeyRef:
              name: importobot-secrets
              key: zephyr-tokens
      restartPolicy: Never
```

## CI/CD Integration

Importobot can be integrated into any CI/CD pipeline. The general approach is to use a containerized deployment (as shown above) within a pipeline step to automatically convert test suites as part of your build or test process.

For a complete, working example using GitHub Actions, see the project's own [test workflow file](https://github.com/athola/importobot/blob/main/.github/workflows/test.yml).
