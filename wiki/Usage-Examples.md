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
result = converter.convert_file("input.json", "output.robot")
print(result.summary())
```

## Medallion Workflow

See [User Guide](User-Guide#medallion-workflow-example) for a Bronze→Gold preview
example with optimization metadata.
