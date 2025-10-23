# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Security regression tests covering API token masking, TLS flag handling, request verb injection, and rate limiter bypass attempts (`tests/unit/test_api_security.py`).
- Hash/checksum steps now auto-generate Robot-friendly comparison commands instead of leaving placeholders, including multi-command expansion via the multi-command parser.
- Added `examples/json/hash_compare.json` to demonstrate automatic comparison step generation via `--apply-suggestions`.
- `EvidenceMetrics` dataclass plus additional regression coverage (`tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`, `tests/unit/medallion/bronze/test_independent_bayesian_scorer.py`) that holds the independent Bayesian scorer to the 1.5:1 ambiguity cap and validates posterior normalization.
- Benchmark artifacts under `wiki/benchmarks/` covering format-detection accuracy, detection latency, and regex cache performance.
- Environment flags (`IMPORTOBOT_SECURITY_RATE_MAX_QUEUE`, `IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE`, `IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX`) to tune the security gateway rate limiter.
- `wiki/architecture/Blueprint-Learning.md` documenting the blueprint learning pipeline and debugging tips.
- Configuration terminology guide in the README describing the shift from "fallback" helpers to "default" helpers.
- Pyright static analysis in CI for cross-checking mypy/ty results.
- **API Retrieval Integration** with support for Zephyr, TestRail, JIRA/Xray, and TestLink platforms:
  - **Enhanced Zephyr Client** with automatic API discovery and adaptive authentication strategies
  - **Multi-Platform Support** for Jira/Xray, Zephyr for Jira, TestRail, and TestLink APIs
  - **Flexible Authentication** supporting Bearer tokens, API keys, Basic auth, and dual-token setups
  - **Adaptive Pagination** with auto-detection of optimal page sizes based on server limits
  - **Robust Payload Handling** supporting diverse endpoint response structures
  - **Progress Feedback** with detailed reporting during large fetch operations
  - **Environment Variable Configuration** with format-specific credential management
  - **Container and Kubernetes Deployment** examples for production environments
  - **Security Best Practices** documentation for API token management and monitoring

### Changed
- CI enforces a minimum pytest collection count via `scripts/devtools/check_test_count.py` to keep reported coverage numbers honest.
- Blueprint registry now caches sanitised templates to disk and logs ingestion progress so large template sets no longer stall startup.
- LRU cache evicts in measured batches, warns on pathological inserts, and avoids unbounded eviction loops.
- Project ID validation now enforces signed 64-bit limits (raising `ConfigurationError` when exceeded) and documents the constraint.
- `update_medallion_config` now imports its Medallion dependency lazily to avoid circular imports and surfaces a clear error when the optional component is absent.
- CLI conversions no longer use blueprints unless `--robot-template` is supplied (or explicitly forced), keeping default renders free of remote/CLI assumptions.
- Blueprint registry now caches sanitised templates to disk and logs ingestion progress so large template sets no longer stall startup.
- Replaced the weighted evidence scorer with the independent Bayesian pipeline. Evidence penalties are now explicit constants and ambiguous data is capped at a 1.5:1 likelihood ratio.
- Hardened the rate limiter with queue caps and exponential backoff; cleaned up the README and wiki to describe the migration path.
- Updated documentation to explain the removal of the `robot.utils` shim and to show empirical results from the new scorer.
- **Enhanced CLI Interface** with `--fetch-format` parameter and shared credential flags for API integration
- **Improved Documentation** across README.md, User Guide, and Deployment Guide with API integration examples
- **Extended Public API** with programmatic access to platform clients via `importobot.integrations.clients`
- Split `blueprints.py` into modular components (`registry.py`, `models.py`, `utils.py`, `cli_builder.py`, `render.py`) with hardened ingestion error reporting.
- Renamed helper APIs from "fallback" to "default/secondary" to keep terminology consistent with configuration defaults.

### Removed
- Legacy `WeightedEvidenceBayesianScorer` entry points and the analysis scripts that referred to it.

## [0.1.2] - 2025-10-21

### Added
- **Application Context Pattern**: Replaced global variables with thread-local application context for better test isolation and dependency management
- **Unified Caching System**: New `importobot.caching` module with LRU cache implementation and security policies
- **JSON-based CLI Task Templates**: Cross-template learning system that extracts patterns from existing Robot files
- **Schema Parser**: New `importobot.core.schema_parser` for extracting field definitions from documentation
- **Enhanced File Operations**: JSON examples for system administration tasks including file hashing, configuration validation, and security scanning
- **API Examples Documentation**: New `wiki/API-Examples.md` with detailed usage patterns
- **Architecture Documentation**: Added ADR-0004 for Application Context Pattern

### Fixed
- **Configuration Resilience**: Enhanced `_parse_project_identifier()` to handle control characters and whitespace-only inputs
- **Project Resolution Defaults**: Improved default-selection logic so CLI arguments that don't parse to valid identifiers use environment variables instead
- **Blueprint Learning Tests**: Fixed test issues with blueprint template system
- **Test Coverage**: Achieved 1,946 tests passing with 0 skips after rewriting Zephyr client discovery test

### Changed
- **Removed Pylint**: Dropped pylint from project, now using ruff/mypy only for streamlined linting
- **Documentation**: Rewrote 5 wiki files to remove formulaic openings and marketing language; replaced with specific technical details and measured outcomes
- **Bayesian Scoring**: Replaced weighted evidence heuristic with proper Bayesian inference; ambiguous inputs capped at 1.5:1 ratio based on ROC analysis of 200 test files
- **Dependencies**: Removed `robot.utils` compatibility shim after Robot Framework updates
- **Configuration Terminology**: Changed from "fallback" to "default/secondary" helpers for consistency

### Technical Details
- Added `raw.isspace()` check in configuration parsing for better whitespace handling
- Implemented thread-local context storage for concurrent instance support
- Created three-tier caching system with LRU cache for patterns, disk cache for templates, and session cache for API calls
- Enhanced blueprint learning with cross-template pattern recognition

## [0.1.1] - 2025-09-29

### Added
- **Medallion Architecture Implementation** with bronze layer data processing supporting JSON ingestion, validation, and enrichment
- **Advanced Bayesian Confidence Scoring** for format detection with mathematical foundations
- **Multi-Format Support** for Zephyr, Xray, TestLink, TestRail, and Generic test formats
- **Validation Service** with quality assessment and security gateway
- **Invariant Testing Framework** with 34 property-based tests using Hypothesis
- **Performance Optimization** with caching and enterprise-scale benchmarking
- **Example Scripts** for advanced features and CLI usage demonstrations
- **Test suite for MVLP Bayesian Confidence Scorer** with 46 new tests achieving 78% coverage
  - Unit tests for `ConfidenceParameters`, `EvidenceMetrics`, and `MVLPBayesianConfidenceScorer`
  - Integration tests for end-to-end confidence calculation workflows
  - Property-based tests for parameter optimization and constraint validation

### Infrastructure
- Expanded test suite to **1539 tests** (1493 → 1539) covering format detection, confidence scoring, and API integration
- Added **mathematical foundations documentation** for confidence algorithms
- Enhanced CI/CD with improved GitHub Packages integration
- Added performance benchmarking and enterprise demo capabilities

### Changed
- Improved type annotations for better mypy compatibility
  - Fixed `complexity_analyzer.py` parameter type annotations (`int | None`)
  - Enhanced `confidence_calculator.py` type mapping for `isinstance` checks
  - Updated `test_optimization.py` to use float types consistently

### Fixed
- Fixed flaky `test_format_detection_scalability_invariant` by using `time.perf_counter()` instead of `time.time()`
- Fixed type checking errors in MVLP Bayesian confidence implementation
- Resolved 8 mypy errors across 3 files

### Removed
- **Internal refactoring**: Removed unused `bayesian_confidence.py` (287 lines) in favor of canonical `mvlp_bayesian_confidence.py`
  - No public API impact - file was never part of the public API or committed to repository
  - `mvlp_bayesian_confidence.py` provides more sophisticated scipy-based optimization
  - Active production use confirmed in `evidence_accumulator.py`

### Quality Improvements
- Achieved **10.00/10 pylint score** across entire codebase
- Fixed all validation issues including AttributeError for non-string dictionary keys
- Added type checking with mypy (243 files clean)
- Implemented fail-fast principles throughout the architecture
- Added shared test data structures to eliminate code duplication

### Documentation
- Enhanced migration guide with clear breaking change documentation
- Added API documentation following pandas-inspired design patterns
- Updated mathematical foundations documentation

### Breaking Changes
- **BREAKING**: Introduced medallion architecture with bronze/silver/gold layer separation
  - All data processing must go through medallion layers
  - No backwards compatibility with pre-0.1.1 internal implementations
  - Public API (`JsonToRobotConverter`, CLI) remains stable
- **BREAKING**: New service layer with validation, security, and format detection
  - Security gateway now required for all input validation
  - Validation service provides unified quality assessment
- **BREAKING**: Enhanced internal API surface with enterprise-focused capabilities
  - Private modules (`importobot.core.*`, `importobot.medallion.*`) may change between minor versions
  - Only public API modules are guaranteed stable

## [0.1.0] - 2025-09-23

### Added
- **Initial release** of Importobot - Test Framework Converter
- **Core conversion engine** for transforming test cases from JSON format to Robot Framework
- **Automated bulk processing** for handling hundreds or thousands of test cases
- **Intelligent field mapping** with automatic detection of test steps, expected results, tags, and priorities
- **Pandas-inspired API** with `JsonToRobotConverter` as the primary interface
- **Enterprise toolkit** via `importobot.api` module for validation, converters, and suggestions
- **CLI interface** with `importobot` command-line tool
- **Security validation** with SSH parameter extraction and security compliance checks
- **Interactive demo system** with business case visualization and ROI calculations
- **Performance benchmarking** infrastructure for enterprise-scale validation
- **Modular architecture** with extensible design for supporting additional input formats
- **Quality assurance** with 1153+ tests achieving complete coverage
- **Professional documentation** with complete API reference and usage examples

### Technical Features
- **Multi-format support** for Zephyr, JIRA/Xray, and TestLink test management systems
- **Error handling** with fail-fast principles and comprehensive validation
- **Type safety** with full mypy compliance and runtime type checking
- **Code quality** achieving 10.00/10.00 pylint score with complete linting
- **CI/CD integration** with GitHub Actions for automated testing and quality checks
- **Package management** using modern uv tooling with lock file dependency management

### Dependencies
- **Core**: Robot Framework ecosystem (SeleniumLibrary, SSHLibrary, RequestsLibrary, DatabaseLibrary)
- **Optional**: matplotlib, numpy, pandas for analytics and visualization features
- **Development**: Testing and linting toolchain
