# Roadmap

This document outlines our future development plans for Importobot.

## Completed highlights (v0.3.0)

- Conversion engine now includes SSH/API/database/web keyword libraries and the suggestion engine by default.
- CLI, validation, and GitHub workflows provide an effective way to run Importobot in CI.
- The test suite contains 1,153 green checks after the recent fixture overhaul.

## Q3 2025 — in-flight

- Improve bulk conversion to handle large, recursive Zephyr exports without manual cleanup.
- Review and merge the Xray/TestLink parser once its validation matches the Zephyr parser.
- Add timing metrics and I/O profiling to find performance bottlenecks.

## Q4 2025 – Q1 2026 — queued next

- A REST API for CI/CD users who prefer a service over the CLI.
- Investigate a plugin architecture to allow adding new formats without changing the core converter.
- Add lightweight reporting (success/error counts, skipped fields) to help teams track conversion trends.

## Later — ideas parked until demand is clear

- Converters targeting frameworks beyond Robot Framework.
- Use machine learning to suggest tag and step modifications.
- A hosted version of Importobot for teams that cannot run the CLI.

## Zephyr Scale Enhancement Plan (Future Work)

### Overview
Zephyr Scale introduces complex test case structures with nested preconditions and parameterized steps. The enhancement plan focuses on field mapping for these structures while maintaining the existing conversion pipeline.

### Key Enhancements Planned

#### Phase 1: Improved Field Recognition
- Add Zephyr-specific field groups for test case details, preconditions, and traceability.
- Improve test case detection for Zephyr's structure patterns.
- Add platform-specific command parsing for multi-platform test designs.

#### Phase 2: Test Analysis & Classification
- Add a Zephyr test level classifier (Minimum Viable CRS, Smoke, Edge Case, Regression).
- Add a precondition analyzer for structured setup requirements.
- Improve Bayesian scoring with Zephyr-specific evidence patterns.

#### Phase 3: Cross-Platform Generation
- Generate Robot Framework tests that support platform variations.
- Convert Zephyr's {variable} format to ${variable}.
- Generate conditional steps for different target platforms.

#### Phase 4: Complete API Integration
- Improve the Zephyr client for better test case retrieval.
- Extract full field mapping and traceability data.
- Support Zephyr's complete test case structure.

### Success Metrics
- 95%+ accuracy in parsing Zephyr test case structures.
- Retain all test case metadata and requirement traceability.
- Handle 90%+ of platform variation patterns.
- Generate executable Robot Framework tests for 95%+ of cases.

### Implementation Timeline
Planned for 2026 based on customer demand and Zephyr adoption patterns.

## Cloud Storage Backend Roadmap

### Phase 1: S3 backend

- Build an `S3StorageBackend` using boto3. It will include endpoint overrides to support MinIO, Wasabi, Backblaze, and DigitalOcean.
- Provide the dependency via `pip install importobot[aws]` to keep the base installation light.

### Phase 2: Azure & GCP

- Implement the interface with `azure-storage-blob` and `google-cloud-storage` when there is demand.
- Offer `importobot[azure]` and `importobot[gcp]` extras instead of bundling everything.

### Phase 3: Future Considerations

- Benchmark alternatives such as `obstore` once the performance wall is hit.
- Consider an fsspec layer only if external integrations need it.

### Current status

- The local filesystem backend is the only production-ready option today.
- The `StorageBackend` abstractions, configuration, and optional-dependency stubs are already in place, so cloud backends can be added when priorities allow.

## Feedback

Please provide feedback on this roadmap! Open an issue on GitHub for specific feature requests.
