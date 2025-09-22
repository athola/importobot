# API Reference

This document outlines Importobot's public API following pandas-inspired design patterns for enterprise integration.

## API Architecture Overview

Importobot provides a **two-tier API structure** designed for both simple usage and enterprise integration:

1. **Primary Interface**: `import importobot` - Core bulk conversion functionality
2. **Enterprise Toolkit**: `importobot.api.*` - Advanced features for CI/CD and QA teams

### Pandas-Inspired Design Principles

- **Clean Public Interface**: Simple imports for core functionality
- **Enterprise Toolkit**: Dedicated `api` module for advanced features
- **Version Stability**: Public API contracts remain stable across versions
- **Type Safety**: Full type hints and `TYPE_CHECKING` support
- **Professional Standards**: Follows industry best practices

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

The main class for bulk test case conversion.

```python
import importobot

converter = importobot.JsonToRobotConverter()
```

#### Methods

**`convert_json_string(json_string: str) -> str`**
- Converts JSON string directly to Robot Framework format
- Validates input JSON and handles parsing errors
- Returns generated Robot Framework code

**`convert_file(input_path: str, output_path: str) -> None`**
- Converts single JSON file to Robot Framework
- Handles file I/O and error reporting
- Creates output directory if needed

**`convert_directory(input_dir: str, output_dir: str) -> Dict[str, Any]`**
- Bulk converts entire directories of test cases
- Processes hundreds or thousands of files efficiently
- Returns conversion statistics and error reports

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

Comprehensive error handling for enterprise pipelines:

```python
import importobot

try:
    converter = importobot.JsonToRobotConverter()
    result = converter.convert_file("test.json")
except importobot.exceptions.ValidationError:
    # Input validation failed
except importobot.exceptions.ConversionError:
    # Conversion process failed
except importobot.exceptions.ParseError:
    # JSON parsing failed
```

#### Exception Hierarchy

- `ImportobotError`: Base exception for all errors
- `ValidationError`: Input validation failures
- `ConversionError`: Conversion process failures
- `ParseError`: JSON parsing failures
- `FileNotFound`: Missing file errors
- `FileAccessError`: File permission errors
- `SuggestionError`: Suggestion engine failures

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
