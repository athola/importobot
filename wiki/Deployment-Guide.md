# Deployment Guide

Deploy Importobot locally, in containers, or inside CI jobs using the steps below.

## Prerequisites

- Python 3.10+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Access to target format exports (Zephyr/JIRA/etc.) OR API credentials for direct integration

> Note: Only the local storage backend ships today; S3/Azure/GCP configuration examples below are ready for when those modules land.

## Local Development

```bash
git clone https://github.com/athola/importobot.git
cd importobot
uv sync
uv run python -m pytest
```

## API Integration Deployment

### Environment Configuration

For production deployments using API integration, configure credentials securely:

```bash
# Zephyr configuration
export IMPORTOBOT_ZEPHYR_API_URL="https://your-zephyr.example.com"
export IMPORTOBOT_ZEPHYR_TOKENS="secure-token-here"

# TestRail configuration
export IMPORTOBOT_TESTRAIL_API_URL="https://testrail.example.com/api/v2"
export IMPORTOBOT_TESTRAIL_TOKENS="api-token-here"
export IMPORTOBOT_TESTRAIL_API_USER="automation-user"

# Jira/Xray configuration
export IMPORTOBOT_JIRA_XRAY_API_URL="https://jira.example.com/rest/api/2/search"
export IMPORTOBOT_JIRA_XRAY_TOKENS="jira-token-here"

# Shared configuration
export IMPORTOBOT_API_INPUT_DIR="/data/api_payloads"
export IMPORTOBOT_API_MAX_CONCURRENCY="4"
```

### Container Deployment with API Support

1. Build the image

   ```bash
   docker build -t importobot:latest .
   ```

2. Run with API credentials

   ```bash
   docker run --rm \
     -v $PWD/data:/data \
     -e IMPORTOBOT_ZEPHYR_API_URL="https://zephyr.example.com" \
     -e IMPORTOBOT_ZEPHYR_TOKENS="secure-token" \
     -e IMPORTOBOT_API_INPUT_DIR="/data/payloads" \
     importobot:latest \
     uv run importobot --fetch-format zephyr --project PROJ --output /data/converted.robot
   ```

3. Using environment file

   ```bash
   # .env file
   IMPORTOBOT_ZEPHYR_API_URL=https://zephyr.example.com
   IMPORTOBOT_ZEPHYR_TOKENS=secure-token
   IMPORTOBOT_ZEPHYR_PROJECT=PROJECT_KEY

   docker run --rm \
     --env-file .env \
     -v $PWD/data:/data \
     importobot:latest \
     uv run importobot --fetch-format zephyr --output /data/converted.robot
   ```

### Kubernetes Deployment

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
        - name: IMPORTOBOT_API_INPUT_DIR
          value: "/data/payloads"
        volumeMounts:
        - name: data-volume
          mountPath: /data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: importobot-data
      restartPolicy: Never
```

## Container deployment

1. Build the image

   ```bash
   docker build -t importobot:latest .
   ```

2. Run conversions

   ```bash
   docker run --rm -v $PWD/data:/data importobot:latest \
       uv run importobot /data/input.json /data/output.robot
   ```

## CI/CD integration

### Basic Conversion Jobs
```yaml
# GitHub Actions example
- name: Convert test cases
  run: |
    uv run importobot input.json output.robot
    uv run python -m pytest output.robot
```

### API Integration Jobs
```yaml
# GitHub Actions example with API integration
- name: Fetch and convert from Zephyr
  env:
    IMPORTOBOT_ZEPHYR_API_URL: ${{ secrets.ZEPHYR_API_URL }}
    IMPORTOBOT_ZEPHYR_TOKENS: ${{ secrets.ZEPHYR_TOKENS }}
    IMPORTOBOT_ZEPHYR_PROJECT: ${{ secrets.ZEPHYR_PROJECT }}
  run: |
    uv run importobot --fetch-format zephyr --output converted.robot
    uv run python -m pytest converted.robot
```

### Performance Monitoring
- Schedule `uv run python -m importobot_scripts.benchmarks.performance_benchmark --parallel` nightly to catch performance regressions and archive `performance_benchmark_results.json`.
- Full validation (`make validate`) takes about 4 minutes; see [Performance-Characteristics](Performance-Characteristics) for timing breakdown and faster alternatives during development.
- Monitor API rate limits and response times when using direct integration.

## Cloud Storage Backend Configuration

### Local storage (current implementation)

```python
from importobot.medallion.storage.config import StorageConfig

config = StorageConfig(
    backend_type="local",
    base_path="./medallion_data",
    compression=False,
    auto_backup=True,
)
```

### S3 and compatible services (planned)

Cloud backends share the same configuration shape; swap `endpoint_url` to target MinIO, Wasabi, Backblaze, or DigitalOcean once the S3 implementation lands:

```python
config = StorageConfig(
    backend_type="s3",
    bucket_name="my-medallion-data",
    region_name="us-east-1",
    endpoint_url="https://s3.wasabisys.com",  # Optional override
)
```

### Azure Blob Storage (Planned)

```python
config = StorageConfig(
    backend_type="azure",
    container_name="medallion-data",
    storage_account="myaccount",
    # Uses DefaultAzureCredential (Managed Identity, Azure CLI, etc.)
)
```

### Google Cloud Storage (Planned)

```python
config = StorageConfig(
    backend_type="gcp",
    bucket_name="my-medallion-data",
    project_id="my-project",
    # Uses Application Default Credentials (service accounts, gcloud, etc.)
)
```

### Installation

**Cloud backend dependencies are optional:**

```bash
# AWS S3 and S3-compatible services (MinIO, Wasabi, Backblaze B2, etc.)
pip install importobot[aws]

# Azure Blob Storage
pip install importobot[azure]

# Google Cloud Storage
pip install importobot[gcp]

# All cloud backends
pip install importobot[aws,azure,gcp]
```

## Production checklist

### General Configuration
- Set medallion storage paths in `importobot.config` and keep backups.
- Run ingestion in strict security mode and aggregate logs for warnings/errors.
- Monitor cache stats and memory via the benchmark harness.
- For cloud backends, configure credentials (IAM/Managed Identity/service accounts) and enable server-side encryption.

### API Integration Security
- Store API tokens in secure secret management systems (Kubernetes Secrets, AWS Secrets Manager, Azure Key Vault).
- Use dedicated service accounts with minimal required permissions for API access.
- Enable token rotation where supported by the upstream platform.
- Monitor API usage and rate limits to avoid service disruptions.
- Implement proper logging and monitoring for API authentication failures.

### Rate Limiting and Performance
- Configure `IMPORTOBOT_API_MAX_CONCURRENCY` based on your platform's rate limits.
- Monitor API response times and implement exponential backoff for retry logic.
- Set appropriate timeouts for API requests to prevent job hangs.
- Use payload caching to reduce redundant API calls for unchanged data.

### Monitoring and Alerting
- Monitor successful vs failed API integrations
- Alert on authentication failures or rate limit breaches
- Track conversion success rates and processing times
- Log API discovery failures for troubleshooting server configuration changes
