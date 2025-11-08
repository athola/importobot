# API Examples

This page provides examples for using Importobot's API.

## Basic Conversion

### Converting a single file

```python
import importobot

converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")

print(f"Converted {summary['test_cases']} test cases")
print(f"Output written to {summary['output_file']}")
```

### Converting a directory

```python
import importobot

converter = importobot.JsonToRobotConverter()
result = converter.convert_directory("./exports/", "./robot_tests/")

print(f"Processed {result['files_processed']} files")
print(f"Generated {result['test_cases_generated']} test cases")
print(f"Errors: {len(result['errors'])}")
```

## API Integration

Importobot can fetch test data directly from test management systems like Zephyr, TestRail, and JIRA/Xray.

### Fetching from Zephyr

```python
from importobot.integrations.clients import get_api_client, SupportedFormat

client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://your-zephyr.example.com",
    tokens=["your-api-token"],
    project_name="PROJECT_KEY",
)

test_cases = []
for payload in client.fetch_all():
    test_cases.extend(payload.get('testCases', []))

print(f"Retrieved {len(test_cases)} test cases")
```

### Fetching from TestRail

```python
from importobot.integrations.clients import get_api_client, SupportedFormat

client = get_api_client(
    SupportedFormat.TESTRAIL,
    api_url="https://testrail.example.com/api/v2",
    tokens=["testrail-api-token"],
    user="automation@example.com",
    project_name="QA",
)

run_data = client.fetch_run(run_id=42)

converter = importobot.JsonToRobotConverter()
result = converter.convert_json_dict(run_data)

with open("testrail_suite.robot", "w") as f:
    f.write(result)
```

## Advanced Conversion

### Schema-Driven Conversion

For test exports with custom field names, provide a schema file to map custom names to Importobot's standard ones.

```python
import importobot
from importobot.core.schema_parser import SchemaParser

schema_parser = SchemaParser()
field_definitions = schema_parser.parse_markdown("docs/test_field_guide.md")

converter = importobot.JsonToRobotConverter(field_schema=field_definitions)
result = converter.convert_file("export.json", "output.robot")
```

### Template-Based Conversion

Importobot can learn from your existing Robot Framework files to ensure new conversions match your team's style.

```python
import importobot
from importobot.core.templates.blueprints import BlueprintManager

blueprint_manager = BlueprintManager()
blueprint_manager.learn_from_directory("./existing_robot_tests/")

converter = importobot.JsonToRobotConverter(blueprint_manager=blueprint_manager)
result = converter.convert_file("new_export.json", "converted.robot")
```

## Validation and Suggestions

### Input Validation

Use the `validation` module to validate your JSON data before conversion.

```python
from importobot.api import validation

try:
    validation.validate_json_dict(test_data)
    print("Data is valid")
except validation.ValidationError as e:
    print(f"Validation error: {e}")
```

### Improvement Suggestions

The `suggestions` module can identify potential improvements in your test cases.

```python
from importobot.api import suggestions

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
        print(f"Unexpected error: {e}")
        return None
```
