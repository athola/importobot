# API Reference

Reference for Importobot's public API surface. Everything here is supported; anything under `importobot.core.*` or `importobot.medallion.*` is considered private.

**Looking for practical examples?** See [API Examples](API-Examples) for detailed usage patterns with the newest features.

## API Overview

Importobot provides two main API layers:

1.  **`importobot`**: The core package containing the main `JsonToRobotConverter` class, configuration settings, and custom exceptions.
2.  **`importobot.api`**: A collection of modules for more advanced use cases, such as CI/CD integration, custom validation, and experimental features.

The public API surface is designed to be stable, while internal modules (`core`, `medallion`, etc.) may change between releases. All public APIs are fully type-hinted for IDE support.

## Primary Interface

### `importobot`

The main package provides the following:

- **`JsonToRobotConverter`**: The core class for converting test exports. It has the following methods:
    - `convert_json_string(json_string: str) -> str`: Converts a JSON string to a Robot Framework string.
    - `convert_file(input_path: str, output_path: str) -> None`: Converts a single file.
    - `convert_directory(input_dir: str, output_dir: str) -> Dict[str, Any]`: Converts all files in a directory.

### `importobot.config`

This module provides access to global configuration settings.

- `MAX_JSON_SIZE_MB`: The maximum size of a JSON file that can be processed.
- `TEST_SERVER_URL`: The URL of the test server to be used for validation.
- `TEST_SERVER_PORT`: The port of the test server.
- `CHROME_OPTIONS`: A set of options for configuring the headless Chrome browser used in testing.

### `importobot.exceptions`

This module contains all custom exceptions raised by Importobot.

- `ImportobotError`: The base class for all Importobot exceptions.
- `ValidationError`: Raised when input data fails validation.
- `ConversionError`: Raised when an error occurs during the conversion process.
- `ParseError`: Raised when a file cannot be parsed.
- `FileNotFound`: Raised when a file cannot be found.
- `FileAccessError`: Raised when a file cannot be accessed.
- `SuggestionError`: Raised when an error occurs in the suggestion engine.

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


## Version Stability Promise

Importobot follows pandas-style API evolution:

- **Public API Stability**: `importobot.*` and `importobot.api.*` remain stable
- **Internal Implementation**: Core modules can be refactored without breaking public API
- **Deprecation Warnings**: Breaking changes include migration guidance
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


## Performance Considerations

- **Bulk Operations**: Use `convert_directory()` for hundreds/thousands of files
- **Memory Management**: Large files are managed within defined size limits
- **Parallel Processing**: Directory conversion uses efficient batching
- **Error Recovery**: Individual file failures don't stop batch processing
- **Bayesian Calculations**: Confidence scoring is O(1) per evaluation with optional Monte Carlo sampling for uncertainty quantification
