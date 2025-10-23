# Roadmap

This document outlines the future development plans for Importobot.

## Completed highlights (v0.3.0)

- Conversion engine now includes SSH/API/database/web keyword libraries and the suggestion engine by default.
- CLI, validation, and GitHub workflows provide an effective way to run Importobot in CI.
- The test suite contains 1,153 green checks after the recent fixture overhaul.

## Q3 2025 — in-flight

- Refinement of bulk conversion so recursive runs handle large Zephyr exports without manual cleanup.
- Xray/TestLink parser review; merge once validation matches the existing Zephyr flow.
- Simple timing metrics and I/O profiling to pinpoint performance bottlenecks.

## Q4 2025 – Q1 2026 — queued next

- REST API for CI/CD users who want a service instead of CLI access.
- Plugin architecture study to enable integration of new formats without touching the converter core.
- Lightweight reporting (success/error counts, skipped fields) to allow operations teams to track trends.

## Later — ideas parked until demand is clear

- Converters targeting frameworks beyond Robot Framework.
- ML-assisted suggestions that suggest tag/step modifications.
- Hosted Importobot for teams that cannot run the CLI themselves.

## Zephyr Scale Enhancement Plan (Future Work)

### Overview
Zephyr Scale introduces complex test case structures with nested preconditions and parameterized steps. The enhancement plan focuses on field mapping for these structures while maintaining the existing conversion pipeline.

### Key Enhancements Planned

#### Phase 1: Improved Field Recognition
- Zephyr-specific field groups for test case details, preconditions, and traceability
- Improved test case detection for Zephyr structure patterns
- Platform-specific command parsing for multi-platform test designs

#### Phase 2: Test Analysis & Classification
- Zephyr test level classifier (Minimum Viable CRS, Smoke, Edge Case, Regression)
- Precondition analyzer for structured setup requirements
- Improved Bayesian scoring with Zephyr-specific evidence patterns

#### Phase 3: Cross-Platform Generation
- Robot Framework generation supporting platform variations
- Variable extraction from Zephyr {variable} format to ${variable} format
- Conditional step generation for different target platforms

#### Phase 4: Complete API Integration
- Improved Zephyr client for improved test case retrieval
- Full field mapping and traceability data extraction
- Support for Zephyr's complete test case structure

### Success Metrics
- 95%+ accuracy in parsing Zephyr test case structures
- Retain all test case metadata and requirement traceability
- Handle 90%+ of platform variation patterns
- Generate executable Robot Framework tests for 95%+ of cases

### Implementation Timeline
Planned for 2026 based on customer demand and Zephyr adoption patterns.

## Cloud Storage Backend Roadmap

### Phase 1: S3 backend

- Build `S3StorageBackend` using boto3, including endpoint overrides so MinIO/Wasabi/Backblaze/DigitalOcean work with the same code path.
- Provide the dependency via `pip install importobot[aws]` so the base install stays light.

### Phase 2: Azure & GCP

- Implement the interface with `azure-storage-blob` and `google-cloud-storage` when demand requires it.
- Offer `importobot[azure]` and `importobot[gcp]` extras instead of bundling everything.

### Phase 3: Future Considerations

- Benchmark alternatives such as `obstore` once the performance wall is hit.
- Consider an fsspec layer only if external integrations need it.

### Current status

- Local filesystem backend is the production path today.
- `StorageBackend` abstractions, configuration plumbing, and optional-dependency stubs already exist, so the cloud work can slot in when priorities allow.

## Feedback

Please provide feedback on this roadmap! Open an issue on GitHub for specific feature requests.
