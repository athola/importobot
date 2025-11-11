# Importobot Project Plan

Roadmap of upcoming features, parked items, and ideas requiring proof-of-concept development.

### What we shipped in November 2025

**Test Architecture Improvements**: Added 55 named constants organized into 9 categories to replace magic numbers throughout the test suite. Replaced `tempfile` usage with pytest's `tmp_path` fixture, added type annotations to all test functions, and documented Arrange-Act-Assert patterns. All 1,541 tests pass with enhanced mypy type checking.

**Client Module Restructuring**: Split `importobot.integrations.clients` into separate modules (base.py, jira_xray.py, testlink.py, testrail.py, zephyr.py) while maintaining backward compatibility. Implemented lazy loading for 3x faster imports. Added ADR-0006 documenting architectural changes.

**Legacy Code Removal**: Dropped compatibility shims for Python < 3.8, deprecated `setup_logger()` and `get_cache_stats()` functions. Updated documentation to use factual descriptions instead of marketing language.

### What we shipped in October 2025

**ASV Performance Benchmarking**: Integrated ASV (Airspeed Velocity) for tracking performance across releases. Three benchmark suites cover conversion performance, memory usage, and bulk operations with ~55ms average detection time. CI workflow automatically generates and publishes benchmark charts to wiki on tagged releases. Configuration in `asv.conf.json`, benchmark suites in `benchmarks/conversion.py`, automated chart generation in `scripts/src/importobot_scripts/benchmarks/generate_asv_charts.py`.

**Linting Consolidation**: Completed migration from pylint to ruff/mypy-only workflow. Removed pylintrc, cleaned up ASV-generated build artifacts (.asv/html/*), and updated all linting configurations to exclude benchmark and example directories. Merged main branch with modern type hints (dict vs Dict for Python 3.9+), improved Windows file locking compatibility using safer getattr() patterns, and consolidated documentation across 22 resolved merge conflicts.

**Tag-based Release Workflow**: PyPI publishing now triggers only on version tags (v*.*.*) instead of main branch pushes, ensuring controlled releases with proper semantic versioning.

**Development Branch Workflow**: Established development branch as integration target for all MRs. Main branch receives only tested releases from development. Documented in wiki/Contributing.md with clear feature/release/hotfix workflows.

**Application Context Pattern**: Fixed race conditions in tests by replacing global variables with thread-local context. This lets multiple Importobot instances run in the same process without interfering with each other. Added `importobot.caching` module with unified LRU cache.

**Template Learning**: Instead of hardcoding Robot Framework patterns, we now learn them from existing files using `--robot-template`. The system extracts patterns and applies them consistently. We tested this on 3 customer Robot suites and it reduced manual post-conversion editing by about 70%.

**Schema Parser**: Added `schema_parser.py` to read customer documentation with `--input-schema`. We measured parsing accuracy improvement from ~85% to ~95% on custom exports where customers use non-standard field names like `test_title` instead of `name`.

**API Integration**: Unified platform fetching under `--fetch-format`. The Zephyr client now does automatic API discovery and adapts to different server configurations. We tested this against 4 different Zephyr instances and they all work with the same client code.

**Documentation**: Wrote proper Migration Guide for 0.1.2→0.1.3 since there were no breaking changes, documented the breaking changes that did exist in previous versions, and created a step-by-step Blueprint Tutorial. Consolidated verbose Bayesian documentation into streamlined Mathematical-Foundations.md.

**Configuration**: Fixed project identifier parsing that was failing on control characters and whitespace. CLI arguments that don't parse to valid identifiers now use environment variables as default values instead of crashing.

**Test status**: All 2,105 tests pass with 0 skips.
**Code quality**: Removed pylint from the project (now using ruff/mypy only) and improved test isolation.
- Fixed formatter to preserve comment placeholders and show both raw/normalized names for auditing
- Selenium tests run in dry-run mode without `robot.utils` shim, removing deprecation warnings
- Property-based tests keep literal step bodies for Hypothesis while testing parameter conversion

## Roadmap

### Q4 2025 — what we're working on

**Template learning improvements**: The current template system works well for basic patterns, but we need to handle more complex Robot Framework constructs like conditional logic (`IF/ELSE`), loops (`FOR`), and custom keyword usage. We have 2 customer Robot suites that use these patterns heavily.

**Schema integration**: The schema parser works, but it's a separate step from the conversion pipeline. We want to automatically apply organization-specific field mappings without requiring users to remember the `--input-schema` flag every time.

**Performance**: Template ingestion takes ~50ms per file, which becomes noticeable with 50+ template directories. We need to optimize the pattern matching algorithm and add better caching.

**MongoDB Library Modernization**: Replace the inadequate `robot-mongodb-library` with a proper Robot Framework-compatible MongoDB library. The current library causes warnings and provides standalone functions instead of proper keywords. GitHub issue #82 tracks this work.

**Specific customer requests**:
- Company A wants to convert TestRail custom fields that don't follow standard naming
- Company B needs better handling of TestLink test suite hierarchies
- Company C has Zephyr exports with embedded HTML that needs sanitization

### Q3 2025 — completed work
- ** JSON template system**: Implemented blueprint-driven rendering with pattern learning capabilities.
- ** Schema parser**: Created documentation-driven field mapping system.
- ** File examples**: JSON test data covering scenarios like user login, file manipulation, and network configuration.
- ** Bulk conversion polish**: Improved recursive directory handling and step mapping for large Zephyr exports.
- ** Performance visibility**: Added timing metrics and I/O profiling for bottleneck identification.

### Q4 2025 – Q1 2026 — queued next
- REST surface for CI/CD. Request for a service wrapper instead of shell access, so prototype it once parsers are integrated.
- Plugin architecture research. The goal is to let us snap in new source formats without rewriting the core converter. Need to prove abstraction on a format other than Zephyr.
- Quality reporting. Lightweight analytics (success/error counts, skipped fields) so operations teams can spot regressions without perusing logs.

- TODO: Refactor `src/importobot/core/templates/blueprints/cli_builder.py` into smaller helper modules
  - Explore table-driven rendering / class-based builders after current release

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

#### MR 1: Foundation & Bronze Layer (Core Infrastructure)  COMPLETED
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

## Test Suite Quality Improvements

Review of 90 test files identified opportunities to improve maintainability and TDD adherence. Current suite has 1537+ passing tests with good coverage but needs structural improvements.

**Current status:**
- Good coverage (1537+ tests)
- Clear organization (unit/integration/invariant/generative)
- Shared test data and fixtures exist
- Edge case testing in distributions, security, SSH modules
- Property-based testing with Hypothesis

**Issues found:**
- 150+ hard-coded magic numbers without constants
- 13 files manually create temp directories instead of using fixtures
- 862 duplicate test data declarations
- 87 files lack explicit AAA structure
- 100+ weak assertion messages
- 20+ missed parametrization opportunities

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

**Phase 1 (Week 1)**
-  Create `test_constants.py`
-  Enhance `shared_test_data.py`
- Convert 5 key test files to use constants
- Convert temp directory creation to fixtures (13 files)

**Phase 2 (Week 2)**
- Add parametrization to security, distribution, and parser tests
- Add AAA comments to 20 most complex tests
- Improve assertion messages in 50 key assertions

**Phase 3 (Week 3)**
- Expand shared test data usage
- Split 5-10 multi-behavior tests
- Add missing edge case tests

**Target metrics:**
- Reduce hard-coded values by 80% (150+ → <30)
- Reduce duplicate test data by 50% (862 → <450)
- 100% of complex tests have AAA structure
- 80% of assertions have descriptive failure messages
