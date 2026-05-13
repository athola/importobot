# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

- `importobot.config.APIIngestConfig` now uses keyword-only construction
  with a private `_SecureTokenListView` for `tokens`. Positional
  construction (`APIIngestConfig(fetch_format, api_url, tokens, …)`)
  and direct list mutation (`config.tokens.append(...)`,
  `config.tokens[i] = "new"`) no longer work. Use the keyword form
  (`APIIngestConfig(fetch_format=..., api_url=..., tokens=[...])`)
  and rebuild the config when tokens change. See PR #90 review C4.

### Security

- Whole-word safe-keyword matching (PR #90 B2): the credential scanner
  no longer suppresses real credential values whose names happen to
  contain dictionary substrings like `test`, `foo`, `bar`.
  `test`/`foo`/`bar`/`baz`/`qux`/`xxx`/`yyy`/`zzz` are removed from
  `SAFE_KEYWORDS`; `example`/`placeholder`/`demo`/`mock`/etc. remain.
- `SecurityError` consolidated to a single class in
  `importobot.exceptions` (PR #90 B3/C5). Imports from
  `importobot.security`, `importobot.security.types`, and
  `importobot.services.security_gateway` now resolve to the same
  class - `except SecurityError` works regardless of import path.
- `SecurityValidator` and `CredentialManager` unified (PR #90 C6/C7).
  `importobot.utils.security` and `importobot.utils.credential_manager`
  remain importable but now re-export the canonical classes from
  `importobot.security`.
- `SecureString.__eq__` uses `hmac.compare_digest`; `__hash__` returns
  an HMAC-SHA256 derived value under a process-local key (PR #90 N5).
- `SecureString.zeroize()` now clears `_original_value` and
  `_normalized_value` so plaintext does not survive zeroization
  (PR #90 I1).
- Failed credential encryption now redacts the parameter value and
  raises a high-severity warning rather than leaving plaintext in the
  output (PR #90 C11).

### Added

- Packaged `src/importobot/data/intent_patterns.yaml` (PR #90 C3) so
  the YAML ships inside installed wheels. The previous
  `<repo_root>/config/intent_patterns.yaml` location crashed
  `PatternMatcher()` with `FileNotFoundError` in production installs.

### Changed

- `coverage-delta` CI job now actually fails when below the 60% gate
  (PR #90 B1). The previous `|| exit 0` trap was removed.
- SIEM stub connectors renamed to `LoggingSplunkSink` /
  `LoggingElasticSink` to make the simulated nature explicit
  (PR #90 C1). Old `SplunkHECConnector` / `ElasticConnector` names
  remain as aliases through 0.1.x and are scheduled for removal in
  0.2.0. Per-connector failures are now caught and logged so a single
  broken sink no longer prevents later sinks from receiving events.
- `SoftwareHSM` renamed to `InMemoryKeyStore` with explicit
  "NOT A REAL HSM" guidance and per-operation mutex (PR #90 C2).
  `SoftwareHSM` remains as an alias through 0.1.x.

### Removed

- `pyright` removed from dev dependencies (PR #90 N8). `make typecheck`
  uses `ty` + `mypy`; install pyright manually if you want to run it
  ad-hoc.
- `asv` no longer a production install dependency (PR #90 N1). It now
  lives only in the `dev` group.
- `pycodestyle` removed from `make lint` (PR #90 N3). `ruff`'s `E`/`W`
  rules cover the same checks at ~50x the speed.

## [0.1.5] - 2026-02-18

### Changed
- **Client Module Refactoring**: Split `importobot.integrations.clients` into focused modules for better maintainability
  - `base.py` - Shared API client functionality (BaseAPIClient, APISource protocol)
  - `jira_xray.py` - JIRA/Xray platform client
  - `testlink.py` - TestLink platform client
  - `testrail.py` - TestRail platform client
  - `zephyr.py` - Zephyr platform client
- **API Client Modularity**: Implemented lazy loading for API clients, resulting in a 3x improvement in import speed while preserving all existing import paths.
- **Test Quality Improvements**:
  - Added 55 named constants in `tests/test_constants.py` to eliminate magic numbers, organized into 9 logical categories with clear section markers
  - Replaced `tempfile` usage with pytest's `tmp_path` fixture (modern pattern)
  - Added type annotations (`-> None`) to all test functions
  - Added Arrange-Act-Assert comments to integration tests for clarity
  - Documented growth strategy: single-file approach until 200 constants, then split into sub-modules
- **Type Safety**: Removed mypy test override to enforce type checking across entire test suite
- **Documentation Cleanup**: Removed subjective marketing terms ("enterprise", "professional") in favor of factual descriptions
- **CI/CD Modernization**: Upgraded all workflows from `actions/checkout@v5` to `@v6`, added `config/**` to trigger paths
- **Security Workflow**: Migrated from pip to uv with top-level permissions block
- **Lint Target**: `make lint` now runs `ruff format --check` and `pycodestyle` in addition to `ruff check` and `pydocstyle`
- **Typecheck Target**: Removed `pyright` from `make typecheck` (mypy and ty remain)
- **CHANGELOG**: Consolidated duplicate `[Unreleased]` sections into one

### Added
- **Coverage Delta CI Job**: New `coverage-delta` workflow job measures test coverage on modified source files during PRs (60% minimum threshold)
- **Pre-commit**: Added `.pre-commit-config.yaml`, `pre-commit` dev dependency, and `.github/workflows/pre-commit.yml` CI workflow
- **Validate Target**: `make validate` now runs `pre-commit run --all-files` as a final check
- **Security Subsystem (`importobot.security`)**: New dedicated package consolidating credential management, scanner checks, secure memory pools, template scanning, and security validation. Replaces ad-hoc helpers previously scattered under `utils/`. Public surface includes `CredentialManager`, `TemplateSecurityScanner`, `SecurityValidator`, and `SecureString`.
- **Encrypted Credentials**: `CredentialManager` enforces Fernet encryption via the optional `security` extra (`pip install 'importobot[security]'`) and the `IMPORTOBOT_ENCRYPTION_KEY` environment variable. OS keyring storage supported via `IMPORTOBOT_KEYRING_SERVICE` / `IMPORTOBOT_KEYRING_USERNAME`.
- **Command Sanitization**: New `importobot.utils.command_security` module hardens shell command construction against injection.
- **International Token Support**: Token validation handles Unicode normalization with configurable placeholder lists (`IMPORTOBOT_TOKEN_PLACEHOLDERS`, `IMPORTOBOT_TOKEN_INDICATORS`, `IMPORTOBOT_MIN_TOKEN_LENGTH`).
- **Enterprise Add-ons (`importobot_enterprise`)**: Optional package via `pip install 'importobot[enterprise]'` exposing `SoftwareHSM`, `SIEMManager` with Splunk/Elastic/Sentinel connectors, `EnterpriseComplianceEngine` for SOC2/ISO27001 scoring, and `rotate_credentials()` for re-wrapping ciphertexts.
- **Wiki**: New [Key Rotation](wiki/Key-Rotation.md) and [SIEM Integration](wiki/SIEM-Integration.md) guides plus [ADR-0007](wiki/architecture/ADR-0007-secure-memory-pool-refactoring.md) covering the secure memory pool refactoring rationale.
- **Security Test Coverage**: 23 new test modules under `tests/unit/security/` and `tests/unit/enterprise/` covering credential patterns, scanner checks, secure memory, template scanning, SIEM forwarding, key rotation, and SOC2 scoring (test suite total: 2,860).

### Removed
- **Backwards Compatibility Code** (0.1.x has no external users):
  - Removed `importlib_metadata` fallback for Python < 3.8 (project requires Python 3.10+)
  - Removed `setup_logger()` function - use `get_logger()` instead
  - Removed `get_cache_stats()` alias - use `get_stats()` instead

### Fixed
- Fixed 24 syntax errors from incorrect type annotation replacements in test files
- Fixed missing `Any` import in `tests/unit/test_hash_file_example.py`
- Fixed environmental test failure in `test_resource_manager.py` by using pytest's `tmp_path` fixture instead of `/tmp`
- Corrected missing `Any` imports and standardized import patterns across test files

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

### Technical Details
- Blueprint storage classes moved to `blueprints/storage.py` (StepPattern, SuiteSettings, etc.)
- Test suite: **1541/1541 tests passing (100% pass rate)** at time of this work
- Mypy enforcement now applies to tests (removed `[[tool.mypy.overrides]]` for `tests.*`)
- Architecture Decision Record: `wiki/architecture/ADR-0006-client-module-refactoring.md`
- Performance validation: No regression detected, lazy loading provides 3x import speed improvement
  (see `wiki/architecture/performance-validation-module-split.md`)

## [0.1.4] - 2025-11-11

### Fixed
- **MongoDB Library Integration**: Replaced broken `robotframework-mongodblibrary` with modern `robot-mongodb-library` to resolve `ModuleNotFoundError: No module named 'mongo_connection_manager'`
- **Type Safety**: Fixed type checking errors in `base_generator.py` and `helpers.py` by properly converting `RobotFrameworkLibrary` enums to string values
- **Code Quality**: Fixed line length violation in `keywords_registry.py` by breaking long description string into multiple lines
- **Multi-Step Parsing**: Fixed 5 failing tests by updating filter patterns to include `SeleniumLibrary.*` prefixes, enabling proper parsing of library-prefixed commands
- **Unicode Compatibility**: Removed all non-ASCII characters from output messages and scripts, replacing Unicode symbols with ASCII alternatives for maximum compatibility

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
  - An enhanced Zephyr client with automatic API discovery and adaptive authentication.
  - Multi-platform support for various APIs.
  - Flexible authentication (Bearer, API keys, Basic auth, dual-token).
  - Adaptive pagination with auto-detection of optimal page sizes.
  - Robust payload handling for diverse endpoint response structures.
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
- **Advanced Bayesian Confidence Scoring**: For format detection, including mathematical foundations.
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
- **Intelligent field mapping** with automatic detection of test steps, results, tags, and priorities.
- **Pandas-inspired API** with `JsonToRobotConverter` as the primary interface.
- **Toolkit** via `importobot.api` for validation, converters, and suggestions.
- **CLI interface** with the `importobot` command-line tool.
- **Security validation** including SSH parameter extraction and compliance checks.
- **Interactive demo system** with business case visualization and ROI calculations.
- **Performance benchmarking** infrastructure for large-scale validation.
- **Modular architecture** with an extensible design for new input formats.
- **Quality assurance** with 1153+ tests achieving complete coverage.
- **Documentation** with a complete API reference and usage examples.

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
