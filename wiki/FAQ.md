# FAQ

Frequently asked questions about Importobot.

## General

### What is Importobot?
Importobot is a tool that converts test cases from various test management frameworks (Zephyr, JIRA/Xray, TestLink, etc.) into Robot Framework format.

### Why use Importobot?
Importobot saves time and reduces errors by automating the migration of test cases to Robot Framework.

### What formats does Importobot support?
Currently, Importobot supports Zephyr JSON format. Support for JIRA/Xray and TestLink is planned.

### What does Importobot generate?
Importobot generates executable Robot Framework test cases.

## Installation

### What are the requirements?
Importobot requires Python 3.10 or higher and the uv package manager.

### How do I install uv?
See the [Getting Started](Getting-Started) guide for installation instructions.

### How do I verify my installation?
Run `uv run pytest` in the project directory. All tests should pass.

## Usage

### How do I convert a single test case?
`uv run importobot input.json output.robot`

### How do I convert multiple test cases?
`uv run importobot --batch input_folder/ output_folder/`

### How does Importobot handle different test steps?
Importobot uses intent-based parsing to generate appropriate Robot Framework keywords for each test step.

### Can I customize the output?
Importobot generates standardized Robot Framework code. You can modify the generated code after conversion.

## Troubleshooting

### "File not found" error
Ensure the input file path is correct. Use absolute paths if you are having issues.

### My converted tests are not running correctly.
1. Check that all required Robot Framework libraries are installed.
2. Verify the generated code matches your expectations.
3. Run `robot --dryrun` to check for syntax errors.

### How do I handle custom fields?
Importobot focuses on standard test case elements. Custom fields may be preserved in metadata but will not affect the conversion.

### What if my JSON format is different?
Importobot can handle some variations in JSON structure. If you have issues, please open an issue on GitHub.

## Development

### How can I contribute?
See the [Contributing](Contributing) guide.

### How do I run the tests?
Run `uv run pytest`.

### How do I add support for a new format?
See the API Reference and Contributing guide for details.

## Security

### Is Importobot secure?
Importobot processes files locally and does not send data to external servers. It includes path validation to prevent directory traversal attacks.

### How does Importobot handle sensitive information?
Importobot preserves the content of your test cases as-is. If your test cases contain sensitive information, the generated Robot Framework files will also contain that information.

## Performance

### How fast is Importobot?
Importobot converts test cases in less than a second per test case.

### Can Importobot handle large test suites?
Yes, Importobot is designed to handle large test suites, especially in batch mode.

## Integration

### How do I integrate Importobot into my CI/CD pipeline?
Importobot can be used as a conversion step in a CI/CD pipeline. The generated Robot Framework files can then be executed as part of your automated testing process. It can be configured to run in a headless environment.

### Can Importobot be used as a library?
Yes, Importobot's core functionality can be imported and used in other Python projects.

## Future Development

### What formats will be supported in the future?
Support for JIRA/Xray and TestLink is planned. CSV and Excel support is also on the roadmap.

### How can I request support for a format?
Open an issue on GitHub with a description of the format and sample data.