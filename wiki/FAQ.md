# FAQ

Frequently asked questions about Importobot.

## General

### What is Importobot?
Importobot is a tool that converts test case exports from formats like Zephyr, Xray, and TestLink into runnable Robot Framework (`.robot`) files.

### Why should I use Importobot?
It automates the manual work of migrating test cases, preserves metadata from the original source, and flags any steps that require manual review, preventing silent errors.

### What formats does Importobot support?
Zephyr, TestRail, Xray, and TestLink formats are supported with JSON and XML inputs.

### What does Importobot generate?
Runnable Robot Framework `.robot` files.

## Installation

### What are the requirements?
Python 3.10+ and the `uv` package manager.

### How do I install uv?
See the [Getting Started](Getting-Started.md) guide for installation instructions.

### How do I verify my installation?
Run `uv run pytest` from the root of the repository. The test suite should pass.

## Usage

### How do I convert a single test case?
`uv run importobot input.json output.robot`

### How do I convert multiple test cases?
`uv run importobot --batch input_dir/ output_dir/`

### How does Importobot interpret test steps?
It analyzes the text of a test step to map it to a known Robot Framework keyword (e.g., "Click button 'Submit'" becomes `Click Button  Submit`). If a step is ambiguous, it is flagged with a comment in the output file for manual review.

### Can I customize the output?
Yes, there are several ways to customize the conversion. See the [User Guide](User-Guide.md) for more details.
- **Templates**: Use the `--robot-template` flag to apply a custom Robot Framework structure.
- **Schema Mapping**: Use `--input-schema` to map custom field names from your export to the names Importobot expects.
- **Blueprint Learning**: Importobot can learn formatting and style from your existing Robot files to keep new conversions consistent.

### How does schema mapping work?
You can provide a Markdown file that defines the custom field names in your export file. Importobot uses this to understand your data structure, improving parsing accuracy. See the [User Guide](User-Guide.md#mapping-custom-field-names) for an example.

### What are blueprint templates?
Blueprint templates learn patterns from your existing Robot Framework files and apply them to new conversions to maintain consistency with your team's style.

## Troubleshooting

### "File not found" error
Check that the file path is correct. Using absolute paths is generally more reliable, especially in scripts.

### My converted tests are not running correctly. What should I do?
1.  First, ensure you have installed the Robot Framework libraries that are listed in the `*** Settings ***` section of the generated file (e.g., `SeleniumLibrary`).
2.  Use the `--dryrun` flag with Robot Framework (`robot --dryrun your_test.robot`) to check for syntax errors.
3.  Inspect the generated file for any `TODO` comments, which indicate steps that Importobot could not convert automatically.

### How do I handle custom fields?
Custom fields are retained in metadata but do not change the generated steps.

### What if my JSON format is slightly different from the standard?
Importobot can handle minor variations in JSON structure. If your format is significantly different, the conversion may fail. In that case, please open a GitHub issue and provide a small, anonymized sample of your export file.

## Development

### How can I contribute?
Follow the steps in the [Contributing](Contributing.md) guide.

### How do I run the tests?
`uv run pytest`

### How do I add support for a new format?
Read the [API Reference](API-Reference.md) and the [Contributing](Contributing.md) guide, which has information on format parsers.

## Security

### Is Importobot secure?
Yes. The tool is designed with security in mind. It runs entirely locally, validates all file paths to prevent directory traversal attacks, and is subject to the strict standards outlined in our [Security Standards](Security-Standards.md) document.

### How does Importobot handle sensitive information in test data?
Importobot copies test data exactly as it appears in the source file. If your test cases contain sensitive information (like passwords or API keys), you should remove them from your export file *before* conversion.

## Performance

### How fast is Importobot?
Performance depends on the size and complexity of the export, but most conversions are very fast. See our [Performance Benchmarks](Performance-Benchmarks.md) for specific numbers.

### Can Importobot handle large test suites?
Yes. Batch mode is designed to convert hundreds or thousands of test cases at a time.

## Integration

### How do I integrate Importobot into CI/CD?
Add a conversion step (`uv run importobot ...`) to your pipeline before the step that executes your Robot Framework tests. The tool runs in headless environments and is well-suited for CI/CD. See the [Deployment Guide](Deployment-Guide.md) for examples.

### Can Importobot be used as a library?
Yes. You can import and use `importobot.JsonToRobotConverter` or the modules under `importobot.api` for programmatic use.

## Future Development

### What is the project roadmap?
Our high-level goals and planned features are outlined in the [Roadmap](Roadmap.md).

### How can I request a feature?
Open a GitHub issue using the "Feature Request" template. Please explain the problem you are trying to solve and the use case for the new feature.
