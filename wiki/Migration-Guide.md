# Migration Guide

This guide provides instructions for migrating between different versions of Importobot.

## 0.1.2 to 0.1.3

Version 0.1.3 introduced an application context pattern to replace global variables, a unified caching system, and a template learning system. No breaking changes were introduced.

- **Application Context Pattern**: Replaced global variables with a thread-local context for better test isolation.
- **Unified Caching System**: Added `importobot.caching` with an LRU cache.
- **JSON Template System**: Added a `--robot-template` flag to learn patterns from existing Robot files.
- **Schema Parser**: Added an `--input-schema` flag to extract field definitions from Markdown files.

## 0.1.1 to 0.1.2

Version 0.1.2 removed the legacy `WeightedEvidenceBayesianScorer`. If you imported it directly, switch to `FormatDetector` or `importobot.medallion.bronze.independent_bayesian_scorer.IndependentBayesianScorer`.

Rate limiting was improved with exponential backoff. The following environment variables can be used for tuning:

```bash
export IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=256
export IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2.0
export IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=8.0
```