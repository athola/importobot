# ADR-0003: Direct API Ingestion from Test Management Tools

**Status**: Implemented
**Date**: 2025-10-16

## Context

Users requested the ability to fetch test suites directly from platforms like Jira and TestRail, as documented in Issue [#58](https://github.com/athola/importobot/issues/58). This would avoid the manual process of exporting and importing files.

## Decision

We will create a set of API clients to ingest data directly from supported test management platforms. The raw data fetched from the APIs will be treated as a new data source for the existing Medallion (Bronze/Silver/Gold) pipeline.

This approach will:

1.  **Support multiple platforms**: Initially Jira/Xray, Zephyr, TestRail, and TestLink.
2.  **Reuse the existing pipeline**: Raw API payloads will be saved and fed into the Bronze layer, requiring no changes to the Silver or Gold layers.
3.  **Offer flexible authentication**: Users can provide credentials via CLI flags, which override environment variables.
4.  **Adapt to platform differences**: The clients will automatically discover API endpoints and try multiple authentication strategies to handle variations between different server versions and configurations.

## Architecture

The data flows from the command line, through a client factory to a platform-specific client, and the resulting payload is sent to the Bronze layer.

```
CLI Layer → API Client Factory → Platform-Specific Clients → Raw Payloads → Bronze Layer
```

### Core Components

**API Client Factory** (`importobot.integrations.clients`)

This module is responsible for creating the correct API client. It contains:
- A factory function, `get_api_client()`, that returns a specific client based on the requested platform.
- The `APISource` protocol, which defines the common interface that all clients must implement (e.g., `fetch_all()`).
- Centralized logic for resolving and validating credentials from the CLI and environment variables.

**Platform-Specific Clients**

Each supported platform has its own client:
- **ZephyrClient**: Handles variations in Zephyr API endpoints, authentication methods, and pagination.
- **XrayClient**: Interacts with the Jira API to search for and retrieve test cases.
- **TestRailClient**: Connects to the TestRail API for test run and case data.
- **TestLinkClient**: Manages integration with the older TestLink XML/JSON API.

### Zephyr Client Example

The `ZephyrClient` is the most complex, as it must handle significant variation between different Zephyr server instances. It is configured to automatically try multiple API endpoint patterns, authentication strategies, and page sizes.

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

To handle variations in platforms (particularly Zephyr), the clients perform an automatic discovery process upon connection:

1.  **Endpoint Discovery**: The client attempts to connect to a list of known API endpoint patterns to find a valid one.
2.  **Authentication Discovery**: If the initial authentication method fails, it automatically tries a series of secondary strategies (e.g., bearer token, API key, basic auth).
3.  **Pagination Discovery**: The client tests different page sizes to find the most efficient one supported by the server.
4.  **Payload Adaptation**: The client can extract the test case data from several known response structures.

### Data Flow

The end-to-end process for API ingestion is as follows:

1.  The `handle_api_ingest()` function manages the process, creating a client and retrieving the data.
2.  For large test suites, the client can issue real-time progress callbacks.
3.  The raw JSON payloads fetched from the API are saved to a configured directory, along with a metadata file.
4.  These saved files are then passed to the Bronze layer, treating them the same as manually provided files.
5.  The rest of the conversion pipeline (Silver and Gold layers) continues without any changes.

### Error Handling

The API clients include robust error handling:
- **Authentication Failures**: If authentication fails, the tool provides clear error messages suggesting which credentials might be incorrect.
- **Rate Limiting**: The clients respect `Retry-After` headers and use an exponential backoff strategy with jitter to avoid overwhelming the server API.
- **Network Issues**: Connection timeouts and temporary network failures are handled with a configurable number of retries.
- **Payload Validation**: The structure of the fetched JSON is validated before it is passed to the Bronze layer.

## Security Considerations

The following security measures are in place:
- **Token Masking**: Authentication tokens are masked in all logs and error messages to prevent accidental exposure.
- **Secure Storage**: The documentation recommends using environment variables for storing credentials, as they are less likely to be exposed in shell history.
- **Input Validation**: All user-provided inputs, such as API URLs and credentials, are validated.
- **Audit Trail**: The metadata files saved alongside the fetched payloads record details of the fetch operation without including any secrets.

## Consequences

### Positive

- Users can now fetch and convert tests with a single command.
- The feature can be integrated directly into CI/CD pipelines, removing the need for manual exports.
- The client's adaptive nature allows it to work with different server versions and configurations automatically.
- The existing Medallion pipeline is reused without modification.
- The design makes it straightforward to add clients for new platforms in the future.

### Negative

- The overall codebase complexity is higher due to the new authentication and error handling logic.
- New dependencies for the HTTP client and retry logic have been added.
- The testing surface area has increased, requiring more integration tests.

### Risks

- **API Instability**: Future changes to a platform's API may break a client, requiring maintenance.
- **Authentication Complexity**: Supporting multiple authentication methods for a single platform adds complexity.
- **Rate Limiting**: Fetching very large test suites may trigger rate limits on the target platform.

## Adoption Strategy

The introduction of this feature does not remove any existing functionality.
- **Backward Compatibility**: File-based conversion works exactly as it did before.
- **Gradual Adoption**: Users can continue to use file-based workflows and adopt the API integration at their own pace.
- **Default Option**: File-based import remains a stable option if API integration is not desired or fails.
- **Configuration**: Using environment variables for credentials allows for easy and secure configuration management.

## Future Work

The following enhancements could be built on this architecture:
- **Caching**: Use `ETag` headers to avoid re-downloading unchanged test suites.
- **Asynchronous Fetching**: Use concurrent requests to speed up fetching of large data sets.
- **Resumable Downloads**: Add the ability to resume an interrupted download.
- **New Platforms**: Add clients for other test management systems.

---
