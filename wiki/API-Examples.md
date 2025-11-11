# API Examples

This page provides practical examples for using Importobot's Python API programmatically.

## Basic Conversion

### Converting a single file

```python
import importobot

# Initialize the converter
converter = importobot.JsonToRobotConverter()

# Convert a single Zephyr JSON export to a Robot Framework file
summary = converter.convert_file("zephyr_export.json", "output.robot")

print(f"Converted {summary['test_cases']} test cases")
print(f"Output written to {summary['output_file']}")
```

### Converting a directory

```python
import importobot

# Initialize the converter
converter = importobot.JsonToRobotConverter()

# Convert all JSON files in the 'exports' directory to the 'robot_tests' directory
result = converter.convert_directory("./exports/", "./robot_tests/")

print(f"Processed {result['files_processed']} files")
print(f"Generated {result['test_cases_generated']} test cases")
print(f"Errors: {len(result['errors'])}")
```

## API Integration

Importobot can fetch test data directly from various test management systems. For more details on configuring API integration, refer to the [User Guide on Fetching Data from an API](User-Guide.md#fetching-data-from-an-api).

### Fetching from Zephyr

```python
import os
from importobot.integrations.clients import get_api_client, SupportedFormat

# Get an API client for Zephyr
client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://your-zephyr.example.com",
    tokens=[os.environ.get("ZEPHYR_TOKEN", "your-api-token")], # Use environment variable or placeholder
    project_name="PROJECT_KEY",
)

test_cases = []
# Fetch all pages of test cases
for payload in client.fetch_all():
    test_cases.extend(payload.get('testCases', []))

print(f"Retrieved {len(test_cases)} test cases")
```

### Fetching from TestRail

```python
import os
import importobot
from importobot.integrations.clients import get_api_client, SupportedFormat

# Get an API client for TestRail
client = get_api_client(
    SupportedFormat.TESTRAIL,
    api_url="https://testrail.example.com/api/v2",
    tokens=[os.environ.get("TESTRAIL_TOKEN", "testrail-api-token")], # Use environment variable or placeholder
    user=os.environ.get("TESTRAIL_USER", "automation@example.com"), # Use environment variable or placeholder
    project_name="QA",
)

# Fetch data for a specific test run
run_data = client.fetch_run(run_id=42)

# Convert the fetched data
converter = importobot.JsonToRobotConverter()
result = converter.convert_json_dict(run_data)

# Write the converted data to a Robot Framework file
with open("testrail_suite.robot", "w") as f:
    f.write(result)
```

## Advanced Conversion

### Schema-Driven Conversion

For test exports with custom field names, you can provide a schema file to map them to the standard names that Importobot expects. See the [User Guide on Schema Mapping](User-Guide.md#mapping-custom-field-names) for a detailed explanation.

```python
import importobot
from importobot.core.schema_parser import SchemaParser

# Parse the schema definition from a Markdown file
schema_parser = SchemaParser()
field_definitions = schema_parser.parse_markdown("docs/test_field_guide.md")

# Initialize the converter with the custom schema
converter = importobot.JsonToRobotConverter(field_schema=field_definitions)

# Convert the export using the defined schema
result = converter.convert_file("export.json", "output.robot")
```

### Template-Based Conversion

Importobot can learn from your existing Robot Framework files to ensure new conversions match your team's style.

```python
import importobot
from importobot.core.templates.blueprints import BlueprintManager

# Learn patterns from an existing directory of Robot Framework tests
blueprint_manager = BlueprintManager()
blueprint_manager.learn_from_directory("./existing_robot_tests/")

# Initialize the converter with the learned blueprints
converter = importobot.JsonToRobotConverter(blueprint_manager=blueprint_manager)

# Convert a new export, applying the learned style
result = converter.convert_file("new_export.json", "converted.robot")
```

## Validation and Suggestions

### Input Validation

Use the `validation` module to validate your JSON data before conversion.

```python
from importobot.api import validation

test_data = {"some": "json_data"} # Replace with actual test data

try:
    validation.validate_json_dict(test_data)
    print("Data is valid")
except validation.ValidationError as e:
    print(f"Validation error: {e}")
```

### Improvement Suggestions

The `suggestions` module can analyze your test cases and provide recommendations for potential improvements, such as identifying ambiguous steps or suggesting more robust keyword usage.

```python
from importobot.api import suggestions

# Assume 'problematic_tests' is a list of test case objects
problematic_tests = [] # Populate with test data

engine = suggestions.GenericSuggestionEngine()
suggestions = engine.suggest_improvements(problematic_tests)

for suggestion in suggestions:
    print(f"Test: {suggestion.test_name}")
    print(f"Issue: {suggestion.issue}")
    print(f"Suggestion: {suggestion.recommendation}")
```

## Error Handling

Importobot uses standard Python exceptions for error handling.

```python
import importobot
from importobot.exceptions import (
    ValidationError,
    ConversionError,
    FormatDetectionError
)

def safe_convert(input_path, output_path):
    """Attempts to convert a file and handles common Importobot exceptions."""
    try:
        converter = importobot.JsonToRobotConverter()
        result = converter.convert_file(input_path, output_path)
        return result

    except ValidationError as e:
        print(f"Input validation failed: {e}")
        return None

    except FormatDetectionError as e:
        print(f"Could not detect format: {e}")
        return None

    except ConversionError as e:
        print(f"Conversion failed: {e}")
        return None

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Example usage:
# safe_convert("invalid_input.json", "output.robot")
```
