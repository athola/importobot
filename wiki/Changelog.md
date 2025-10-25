# Changelog

This page tracks recent changes and improvements to Importobot.

## Recent Changes (October 2025)

**ASV Performance Benchmarking**: Added ASV (Airspeed Velocity) to track performance across releases. Three benchmark suites measure conversion, memory usage, and bulk operations (~55ms detection time). CI automatically generates and publishes benchmark charts on tagged releases.

**Linting Consolidation**: Migrated from pylint to ruff/mypy-only workflow. Removed pylintrc, cleaned up ASV build artifacts, and updated to modern type hints (dict vs Dict for Python 3.9+).

**Tag-based Release Workflow**: PyPI publishing now triggers only on version tags (v*.*.*) instead of main branch pushes.

**Development Branch Workflow**: Development branch is now the integration target for all MRs. Main branch receives only tested releases.

### Version 0.1.3 Release

**Application Context Pattern**: Replaced global variables with thread-local context to fix test race conditions. Added `importobot.caching` module with unified LRU cache.

**Enhanced Template Learning**: Blueprint system learns from existing Robot files using `--robot-template` flag. Tested on 3 customer suites, reduced manual post-conversion editing by ~70%.

**Schema Parser**: Added `--input-schema` flag to read team documentation (SOPs, READMEs) for custom field naming conventions. Improved parsing accuracy from ~85% to ~95% on customer exports.

**Unified API Integration**: Enhanced `--fetch-format` supporting Zephyr, TestRail, JIRA/Xray, and TestLink with better detection and authentication.

**Documentation**: Added Migration Guide for 0.1.2→0.1.3 (no breaking changes) and Blueprint Tutorial.

### Previous Improvements

**Public API Formalization**: Stabilized pandas-style API surface with controlled `__all__` exports. Core implementation remains private while `importobot.api` provides a robust set of tools for integration.

**Template System**: The blueprint system learns from your existing Robot files. If you have a consistent way of writing test cases, Importobot will apply that pattern to new conversions. This replaced the old hardcoded templates.

**Format Detection**: Replaced the weighted heuristic scoring with proper Bayesian confidence calculation. The new system caps ambiguous ratios at 1.5:1 and applies penalties when required fields are missing.

**Test Generation**: Parameter conversion skips comment lines, so placeholders like `${USERNAME}` stay visible in traceability comments. Test cases now track both original and normalized names to handle cases involving control characters.

**Code Quality**: Removed pylint from the project (now using ruff/mypy only) and enhanced test isolation through automatic context cleanup.
