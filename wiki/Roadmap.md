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

## Zephyr Scale Enhancement Plan (Future Work)

### Overview
Enhance Importobot to support Zephyr Scale's sophisticated test case methodology while maintaining automated Robot Framework conversion.

### Key Enhancements Planned

#### Phase 1: Enhanced Field Recognition
- Zephyr-specific field groups for test case details, preconditions, and traceability
- Enhanced test case detection recognizing Zephyr structure patterns
- Platform-specific command parsing for multi-platform test designs

#### Phase 2: Test Analysis & Classification
- Zephyr test level classifier (Minimum Viable CRS, Smoke, Edge Case, Regression)
- Precondition analyzer for structured setup requirements
- Enhanced Bayesian scoring with Zephyr-specific evidence patterns

#### Phase 3: Platform-Agnostic Generation
- Robot Framework generation supporting platform variations
- Variable extraction from Zephyr {variable} format to ${variable} format
- Conditional step generation for different target platforms

#### Phase 4: Complete API Integration
- Enhanced Zephyr client for comprehensive test case retrieval
- Full field mapping and traceability data extraction
- Support for Zephyr's complete test case structure

### Success Metrics
- 95%+ accuracy in parsing Zephyr test case structures
- Preserve all test case metadata and requirement traceability
- Handle 90%+ of platform variation patterns
- Generate executable Robot Framework tests for 95%+ of cases

### Implementation Timeline
Planned for 2026 based on customer demand and Zephyr adoption patterns.

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
