# Usage Examples

This page provides a collection of common usage examples for Importobot.

## Command-Line Interface (CLI)

The CLI is the easiest way to get started with Importobot. It provides a simple and intuitive interface for converting test exports.

### Convert a single file

```bash
uv run importobot zephyr_export.json converted_tests.robot
```

### Convert a directory of files

```bash
uv run importobot --batch ./exports ./robot-output
```

## Python API

The Python API provides more flexibility for integrating Importobot into your own scripts and workflows.

```python
from importobot.api import converters

# Create a converter instance
converter = converters.JsonToRobotConverter()

# Convert a single file
summary = converter.convert_file("input.json", "output.robot")
print(summary)

# Convert a directory of files
summary = converter.convert_directory("inputs", "outputs")
print(summary)
```

## Schema-Driven Parsing

For test exports with custom field names, you can provide a schema file to map the custom names to the standard ones expected by Importobot.

### Example Schema File (`docs/field_guide.md`)

```markdown
# Field Guide

This document outlines the custom fields used in our Zephyr exports.

## Test Case Fields

-   **Title**: The main title of the test case. This should be mapped to the `name` field.
-   **Description**: A detailed description of the test case. This should be mapped to the `description` field.
-   **Steps**: The steps to be executed in the test case. This should be mapped to the `steps` field.
```

### CLI Usage

```bash
# Provide the schema file to the --input-schema argument
uv run importobot \
  --input-schema docs/field_guide.md \
  custom_export.json \
  converted.robot
```

### Programmatic Usage

```python
from importobot.core.schema_parser import SchemaParser
from importobot.api import converters

# Parse the schema file
schema_parser = SchemaParser()
schema = schema_parser.parse_markdown("docs/field_guide.md")

# Create a converter with the custom schema
converter = converters.JsonToRobotConverter(field_schema=schema)

# Convert the file
result = converter.convert_file("custom_export.json", "converted.robot")
```

## API Integration

Importobot can fetch test data directly from test management systems like Zephyr, TestRail, and JIRA/Xray.

```python
import os
from importobot.integrations.clients import get_api_client, SupportedFormat

# Get the appropriate API client
client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://zephyr.example.com",
    tokens=[os.environ["ZEPHYR_TOKEN"]],
    project_name="ENG-QA",
)

# Fetch the test data
for page in client.fetch_all():
    # Process each page of test data
    process_page(page)
```
