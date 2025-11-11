# Usage Examples

This page presents common usage examples for Importobot, demonstrating how to perform various conversion tasks.

## Command-Line Interface (CLI)

### Convert a single file

```bash
uv run importobot zephyr_export.json converted_tests.robot
```

### Convert a directory of files

```bash
uv run importobot --batch ./exports ./robot-output
```

## Python API

For programmatic use, Importobot provides a Python API.

```python
from importobot.api import converters

converter = converters.JsonToRobotConverter()

# Convert a single JSON file to a Robot Framework file
converter.convert_file("input.json", "output.robot")

# Convert all JSON files in an input directory to a specified output directory
converter.convert_directory("inputs", "outputs")
```

## Schema Mapping

If your test exports use custom field names, you can provide a schema file to map them to the standard names that Importobot expects. For a detailed explanation, see the [User Guide on Schema Mapping](User-Guide.md#mapping-custom-field-names).

### Example Schema File (`docs/field_guide.md`)

```markdown
# Field Guide

- **Title**: Maps to `name`
- **Description**: Maps to `description`
- **Steps**: Maps to `steps`
```

### CLI Usage

```bash
uv run importobot \
  --input-schema docs/field_guide.md \
  custom_export.json \
  converted.robot
```

## API Integration

Importobot can fetch test data directly from test management systems. For more details on configuring API integration, refer to the [User Guide on Fetching Data from an API](User-Guide.md#fetching-data-from-an-api).

```python
import os
from importobot.integrations.clients import get_api_client, SupportedFormat

client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://zephyr.example.com",
    tokens=[os.environ["ZEPHYR_TOKEN"]],
    project_name="ENG-QA",
)

for page in client.fetch_all():
    process_page(page)
```
