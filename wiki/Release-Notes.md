# Release Notes

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
