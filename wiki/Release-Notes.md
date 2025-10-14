# Release Notes

## v0.1.2 (October 2025)

**Release Date**: 2025-10-10
**Branch**: bronze-cleanup
**Status**: Ready for production

**Highlights**
- Bronze layer in-memory cache for 50-80% performance improvement on repeated queries
- Comprehensive validation performance optimization with adaptive thresholds
- Enhanced developer experience with fast-lint options and progress indicators
- Code organization improvements with restructured test utilities and benchmarks

**New Features**

### Bronze Layer In-Memory Cache
- Configurable in-memory cache for recently ingested records
- Default capacity: 1024 records (~1MB memory footprint)
- Optional TTL for cache expiration
- 50-80% performance improvement for repeated queries
- Graceful degradation when storage backend unavailable

**Configuration**:
```python
from importobot.medallion.bronze_layer import BronzeLayer

bronze = BronzeLayer(
    storage_path=Path("./storage"),
    storage_backend=storage_backend,
    max_in_memory_records=2048,    # Optional: customize cache size
    in_memory_ttl_seconds=300,     # Optional: 5-minute TTL
)
```

Environment variables:
- `IMPORTOBOT_BRONZE_MAX_IN_MEMORY_RECORDS` (default: 1024)
- `IMPORTOBOT_BRONZE_IN_MEMORY_TTL_SECONDS` (default: 0, disabled)

### Performance Optimization
- Added `make lint-fast` for quick pre-commit checks (~10 seconds)
- Full validation suite optimized and documented
- Validation pipeline timing breakdown added to wiki

### Code Organization
- Benchmark scripts reorganized into `benchmarks/` subpackage
- Test utilities restructured into focused modules:
  - `tests/utils/test_helpers.py` - Core test utilities
  - `tests/utils/performance_utils.py` - Performance testing tools
- Enhanced `performance_benchmark.py` (912 → 1078 lines)
- New `run_bronze_benchmark.py` for Bronze layer-specific benchmarks

**Improvements**

### Documentation
- Comprehensive Bronze layer cache configuration guide in Migration Guide
- Memory impact analysis with usage examples
- Default value rationale documented in config.py
- Validation performance section added to Performance Characteristics wiki
- CI/CD timing guidance in Deployment Guide

### Testing
- All 1833 tests passing
- 4 benchmark tests covering new functionality
- Property-based tests with Hypothesis
- Invariant tests for architectural guarantees
- Performance tests with adaptive thresholds

### Developer Experience
- Makefile targets include timing estimates
- Progress indicators during validation
- Fast-lint option for development workflow
- Clear error messages and logging

**Breaking Changes**
**None**. This release is fully backward compatible with v0.1.1.

**Migration Notes**
Upgrading from v0.1.0 or v0.1.1:
1. **No code changes required** - defaults preserve existing behavior
2. **Memory usage increase** - Budget ~1MB additional memory (default cache)
3. **Performance improvement** - Automatic 50-80% speedup for repeated queries
4. **Optional tuning** - Profile your workload and adjust if needed

**Breaking change for internal API users**:
If you were directly accessing `bronze._records` (private API), this has moved to `bronze._in_memory_records` with different structure. Use the public API `bronze.get_bronze_records()` instead.

**Bug Fixes**
- Fixed validation pipeline timeout issues (clarified expected 4-minute duration)
- Resolved test utilities module/package conflict
- Improved type safety with complete inline annotations

**Technical Details**

### Validation Performance
- Total time: ~4 minutes (240s)
- Breakdown: lint 120s (50%), test 100s (42%), typecheck 5s (2%), security 15s (6%)
- Pylint takes 95s for comprehensive static analysis (expected for codebase size)
- Use `make lint-fast` during development for 10-second checks

### Memory Impact
| Records | Memory | Use Case |
|---------|--------|----------|
| 512 | ~500KB | Small projects, CI pipelines |
| 1024 | ~1MB | Default - typical enterprise test suite |
| 2048 | ~2MB | Large organizations (5000+ tests) |
| 4096 | ~4MB | Very large test repositories |

### Code Quality
- 15,000+ lines of code across 144 source files + 120 test files
- All validation checks pass (ruff, pylint, pycodestyle, pydocstyle, mypy)
- No security issues detected (detect-secrets, bandit)
- 100% backward compatibility maintained

**What's Next (v0.1.2+)**
Planned improvements:
- Pre-commit hooks for faster feedback
- Pylint incremental mode for changed files only
- Additional load tests for cache eviction
- Concurrent access tests for thread safety

---

## v0.1.1 (September 2025)

**Highlights**
- Added medallion Bronze/Silver/Gold layers so raw exports, curated models, and Robot output each have their own checkpoints.
- Expanded format detection with a Bayesian confidence score and support for Xray, TestLink, TestRail, and a generic JSON path.
- Tightened up the CLI with argument validation and conversion strategy hooks; the same engine now powers the interactive demo.
- Extended the keyword libraries (SSH, API, database, web) and wired the suggestion engine into the standard conversion flow.

**Quality & tooling**
- Cleaned up `.gitignore`, added `make clean` / `make deep-clean`, and removed orphaned artifacts.
- Brought ruff, mypy, and pylint back to zero warnings; unused imports and long docstrings were fixed instead of silenced.
- Repaired flaky tests by restructuring shared fixtures and data files; the suite now runs 1,153 checks reliably.
- Documented every Makefile target in the help output after repeatedly rediscovering them.

**Infrastructure notes**
- Added uv-managed dependency locks and baseline Ansible/Terraform scripts for environments that need repeatable VM setup.
- Introduced shared utilities (`utils/data_analysis.py`, pattern extraction, step comments) to remove duplicate code across converters and demos.

**Interactive demo**
- New `scripts/interactive_demo.py` shows cost comparisons, performance data, and conversion walkthroughs. It reuses the same helpers as the CLI so behaviour stays aligned between sales demos and production runs.

**January 2025 cleanup (carried into this release)**
- Removed ~200 lines of legacy compatibility code, enforced public/private API boundaries with explicit `__all__`, and trimmed extra layers of indirection.
- Refreshed documentation (README, PLAN, CLAUDE, wiki) to match the current architecture.

## v0.1.0 (Initial Release - September 2025)

- **Zephyr JSON Support**: Convert Zephyr JSON test cases to Robot Framework format.
- **Batch Processing**: Convert multiple files or entire directories at once.
- **Intent-Based Parsing**: Pattern recognition for accurate conversion of test steps.
- **Automatic Library Detection**: Automatic detection and import of required Robot Framework libraries.
- **Input Validation**: JSON validation with detailed error handling.
- **Performance**: Converts typical Zephyr cases in under a second each.
- **Quality**: Ships with a comprehensive test suite and linting in CI.
- **Developer experience**: Modular CLI, better error messages, and type hints throughout.
- **Dependencies**: Managed via uv, with Dependabot watching the lockfile.
- **Security**: Path safety checks, input validation, string sanitization.
- **Examples**: User registration, file transfer, database/API, login, suggestions.
- **CI/CD**: Automated tests and quality gates.

## Previous Releases

### v0.0.1 - Early Development
- Basic Zephyr JSON to Robot Framework conversion.
- Simple command-line interface.
- Core conversion engine implementation.
- Initial test suite with basic functionality.
