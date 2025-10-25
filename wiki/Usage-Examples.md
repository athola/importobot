# Usage Examples

## CLI

```bash
uv run importobot zephyr_export.json converted_tests.robot

# Batch mode
uv run importobot --batch ./exports ./robot-output
```

## Python API

```python
from importobot.api import converters

converter = converters.JsonToRobotConverter()
summary = converter.convert_file("input.json", "output.robot")
print(summary)
```

## Schema Parser

### CLI Quick Start

```bash
# Provide one or more documentation sources describing custom fields
uv run importobot \
  --input-schema docs/field_guide.md \
  --input-schema docs/backend_cheat_sheet.md \
  custom_export.json \
  converted.robot
```

- Pass `--input-schema` multiple times to merge definitions from different teams.
- Keep documentation in Markdown or plain text; Importobot extracts headings and bullet lists automatically.
- Combine with `--batch` or `--robot-template` flags when running migrations.

### Preview Field Mapping

```bash
# Show how the schema affects field mapping without writing output files
uv run importobot \
  --input-schema docs/field_guide.md \
  --dry-run \
  custom_export.json
```

### Programmatic Usage

```python
from importobot.core.schema_parser import SchemaParser
from importobot.api import converters

schema_parser = SchemaParser()
schema = schema_parser.parse_markdown("docs/field_guide.md")

# Merge multiple sources if you have team-specific guides
schema.update(schema_parser.parse_markdown("docs/backend_cheat_sheet.md"))

converter = converters.JsonToRobotConverter(field_schema=schema)
result = converter.convert_json_dict(payload)
```

### Verification

- Watch for `SchemaParser` warnings on stdout/stderr; they flag missing files, unsupported extensions, or truncated content.
- Use `--dry-run` to confirm parsed fields before writing Robot Framework output.

## Medallion workflow preview

The medallion optimization example lives in the [User Guide](User-Guide#medallion-workflow-example).
