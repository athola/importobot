# API Examples

This page provides detailed API usage examples for Importobot, expanding on the quick start examples in the README.

## Core Conversion API

### Basic File Conversion

```python
import importobot

# Simple conversion
converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")

print(f"Converted {summary['test_cases']} test cases")
print(f"Output written to {summary['output_file']}")
```

### Directory Processing

```python
import importobot

converter = importobot.JsonToRobotConverter()
result = converter.convert_directory("./exports/", "./robot_tests/")

print(f"Processed {result['files_processed']} files")
print(f"Generated {result['test_cases_generated']} test cases")
print(f"Errors: {len(result['errors'])}")
```

### Conversion with Custom Configuration

```python
import importobot
from importobot.config import ImportobotConfig

# Custom configuration
config = ImportobotConfig(
    confidence_threshold=0.7,
    enable_telemetry=True,
    cache_max_size=2000
)

converter = importobot.JsonToRobotConverter(config=config)
summary = converter.convert_file("input.json", "output.robot")
```

## API Retrieval and Conversion

### Zephyr with Automatic Discovery

```python
from importobot.integrations.clients import get_api_client, SupportedFormat

# Zephyr client automatically discovers API patterns
client = get_api_client(
    SupportedFormat.ZEPHYR,
    api_url="https://your-zephyr.example.com",
    tokens=["your-api-token"],
    project_name="PROJECT_KEY",
    project_id=None,  # Auto-discovered if needed
    max_concurrency=5
)

# Process results as they stream in
test_cases = []
for payload in client.fetch_all(progress_callback=lambda **kw: print(f"Fetched {kw.get('items', 0)} items")):
    test_cases.extend(payload.get('testCases', []))

print(f"Retrieved {len(test_cases)} test cases")
```

### TestRail API Integration

```python
from importobot.integrations.clients import get_api_client, SupportedFormat

client = get_api_client(
    SupportedFormat.TESTRAIL,
    api_url="https://testrail.example.com/api/v2",
    tokens=["testrail-api-token"],
    user="automation@example.com",
    project_name="QA",
    max_concurrency=3
)

# Fetch specific run
run_data = client.fetch_run(run_id=42)
converter = importobot.JsonToRobotConverter()
result = converter.convert_json_dict(run_data)

# Save result
with open("testrail_suite.robot", "w") as f:
    f.write(result)
```

### JIRA/Xray Integration

```python
from importobot.integrations.clients import get_api_client, SupportedFormat

client = get_api_client(
    SupportedFormat.JIRA_XRAY,
    api_url="https://jira.example.com/rest/api/2/search",
    tokens=["jira-api-token"],
    project_name="ENG-QA",
    max_concurrency=4
)

# Fetch with JQL query
payloads = list(client.fetch_all(jql="project = ENG-QA AND labels = automated"))
print(f"Found {len(payloads)} test issues")
```

## Template-Based Conversion

### Using Existing Robot Templates

```python
import importobot
from importobot.core.templates.blueprints import BlueprintManager

# Load templates from existing Robot files
blueprint_manager = BlueprintManager()
blueprint_manager.learn_from_directory("./existing_robot_tests/")

# Convert using learned patterns
converter = importobot.JsonToRobotConverter(blueprint_manager=blueprint_manager)
result = converter.convert_file("new_export.json", "converted.robot")

# The output will match the style of your existing tests
```

### Schema-Driven Conversion

```python
import importobot
from importobot.core.schema_parser import SchemaParser

# Parse your organization's documentation
schema_parser = SchemaParser()
field_definitions = schema_parser.parse_markdown("docs/test_field_guide.md")

# Use schema for better field mapping
converter = importobot.JsonToRobotConverter(field_schema=field_definitions)
result = converter.convert_file("export.json", "output.robot")
```

## Validation and Suggestions API

### Input Validation

```python
from importobot.api import validation

# Validate JSON structure before conversion
try:
    validation.validate_json_dict(test_data)
    validation.validate_zephyr_format(test_data)
    print("Data is valid Zephyr format")
except validation.ValidationError as e:
    print(f"Validation error: {e}")
    print(f"Field: {e.field}")
    print(f"Expected: {e.expected}")
```

### Improvement Suggestions

```python
from importobot.api import suggestions

# Get suggestions for problematic test cases
engine = suggestions.GenericSuggestionEngine()
suggestions = engine.suggest_improvements(problematic_tests)

for suggestion in suggestions:
    print(f"Test: {suggestion.test_name}")
    print(f"Issue: {suggestion.issue}")
    print(f"Suggestion: {suggestion.recommendation}")
```

## Advanced Features

### Bayesian Optimization (Advanced Package)

```python
# Requires: pip install "importobot[advanced]"
from importobot.medallion.bronze import optimization

# Optimize confidence parameters
optimizer = optimization.MVLPConfidenceOptimizer()
optimizer.tune_parameters("fixtures/complex_suite.json")

# Get optimized parameters
params = optimizer.get_optimized_parameters()
print(f"Optimized epsilon: {params.numerical_epsilon}")
print(f"Optimized ambiguity cap: {params.ambiguous_ratio_cap}")
```

### Custom Format Detection

```python
from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.bronze.formats import GenericFormat

# Create custom format detector
detector = FormatDetector()

# Add custom format patterns
custom_format = GenericFormat(
    name="CustomCRM",
    required_fields=["testCase", "steps"],
    optional_fields=["priority", "tags"],
    field_patterns={
        "testCase": r"test_case|testCase",
        "steps": r"steps|testSteps"
    }
)

detector.register_format(custom_format)

# Use in conversion
converter = importobot.JsonToRobotConverter(format_detector=detector)
```

### Telemetry and Monitoring

```python
import importobot
from importobot.telemetry import TelemetryClient

# Enable telemetry for monitoring
telemetry = TelemetryClient()
telemetry.enable()

converter = importobot.JsonToRobotConverter()

# Convert and get metrics
result = converter.convert_directory("./exports/", "./output/")

# Get performance metrics
metrics = telemetry.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
print(f"Average conversion time: {metrics['avg_conversion_time']:.2f}ms")
print(f"Format detection accuracy: {metrics['detection_accuracy']:.2%}")
```

## Error Handling

### Robust Error Handling

```python
import importobot
from importobot.exceptions import (
    ValidationError,
    ConversionError,
    FormatDetectionError
)

def safe_convert(input_path, output_path):
    try:
        converter = importobot.JsonToRobotConverter()
        result = converter.convert_file(input_path, output_path)
        return result

    except ValidationError as e:
        print(f"Input validation failed: {e}")
        return None

    except FormatDetectionError as e:
        print(f"Could not detect format: {e}")
        print(f"Confidence scores: {e.confidence_scores}")
        return None

    except ConversionError as e:
        print(f"Conversion failed: {e}")
        print(f"Error details: {e.details}")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
result = safe_convert("input.json", "output.robot")
if result:
    print(f"Successfully converted {result['test_cases']} test cases")
```

## Configuration

### Environment-Based Configuration

```python
import os
import importobot
from importobot.config import ImportobotConfig

# Configure from environment variables
config = ImportobotConfig(
    confidence_threshold=float(os.getenv("IMPORTOBOT_CONFIDENCE_THRESHOLD", "0.5")),
    cache_max_size=int(os.getenv("IMPORTOBOT_CACHE_MAX_SIZE", "1000")),
    enable_telemery=os.getenv("IMPORTOBOT_ENABLE_TELEMETRY", "false").lower() == "true",
    headless_browser=os.getenv("IMPORTOBOT_HEADLESS_BROWSER", "true").lower() == "true"
)

converter = importobot.JsonToRobotConverter(config=config)
```

### Custom Keyword Libraries

```python
import importobot
from importobot.core.keywords.generators import OperatingSystemKeywords

# Add custom keyword generators
converter = importobot.JsonToRobotConverter()
converter.add_keyword_generator(OperatingSystemKeywords())

# Convert with custom keywords
result = converter.convert_file("sysadmin_tests.json", "sysadmin.robot")
```

## Performance Optimization

### Bulk Processing with Progress Tracking

```python
import importobot
from importobot.utils.progress_reporter import ProgressReporter

def progress_callback(current, total, file_path):
    percent = (current / total) * 100
    print(f"Processing {file_path}: {current}/{total} ({percent:.1f}%)")

# Process directory with progress tracking
converter = importobot.JsonToRobotConverter()
result = converter.convert_directory(
    input_dir="./large_export/",
    output_dir="./robot_tests/",
    progress_callback=progress_callback
)

print(f"Completed: {result['summary']}")
```

### Memory-Efficient Processing

```python
import importobot
from importobot.config import ImportobotConfig

# Configure for large files
config = ImportobotConfig(
    cache_max_size=500,  # Smaller cache
    file_cache_max_mb=50,  # Limit memory usage
    enable_streaming=True  # Process in chunks
)

converter = importobot.JsonToRobotConverter(config=config)

# Process large file
result = converter.convert_file("large_export.json", "output.robot")
```

## Testing and Debugging

### Dry Run Mode

```python
import importobot

# Test conversion without writing files
converter = importobot.JsonToRobotConverter(dry_run=True)
result = converter.convert_file("test_input.json")

print(f"Would generate {result['test_cases']} test cases")
print(f"First test case: {result['preview'][0]['name']}")
```

### Format Detection Debugging

```python
from importobot.medallion.bronze.format_detector import FormatDetector

detector = FormatDetector()

# Get detailed format detection info
detection_result = detector.detect_format(test_data)

print(f"Detected format: {detection_result.best_format}")
print(f"Confidence: {detection_result.confidence:.3f}")
print(f"Evidence breakdown:")
for evidence, score in detection_result.evidence_scores.items():
    print(f"  {evidence}: {score:.3f}")
```