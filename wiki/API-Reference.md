# API Reference

This document is the reference for Importobot's public API. All components described here are officially supported. Modules under `importobot.core.*` or `importobot.medallion.*` are internal and subject to change.

For practical examples, see [API Examples](API-Examples.md).

## API Overview

Importobot's API has three primary layers:

1.  **`importobot`**: The main package, containing the `JsonToRobotConverter` class, global configuration, and custom exceptions.
2.  **`importobot.api`**: Modules for advanced use cases like CI/CD integration, custom validation, and experimental features.
3.  **`importobot.security`**: New in 0.1.5; houses credential encryption, template scanning, HSM integration, SIEM connectors, and automated compliance helpers.

The public API is stable across releases. Internal modules (e.g., `core`, `medallion`) are subject to change. All public APIs include type hints for IDE support.

## Primary Interface

### `importobot`

The main `importobot` package provides the following core components:

-   **`JsonToRobotConverter`**: The central class for converting test exports. Key methods include:
    -   `convert_json_string(json_string: str) -> str`: Converts a JSON string to a Robot Framework string.
    -   `convert_file(input_path: str, output_path: str) -> None`: Converts a single input file to a Robot Framework file.
    -   `convert_directory(input_dir: str, output_dir: str) -> Dict[str, Any]`: Converts all supported files within a directory.

### `importobot.config`

This module provides access to global configuration settings:

-   `MAX_JSON_SIZE_MB`: Defines the maximum size (in MB) of a JSON file that can be processed.
-   `TEST_SERVER_URL`: Specifies the URL of the test server used for validation.
-   `TEST_SERVER_PORT`: Specifies the port of the test server.
-   `CHROME_OPTIONS`: A set of options for configuring the headless Chrome browser, primarily used in testing.

### `importobot.exceptions`

This module defines all custom exceptions raised by Importobot:

-   `ImportobotError`: The base class for all Importobot-specific exceptions.
-   `ValidationError`: Raised when input data fails validation checks.
-   `ConversionError`: Raised when an error occurs during the conversion process.
-   `ParseError`: Raised when an input file cannot be parsed.
-   `FileNotFound`: Raised when a specified file does not exist.
-   `FileAccessError`: Raised when a file cannot be accessed due to permissions or other issues.
-   `SuggestionError`: Raised when an error occurs within the suggestion engine.

## Advanced API Utilities (`importobot.api`)

### `importobot.api.converters`

This module provides advanced conversion engines for integration purposes.

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
-   A low-level conversion engine with many configuration options.
-   Supports custom keyword mapping and various format options.
-   Used internally by `JsonToRobotConverter`.

### `importobot.api.validation`

This module offers utilities for CI/CD and general data validation.

```python
from importobot.api import validation

# Validate JSON structure before conversion
validation.validate_json_dict(test_data)

# Security validation for file paths
validation.validate_safe_path(output_path)
```

#### Functions

**`validate_json_dict(data: dict) -> None`**
-   Validates the structure and content of JSON data.
-   Raises `ValidationError` upon failure.
-   Checks for required fields and correct data types.

**`validate_safe_path(path: str) -> str`**
-   Validates file paths to prevent directory traversal attacks.
-   Returns a sanitized path.

**`ValidationError`**
-   The exception class for validation failures.
-   Provides detailed error messages.
-   Used throughout the validation pipeline.

### `importobot.api.suggestions`

This module provides a suggestion engine for quality assurance, designed to handle ambiguous test cases.

```python
from importobot.api import suggestions

# Handle problematic test cases
engine = suggestions.GenericSuggestionEngine()
fixes = engine.suggest_improvements(ambiguous_test_data)
```

#### Classes

**`GenericSuggestionEngine`**
-   Analyzes problematic test cases.
-   Provides suggestions for improvements.
-   Handles ambiguous or incomplete test data.

## API Client Error Handling

Importobot's HTTP clients (for Zephyr, TestRail, Jira/Xray, TestLink), which inherit from `BaseAPIClient`, raise standard Python exceptions upon request failures.

-   `requests.HTTPError`: Raised by `response.raise_for_status()` for non-success status codes. Inspect `err.response.status_code` and `err.response.text` for remediation guidance.
-   `RuntimeError("Exceeded retry budget ...")`: Raised after the client exhausts its retry budget (default: 3 retries). Implement a custom retry loop for a longer budget.
-   `ValueError("Unsupported fetch format ...")`: Raised by `get_api_client` if the provided `SupportedFormat` is not mapped to a client, or if an unsupported HTTP method is invoked.
-   Standard `requests` exceptions (`ConnectionError`, `Timeout`, etc.): These exceptions are propagated for network issues occurring before a response is returned.

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

## Security Package (`importobot.security`)

The new security namespace keeps all security-critical components together.

### Credential Manager

```python
from importobot.security import CredentialManager

manager = CredentialManager()  # Requires cryptography + IMPORTOBOT_ENCRYPTION_KEY
encrypted = manager.encrypt_credential("super-secret-token")
token = manager.decrypt_credential(encrypted)
```

- Raises `SecurityError` if `cryptography` is missing or if it cannot fingerprint the configured key.

### Template Security Scanner

```python
from importobot.security import TemplateSecurityScanner

scanner = TemplateSecurityScanner()
report = scanner.scan_template_file("templates/smoke.robot")
if not report.is_safe:
    handle(report.issues)
```

- `report.issues` include line numbers, severity, and remediation strings to drive CI decisions.

### SIEM Connectors

```python
from importobot.security import create_splunk_connector, get_siem_manager

splunk = create_splunk_connector(
    host="https://splunk.example.com",
    token=os.environ["SPLUNK_HEC_TOKEN"],
)
manager = get_siem_manager()
manager.add_connector(splunk)
manager.start()
manager.send_security_event(security_event)
```

- Elastic and Microsoft Sentinel connectors expose the same interface; see `importobot/security/siem_integration.py`.

### Compliance Engine

```python
from importobot.security import get_compliance_engine, ComplianceStandard

engine = get_compliance_engine()
report = engine.assess_compliance(standard=ComplianceStandard.SOC_2)
report.export_csv("compliance/soc2.csv")
```

- Each report contains control-level scores, evidence references, and next-assessment timestamps stored under `~/.importobot/compliance/`.


## Version Stability Promise

Importobot follows a versioning model similar to Pandas:

-   **Public API Stability**: The public API (`importobot.*` and `importobot.api.*`) is stable.
-   **Internal Implementation**: Core modules may change between releases.
-   **Deprecation Warnings**: Breaking changes are announced with deprecation warnings and migration instructions.
-   **Semantic Versioning**: Versioning follows the Major.Minor.Patch convention.

## Environment Variables

Configuration can be customized using environment variables:

-   `IMPORTOBOT_TEST_SERVER_URL`: Specifies the test server URL (default: "http://localhost:8000").
-   `IMPORTOBOT_MAX_JSON_SIZE_MB`: Sets the maximum JSON file size in MB (default: "10").

Example:
```bash
export IMPORTOBOT_MAX_JSON_SIZE_MB=50
export IMPORTOBOT_TEST_SERVER_URL=https://testing.example.com
```

## Migration from Internal APIs

If you were previously accessing internal modules directly, please update your imports to use the public API:

```python
#  Old internal access (will break)
from importobot.core.engine import GenericConversionEngine
from importobot.utils.validation import validate_json_dict

#  New public API (stable)
from importobot.api import converters, validation

engine = converters.GenericConversionEngine()
validation.validate_json_dict(data)
```

## Type Hints & IDE Support

The API includes type hints for IDE support and static analysis:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importobot.api import suggestions

# IDE autocomplete and type checking work correctly
engine: suggestions.GenericSuggestionEngine = ...
```


## Performance Considerations

-   **Bulk Operations**: Use `convert_directory()` for processing many files.
-   **Memory Management**: File size limits are used to prevent high memory usage.
-   **Parallel Processing**: Directory conversion is parallelized by processing files in batches.
-   **Error Recovery**: An error on a single file does not halt a batch conversion.
-   **Bayesian Calculations**: Confidence scoring is O(1) per evaluation. Monte Carlo sampling is available for uncertainty quantification.
