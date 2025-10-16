# API Retrieval Implementation Plan

This document outlines the implementation plan for issue [#58](https://github.com/athola/importobot/issues/58), enabling Importobot to fetch test suites directly from supported platforms via API credentials, while keeping the existing bronze/silver/gold architecture contract intact.

## Requirements & Scope
- Support direct API ingestion for Jira/Xray, Zephyr for Jira, TestRail, and TestLink.
- Allow users to supply authentication both from CLI flags (`--api-url`, `--tokens`, `--api-user`, `--project`, etc.) and environment variables (`IMPORTOBOT_<FORMAT>_API_URL`, `IMPORTOBOT_<FORMAT>_TOKENS`, ...).
- Preserve raw payloads as-is; rely on the bronze detection pipeline for normalization.
- Handle pagination/rate limiting for large suites and provide progress feedback.
- Save retrieved JSON into `--input-dir` when provided, otherwise to the current working directory, and optionally pass the saved file into the conversion workflow.

## CLI & Configuration Updates - COMPLETED
- Extend `src/importobot/cli/parser.py` with a new `--fetch-format` flag (values mapped to `SupportedFormat`), plus shared flags for API URL, tokens, username, project key, and optional output directory (`--input-dir` aliasing existing semantics).
- Ensure compatibility with existing conversion flags by structuring mutually exclusive groups carefully (fetch mode can coexist with conversions when both are supplied).
- Wire a new handler in `src/importobot/__main__.py` that can trigger API ingestion before invoking existing conversion paths.
- Centralize credential resolution in `src/importobot/config.py`: CLI arguments override environment variables; missing mandatory values should yield clear errors. Always mask tokens in logs and errors.
- Implement `--tokens` as a multi-value option (comma-separated or repeatable) so formats needing multiple secrets (e.g., Jira host token + Zephyr token) are supported.

## API Client & Pagination Layer - COMPLETED
- Add a new `importobot.integrations.clients` package with a base protocol (`APISource`) defining `fetch_all(progress_cb: Callable)` returning an iterator/generator of payload chunks.
- Implement format-specific clients:
  - **Jira/Xray**: support API key header auth, pagination via `startAt` / `maxResults`, and rate-limit handling.
  - **Zephyr**: handle dual-token auth and Jira host coordination. (ENHANCED - see critical insights below)
  - **TestRail**: support basic auth/token hybrid and pagination of runs/cases.
  - **TestLink**: handle API key auth and chunked retrieval.
- Use a single HTTP backend (`httpx` or `requests`) with retry/backoff, 429 handling, and optional concurrency limits for load balancing. Expose configuration via CLI/env for advanced users.
- Surface progress via callbacks (items fetched, total known/unknown, percentage) so the CLI can print progress bars or concise updates.

### ENHANCED ZEPHYR CLIENT DESIGN PRINCIPLES
The example `zephyr_data_pull_example.py` provides valuable insights, but we need a **more flexible approach** that accommodates various Zephyr server configurations and deployment patterns:

**Key Design Principles:**
1. **Adaptive API Discovery**: Support multiple Zephyr API patterns without hardcoding specific endpoints
2. **Configurable Authentication**: Handle various auth methods (Bearer token, Basic auth, API tokens, dual-token setups)
3. **Flexible Pagination**: Adapt to different server limits and API constraints
4. **Graceful Fallbacks**: Provide fallback mechanisms when preferred endpoints aren't available
5. **Server Configuration Detection**: Auto-detect server capabilities and adjust accordingly

**Enhanced Zephyr Client Architecture:**
```python
class ZephyrClient(BaseAPIClient):
    """
    Flexible Zephyr client that adapts to different server configurations.
    Supports multiple API patterns, authentication methods, and pagination strategies.
    """

    # Configurable page sizes with auto-detection fallback
    DEFAULT_PAGE_SIZES = [100, 200, 250, 500]

    # Multiple API endpoint patterns to try
    API_PATTERNS = [
        # Modern Zephyr Scale API pattern
        {
            "testcase_search": "/rest/atm/1.0/testcase/search",
            "test_executions": "/rest/atm/1.0/testexecutions",
            "requires_keys_stage": False,
        },
        # Legacy Zephyr for Jira pattern (like the example)
        {
            "keys_search": "/rest/tests/1.0/testcase/search",
            "details_search": "/rest/atm/1.0/testcase/search",
            "requires_keys_stage": True,
        },
        # Alternative Zephyr patterns
        {
            "testcase_search": "/rest/zephyr/latest/testcase",
            "requires_keys_stage": False,
        }
    ]

    # Multiple authentication strategies
    AUTH_STRATEGIES = [
        {"type": "bearer", "header": "Authorization"},
        {"type": "api_key", "header": "X-Atlassian-Token"},
        {"type": "basic", "use_session_auth": True},
        {"type": "dual_token", "headers": ["Authorization", "X-Authorization"]},
    ]
```

## Data Retrieval Orchestration - COMPLETED
- Introduce `handle_api_ingest` in `src/importobot/cli/handlers.py` that:
  1. Resolves credentials/config via the new helpers.
  2. Instantiates the appropriate client through a factory.
  3. Streams paginated results, writing each page to disk (temporary file or in-memory merge) and ultimately persisting a single JSON document under the resolved directory (default: current working directory).
  4. Emits progress updates and handles retries/rate-limit warnings gracefully.
  5. If conversion flags/output are provided, injects the saved JSON path into the existing conversion handlers after ingestion completes.
- Reuse existing utilities in `importobot.utils.file_operations` where possible; extend them if necessary to avoid code duplication.

## Pagination & Load Balancing Tasks
- For each client, define pagination parameters (page size default, maximum items per request) and implement iteration respecting API contracts.
- Add adaptive rate limiting: respect `Retry-After` headers, implement exponential backoff with jitter, and allow user-configurable concurrency (e.g., `--max-concurrency`).
- Offer optional resume metadata (e.g., last page token) for extremely large suites, storing it alongside the downloaded JSON for future use.
- Provide clear CLI logging when pagination completes, including total items fetched and duration.

## Testing Strategy
- **Unit tests**: cover CLI argument parsing, credential precedence (CLI vs. env), pagination loops (mocked HTTP responses), retry/backoff logic, and progress callback invocation.
- **Integration tests**: add suites that simulate multi-page responses and verify merged JSON files are saved in the correct directory and optionally fed into conversion.
- **Failure cases**: ensure informative errors for authentication failures, pagination errors, and exhausted retry budgets without leaking secrets.
- Update or extend fixtures to represent platform-specific responses (e.g., Jira search results, TestRail run pages).

## Documentation & Release Notes
- Update README.md and wiki/User-Guide.md with new CLI usage examples, environment variable names, and token-handling guidance.
- Document format-specific token requirements and combinations (e.g., `--tokens jira_token,zephyr_token`) with explicit examples.
- Add notes on pagination behaviour, rate limiting, and storage locations to the wiki/Deployment-Guide or a new “API Retrieval” section.
- Record the feature under the “Unreleased” section in CHANGELOG.md and mention new dependencies in PACKAGING.md.

## Security & UX Considerations
- Mask tokens and sensitive values in logs; avoid printing full URLs when they contain credentials.
- Warn users about storing tokens in shell history; suggest environment variables or `.env` files as safer alternatives.
- Evaluate future enhancements such as secret-store integration, caching repeated fetches (ETag support), or asynchronous fetching for very large datasets; capture these as follow-up items.

## IMMEDIATE ACTION ITEMS

## IMPLEMENTATION STATUS - COMPLETED

### High Priority: Implement Flexible Zephyr Client - COMPLETED
1. **Design Adaptive ZephyrClient Architecture**:
   - Replace `ZephyrScaleClient` with flexible `ZephyrClient`
   - Implement API pattern discovery that tries multiple endpoint configurations
   - Support multiple authentication strategies with automatic fallback
   - Add configurable pagination with server limit detection

2. **Implement Multi-Strategy API Access**:
   - **API Discovery**: Try different endpoint patterns until finding working ones
   - **Authentication Fallbacks**: Support Bearer, Basic, API key, and dual-token auth
   - **Pagination Adaptation**: Auto-detect server limits and adjust batch sizes
   - **Query Flexibility**: Handle different JQL/query syntax variations

3. **Configuration-Driven Approach**:
   - Allow users to specify preferred API patterns via CLI/env vars
   - Support custom endpoint configurations for non-standard setups
   - Provide override options for authentication methods
   - Enable custom field selection and query parameters

4. **Robust Error Handling & Recovery**:
   - Graceful fallback when primary API patterns fail
   - Clear error messages suggesting configuration changes
   - Automatic retry with different strategies
   - Comprehensive logging for troubleshooting

5. **Enhanced Payload Structure Support**:
   - Extended `_extract_results` to handle various Zephyr response structures
   - Extended `_extract_total` to support different total count field names
   - Support for nested, wrapped, and legacy payload formats
   - Comprehensive test coverage for payload extraction variants

6. **Comprehensive Testing**:
   - Mock multiple Zephyr server configurations
   - Test authentication strategy fallbacks
   - Validate API discovery mechanisms
   - Test pagination adaptation and limit detection
   - Test payload structure extraction with comprehensive variants

### Medium Priority: Documentation Updates
4. **Update Documentation**:
   - Document specific Zephyr API patterns and requirements
   - Add example usage commands that match the working pattern
   - Update README with Zephyr-specific authentication notes

### Lower Priority: Performance Optimizations
5. **Future Enhancements**:
   - Consider caching of test case keys to avoid re-fetching
   - Add resume capability for interrupted large downloads
   - Implement concurrent fetching within Zephyr API limits

## Open Follow-Ups
- Clarify whether we need to normalize filenames per format (e.g., including project key/run ID).
- Decide on strategy for extremely large suites (splitting output files vs. single merged JSON) once MVP is delivered.
- Consider telemetry hooks to measure API fetch performance across formats for future optimization.
