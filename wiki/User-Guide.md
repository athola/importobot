# User Guide

This guide details some of Importobot's key features and how to use them. For a complete list of commands and examples, see the [API Reference](API-Reference.md) and [Usage Examples](Usage-Examples.md).

## Supported Input Formats

Importobot can process files or API responses from:

- Zephyr (JSON)
- JIRA/Xray (JSON)
- TestLink (XML, JSON)
- TestRail (API Payloads)
- Custom formats via Python dictionaries

## Fetching Data from an API

Instead of using a local file, Importobot can fetch test data directly from a test management tool's API.

### CLI Usage

```bash
# Fetch from TestRail and convert
uv run importobot \
    --fetch-format testrail \
    --api-url https://testrail.example/api/v2/get_runs/42 \
    --api-user automation@example.com \
    --tokens api-token-value \
    --project QA \
    --output suite.robot
```

### Programmatic Usage

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

## Mapping Custom Field Names

If your export file uses custom field names (e.g., `Test_Title` instead of `name`), you can provide a schema file to map your custom names to the standard fields Importobot recognizes.

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

## Other Features

- **Automatic Library Imports**: Importobot detects keywords in test steps (e.g., `Open Browser`, `Execute Command`) and automatically adds the corresponding `Library` statements (e.g., `SeleniumLibrary`, `SSHLibrary`) to the generated Robot Framework file.
- **Automatic Format Detection**: When you provide a file, Importobot automatically detects its format (e.g., Zephyr, Xray). This means you don't have to specify the format manually for file-based conversions.