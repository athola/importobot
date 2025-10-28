# Migration Guide

This guide provides instructions for migrating between different versions of Importobot.

## Migrating from 0.1.2 to 0.1.3

Version 0.1.3 adds significant architectural enhancements, new features, and documentation cleanup. No breaking changes were introduced.

**New architecture:**
- **Application Context Pattern**: Replaced global variables with thread-local context to improve test isolation
- **Unified Caching System**: New `importobot.caching` module with LRU cache implementation

**New features:**
- **JSON Template System**: Learns patterns from your existing Robot files via `--robot-template` flag
- **Schema Parser**: Extracts field definitions from your documentation via `--input-schema` flag
- **Improved File Operations**: More JSON examples for system administration tasks
- **API Examples**: New usage examples in `wiki/API-Examples.md`

**Configuration improvements:**
- Better handling of control characters and whitespace in project identifiers
- CLI arguments that don't parse as valid identifiers default to environment variables

**Code quality:**
- Removed pylint (now using ruff/mypy only)
- Cleaned up documentation to remove AI-generated content patterns
- All 1,946 tests pass with 0 skips

## Migrating from 0.1.1 to 0.1.2

Version 0.1.2 removes the legacy `WeightedEvidenceBayesianScorer`. If you imported it
directly, switch to `FormatDetector` or the new
`importobot.medallion.bronze.independent_bayesian_scorer.IndependentBayesianScorer`.
The behaviour is covered by `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`.

Security rate limiting was improved with exponential backoff. Existing deployments work
unchanged, but can be tuned with:

```bash
export IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=256
export IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2.0
export IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=8.0
```