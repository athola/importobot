# Blueprint Learning Pipeline

Importobot learns Robot Framework structure from existing suites so conversions remain consistent. The learning subsystem sits inside `importobot.core.templates.blueprints.registry` and is composed of four collaborating services:

- **TemplateRegistry** – in-memory map of template keys to sanitised `SandboxedTemplate` objects. Keys are normalised variants of the original file stem (`foo`, `Foo`, `foo_bar`, etc.).
- **KnowledgeBase** – bucketed store of `StepPattern` instances keyed by location (`cli`, `target`, `host`) and command tokens.
- **KeywordLibrary** – inventory of keyword names scraped from Robot resources and Python helpers. Populates autocomplete-style suggestions during conversion.
- **ResourceImports** – list of resource references discovered while parsing templates, used to emit deterministic `Resource` statements in generated suites.

## Processing Stages

1. **Ingestion**  
   - `configure_template_sources` clears all registries, resolves user-supplied paths (supports `NAME=path` overrides), enforces CWD confinement, and imposes file-count and file-size limits (`MAX_TEMPLATE_FILES`, `MAX_TEMPLATE_FILE_SIZE_BYTES`).  
   - `_ingest_source_file` normalises line endings, strips BOMs, and rejects binary samples. Resources and Python helpers flow through the same sanitisation path to keep the registry consistent.
2. **Pattern extraction**  
   - `_learn_from_template` iterates Robot blocks beginning with `Switch Connection`, isolates the command token from subsequent `Write` or `Execute Command` statements, and generates a placeholder-aware `StepPattern`.  
   - `_learn_from_python` AST-parses helper modules to surface keyword names while ignoring invalid syntax.
3. **Knowledge base refresh**  
   - Cleaned templates are registered under every derived key, patterns are stored in the knowledge base, and resource imports are deduplicated through `_format_resource_reference` to keep relative paths stable when the blueprint directory moves.
4. **Conversion**  
   - When the converter encounters a JSON step, it calls `find_step_pattern`. The knowledge base returns the best match for the command token (falling back to generic patterns when requested). The sequencer then emits the stored line skeleton with context-specific substitutions; if no pattern is found, Importobot falls back to the deterministic renderer.

The pipeline is intentionally stateless between invocations—callers should initialise templates once at process start. Repeated calls to `configure_template_sources` remain supported (they rebuild the registry) but incur proportional ingestion cost.

## Error Handling

- Unreadable templates/resources raise `TemplateIngestionError`, emit a warning, and the offending path is skipped. Tests cover unreadable files, symlinks, oversize payloads, and directory traversal attempts.
- Invalid helper modules (syntax errors, disallowed placeholders, inline `Evaluate`, etc.) trigger `TemplateIngestionError` and do not poison the registry.
- Conversion never aborts due to a bad template; defaults ensure output is produced even when all template sources fail.

## Troubleshooting

- Run Importobot with `--robot-template` to load custom suites. Check logs for warnings about skipped files.
- Ensure helper Python modules compile cleanly and expose Robot-friendly keywords.
- Use the performance benchmarks (`make perf-test`) to verify lazy-loading improvements remain healthy after template changes.

## Testing Strategy

- Property-based tests (`tests/generative/test_blueprint_learning_generative.py`) synthesise Robot templates with varied encodings, placeholders, and command shapes to guarantee ingestion, sanitisation, and pattern learning stay resilient.
- Unit tests in `tests/unit/templates/test_blueprint_registry.py` exercise guardrails (size limits, traversal prevention, BOM stripping, unreadable files, disallowed placeholders).
- Integration tests (`tests/integration/test_cli_task_blueprint.py`, `test_cli_task_cross_template.py`) verify that learned patterns influence end-to-end conversions.
