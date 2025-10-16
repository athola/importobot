# FAQ

Frequently asked questions about Importobot.

## General

### What is Importobot?
Importobot converts structured test exports (Zephyr today) into Robot Framework suites.

### Why use Importobot?
Eliminates manual copy/paste work when migrating test cases, preserves metadata, and highlights items needing manual review.

### What formats does Importobot support?
Zephyr JSON is supported now. Xray and TestLink parsers are in review.

### What does Importobot generate?
Executable Robot Framework `.robot` files.

## Installation

### What are the requirements?
Python 3.10+ and the `uv` package manager.

### How do I install uv?
See the [Getting Started](Getting-Started) guide for installation instructions.

### How do I verify my installation?
Run `uv run pytest` in the repo. The suite should pass.

## Usage

### How do I convert a single test case?
`uv run importobot input.json output.robot`

### How do I convert multiple test cases?
`uv run importobot --batch input_dir/ output_dir/`

### How does Importobot handle different test steps?
Intent-based parsing maps steps to appropriate Robot keywords; ambiguous cases are surfaced in the output for review.

### Can I customize the output?
Not directly. Edit the generated Robot files if bespoke behaviour is required.

## Troubleshooting

### "File not found" error
Check the path and prefer absolute paths when scripting.

### My converted tests are not running correctly.
1. Install the Robot libraries referenced in the output.
2. Inspect the generated `.robot` file for missing data.
3. Run `robot --dryrun` to surface syntax issues quickly.

### How do I handle custom fields?
Custom fields are preserved in metadata but do not change the generated steps.

### What if my JSON format is different?
Minor variations are fine. For major differences, open an issue with a sample export.

## Development

### How can I contribute?
Follow the steps in [Contributing](Contributing).

### How do I run the tests?
`uv run pytest`

### How do I add support for a new format?
Read the API Reference plus the contributing notes on format parsers.

## Security

### Is Importobot secure?
Yes. It runs locally, validates paths, and blocks obvious traversal attempts.

### How does Importobot handle sensitive information?
It copies your test data verbatim. Scrub secrets before exporting if you do not want them in the Robot output.

## Performance

### How fast is Importobot?
Typical conversions stay under a second per test.

### Can Importobot handle large test suites?
Yes. Batch mode is designed for hundreds of cases at a time.

## Integration

### How do I integrate Importobot into CI/CD?
Add a conversion step (`uv run importobot ...`) before your Robot execution job. It runs fine in headless containers.

### Can Importobot be used as a library?
Yes. Import `importobot.JsonToRobotConverter` or the modules under `importobot.api`.

## Future Development

### What formats are next?
Xray and TestLink are in progress. CSV/Excel are under consideration.

### How can I request support for a format?
Open an issue with a sample export and the necessary fields to be added.
