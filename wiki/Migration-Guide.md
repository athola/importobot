# Migration Guide

This guide details the changes and necessary steps when migrating between different versions of Importobot.

## 0.1.3 to 0.1.4

Version 0.1.4 focused on improving code quality, refactoring internal module architecture, and enhancing type safety. This release includes some breaking changes due to the removal of deprecated APIs.

### Breaking Changes

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

#### Cache Statistics API
**Before:**
```python
cache = LRUCache(...)
stats = cache.get_cache_stats()
```

**After:**
```python
cache = LRUCache(...)
stats = cache.get_stats()
```

#### Module Structure (Optional Migration)
The `importobot.integrations.clients` module has been split into focused modules, but existing import paths continue to work:

```python
# This still works (no changes required)
from importobot.integrations.clients import ZephyrClient

# New more specific imports (optional)
from importobot.integrations.clients.zephyr import ZephyrClient
```

### Improvements
- **Test Suite**: The test suite now uses 55 named constants, replacing magic numbers, and adopts modern pytest patterns for improved readability and maintainability.
- **Type Safety**: Mypy now performs comprehensive type checking across the entire test suite, ensuring consistent code quality.
- **Performance**: Lazy loading of modules has improved import speed by 3x.
- **Documentation**: The project documentation has been enhanced with more factual and technical descriptions.

## 0.1.2 to 0.1.3

Version 0.1.3 introduced an application context pattern to replace global variables, a unified caching system, and a template learning system. This release contained no breaking changes.

- **Application Context Pattern**: Global variables were replaced with a thread-local context, improving test isolation and overall stability.
- **Unified Caching System**: A new `importobot.caching` module was introduced, providing a unified LRU cache for various internal operations.
- **Robot Template System**: The `--robot-template` flag was added, allowing Importobot to learn patterns from existing Robot Framework files for consistent output.
- **Schema-Aware Parsing**: The `--input-schema` flag was introduced, enabling the extraction of field definitions from Markdown files to guide parsing.

## 0.1.1 to 0.1.2

Version 0.1.2 removed the legacy `WeightedEvidenceBayesianScorer`. Users who directly imported this class should now use `FormatDetector` or `importobot.medallion.bronze.independent_bayesian_scorer.IndependentBayesianScorer`.

This version also introduced improved rate limiting with exponential backoff. The following environment variables can be used to tune its behavior:

```bash
export IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=256
export IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2.0
export IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=8.0
```