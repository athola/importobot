# User Guide

This guide explains how to use Importobot to convert test cases from various test management systems to Robot Framework.

For a quick collection of common usage patterns, see the [Usage Examples](Usage-Examples.md) page.

## Supported Input Formats

- Zephyr JSON exports
- JIRA/Xray JSON
- TestLink XML/JSON
- TestRail API payloads
- Generic dictionaries

## API Integration

Importobot can fetch test data directly from test management systems.

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

## Schema-Driven Parsing

If your test exports use custom field names, you can provide a schema file to map them to the standard names that Importobot expects.

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

## Key Features

- **Library Detection**: Automatically adds the required Robot Framework libraries (e.g., `SeleniumLibrary`, `SSHLibrary`) to the generated files by analyzing the text of the test steps.
- **Format Detection**: Uses a Bayesian confidence scorer to automatically identify the format of your test export files.