# ADR-0003: API Integration Architecture

**Status**: Implemented
**Date**: 2025-10-16
**Decision**: Enable direct API ingestion for test platforms while preserving bronze/silver/gold architecture

## Context

Issue [#58](https://github.com/athola/importobot/issues/58) requested the ability to fetch test suites directly from supported platforms via API credentials, rather than requiring users to manually export and import JSON files.

## Decision

Implemented a flexible API client architecture that:

1. **Supports multiple platforms**: Jira/Xray, Zephyr for Jira, TestRail, and TestLink
2. **Preserves existing architecture**: Raw payloads feed into the bronze layer for normalization
3. **Provides flexible authentication**: CLI flags override environment variables
4. **Handles platform variability**: Adaptive discovery and secondary mechanisms

## Architecture

### Core Components

```
CLI Layer → API Client Factory → Platform-Specific Clients → Raw Payloads → Bronze Layer
```

**API Client Factory** (`importobot.integrations.clients`):
- `get_api_client()` factory function for client instantiation
- `APISource` protocol defining `fetch_all(progress_cb)` interface
- Centralized credential resolution and validation

**Platform-Specific Clients**:
- **ZephyrClient**: Adaptive API discovery, multiple auth strategies, configurable pagination
- **XrayClient**: Jira API integration with issue search and test case retrieval
- **TestRailClient**: Test run and case management API integration
- **TestLinkClient**: Legacy XML/JSON API integration

### Enhanced Zephyr Client

The Zephyr client implements sophisticated adaptation:

```python
class ZephyrClient(BaseAPIClient):
    # Configurable page sizes with auto-detection
    DEFAULT_PAGE_SIZES = [100, 200, 250, 500]

    # Multiple API endpoint patterns to try
    API_PATTERNS = [
        # Modern Zephyr Scale API pattern
        {"testcase_search": "/rest/atm/1.0/testcase/search"},
        # Legacy Zephyr for Jira pattern
        {"keys_search": "/rest/tests/1.0/testcase/search"},
        # Alternative patterns
        {"testcase_search": "/rest/zephyr/latest/testcase"}
    ]

    # Multiple authentication strategies
    AUTH_STRATEGIES = [
        {"type": "bearer", "header": "Authorization"},
        {"type": "api_key", "header": "X-Atlassian-Token"},
        {"type": "basic", "use_session_auth": True},
        {"type": "dual_token", "headers": ["Authorization", "X-Authorization"]}
    ]
```

### Configuration System

**CLI Arguments** (override environment variables):
```bash
--fetch-format zephyr
--api-url https://zephyr.example.com
--tokens token1,token2
--api-user username
--project PROJECT_KEY
--input-dir ./payloads
```

**Environment Variables**:
- `IMPORTOBOT_ZEPHYR_API_URL`
- `IMPORTOBOT_ZEPHYR_TOKENS`
- `IMPORTOBOT_ZEPHYR_API_USER`
- `IMPORTOBOT_ZEPHYR_PROJECT`
- `IMPORTOBOT_API_INPUT_DIR`
- `IMPORTOBOT_API_MAX_CONCURRENCY`

## Implementation Details

### API Discovery Process

1. **Pattern Discovery**: Try endpoint patterns until finding working configuration
2. **Secondary Authentication Strategies**: Attempt multiple auth strategies automatically
3. **Pagination Adaptation**: Test page sizes (100, 200, 250, 500) to find optimal limits
4. **Payload Structure Handling**: Extract results from various response formats

### Data Flow

1. **API Ingestion**: `handle_api_ingest()` orchestrates client instantiation and data retrieval
2. **Progress Tracking**: Real-time progress callbacks during large fetches
3. **Payload Storage**: Raw JSON saved to configured directory with metadata
4. **Bronze Integration**: Saved files feed into existing bronze layer processing
5. **Conversion Pipeline**: Standard silver/gold processing continues unchanged

### Error Handling

- **Authentication Failures**: Clear error messages with configuration suggestions
- **Rate Limiting**: Exponential backoff with jitter and `Retry-After` header support
- **Network Issues**: Configurable retry budgets and timeout handling
- **Payload Validation**: JSON structure validation before bronze layer processing

## Security Considerations

- **Token Masking**: All tokens masked in logs and error messages
- **Secure Storage**: Recommendation for environment variables over shell history
- **Input Validation**: URL validation and credential format checking
- **Audit Trail**: Metadata files record fetch details without exposing secrets

## Consequences

### Positive

- **Improved User Experience**: Single-command fetch and conversion
- **Automation Ready**: Direct CI/CD integration without manual export steps
- **Platform Flexibility**: Adapts to different server configurations automatically
- **Architecture Preservation**: No changes to existing bronze/silver/gold pipeline
- **Extensibility**: Easy to add new platform clients following established patterns

### Negative

- **Increased Complexity**: Additional authentication and error handling logic
- **Dependency Management**: HTTP client dependencies and retry logic
- **Testing Surface**: More integration scenarios requiring test coverage

### Risks

- **API Changes**: Platform APIs may evolve, requiring client updates
- **Authentication Complexity**: Dual-token and multi-auth scenarios increase complexity
- **Rate Limiting**: Aggressive fetching may trigger platform rate limits

## Migration Path

1. **Backward Compatibility**: Existing file-based conversion unchanged
2. **Gradual Adoption**: Users can adopt API integration incrementally
3. **Alternative Options**: File import remains available when API integration fails
4. **Configuration Migration**: Environment variables provide easy credential management

## Future Enhancements

- **Caching**: ETag support for conditional requests
- **Async Fetching**: Concurrent request handling for large datasets
- **Resume Capability**: Resume interrupted downloads from last known state
- **Additional Platforms**: Extend pattern to other test management systems

---
