# Blueprint Learning Pipeline

Importobot analyzes existing Robot Framework suites to ensure that new conversions remain consistent with established patterns. The learning subsystem, located in `importobot.core.templates.blueprints.registry`, comprises four collaborating services:

-   **TemplateRegistry**: An in-memory map of template keys to sanitized `SandboxedTemplate` objects. Keys are normalized variants of the original file stem (e.g., `foo`, `Foo`, `foo_bar`).
-   **KnowledgeBase**: A categorized store of `StepPattern` instances, keyed by location (`cli`, `target`, `host`) and command tokens.
-   **KeywordLibrary**: An inventory of keyword names extracted from Robot resources and Python helpers, used to populate autocomplete-style suggestions during conversion.
-   **ResourceImports**: A list of resource references discovered during template parsing, used to generate deterministic `Resource` statements in the final suites.

## Processing Stages

1.  **Ingestion**:
    -   `configure_template_sources` clears all registries, resolves user-supplied paths (supporting `NAME=path` overrides), enforces CWD confinement, and imposes file-count and file-size limits (`MAX_TEMPLATE_FILES`, `MAX_TEMPLATE_FILE_SIZE_BYTES`).
    -   `_ingest_source_file` normalizes line endings, strips BOMs, and rejects binary samples. Resources and Python helpers follow the same sanitization path to maintain registry consistency.
2.  **Pattern Extraction**:
    -   `_learn_from_template` iterates through Robot blocks beginning with `Switch Connection`, isolates the command token from subsequent `Write` or `Execute Command` statements, and generates a placeholder-aware `StepPattern`.
    -   `_learn_from_python` performs AST parsing of helper modules to extract keyword names while ignoring invalid syntax.
3.  **Knowledge Base Refresh**:
    -   Cleaned templates are registered under every derived key, patterns are stored in the knowledge base, and resource imports are deduplicated via `_format_resource_reference` to ensure stable relative paths when the blueprint directory is moved.
4.  **Conversion**:
    -   When the converter encounters a JSON step, it calls `find_step_pattern`. The knowledge base returns the best match for the command token, using generic patterns as a secondary option if requested. The sequencer then emits the stored line skeleton with context-specific substitutions. If no pattern is found, Importobot uses the deterministic renderer as a default.

The pipeline is intentionally stateless between invocations; callers should initialize templates once at the start of the process. Repeated calls to `configure_template_sources` are supported (they rebuild the registry) but incur a proportional ingestion cost.

## Error Handling

-   Unreadable templates or resources raise a `TemplateIngestionError`, emit a warning, and the offending path is skipped. Tests cover unreadable files, symlinks, oversized payloads, and directory traversal attempts.
-   Invalid helper modules (due to syntax errors, disallowed placeholders, inline `Evaluate`, etc.) trigger a `TemplateIngestionError` and do not corrupt the registry.
-   Conversion does not abort due to a bad template; default renderers ensure that output is produced even if all template sources fail.

## Troubleshooting

-   Run Importobot with `--robot-template` to load custom suites and check the logs for warnings about skipped files.
-   Ensure that helper Python modules compile cleanly and expose Robot-friendly keywords.
-   Use the performance benchmarks (`make perf-test`) to verify that lazy-loading improvements remain effective after template changes.

## Testing Strategy

-   Property-based tests (`tests/generative/test_blueprint_learning_generative.py`) generate Robot templates with varied encodings, placeholders, and command shapes to ensure that ingestion, sanitization, and pattern learning remain resilient.
-   Unit tests in `tests/unit/templates/test_blueprint_registry.py` validate security and robustness measures (e.g., size limits, traversal prevention, BOM stripping, unreadable files, disallowed placeholders).
-   Integration tests (`tests/integration/test_cli_task_blueprint.py`, `test_cli_task_cross_template.py`) verify that learned patterns correctly influence end-to-end conversions.
