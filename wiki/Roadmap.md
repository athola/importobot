# Roadmap

This document outlines the future development plans for Importobot.

## Completed highlights (v0.3.0)

- Conversion engine now ships with SSH/API/database/web keyword libraries and the suggestion engine by default.
- CLI, validation, and GitHub workflows are the effective way to run Importobot in CI.
- The test suite sits at 1,153 green checks after the recent fixture overhaul.

## Q3 2025 — in-flight

- Bulk conversion polish so recursive runs handle large Zephyr exports without manual cleanup.
- Xray/TestLink parser review; merge once validation matches the existing Zephyr flow.
- Simple timing metrics and I/O profiling to pinpoint performance bottlenecks.

## Q4 2025 – Q1 2026 — queued next

- REST surface for CI/CD users who want a service instead of CLI access.
- Plugin architecture study to let us slot in new formats without touching the converter core.
- Lightweight reporting (success/error counts, skipped fields) so ops teams can track trends.

## Later — ideas parked until demand is clear

- Converters targeting frameworks beyond Robot Framework.
- ML-assisted suggestions that propose tag/step tweaks.
- Hosted Importobot for teams that cannot run the CLI themselves.

## Cloud Storage Backend Roadmap

### Phase 1: S3 backend

- Build `S3StorageBackend` atop boto3, including endpoint overrides so MinIO/Wasabi/Backblaze/DigitalOcean work with the same code path.
- Ship the dependency behind `pip install importobot[aws]` so the base install stays light.

### Phase 2: Azure & GCP

- Mirror the interface with `azure-storage-blob` and `google-cloud-storage` when demand requires it.
- Offer `importobot[azure]` and `importobot[gcp]` extras instead of bundling everything.

### Phase 3: Nice-to-haves

- Benchmark alternatives such as `obstore` once the performance wall is hit.
- Consider an fsspec layer only if external integrations need it.

### Current status

- Local filesystem backend is the production path today.
- `StorageBackend` abstractions, configuration plumbing, and optional-dependency stubs already exist, so the cloud work can slot in when priorities allow.

## Feedback

Please provide feedback on this roadmap! Open an issue on GitHub for specific feature requests.
