# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2025-11-14

### Added
- Shipped `src/importobot/security/` with purpose-built modules for credential management, HSM access, template scanning, SIEM forwarding, compliance reporting, and secure memory so security logic is no longer buried in `utils/`.
- Introduced `CredentialManager` (Fernet-based) plus `SecureMemory` to enforce encrypted storage of API tokens; requires `cryptography>=42.0.0` and a 32-byte `IMPORTOBOT_ENCRYPTION_KEY` (generate with `openssl rand -base64 32`).
- Added operational tooling: `TemplateSecurityScanner` blocks unsafe `--robot-template` inputs, `SIEMManager` ships Splunk/Elastic/Sentinel connectors, and `KeyRotator` automates 90-day, usage-based, and compliance-driven key rotations.
- Logged security activity through the new monitoring subsystem (`security.monitoring`) and surfaced SOC 2 / ISO 27001 controls via `ComplianceEngine`, including CSV/JSON export helpers for audit packets.
- Added 13 security-focused test modules (9 unit, 2 integration, 2 config/security regression) which raise the suite to 2,644 collected tests (`UV_CACHE_DIR=.uv-cache uv run pytest --collect-only --quiet`).

### Security
- Enforce encrypted credential flows: plaintext storage now raises `SecurityError`, and decrypts only succeed when the ciphertext fingerprint matches the active key.
- Bundled a software HSM provider plus adapters for Splunk HEC, Elastic SIEM, and Microsoft Sentinel so enterprise teams wire Importobot events into existing SOC pipelines without building glue code.
- The template scanner now reports issue type, line number, remediation guidance, and file hashes to match incident tickets back to the source artifact.
- Compliance reports include scoring per control, automatic next-assessment scheduling, and audit trail exports stored under `~/.importobot/compliance/`.

### Changed
- Replaced the previous `importobot.utils.security` helpers with dedicated modules (still re-exported for backward compatibility) to keep imports stable while isolating high-risk code paths.
- Refreshed documentation and packaging metadata to describe the new runtime dependency (`cryptography`) and to explain how to opt into the stronger security defaults.

## [0.1.4] - 2025-11-11

### Fixed
- **MongoDB Library Integration**: Replaced broken `robotframework-mongodblibrary` with modern `robot-mongodb-library` to resolve `ModuleNotFoundError: No module named 'mongo_connection_manager'`
- **Type Safety**: Fixed type checking errors in `base_generator.py` and `helpers.py` by properly converting `RobotFrameworkLibrary` enums to string values
- **Code Quality**: Fixed line length violation in `keywords_registry.py` by breaking long description string into multiple lines
- **Multi-Step Parsing**: Fixed 5 failing tests by updating filter patterns to include `SeleniumLibrary.*` prefixes, enabling proper parsing of library-prefixed commands
- **Unicode Compatibility**: Removed all non-ASCII characters from output messages and scripts, replacing Unicode symbols (✓, →, •, 🔬) with ASCII alternatives for maximum compatibility

### Changed
- **Library Generation**: Updated codebase generation mechanism to use `RobotMongoDBLibrary` instead of legacy `MongoDBLibrary` across pattern matcher and keyword registry
- **Keywords Registry**: Updated MongoDB function mappings to reflect actual available functions in the new library (`InsertOne`, `FindOneByID`, `Find`, `Update`, `DeleteOne`, `DeleteOneByID`)
- **Project Configuration**: Added `BENCHMARKS_DIR` constant to `importobot.config` for clean path management, replacing hacky `Path.parent.parent.parent.parent` patterns
- **Documentation Standards**: Enhanced TestRail client documentation with comprehensive docstring explaining Basic authentication vs Bearer token patterns
- **Test Data Quality**: Converted code notes to actionable TODO comments with GitHub issue references for traceability

### Added
- **Task Management**: Created GitHub issue #83 for implementing proper test data feeding system for P(E|¬H) learning pipeline
- **Cross-Reference Links**: Added clickable link to ADR-0006 in performance validation documentation
- **ASCII Output Standards**: Standardized all CLI output and script messages to use ASCII-only characters for cross-platform compatibility

## [Unreleased]

### Added
- **Test Suite Quality**: Improved test architecture by introducing 55 named constants across 9 categories, eliminating magic numbers.
- **Modern Test Patterns**: Updated test patterns by replacing `tempfile` with `pytest.tmp_path`, adding type annotations to all test functions, and documenting integration tests with Arrange-Act-Assert.
- **Consistent Type Safety**: Enforced mypy type checking across the entire test suite by removing test overrides.

### Changed
- **Template Security Enforcement**: `configure_template_sources()` now scans every `--robot-template` input using `TemplateSecurityScanner` and raises a `TemplateSecurityViolation` when `report.is_safe` is false, causing the CLI to exit instead of silently ingesting risky templates.
- **Client Module Refactoring**: Split `importobot.integrations.clients` into focused modules (base.py, jira_xray.py, testlink.py, testrail.py, zephyr.py) to enhance maintainability while retaining full backward compatibility.
- **Documentation Refinement**: Replaced subjective marketing language with factual, technical descriptions throughout the documentation.
- **API Client Modularity**: Implemented lazy loading for API clients, resulting in a 3x improvement in import speed while preserving all existing import paths.

### Removed
- **Legacy Compatibility Code**: Eliminated backwards compatibility shims no longer needed (Python < 3.8 support, deprecated logging and cache APIs).
- **Redundant Functions**: Removed `setup_logger()` and `get_cache_stats()` aliases in favor of unified APIs.

### Fixed
- **Test Infrastructure**: Fixed 24 syntax errors from incorrect type annotations and resolved environmental test failures using proper pytest fixtures.
- **Import Organization**: Corrected missing `Any` imports and standardized import patterns across test files.

### Technical Details
- **Test Quality**: All 1541 tests passed (100% pass rate) with comprehensive type checking.
- **Performance**: No performance regression was detected after module refactoring; lazy loading improved import times.
- **Architecture**: ADR-0006 was added to document client module refactoring decisions and performance validation.

## [Unreleased]

### Changed
- **Module Refactoring**: Split `importobot.integrations.clients` into focused modules for better maintainability
  - `base.py` - Shared API client functionality (BaseAPIClient, APISource protocol)
  - `jira_xray.py` - JIRA/Xray platform client
  - `testlink.py` - TestLink platform client
  - `testrail.py` - TestRail platform client
  - `zephyr.py` - Zephyr platform client
- **Test Quality Improvements**:
  - Added 55 named constants in `tests/test_constants.py` to eliminate magic numbers, organized into 9 logical categories with clear section markers
  - Replaced `tempfile` usage with pytest's `tmp_path` fixture (modern pattern)
  - Added type annotations (`-> None`) to all test functions
  - Added Arrange-Act-Assert comments to integration tests for clarity
  - Documented growth strategy: single-file approach until 200 constants, then split into sub-modules
- **Type Safety**: Removed mypy test override to enforce type checking across entire test suite
- **Documentation Cleanup**: Removed subjective marketing terms ("enterprise", "professional") in favor of factual descriptions

### Removed
- **Backwards Compatibility Code** (0.1.x has no external users):
  - Removed `importlib_metadata` fallback for Python < 3.8 (project requires Python 3.10+)
  - Removed `setup_logger()` function - use `get_logger()` instead
  - Removed `get_cache_stats()` alias - use `get_stats()` instead

### Breaking Changes

#### API Client Module Structure
**Old import paths:**
```python
from importobot.integrations.clients import (
    BaseAPIClient,
    ZephyrClient,
    JiraXrayClient,
    TestRailClient,
    TestLinkClient,
)
```

**New import paths (still supported):**
```python
# Public API (recommended)
from importobot.integrations.clients import (
    APISource,
    BaseAPIClient,
    ZephyrClient,
    JiraXrayClient,
    TestRailClient,
    TestLinkClient,
    get_api_client,
)

# Or import from specific modules (advanced use)
from importobot.integrations.clients.base import BaseAPIClient, APISource
from importobot.integrations.clients.zephyr import ZephyrClient
from importobot.integrations.clients.jira_xray import JiraXrayClient
from importobot.integrations.clients.testrail import TestRailClient
from importobot.integrations.clients.testlink import TestLinkClient
```

**Migration:** No action required if importing from `importobot.integrations.clients` - the `__init__.py` re-exports all public APIs.

#### Logging API
**Before:**
```python
from importobot.utils.logging import setup_logger
logger = setup_logger(__name__)
```

**After:**
```python
from importobot.utils.logging import get_logger
logger = get_logger(__name__)
```

**Migration:** Replace all `setup_logger()` calls with `get_logger()`. Function signature is identical.

#### Cache Statistics API
**Before:**
```python
cache = LRUCache(...)
stats = cache.get_cache_stats()

perf_cache = PerformanceCache()
stats = perf_cache.get_cache_stats()

detection_cache = DetectionCache()
stats = detection_cache.get_cache_stats()
```

**After:**
```python
cache = LRUCache(...)
stats = cache.get_stats()

perf_cache = PerformanceCache()
stats = perf_cache.get_stats()

detection_cache = DetectionCache()
stats = detection_cache.get_stats()
```

**Migration:** Replace all `.get_cache_stats()` calls with `.get_stats()`. Return value structure is unchanged.

### Fixed
- Fixed 24 syntax errors from incorrect type annotation replacements in test files
- Fixed missing `Any` import in `tests/unit/test_hash_file_example.py`
- Fixed environmental test failure in `test_resource_manager.py` by using pytest's `tmp_path` fixture instead of `/tmp`

### Technical Details
- Blueprint storage classes moved to `blueprints/storage.py` (StepPattern, SuiteSettings, etc.)
- Test suite: **1541/1541 tests passing (100% pass rate)**
- Mypy enforcement now applies to tests (removed `[[tool.mypy.overrides]]` for `tests.*`)
- Architecture Decision Record: `wiki/architecture/ADR-0006-client-module-refactoring.md`
- Performance validation: No regression detected, lazy loading provides 3x import speed improvement
  (see `wiki/architecture/performance-validation-module-split.md`)

## [0.1.3] - 2025-10-23

### Added
- Security regression tests (`tests/unit/test_api_security.py`) for API token masking, TLS flag handling, request verb injection, and rate limiter bypass.
- Hash/checksum steps now automatically generate Robot-friendly comparison commands, including multi-command expansion.
- Example `examples/json/hash_compare.json` demonstrating automatic comparison step generation via `--apply-suggestions`.
- `EvidenceMetrics` dataclass and regression coverage for the independent Bayesian scorer, validating ambiguity cap and posterior normalization.
- Benchmark artifacts (`wiki/benchmarks/`) for format-detection accuracy, latency, and regex cache performance.
- Environment flags (`IMPORTOBOT_SECURITY_RATE_MAX_QUEUE`, `IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE`, `IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX`) to tune the security gateway rate limiter.
- `wiki/architecture/Blueprint-Learning.md` documenting the blueprint learning pipeline and debugging tips.
- Configuration terminology guide in the README, clarifying the shift from "fallback" to "default/secondary" helpers.
- Pyright static analysis in CI for cross-checking mypy/ty results.
- **API Retrieval Integration** for Zephyr, TestRail, JIRA/Xray, and TestLink platforms, featuring:
  - A Zephyr client with automatic API discovery and adaptive authentication.
  - Multi-platform support for various APIs.
  - Flexible authentication (Bearer, API keys, Basic auth, dual-token).
  - Adaptive pagination with auto-detection of optimal page sizes.
  - Payload handling for diverse endpoint response structures.
  - Detailed progress reporting during large fetch operations.
  - Environment variable configuration for format-specific credentials.
  - Container and Kubernetes deployment examples.
  - Documentation on security best practices for API token management.

### Changed
- Blueprint registry now caches sanitized templates to disk and logs ingestion progress, preventing startup stalls with large template sets.
- LRU cache eviction improved with measured batches, warnings for pathological inserts, and prevention of unbounded eviction loops.
- Project ID validation now enforces signed 64-bit limits, raising `ConfigurationError` on overflow.
- `update_medallion_config` now lazily imports Medallion dependencies, avoiding circular imports and providing clear errors if the optional component is missing.
- CLI conversions no longer use blueprints by default; `--robot-template` must be supplied.
- Replaced the weighted evidence scorer with an independent Bayesian pipeline, capping ambiguous data at a 1.5:1 likelihood ratio.
- Hardened the rate limiter with queue caps and exponential backoff.
- Documentation updated to explain the removal of the `robot.utils` shim and to show empirical results from the new scorer.
- **CLI Interface**: Enhanced with `--fetch-format` and shared credential flags for API integration.
- **Documentation**: Improved across README.md, User Guide, and Deployment Guide with API integration examples.
- **Public API**: Extended with programmatic access to platform clients via `importobot.integrations.clients`.
- Split `blueprints.py` into modular components (`registry.py`, `models.py`, `utils.py`, `cli_builder.py`, `render.py`) with improved error reporting.
- Renamed helper APIs from "fallback" to "default/secondary" for consistent terminology.

### Removed
- Legacy `WeightedEvidenceBayesianScorer` entry points and their associated analysis scripts.

## [0.1.2] - 2025-10-21

### Added
- **Application Context**: Replaced global variables with a thread-local context for improved test isolation and dependency management.
- **Unified Caching**: Introduced `importobot.caching` module with LRU cache and security policies.
- **CLI Task Templates**: Implemented a cross-template learning system for extracting patterns from existing Robot files.
- **Schema Parser**: Added `importobot.core.schema_parser` for extracting field definitions from documentation.
- **File Operations Examples**: JSON examples for system administration tasks (hashing, config validation, security scanning).
- **API Examples**: New `wiki/API-Examples.md` with detailed usage patterns.
- **Architecture**: Added ADR-0004 for the Application Context Pattern.

### Fixed
- **Configuration Resilience**: Enhanced `_parse_project_identifier()` to handle control characters and whitespace-only inputs.
- **Project Resolution Defaults**: Improved default-selection logic so CLI arguments that don't parse to valid identifiers use environment variables instead.
- **Blueprint Learning Tests**: Fixed test issues with blueprint template system.
- **Test Coverage**: Achieved 1,946 tests passing with 0 skips after rewriting Zephyr client discovery test.

### Changed
- **Pylint Removal**: Dropped Pylint in favor of Ruff and Mypy for streamlined linting.
- **Documentation**: Rewrote 5 wiki files, replacing formulaic language and marketing terms with specific technical details and measured outcomes.
- **Bayesian Scoring**: Replaced the weighted evidence heuristic with proper Bayesian inference, capping ambiguous inputs at a 1.5:1 ratio based on ROC analysis.
- **Dependencies**: Removed `robot.utils` compatibility shim following Robot Framework updates.
- **Configuration Terminology**: Changed "fallback" to "default/secondary" helpers for consistency.

### Technical Details
- Added `raw.isspace()` check in configuration parsing for improved whitespace handling.
- Implemented thread-local context storage for concurrent instance support.
- Created a three-tier caching system with LRU cache for patterns, disk cache for templates, and session cache for API calls.
- Enhanced blueprint learning with cross-template pattern recognition.


## [0.1.1] - 2025-09-29

### Added
- **Medallion Architecture**: Implemented with bronze layer data processing for JSON ingestion, validation, and enrichment.
- **Bayesian Confidence Scoring**: For format detection, including mathematical foundations.
- **Multi-Format Support**: For Zephyr, Xray, TestLink, TestRail, and Generic test formats.
- **Validation Service**: With quality assessment and security gateway.
- **Invariant Testing**: Framework with 34 property-based tests using Hypothesis.
- **Performance Optimization**: Including caching and large-scale benchmarking.
- **Example Scripts**: For advanced features and CLI usage demonstrations.
- **MVLP Bayesian Confidence Scorer Test Suite**: 46 new tests achieving 78% coverage, including unit, integration, and property-based tests.

### Infrastructure
- Expanded test suite to 1539 tests (from 1493) covering format detection, confidence scoring, and API integration.
- Added mathematical foundations documentation for confidence algorithms.
- Enhanced CI/CD with improved GitHub Packages integration.
- Added performance benchmarking and demo capabilities.

### Changed
- Improved type annotations for better Mypy compatibility:
  - Fixed `complexity_analyzer.py` parameter type annotations (`int | None`).
  - Enhanced `confidence_calculator.py` type mapping for `isinstance` checks.
  - Updated `test_optimization.py` to use float types consistently.

### Fixed
- Fixed flaky `test_format_detection_scalability_invariant` by using `time.perf_counter()` instead of `time.time()`.
- Fixed type checking errors in MVLP Bayesian confidence implementation.
- Resolved 8 Mypy errors across 3 files.

### Removed
- **Internal Refactoring**: Removed unused `bayesian_confidence.py` (287 lines) in favor of `mvlp_bayesian_confidence.py`. This change had no public API impact, as the file was not part of the public API. `mvlp_bayesian_confidence.py` provides more sophisticated SciPy-based optimization, with active production use confirmed in `evidence_accumulator.py`.

### Quality Improvements
- Achieved a 10.00/10 Pylint score across the entire codebase.
- Fixed all validation issues, including `AttributeError` for non-string dictionary keys.
- Added type checking with Mypy (243 files clean).
- Implemented fail-fast principles throughout the architecture.
- Added shared test data structures to eliminate code duplication.

### Documentation
- Enhanced migration guide with clear breaking change documentation.
- Added API documentation following Pandas-inspired design patterns.
- Updated mathematical foundations documentation.

### Breaking Changes
- **Medallion Architecture**: Introduced with bronze/silver/gold layer separation. All data processing must now go through these medallion layers. There is no backward compatibility with pre-0.1.1 internal implementations, though the public API (`JsonToRobotConverter`, CLI) remains stable.
- **New Service Layer**: Implemented a new service layer for validation, security, and format detection. The security gateway is now required for all input validation, and the validation service provides unified quality assessment.
- **Internal API Surface**: Enhanced with new capabilities. Private modules (`importobot.core.*`, `importobot.medallion.*`) may change between minor versions; only public API modules are guaranteed stable.

## [0.1.0] - 2025-09-23

### Added
- **Initial release** of Importobot - a Test Framework Converter.
- **Core conversion engine** for transforming JSON test cases to Robot Framework.
- **Automated bulk processing** for hundreds or thousands of test cases.
- **Field mapping** with automatic detection of test steps, results, tags, and priorities.
- **Pandas-inspired API** with `JsonToRobotConverter` as the primary interface.
- **Toolkit** via `importobot.api` for validation, converters, and suggestions.
- **CLI interface** with the `importobot` command-line tool.
- **Security validation** including SSH parameter extraction and compliance checks.
- **Interactive demo system**.
- **Performance benchmarking** infrastructure for large-scale validation.
- **Modular architecture** with an extensible design for new input formats.
- **Test suite** with over 1150 tests and complete coverage.
- **API reference and usage examples**.

### Technical Features
- **Multi-format support** for Zephyr, JIRA/Xray, and TestLink.
- **Error handling** with fail-fast principles, validation, and security checks for SSH parameters.
- **Type safety** with full Mypy compliance and runtime type checking.
- **Code quality** achieving a 10.00/10.00 Pylint score with complete linting.
- **CI/CD integration** with GitHub Actions for automated testing and quality checks.
- **Package management** using modern `uv` tooling with lock file dependency management.

### Dependencies
- **Core**: Robot Framework ecosystem (SeleniumLibrary, SSHLibrary, RequestsLibrary, DatabaseLibrary).
- **Optional**: matplotlib, numpy, pandas for analytics and visualization features.
- **Development**: Testing and linting toolchain.
