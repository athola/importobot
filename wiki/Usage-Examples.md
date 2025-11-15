# Usage Examples

This page provides common usage examples for various conversion tasks.

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

You can also use Importobot programmatically through its Python API.

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

## Security Examples

### Encrypt a Token Before Storing It

```python
from importobot.security import CredentialManager

manager = CredentialManager()
encrypted = manager.encrypt_credential(os.environ["ZEPHYR_TOKEN"])
save_bytes(encrypted.ciphertext)  # Write to your secret store
restored_token = manager.decrypt_credential(encrypted)
```

### Scan a Template Before Passing It to `--robot-template`

```python
from importobot.security import TemplateSecurityScanner

scanner = TemplateSecurityScanner()
report = scanner.scan_template_file("templates/login.robot")
if not report.is_safe:
    raise RuntimeError(report.issues)
```

### Forward Security Events to Splunk

```python
import os
from importobot.security import create_splunk_connector, get_siem_manager

splunk = create_splunk_connector(
    host="https://splunk.example.com",
    token=os.environ["SPLUNK_HEC_TOKEN"],
)
manager = get_siem_manager()
manager.add_connector(splunk)
manager.start()
```

- Repeat the same pattern with `create_elastic_connector()` or `create_sentinel_connector()` (see [SIEM Integration](SIEM-Integration.md) for full scripts).
