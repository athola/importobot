# User Guide

This guide provides a comprehensive overview of how to use Importobot to convert test cases from various test management systems to Robot Framework.

For a quick collection of common usage patterns, see the [Usage Examples](Usage-Examples.md) page.

## Supported Input Formats

- **Zephyr** JSON exports
- **JIRA/Xray** JSON
- **TestLink** XML/JSON conversions
- **TestRail** API payloads
- **Generic** dictionaries for ad-hoc conversions

## API Integration

Importobot can fetch test data directly from test management systems like Zephyr, TestRail, and JIRA/Xray.

### CLI Usage

```bash
# Fetch from TestRail and convert in one step
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

## Advanced Topics

### Library Detection

Importobot automatically infers the required Robot Framework libraries (e.g., `SeleniumLibrary`, `SSHLibrary`) by analyzing the text of the test steps.

### Intent-Based Conversion

Instead of relying on rigid templates, Importobot parses the *intent* of each test step (e.g., "navigate", "assert") to select the most appropriate Robot Framework keyword.

### Suggestion Engine

The suggestion engine, available through `importobot.api.suggestions`, can be used to review generated tests and identify potential issues, such as missing assertions or weak error handling.

### Format Detection

Importobot uses a Bayesian confidence scorer to automatically identify the format of your test export files. If the confidence score is low, the tool will issue a warning, allowing you to verify that the correct format is being used.