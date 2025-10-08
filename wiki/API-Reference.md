# API Reference

Reference for Importobot’s public API surface. Everything here is supported; anything under `importobot.core.*` or `importobot.medallion.*` is considered private.

## API Architecture Overview

Importobot exposes two layers:
1. `import importobot` — core converter, config, and exceptions.
2. `importobot.api.*` — validation, suggestions, additional converters.

### Design notes

- Public imports stay stable; internal modules can change without notice.
- Type hints and `TYPE_CHECKING` guards keep IDE support strong.

## Public API Structure

```
importobot/
├── JsonToRobotConverter    # Core bulk conversion class
├── config                  # Enterprise configuration
├── exceptions              # Comprehensive error handling
└── api/                    # Enterprise toolkit
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

Access enterprise configuration settings:

```python
import importobot

# Enterprise configuration
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

## Enterprise Toolkit (importobot.api)

### importobot.api.converters

Advanced conversion engines for enterprise integration.

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

CI/CD pipeline validation utilities.

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
- Provides intelligent suggestions for improvements
- Handles ambiguous or incomplete test data

## Business Use Cases

### 1. Bulk Conversion Pipeline

```python
import importobot

# Enterprise bulk conversion
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

- **Public API Contracts**: `importobot.*` and `importobot.api.*` remain stable across versions
- **Internal Implementation**: Core modules can be refactored freely without breaking public API
- **Deprecation Warnings**: Any breaking changes include migration guidance
- **Semantic Versioning**: Major.Minor.Patch versioning with clear upgrade paths

## Environment Variables

Enterprise configuration can be customized via environment variables:

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
- **Memory Management**: Large files automatically handled within size limits
- **Parallel Processing**: Directory conversion uses efficient batching
- **Error Recovery**: Individual file failures don't stop batch processing
