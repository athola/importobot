# API Reference

This document outlines Importobot's modules, classes, and functions.

## Project Structure

```
src/importobot/
├── cli/                 # Command-line interface
│   ├── parser.py       # Argument parsing
│   └── handlers.py     # Command handlers
├── core/               # Core conversion logic
│   ├── engine.py       # Conversion engine
│   ├── converter.py    # File operations
│   └── parser.py       # Test case parsing
├── utils/              # Utility modules
└── __main__.py         # Entry point (55 lines)

tests/
├── unit/               # Unit tests (188)
├── integration/        # Integration tests (24)
└── cli/               # CLI tests (31)
```

## CLI Modules

### parser.py

Handles command-line argument parsing.

#### Functions

`parse_arguments()`
- Parses command-line arguments.
- Validates input files and directories.
- Returns a parsed arguments object.

### handlers.py

Contains logic for CLI operations.

#### Functions

`handle_conversion(input_path, output_path, batch_mode)`
- Handles file conversions.
- Processes single files or directories.
- Returns conversion status.

## Core Modules

### engine.py

The conversion engine that orchestrates the conversion process.

#### Classes

`ConversionEngine`
- Orchestrates file conversions.
- Methods:
  - `convert_test_case(test_data)`: Converts a single test case.
  - `process_batch(input_dir, output_dir)`: Processes multiple test cases in a directory.

#### Functions

`detect_required_libraries(test_steps)`
- Analyzes test steps to determine required Robot Framework libraries.
- Returns a list of library names.

### converter.py

Handles file loading and saving.

#### Functions

`load_json_file(file_path)`
- Loads and validates a JSON file.
- Returns parsed JSON data.

`save_robot_file(file_path, robot_content)`
- Saves Robot Framework content to a file.

`validate_safe_path(base_path, target_path)`
- Validates file paths to prevent directory traversal.
- Returns a validated path.

### parser.py

Parses input data with intent recognition.

#### Functions

`parse_test_case(json_data)`
- Parses test case data from JSON.
- Extracts test steps, descriptions, and expected results.
- Returns a structured test case object.

`extract_intent(step_description)`
- Analyzes a step description to identify intent.
- Returns the intent category and parameters.

`generate_robot_keywords(test_steps)`
- Generates Robot Framework keywords from intents.
- Returns a list of keyword strings.

## Utility Modules

### utils/file_operations.py

Provides utility functions for file operations.

#### Functions

`ensure_directory_exists(directory_path)`
- Creates a directory if it does not exist.
- Returns the directory path.

`get_file_extension(file_path)`
- Extracts the file extension from a path.
- Returns the extension as a string.

### utils/validation.py

Provides utility functions for data validation.

#### Functions

`validate_json_structure(json_data)`
- Validates a JSON structure against a schema.
- Raises `ValidationException` on failure.

`sanitize_robot_string(input_string)`
- Sanitizes strings for Robot Framework output.
- Prevents syntax errors.

## Exception Hierarchy

### ImportobotError
Base exception class for all Importobot errors.

### ValidationError
Raised when input validation fails.

### ConversionError
Raised when the conversion process fails.

### FileNotFoundError
Raised when a required file is not found.

## Configuration

### Environment Variables

`IMPORTOBOT_TEST_SERVER_URL`
- Default: "http://localhost:8000"
- Overrides the test server URL.

`IMPORTOBOT_TEST_SERVER_PORT`
- Default: "8000"
- Overrides the test server port.

`IMPORTOBOT_HEADLESS_BROWSER`
- Default: "False"
- Set to "True" to run Chrome in headless mode.
