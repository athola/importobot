#!/bin/bash
# Example CI/CD pipeline integration for Importobot

set -e  # Exit on error

echo "Starting automated test conversion pipeline..."

# Define directories
INPUT_DIR="/home/alext/importobot/examples/json"
OUTPUT_DIR="/home/alext/importobot/examples/output/pipeline"
REPORT_FILE="/home/alext/importobot/examples/conversion_report.txt"

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
        output_file="$OUTPUT_DIR/${filename}.robot"

        echo "Processing: $json_file"
        TOTAL_COUNT=$((TOTAL_COUNT + 1))

        # Attempt conversion with uv run first, then use the secondary path
        if cd "/home/alext/importobot" && uv run python -m importobot \
            "$json_file" "$output_file" 2>/dev/null; then
            echo " SUCCESS: $filename" >> \
                "$REPORT_FILE"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        elif cd "/home/alext/importobot" && python -m importobot \
            "$json_file" "$output_file" 2>/dev/null; then
            echo " SUCCESS: $filename" >> \
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
