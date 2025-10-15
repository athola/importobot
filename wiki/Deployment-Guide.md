# Deployment Guide

Deploy Importobot locally, in containers, or inside CI jobs using the steps below.

## Prerequisites

- Python 3.10+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Access to target format exports (Zephyr/JIRA/etc.)

> Note: Only the local storage backend ships today; S3/Azure/GCP configuration examples below are ready for when those modules land.

## Local Development

```bash
git clone https://github.com/athola/importobot.git
cd importobot
uv sync
uv run python -m pytest
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

- Call the CLI (`uv run importobot ...`) or `importobot.JsonToRobotConverter()` inside your test job.
- Schedule `uv run python -m importobot_scripts.benchmarks.performance_benchmark --parallel` nightly to catch performance regressions and archive `performance_benchmark_results.json`.
- Full validation (`make validate`) takes about 4 minutes; see [Performance-Characteristics](Performance-Characteristics) for timing breakdown and faster alternatives during development.

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

- Set medallion storage paths in `importobot.config` and keep backups.
- Run ingestion in strict security mode and aggregate logs for warnings/errors.
- Monitor cache stats and memory via the benchmark harness.
- For cloud backends, configure credentials (IAM/Managed Identity/service accounts) and enable server-side encryption.
