# Migration Guide

This guide details the changes and necessary steps when migrating between different versions of Importobot.

## 0.1.4 to 0.1.5

Version 0.1.5 adds a first-class security package without breaking the existing public API, but you must wire up the new defaults if you want encrypted credentials or SIEM forwarding.

### Dependency Changes
- `cryptography` moved to an optional extra so lightweight installations stay slim. Install it explicitly when you need encryption:

```bash
pip install 'importobot[security]'
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

### Token Handling Changes
- `APIIngestConfig.tokens` now stores `SecureString` instances instead of raw strings. Prefer `config.get_token(index)`, `config.get_all_tokens()`, or `config.secure_tokens`.
- Temporarily accessing plaintext tokens is possible via `config.plaintext_tokens`, which emits a `DeprecationWarning` and keeps tokens zeroizable.
- Set `IMPORTOBOT_MIN_TOKEN_LENGTH` (default `12`, hard minimum `8`), `IMPORTOBOT_TOKEN_PLACEHOLDERS`, or `IMPORTOBOT_TOKEN_INDICATORS` to tune validation rules, or `IMPORTOBOT_SKIP_TOKEN_VALIDATION=1` when running trusted benchmarks.
- Enterprise-only modules (`importobot_enterprise.*`) are now distributed separately. Install
  them with `pip install 'importobot[enterprise]'` to access SIEM connectors, the HSM helper,
  and the key rotation utilities.

### Required When Using `importobot.security`
1. **Install cryptography**: `uv sync` already pulls `cryptography>=42.0.0`. If you deploy from a trimmed image, run `pip install cryptography`.
2. **Export a Fernet key**: `CredentialManager` fails closed unless `IMPORTOBOT_ENCRYPTION_KEY` contains a 32-byte key.

```bash
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

### Opting Into the New Modules

#### Credential Encryption

```python
from importobot.security import CredentialManager

manager = CredentialManager()
encrypted = manager.encrypt_credential(os.environ["ZEPHYR_TOKEN"])
store(encrypted.ciphertext)
```

- Reason: the old `importobot.utils.security` helpers are now thin re-exports of this package; migrate to avoid future deprecation.

#### Template Security Checks

```python
from importobot.security import TemplateSecurityScanner

report = TemplateSecurityScanner().scan_template_file("templates/login.robot")
if not report.is_safe:
    fail_build(report.issues)
```

- Use before `--robot-template` conversions so credential leaks and suspicious variables fail fast.

#### SIEM / Compliance Hooks

```python
from importobot.security import create_splunk_connector, get_siem_manager

manager = get_siem_manager()
manager.add_connector(create_splunk_connector(
    host="https://splunk.example.com",
    token=os.environ["SPLUNK_HEC_TOKEN"],
))
manager.start()
```

- Connectors exist for Splunk, Elastic, and Sentinel; each enforces TLS and logs failures with context.

### Validation Checklist
- Run `UV_CACHE_DIR=.uv-cache uv run pytest --collect-only --quiet` to confirm the security-focused tests (13 new modules) load on your platform.
- Verify that CI/CD logs include the new `security` logger entries so audit teams can trace template scans, credential decryptions, and SIEM forwarding attempts.

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
- **Type Safety**: Mypy now checks types across the entire test suite, which helps maintain code quality.
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
