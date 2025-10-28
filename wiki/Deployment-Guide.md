# Deployment Guide

This guide provides instructions for deploying Importobot in various environments.

## Local Deployment

For local development and testing, you can clone the repository and run the tool directly.

```bash
git clone https://github.com/athola/importobot.git
cd importobot
uv sync
uv run python -m pytest
```

## Containerized Deployment

For production and CI/CD environments, we recommend deploying Importobot as a Docker container.

### Building the Docker Image

```bash
docker build -t importobot:latest .
```

### Running Basic Conversions

```bash
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

For large-scale deployments, you can use the provided Kubernetes Job specification to run Importobot as a one-off task.

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

Importobot is designed to be easily integrated into your CI/CD pipelines. For a complete example of how to use Importobot in a GitHub Actions workflow, see the [test.yml](/.github/workflows/test.yml) file.
