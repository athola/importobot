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

## Medallion workflow preview

The medallion optimization example lives in the [User Guide](User-Guide#medallion-workflow-example).
