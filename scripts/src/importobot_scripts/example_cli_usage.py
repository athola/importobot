#!/usr/bin/env python3
"""
Command Line Interface examples for Importobot.

This script demonstrates how to use Importobot from the command line
and provides examples of integrating it into automated workflows.
"""

import os
import subprocess
from pathlib import Path

# Get root directory for file paths
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent


def run_command(command: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """
    Run a command and return exit code, stdout, and stderr.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def basic_cli_example() -> None:
    """Demonstrate basic CLI usage."""
    print("=== Basic CLI Example ===")

    # Check if importobot CLI is available using uv
    commands_to_try = [
        ["uv", "run", "python", "-m", "importobot", "--help"],
        ["python", "-m", "importobot", "--help"],
    ]

    for command in commands_to_try:
        print(f"Trying: {' '.join(command)}")
        exit_code, stdout, stderr = run_command(command, cwd=root_dir)

        if exit_code == 0:
            print(" Importobot CLI is available")
            print("Help output preview:")
            print("-" * 30)
            print(stdout[:500] + "..." if len(stdout) > 500 else stdout)
            return

        print(f"Command failed: {stderr}")

    print(" CLI not available or not installed properly")
    print("Try running with: uv run python -m importobot --help")


def file_conversion_cli_example() -> None:
    """Demonstrate converting files via CLI."""
    print("\n=== File Conversion CLI Example ===")

    # Use an existing JSON file
    json_files = list((root_dir / "examples" / "json").glob("*.json"))

    if not json_files:
        print("No JSON example files found")
        return

    # Use the first available JSON file
    input_file = json_files[0]
    output_dir = root_dir / "examples" / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"cli_{input_file.stem}.robot"

    print(f"Converting {input_file} to {output_file}")

    # Attempt CLI conversion using uv
    commands_to_try = [
        ["uv", "run", "python", "-m", "importobot", str(input_file), str(output_file)],
        ["python", "-m", "importobot", str(input_file), str(output_file)],
    ]

    for command in commands_to_try:
        print(f"Trying: {' '.join(command[:4])} ...")
        exit_code, stdout, stderr = run_command(command, cwd=root_dir)

        if exit_code == 0:
            print(" CLI conversion successful")
            if stdout:
                print("Output:", stdout)

            # Verify output file was created
            if output_file.exists():
                file_size = os.path.getsize(output_file)
                print(f"Generated file: {output_file} ({file_size} bytes)")

                # Show first few lines
                with open(output_file, encoding="utf-8") as f:
                    lines = f.readlines()[:10]
                print("Preview:")
                print("-" * 30)
                print("".join(lines))
                print("-" * 30)
            else:
                print("WARNING: Output file was not created")
            return

        print(f"Command failed: {stderr}")

    print(" All CLI conversion attempts failed")


def batch_processing_cli_example() -> None:
    """Demonstrate batch processing via CLI."""
    print("\n=== Batch Processing CLI Example ===")

    json_dir = root_dir / "examples" / "json"
    output_dir = root_dir / "examples" / "output" / "batch"

    if not json_dir.exists():
        print(f"JSON directory {json_dir} not found")
        return

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON files
    json_files = list(json_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files for batch processing")

    success_count = 0
    for json_file in json_files[:3]:  # Limit to first 3 for demo
        output_file = output_dir / f"{json_file.stem}.robot"

        # Try uv run first
        commands_to_try = [
            [
                "uv",
                "run",
                "python",
                "-m",
                "importobot",
                str(json_file),
                str(output_file),
            ],
            ["python", "-m", "importobot", str(json_file), str(output_file)],
        ]

        print(f"Processing {json_file.name}...")
        converted = False

        for command in commands_to_try:
            exit_code, _stdout, _stderr = run_command(command, cwd=root_dir)

            if exit_code == 0:
                print(f"   {json_file.name} -> {output_file.name}")
                success_count += 1
                converted = True
                break

        if not converted:
            print(f"   Failed to process {json_file.name}")

    print(
        f"\nBatch processing completed: {success_count}/"
        f"{len(json_files[:3])} files successful"
    )


def pipeline_integration_example() -> None:
    """Demonstrate CI/CD pipeline integration."""
    print("\n=== Pipeline Integration Example ===")

    # Create a mock pipeline script
    pipeline_script = root_dir / "examples" / "pipeline_example.sh"
    pipeline_script.parent.mkdir(exist_ok=True)

    pipeline_content = f"""#!/bin/bash
# Example CI/CD pipeline integration for Importobot

set -e  # Exit on error

echo "Starting automated test conversion pipeline..."

# Define directories
INPUT_DIR="{root_dir}/examples/json"
OUTPUT_DIR="{root_dir}/examples/output/pipeline"
REPORT_FILE="{root_dir}/examples/conversion_report.txt"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize report
echo "Importobot Conversion Report - $(date)" > "$REPORT_FILE"
echo "=================================" >> "$REPORT_FILE"

# Counter for statistics
SUCCESS_COUNT=0
TOTAL_COUNT=0

# Process each JSON file
for json_file in "$INPUT_DIR"/*.json; do
    if [ -f "$json_file" ]; then
        filename=$(basename "$json_file" .json)
        output_file="$OUTPUT_DIR/${{filename}}.robot"

        echo "Processing: $json_file"
        TOTAL_COUNT=$((TOTAL_COUNT + 1))

        # Attempt conversion with uv run first, then use the secondary path
        if cd "{root_dir}" && uv run python -m importobot \\
            "$json_file" "$output_file" 2>/dev/null; then
            echo " SUCCESS: $filename" >> \\
                "$REPORT_FILE"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        elif cd "{root_dir}" && python -m importobot \\
            "$json_file" "$output_file" 2>/dev/null; then
            echo " SUCCESS: $filename" >> \\
                "$REPORT_FILE"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo " FAILED: $filename" >> "$REPORT_FILE"
        fi
    fi
done

# Generate summary
echo "" >> "$REPORT_FILE"
echo "Summary:" >> "$REPORT_FILE"
echo "--------" >> "$REPORT_FILE"
echo "Total files: $TOTAL_COUNT" >> "$REPORT_FILE"
echo "Successful: $SUCCESS_COUNT" >> "$REPORT_FILE"
echo "Failed: $((TOTAL_COUNT - SUCCESS_COUNT))" >> "$REPORT_FILE"
if [ $TOTAL_COUNT -gt 0 ]; then
    echo "Success rate: $(( SUCCESS_COUNT * 100 / TOTAL_COUNT ))%" >> "$REPORT_FILE"
fi

echo "Pipeline completed. Report saved to: $REPORT_FILE"
"""

    # Write pipeline script
    with open(pipeline_script, "w", encoding="utf-8") as f:
        f.write(pipeline_content)

    # Make it executable (on Unix systems)
    if os.name != "nt":  # Not Windows
        os.chmod(pipeline_script, 0o755)

    print(f"Created pipeline script: {pipeline_script}")

    # Execute the pipeline script
    if os.name == "nt":  # Windows
        command = ["cmd", "/c", str(pipeline_script)]
    else:  # Unix-like
        command = ["bash", str(pipeline_script)]

    print("Executing pipeline script...")
    exit_code, stdout, stderr = run_command(command, cwd=root_dir)

    if exit_code == 0:
        print(" Pipeline execution successful")
        if stdout:
            print("Pipeline output:")
            print(stdout)

        # Show report if it exists
        report_file = root_dir / "examples" / "conversion_report.txt"
        if report_file.exists():
            print("\nConversion Report:")
            print("-" * 30)
            with open(report_file, encoding="utf-8") as f:
                print(f.read())
    else:
        print(" Pipeline execution failed")
        if stderr:
            print(f"Error: {stderr}")


def validation_cli_example() -> None:
    """Demonstrate validation via CLI."""
    print("\n=== Validation CLI Example ===")

    # Create a test file with validation issues
    invalid_json = root_dir / "examples" / "output" / "invalid_test.json"
    invalid_json.parent.mkdir(exist_ok=True)

    # Invalid JSON structure for testing
    invalid_content = """
{
    "tests": [
        {
            "name": "Invalid Test",
            "steps": [
                {
                    "action": "Missing expected result"
                }
            ]
        }
    ]
}
"""

    with open(invalid_json, "w", encoding="utf-8") as f:
        f.write(invalid_content)

    print(f"Created invalid test file: {invalid_json}")

    # Attempt to validate invalid file (note: CLI doesn't have validate subcommand)
    # This will show error handling when conversion fails
    commands_to_try = [
        [
            "uv",
            "run",
            "python",
            "-m",
            "importobot",
            str(invalid_json),
            "/tmp/invalid_output.robot",
        ],
        ["python", "-m", "importobot", str(invalid_json), "/tmp/invalid_output.robot"],
    ]

    for command in commands_to_try:
        print(f"Trying validation: {' '.join(command[:4])} ...")
        exit_code, stdout, stderr = run_command(command, cwd=root_dir)

        if exit_code != 0:
            print(" Validation correctly detected issues")
            print("Validation output:")
            print(stderr if stderr else stdout)
            return

        print("Command executed but didn't detect expected issues")

    print("WARNING: Validation commands not available or didn't detect issues")


def help_and_documentation_example() -> None:
    """Demonstrate help and documentation features."""
    print("\n=== Help and Documentation Example ===")

    help_commands = [
        ["uv", "run", "python", "-m", "importobot", "--help"],
        ["python", "-m", "importobot", "--help"],
    ]

    for command in help_commands:
        print(f"\nRunning: {' '.join(command)}")
        exit_code, stdout, stderr = run_command(command, cwd=root_dir)

        if exit_code == 0:
            print("Output:")
            print("-" * 20)
            print(stdout[:200] + "..." if len(stdout) > 200 else stdout)
            break  # Stop after first successful command

        print(f"Command failed: {stderr}")


def main() -> int:
    """Run all CLI examples."""
    print("Importobot CLI Examples")
    print("=" * 50)

    # Ensure example directories exist
    (root_dir / "examples" / "output").mkdir(parents=True, exist_ok=True)
    (root_dir / "examples" / "json").mkdir(parents=True, exist_ok=True)

    try:
        # Run CLI examples
        basic_cli_example()
        file_conversion_cli_example()
        batch_processing_cli_example()
        pipeline_integration_example()
        validation_cli_example()
        help_and_documentation_example()

        print("\n" + "=" * 50)
        print("CLI examples completed!")

        # Show generated files
        output_files = list((root_dir / "examples" / "output").rglob("*.robot"))
        if output_files:
            print("\nGenerated Robot Framework files:")
            for file in output_files:
                print(f"  File: {file}")

    except Exception as e:
        print(f"\nError running CLI examples: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
