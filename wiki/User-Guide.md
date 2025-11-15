# User Guide

This guide covers key features for handling API data, custom fields, and other advanced conversion tasks. For a complete list of commands and examples, see the [API Reference](API-Reference.md) and [Usage Examples](Usage-Examples.md).

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
from importobot.integrations.clients import get_api_client, SupportedFormat

# See the API Reference for detailed examples
client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://zephyr.example.com",
)

for page in client.fetch_all():
    process_page(page)
```

## Mapping Custom Field Names

If your export file uses custom field names (e.g., `Test_Title` instead of `name`), you can provide a schema file to map your custom names to the standard fields Importobot recognizes.

### Example Schema File (`field_mapping.json`)

```json
{
  "Test_Title": "name",
  "Description": "description",
  "Steps": "steps"
}
```

### CLI Usage

```bash
uv run importobot \
  --input-schema field_mapping.json \
  custom_export.json \
  converted.robot
```

## Automation Features

- **Automatic Library Imports**: Detects keywords in test steps and adds the corresponding `Library` statements to the generated Robot Framework file.
- **Automatic Format Detection**: Automatically detects the format of input files (e.g., Zephyr, Xray), so you don't have to specify it manually.

## Security Controls

Version 0.1.5 added a first-class security package. Use it when wiring Importobot into CI/CD:

### Encrypting Long-Lived Tokens

```python
from importobot.security import CredentialManager

manager = CredentialManager()  # Requires IMPORTOBOT_ENCRYPTION_KEY
encrypted = manager.encrypt_credential(os.environ["ZEPHYR_TOKEN"])
store(encrypted.ciphertext)

# Later
zephyr_token = manager.decrypt_credential(encrypted)
```

- `CredentialManager` fails fast if `cryptography` is missing or the Fernet key is absent/incorrect.

### Scanning Robot Templates

```python
from importobot.security import TemplateSecurityScanner

report = TemplateSecurityScanner().scan_template_file("templates/smoke.robot")
if not report.is_safe:
    raise RuntimeError(report.issues[0].description)
```

- Use this before invoking `--robot-template` so compromised templates never reach the converter.
- The CLI now performs this scan automatically when `--robot-template` is supplied and will terminate if any template fails.

### Shipping Alerts to SIEM

```python
from importobot.security import create_splunk_connector, get_siem_manager

splunk = create_splunk_connector(
    host="https://siem.example.com",
    token=os.environ["SPLUNK_HEC_TOKEN"],
)
manager = get_siem_manager()
manager.add_connector(splunk)
manager.start()
manager.send_security_event(security_event)
```

- Splunk, Elastic, and Sentinel connectors share the same `SIEMEvent` payload, so one integration feeds multiple tools.
- See the dedicated [SIEM Integration](SIEM-Integration.md) guide for full scripts (environment variables, verification steps, and monitor wiring).
