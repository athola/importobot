# Importobot Project Plan

This outline enforces the roadmap: what to ship next, what is parked, and which ideas still require further proof-of-concept.

### Latest engineering update (October 2025)
- **✅ ASV PERFORMANCE BENCHMARKING**: ASV (Airspeed Velocity) integration complete with three benchmark suites (conversion performance, memory usage, bulk operations). CI workflow automatically generates and publishes benchmark charts to wiki on tagged releases. Configuration in `asv.conf.json`, benchmark suites in `benchmarks/conversion.py`, chart generation in `scripts/src/importobot_scripts/benchmarks/generate_asv_charts.py`.
- **✅ TAG-BASED RELEASE WORKFLOW**: PyPI publishing workflow now triggers only on version tags (v*.*.*) instead of main branch pushes, ensuring controlled releases with proper semantic versioning.
- **✅ DEVELOPMENT BRANCH WORKFLOW**: Established `development` as integration branch for all MRs. `main` branch receives only tested releases. Branching strategy documented in wiki/Contributing.md with clear workflows for features, releases, and hotfixes.
- **✅ WIKI CONSOLIDATION**: Removed verbose Bayesian documentation files (Bayesian-Redesign.md, Bayesian-Scorer-Mathematical-Review.md) to streamline wiki for general developers. Essential mathematical content remains in Mathematical-Foundations.md.
- **✅ MATHEMATICALLY RIGOROUS BAYESIAN CONFIDENCE**: The weighted evidence shim is gone; the independent scorer now owns confidence calculations. Evidence flows through `EvidenceMetrics`, missing unique indicators are penalised, and ambiguous inputs are capped at a 1.5:1 likelihood ratio. The new regression suite (`tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`) locks these behaviours down.
- Conversion invariants are stable again after teaching the formatter to leave comment placeholders untouched and to surface both raw and normalized names for auditing.
- Selenium integration coverage now runs entirely in dry-run mode without the old `robot.utils` shim, so CI remains free of legacy deprecation noise.
- Property-based tests retain literal step bodies, which keeps Hypothesis satisfied while still exercising the parameter conversion logic.

## Roadmap

### Q4 2025 — in-flight work
- Bulk conversion polish. Tighten recursive directory handling and step mapping because current heuristics stumble on large Zephyr dumps.
- Additional format support. Xray and TestLink parsers are in review; once merged, bake them into the same validation path as Zephyr so quality is consistent between formats.
- Performance visibility. ASV benchmarking now tracks conversion performance across releases with automated chart generation. Next: add per-format profiling and I/O bottleneck identification.

### Q4 2025 – Q1 2026 — queued next
- REST surface for CI/CD. Request for a service wrapper instead of shell access, so prototype it once parsers are integrated.
- Plugin architecture research. The goal is to let us snap in new source formats without rewriting the core converter. Need to prove abstraction on a format other than Zephyr.
- Quality reporting. Lightweight analytics (success/error counts, skipped fields) so operations teams can spot regressions without perusing logs.

### Later — stays on the backlog until we learn more
- Converters targeting frameworks beyond Robot Framework.
- ML-assisted suggestions that propose tag/step tweaks automatically.
- Cloud-hosted Importobot for customers who do not want to run the CLI themselves.

## Storage Backend Strategy

Only local filesystem backend has support with the current implementation. The abstractions for S3/Azure/GCP are in place but unimplemented; the code paths are exercised through unit tests with mocks such that cloud SDKs can later be added without rewriting callers.

Initial priority is S3 because one implementation covers several lookalike providers (AWS, MinIO, Wasabi, Backblaze, DigitalOcean Spaces) by swapping the endpoint URL. Azure and GCP remain queued until live deployments require them to move up in priority.

Configuration will follow the same pattern across providers:

```python
config = {
    "backend_type": "s3",
    "bucket_name": "my-medallion-data",
    "endpoint_url": "https://s3.wasabisys.com",  # Optional override
    "region_name": "us-east-1",
}
```

### Implementation Roadmap

**Phase 1: S3 backend (next up once roadmap items above land)**
- Implement `S3StorageBackend` with boto3, starting with upload/download/listing.
- Keep the optional dependency small: `pip install importobot[aws]` should bring in everything required.
- Make endpoint overrides first-class so the same code runs against MinIO and friends.

**Phase 2: Azure and GCP (i.e. when adopters request these to be added)**
- Mirror the same interface with `azure-storage-blob` and `google-cloud-storage`.
- Ship as optional extras (`importobot[azure]`, `importobot[gcp]`) to avoid inflating the base install.

**Phase 3: Nice-to-haves**
- Benchmark alternatives such as `obstore` if we hit performance walls.
- Revisit a generic fsspec shim only if external tooling needs it.

### Security & Best Practices

No backend ships without story-for-story coverage of authentication and encryption. For S3 that means IAM roles first, access keys only when necessary. Azure and GCP equivalents (Managed Identity, service accounts) will follow the same pattern. All traffic remains HTTPS and server-side encryption stays on by default; customer-managed keys will be required by enterprise users, so each backend needs a way to plug them in.

## Medallion Architecture Implementation

### Overview
Decision was made to layer Databricks-style Bronze → Silver → Gold design onto Importobot so that raw exports, curated models, and final Robot suites each have their own guardrails. This pipeline will quickly identify where and why data gets stuck.

### Implementation Roadmap

#### MR 1: Foundation & Bronze Layer (Core Infrastructure) ✅ COMPLETED
**Scope**: Establish Medallion foundation and implement Bronze layer for raw data ingestion

**Completed Tasks:**
- **Data Models & Interfaces** (`src/importobot/medallion/`)
  - Created `DataLayer` interface and `BronzeLayer`, `SilverLayer`, `GoldLayer` classes
  - Implemented `LayerMetadata` for lineage tracking (source, timestamp, version)
  - Added `DataQualityMetrics` for validation scoring across layers

- **Bronze Layer Implementation** (`src/importobot/medallion/bronze/`)
  - `RawDataProcessor` class for schema-aware JSON intake
  - Enhanced validation with format detection (Zephyr, TestRail, JIRA/Xray)
  - Immutable storage with versioning and audit metadata
  - Integration points with existing `GenericTestFileParser`

- **Configuration & Storage**
  - Added medallion settings to `importobot.config` (layer paths, retention policies)
  - Implemented storage abstraction for local/cloud deployment flexibility
  - Updated `pyproject.toml` with optional medallion dependencies

#### MR 2: Silver Layer (Data Standardization & Quality) - PLANNED
**Scope**: Implement curated data layer with standardization and enrichment

**Tasks:**
- **Standardization Engine** (`src/importobot/medallion/silver/`)
  - `TestCaseNormalizer` for cross-format standardization
  - `MetadataEnricher` for business rule application and traceability
  - `QualityValidator` with completeness, consistency, and referential integrity checks

- **Data Lineage & Versioning**
  - Implement change tracking between Bronze and Silver transformations
  - Add incremental processing capabilities for changed data only
  - Create rollback mechanisms for data quality issues

- **Enhanced API Integration**
  - Extend `importobot.api.validation` with medallion quality metrics
  - Add layer-specific validation endpoints for CI/CD integration

#### MR 3: Gold Layer (Business-Ready Output) - PLANNED
**Scope**: Implement consumption-ready layer with optimization and export capabilities

**Tasks:**
- **Gold Layer Engine** (`src/importobot/medallion/gold/`)
  - `OptimizedConverter` for faster Robot Framework generation without sacrificing readability
  - `SuiteOrganizer` to keep related tests together instead of dumping them alphabetically
  - `LibraryOptimizer` to trim redundant imports
  - Optimization benchmarking: start with gradient-descent-style tuning, compare against the current heuristic, and keep extra algorithms only if they perform well on real fixtures (small, medium, large suites drawn from Zephyr/TestRail/Xray regressions).

- **Export & Analytics**
  - Multiple output formats beyond Robot Framework (TestNG, pytest)
  - Conversion analytics and quality reporting dashboard
  - Integration with existing `GenericSuggestionEngine`
  - ADR & deployment documentation tracked in `wiki/architecture` and `wiki/Deployment-Guide.md`

#### MR 4: Enterprise Features & Scalability - PLANNED
**Scope**: Production-ready features for enterprise deployment

**Tasks:**
- **Parallel Processing Framework**
  - Implement concurrent processing across all layers
  - Add batch processing capabilities for large test suites
  - Resource management and performance monitoring

- **Advanced Analytics** (`src/importobot/medallion/analytics/`)
  - Test coverage analysis across the conversion pipeline
  - Performance metrics and bottleneck identification
  - Quality trend analysis and recommendations

### Outstanding Implementation Items

#### Bronze Layer methods still undone
Location: `src/importobot/medallion/bronze_layer.py`

1. `get_record_metadata(record_id: str)` — low effort. Metadata already lives in `self._metadata_store`; return it instead of `None` and cover with unit tests.
2. `get_record_lineage(record_id: str)` — low effort. Same story for `self._lineage_store`.
3. `get_bronze_records(filter_criteria, limit)` — medium effort. Needs filtering/pagination plus conversion into `BronzeRecord` objects.

Estimated effort: roughly half a day for the trio, including tests. Please fix the misleading inline comments while touching these functions.

### Technical Architecture

#### Layer Structure:
```
Bronze Layer (Raw): JSON ingestion → Schema validation → Audit metadata
Silver Layer (Curated): Normalization → Enrichment → Quality gates
Gold Layer (Consumption): Optimization → Organization → Export
```

#### Integration Strategy:
- **Backward Compatibility**: Existing `JsonToRobotConverter` API unchanged
- **Opt-in Enhancement**: Medallion features accessible via `importobot.api.medallion`
- **Progressive Migration**: Current users can adopt layers incrementally

#### Quality Gates:
- **Bronze**: Syntax validation, format detection, completeness checks
- **Silver**: Semantic validation, business rule compliance, data consistency
- **Gold**: Execution feasibility, performance optimization, export readiness

### Current Architecture Analysis

#### Current Data Flow:
1. **Input**: JSON test data files (various formats)
2. **Loading & Validation**: File I/O, JSON parsing, basic structure validation
3. **Parsing**: GenericTestFileParser finds test cases and steps
4. **Conversion**: GenericConversionEngine orchestrates transformation
5. **Library Detection**: Pattern matching for Robot Framework libraries
6. **Output Generation**: Assembles Robot Framework files
7. **Persistence**: Writes to .robot files

#### Medallion Enhancement Mapping:
- **Bronze Layer Enhancements**: Schema-aware ingestion with metadata capture, data lineage tracking, format-specific validation
- **Silver Layer Enhancements**: Standardized test case model, enhanced metadata extraction, data quality rules enforcement, business rule enrichment
- **Gold Layer Enhancements**: Optimized Robot Framework representation, library dependency resolution, test suite organization, performance optimization

## Recent Improvements

### Artifact management
- `.gitignore` now drops generated `.robot` files and scratch data so they stop sneaking into commits.
- `make clean` and `make deep-clean` remove build and test leftovers, which keeps CI and laptops in sync.
- Historical artifacts from before the cleanup have been removed.

### Code quality snapshot (September 2025)
- Restored the pylint score to 10.0 by fixing warnings rather than suppressing them.
- Closed out pycodestyle/pydocstyle issues (mostly long lines and missing summaries) and standardized formatting with ruff/Black.
- Tightened error handling and type hints so mypy runs cleanly.

### Tests and fixtures (September 2025)
- Filled in missing fixtures and import paths so the suite now passes 1153 checks consistently.
- Rebalanced SSH sample data that had been masking validation failures.
- Cleared noisy pytest warnings by fixing constructors and redundant markers.

### January 2025 cleanup highlights
- Removed ~200 lines of legacy compatibility code and consolidated duplicate data-processing helpers.
- Added explicit `__all__` exports to mark the public API surface and kept internal modules private.
- Updated documentation across README/PLAN/CLAUDE/wiki to drop marketing filler and reflect the current architecture.

### Interactive demo + analytics work
- Added `scripts/interactive_demo.py` with scenarios that show cost, conversion speed, and automation ROI for stakeholders.
- Built lightweight visualization hooks for performance runs; results feed the same KPI cards for demo to leadership.
- Shared utilities now power both the CLI and demo flows (pattern extraction, step comment generation, SSH keyword coverage).

**API Design Decisions:**
- **Primary Interface**: `import importobot` → `JsonToRobotConverter()` for core bulk conversion
- **Enterprise Features**: `importobot.api.*` → validation, converters, suggestions for CI/CD and QA teams
- **Configuration Access**: `importobot.config` and `importobot.exceptions` for enterprise integration
- **Security Controls**: Core implementation modules marked private (empty `__all__` lists)

**Business Use Case Alignment:**
1. **Bulk Conversion Pipeline**: Simple `JsonToRobotConverter` for thousands of test cases
2. **CI/CD Integration**: `importobot.api.validation` for automated pipeline validation
3. **QA Suggestion Engine**: `importobot.api.suggestions` for handling ambiguous test cases
4. **Enterprise Configuration**: Configurable limits and settings for production deployments

**Pattern Analysis & Validation:**
- Researched pandas, numpy, requests, flask import patterns
- Validated namespace management techniques against industry standards
- Confirmed import/del cleanup pattern is acceptable practice (pandas uses similar)
- Established version stability promises following pandas model

## Missing Test Coverage

### Error Scenarios
- **Large file handling**: Tests for processing extremely large test files
- **Network timeouts**: Tests for handling network interruptions during remote file operations
- **Malformed templates**: Tests for handling corrupted or incorrectly formatted template files

### Security Tests
- **Path traversal attempts**: Tests to prevent directory traversal attacks in file operations
- **Malicious JSON**: Tests for handling intentionally malformed or dangerous JSON inputs
- **Command injection**: Tests to prevent shell command injection through test parameters

### Performance Tests
- **Load testing for large-scale generation**: Tests to verify performance when generating thousands of test cases
- **Memory usage monitoring**: Tests to track memory consumption during large conversions
- **Concurrent processing**: Tests for handling multiple simultaneous conversion requests

## Test Suite Quality Improvement Plan

### Executive Summary

Comprehensive review of 90 test files revealed systematic opportunities to improve test quality, maintainability, and adherence to TDD principles. Current test suite has 1537+ passing tests with good coverage but requires structural improvements for maintainability.

### Current Test Suite Status

**Strengths:**
✅ Good test coverage (1537+ tests)
✅ Clear test organization (unit/integration/invariant/generative)
✅ Existing shared test data and fixtures
✅ Comprehensive edge case testing in some areas (distributions, security, SSH)
✅ Use of hypothesis for property-based testing (invariant tests)

**Areas for Improvement:**
⚠️ 150+ hard-coded magic numbers without named constants
⚠️ 13 files manually create temp directories instead of using fixtures
⚠️ 862 duplicate test data declarations
⚠️ 87 test files lack explicit AAA (Arrange-Act-Assert) structure
⚠️ 100+ weak assertion messages
⚠️ 20+ missed parametrization opportunities

### Completed Improvements

**Test Constants Module** (`tests/test_constants.py`):
- Eliminates hard-coded magic numbers across test suite
- Includes exit codes, security warning counts, distribution expectations, resource limits, optimization parameters
- Makes 150+ test assertions more readable and maintainable

**Enhanced Shared Test Data** (`tests/shared_test_data.py`):
- Added common Zephyr format test data, enterprise app testing, web navigation, database operations, API testing
- Reduces duplicate test data across 862+ instances

### High-Priority Improvements (Ready for Implementation)

**Priority 1: Use Test Constants**
- **Effort**: Medium (2-3 hours)
- **Impact**: High
- **Files affected**: 15+ test files
- Replace magic numbers in distributions, CLI, security, optimization, and resource management tests

**Priority 2: Convert Temp Directory Creation to Fixtures**
- **Effort**: Low (1-2 hours)
- **Impact**: High
- **Files affected**: 13 test files
- Use existing `temp_dir` fixture instead of manual `tempfile.TemporaryDirectory()`

**Priority 3: Add Parametrization to Similar Tests**
- **Effort**: Medium (3-4 hours)
- **Impact**: Medium-High
- **Files affected**: 5+ test files
- Consolidate similar security tests and distribution tests using `@pytest.mark.parametrize`

**Priority 4: Add AAA Comments to Tests**
- **Effort**: Low-Medium (2-3 hours for high-value tests)
- **Impact**: Medium
- **Files affected**: 87 test files (focus on complex ones first)
- Add explicit Arrange-Act-Assert structure comments

**Priority 5: Improve Assertion Messages**
- **Effort**: Medium (3-4 hours)
- **Impact**: High (better debugging experience)
- **Files affected**: 100+ assertion statements
- Add descriptive failure messages for better debugging

### Implementation Phases

**Phase 1: Quick Wins (Week 1)**
- ✅ Create `test_constants.py`
- ✅ Enhance `shared_test_data.py`
- ⏳ Convert 5 key test files to use constants
- ⏳ Convert temp directory creation to fixtures (13 files)

**Phase 2: Quality Improvements (Week 2)**
- ⏳ Add parametrization to security, distribution, and parser tests
- ⏳ Add AAA comments to 20 most complex tests
- ⏳ Improve assertion messages in 50 key assertions

**Phase 3: Structural Improvements (Week 3)**
- ⏳ Expand shared test data usage
- ⏳ Split 5-10 multi-behavior tests
- ⏳ Add missing edge case tests

**Success Metrics**
- Reduce hard-coded values by 80% (from 150+ to <30)
- Reduce duplicate test data by 50% (from 862 to <450)
- 100% of complex tests have AAA structure
- 80% of assertions have descriptive failure messages
