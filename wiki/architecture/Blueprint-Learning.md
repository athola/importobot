# Blueprint Learning Pipeline

Importobot learns Robot Framework structure from existing suites so conversions remain consistent.

## Processing Stages

1. **Ingestion** – The registry loads `.robot`, resource, and helper Python files from user-defined directories. Any unreadable file surfaces as a warning (without stopping the run).
2. **Pattern extraction** – Robot sections are analysed to capture step patterns (connection, command token, command body) and keyword/resource metadata.
3. **Knowledge base** – Extracted patterns are stored in an in-memory knowledge base keyed by location (CLI/host/target) and command tokens.
4. **Conversion** – During JSON→Robot conversion, the blueprint matches each step against the knowledge base, falling back to the generated default renderer when no pattern matches.

## Error Handling

- Unreadable templates/resources raise `TemplateIngestionError` and are skipped with a warning.
- Invalid helper modules (syntax errors, etc.) are treated similarly—logged and ignored.
- Conversion never aborts due to a bad template; defaults ensure output is produced.

## Troubleshooting

- Run Importobot with `--robot-template` to load custom suites. Check logs for warnings about skipped files.
- Ensure helper Python modules compile cleanly and expose Robot-friendly keywords.
- Use the performance benchmarks (`make perf-test`) to verify lazy-loading improvements remain healthy after template changes.
