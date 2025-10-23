# API Reference

Reference for Importobot's public API surface. Everything here is supported; anything under `importobot.core.*` or `importobot.medallion.*` is considered private.

**Looking for practical examples?** See [API Examples](API-Examples) for detailed usage patterns with the newest features.

## API Architecture Overview

Importobot exposes two layers:
1. `import importobot` — core converter, config, and exceptions.
2. `importobot.api.*` — validation, suggestions, additional converters.

### Design notes

- Public imports stay stable; internal modules can change without notice.
- Type hints and `TYPE_CHECKING` guards provide IDE support.

## Public API Structure

```
importobot/
├── JsonToRobotConverter    # Core bulk conversion class
├── config                  # Configuration settings
├── exceptions              # Error handling
└── api/                    # Advanced API utilities
    ├── converters          # Advanced conversion engines
    ├── suggestions         # QA suggestion engine
    └── validation          # CI/CD validation utilities
```

### Internal Implementation (Private)
```
src/importobot/
├── cli/                    # Command-line interface (private)
├── core/                   # Core conversion logic (private)
├── utils/                  # Utility modules (private)
└── __main__.py            # Entry point
```

## Primary Interface

### JsonToRobotConverter

```python
import importobot

converter = importobot.JsonToRobotConverter()
```

- `convert_json_string(json_string: str) -> str` — Convert JSON text to Robot code.
- `convert_file(input_path: str, output_path: str) -> None` — Convert one file; creates the output directory when needed.
- `convert_directory(input_dir: str, output_dir: str) -> Dict[str, Any]` — Bulk conversion with success/error counts.

### Configuration

Access configuration settings:

```python
import importobot

# Configuration settings
max_size = importobot.config.MAX_JSON_SIZE_MB
test_url = importobot.config.TEST_SERVER_URL
chrome_options = importobot.config.CHROME_OPTIONS
```

#### Available Settings

- `MAX_JSON_SIZE_MB`: Maximum JSON file size (default: 10MB)
- `TEST_SERVER_URL`: Test server URL for validation
- `TEST_SERVER_PORT`: Test server port
- `CHROME_OPTIONS`: Headless browser configuration

### Exceptions

Example error handling:

```python
import importobot

try:
    importobot.JsonToRobotConverter().convert_file("test.json", "out.robot")
except importobot.exceptions.ValidationError:
    ...  # bad input
except importobot.exceptions.ConversionError:
    ...  # failure during generation
```

Key exceptions:
- `ImportobotError`
- `ValidationError`
- `ConversionError`
- `ParseError`
- `FileNotFound`
- `FileAccessError`
- `SuggestionError`

## Advanced API Utilities (importobot.api)

### importobot.api.converters

Advanced conversion engines for integration.

```python
from importobot.api import converters

# Access to advanced conversion engine
engine = converters.GenericConversionEngine()
result = engine.convert(test_data, config=custom_config)

# Direct access to main converter
converter = converters.JsonToRobotConverter()
```

#### Classes

**`GenericConversionEngine`**
- Low-level conversion engine with configuration options
- Supports custom keyword mapping and format options
- Used internally by `JsonToRobotConverter`

### importobot.api.validation

CI/CD validation utilities.

```python
from importobot.api import validation

# Validate JSON structure before conversion
validation.validate_json_dict(test_data)

# Security validation for file paths
validation.validate_safe_path(output_path)
```

#### Functions

**`validate_json_dict(data: dict) -> None`**
- Validates JSON structure and content
- Raises `ValidationError` on failure
- Checks required fields and data types

**`validate_safe_path(path: str) -> str`**
- Prevents directory traversal attacks
- Validates file path security
- Returns sanitized path

**`ValidationError`**
- Exception class for validation failures
- Provides detailed error messages
- Used throughout validation pipeline

### importobot.api.suggestions

QA suggestion engine for handling ambiguous test cases.

```python
from importobot.api import suggestions

# Handle problematic test cases
engine = suggestions.GenericSuggestionEngine()
fixes = engine.suggest_improvements(ambiguous_test_data)
```

#### Classes

**`GenericSuggestionEngine`**
- Analyzes problematic test cases
- Provides suggestions for improvements
- Handles ambiguous or incomplete test data

## API Client Error Handling

Importobot's HTTP clients (Zephyr, TestRail, Jira/Xray, TestLink) inherit from `BaseAPIClient` and raise familiar Python exceptions when requests fail.

- `requests.HTTPError` — raised by `response.raise_for_status()` for non-success status codes. Inspect `err.response.status_code` and `err.response.text` for remediation guidance.
- `RuntimeError("Exceeded retry budget ...")` — raised after the client retries the same request `_max_retries + 1` times (default: 3 retries). Wrap calls in your own retry loop if you need a longer budget.
- `ValueError("Unsupported fetch format ...")` — raised by `get_api_client` when the supplied `SupportedFormat` is not mapped to a client, or when an unsupported HTTP method is invoked.
- Standard `requests` exceptions (`ConnectionError`, `Timeout`, etc.) — bubbled up for network issues before any response is returned.

```python
import logging
import os
import requests
from importobot.exceptions import ConfigurationError
from importobot.integrations.clients import get_api_client, SupportedFormat

logger = logging.getLogger(__name__)

client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://zephyr.example.com",
    tokens=[os.environ["ZEPHYR_TOKEN"]],
    user=None,
    project_name="ENG-QA",
    project_id=None,
    max_concurrency=5,
    verify_ssl=True,
)

try:
    for page in client.fetch_all(progress_cb=lambda **kw: None):
        process_page(page)
except requests.HTTPError as err:
    logger.error(
        "Zephyr API request %s failed with %s",
        err.request.url,
        err.response.status_code,
    )
    raise
except RuntimeError as retry_err:
    logger.warning("Importobot exhausted built-in retries for %s", client.api_url)
    raise
except ValueError as config_err:
    raise ConfigurationError(f"Misconfigured API client: {config_err}") from config_err
```

> Tip: Only disable TLS verification (`verify_ssl=False`) in trusted development environments. Importobot logs a warning whenever verification is turned off.

## Business Use Cases

### 1. Bulk Conversion Pipeline

```python
import importobot

# Bulk conversion
converter = importobot.JsonToRobotConverter()
results = converter.convert_directory("/zephyr/exports", "/robot/tests")

print(f"Converted {results['success_count']} test cases")
print(f"Failed: {results['error_count']} files")
```

### 2. CI/CD Integration

```python
from importobot.api import validation, converters

# Validate before conversion in automated pipeline
validation.validate_json_dict(test_data)
validation.validate_safe_path(output_directory)

# Convert with error handling
converter = converters.JsonToRobotConverter()
try:
    result = converter.convert_json_string(json_data)
except Exception as e:
    # Log and handle conversion failures
    pass
```

### 3. QA Suggestion Engine

```python
from importobot.api import suggestions

# Handle ambiguous test cases
suggestion_engine = suggestions.GenericSuggestionEngine()

for test_case in problematic_tests:
    fixes = suggestion_engine.suggest_improvements(test_case)
    # Apply or review suggested improvements
```

## Version Stability Promise

Following pandas-style API evolution:

- **Public API Stability**: `importobot.*` and `importobot.api.*` remain stable across versions
- **Internal Implementation**: Core modules can be refactored freely without breaking public API
- **Deprecation Warnings**: Any breaking changes include migration guidance
- **Semantic Versioning**: Major.Minor.Patch versioning with clear upgrade paths

## Environment Variables

Configuration can be customized via environment variables:

- `IMPORTOBOT_TEST_SERVER_URL`: Test server URL (default: "http://localhost:8000")
- `IMPORTOBOT_MAX_JSON_SIZE_MB`: Maximum JSON file size in MB (default: "10")

Example:
```bash
export IMPORTOBOT_MAX_JSON_SIZE_MB=50
export IMPORTOBOT_TEST_SERVER_URL=https://testing.example.com
```

## Migration from Internal APIs

If you were previously using internal modules directly:

```python
# ❌ Old internal access (will break)
from importobot.core.engine import GenericConversionEngine
from importobot.utils.validation import validate_json_dict

# ✅ New public API (stable)
from importobot.api import converters, validation

engine = converters.GenericConversionEngine()
validation.validate_json_dict(data)
```

## Type Hints & IDE Support

Full type safety for development:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importobot.api import suggestions

# IDE autocomplete and type checking work correctly
engine: suggestions.GenericSuggestionEngine = ...
```

## Confidence Scoring API

Access the Bayesian confidence scoring system for advanced use cases:

### Bayesian Configuration

```python
from importobot.medallion.bronze.independent_bayesian_scorer import BayesianConfiguration

# Create custom configuration
config = BayesianConfiguration(
    min_evidence_not_format=0.01,      # Lower bound for P(E|¬H)
    evidence_not_format_scale=0.49,    # Scale factor for quadratic decay
    evidence_not_format_exponent=2.0,  # Quadratic decay exponent
    numerical_epsilon=1e-15,           # Division by zero prevention
)

# Validate configuration
if not config.validate():
    raise ValueError("Invalid Bayesian configuration")
```

### Evidence Metrics

```python
from importobot.medallion.bronze.evidence_metrics import EvidenceMetrics

# Create evidence metrics
metrics = EvidenceMetrics(
    completeness=0.8,    # Evidence coverage [0, 1]
    quality=0.9,         # Average confidence [0, 1]
    uniqueness=0.7,      # Normalized uniqueness [0, 1]
    evidence_count=15,   # Total evidence items [0, ∞)
    unique_count=8,      # Unique evidence items [0, ∞)
    complexity_score=0.2 # Optional complexity scaling [0, 1]
)
```

### Independent Bayesian Scoring

```python
from importobot.medallion.bronze.independent_bayesian_scorer import (
    IndependentBayesianParameters,
    IndependentBayesianScorer,
)

scorer = IndependentBayesianScorer(
    parameters=IndependentBayesianParameters(),
)

likelihood = scorer.calculate_likelihood(metrics)
posterior = scorer.calculate_posterior(
    likelihood=likelihood,
    format_name="TESTRAIL",
    metrics=metrics,
)

print(f"Likelihood: {likelihood:.3f}")
print(f"Posterior confidence: {posterior:.3f}")
```

### Parameter Customization

```python
from importobot.medallion.bronze.independent_bayesian_scorer import IndependentBayesianParameters

custom_parameters = IndependentBayesianParameters(
    quality_alpha=4.0,
    quality_beta=1.2,
    uniqueness_alpha=3.5,
    uniqueness_beta=1.2,
)

if not custom_parameters.validate():
    raise ValueError("Invalid Bayesian parameter configuration")
```

### Mathematical Constants Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_evidence_not_format` | 0.01 | Minimum P(E|¬H) for perfect evidence |
| `evidence_not_format_scale` | 0.49 | Scale factor for quadratic decay |
| `evidence_not_format_exponent` | 2.0 | Decay exponent (quadratic) |
| `numerical_epsilon` | 1e-15 | Division by zero prevention |

## Performance Considerations

- **Bulk Operations**: Use `convert_directory()` for hundreds/thousands of files
- **Memory Management**: Large files are managed within defined size limits
- **Parallel Processing**: Directory conversion uses efficient batching
- **Error Recovery**: Individual file failures don't stop batch processing
- **Bayesian Calculations**: Confidence scoring is O(1) per evaluation with optional Monte Carlo sampling for uncertainty quantification
