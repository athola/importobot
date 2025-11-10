# ADR-0006: API Client Module Refactoring

## Status

Implemented – November 2025

## Context

The `importobot.integrations.clients` module had grown to over 1,200 lines within a single `__init__.py` file, encompassing:
-   A base API client with retry logic, circuit breaker, and rate limiting (over 300 lines).
-   Four platform-specific client implementations (each over 200 lines).
-   Shared utilities and protocols (over 100 lines).

### Problems

1.  **Poor Maintainability**: A single 1,200-line file hindered code navigation and understanding.
2.  **Tight Coupling**: Consolidating all clients in one file increased the risk of unintended dependencies.
3.  **Testing Complexity**: Modifications to one client could inadvertently affect tests for other clients.
4.  **Code Review Burden**: Large file changes necessitated reviewing unrelated client logic.
5.  **Import Bloat**: Importing any client resulted in loading all client implementations.

### Metrics

-   File size: Over 1,200 lines.
-   Number of classes: 5 (BaseAPIClient + 4 platform clients).
-   Cyclomatic complexity: High, attributed to multiple authentication strategies per client.
-   Test coupling: 38 test files imported from this single module.

## Decision

We will split `importobot.integrations.clients/__init__.py` into focused modules, each with clear responsibilities.

### Module Structure

```
src/importobot/integrations/clients/
├── __init__.py          # Public API re-exports (89 lines)
├── base.py             # BaseAPIClient, protocols, shared utilities
├── zephyr.py           # ZephyrClient implementation
├── jira_xray.py        # JiraXrayClient implementation
├── testrail.py         # TestRailClient implementation
└── testlink.py         # TestLinkClient implementation
```

### Design Principles

1.  **Single Responsibility**: Each file will contain a single client implementation or shared base functionality.
2.  **Clear Boundaries**: Platform-specific logic will be isolated from shared infrastructure.
3.  **Stable Public API**: The `__init__.py` file will re-export public APIs to maintain backward compatibility.
4.  **Improved Testability**: Each module can now be tested independently.

### Public API Design

```python
# Public API (unchanged for users)
from importobot.integrations.clients import (
    ZephyrClient,
    JiraXrayClient,
    TestRailClient,
    TestLinkClient,
    BaseAPIClient,
    APISource,
    get_api_client,
)

# Advanced users can import from specific modules
from importobot.integrations.clients.zephyr import ZephyrClient
from importobot.integrations.clients.base import BaseAPIClient
```

## Alternatives Considered

### Alternative 1: Keep Single File with Better Organization
**Rejected**: Comments and sections do not fundamentally resolve the maintainability issues of a 1,200-line file, which remains difficult to navigate and test.

### Alternative 2: Split Into Package Per Client
```
clients/
├── zephyr/
│   ├── __init__.py
│   ├── client.py
│   └── auth.py
├── jira_xray/
│   └── ...
```

**Rejected**: This approach was deemed over-engineering for the current complexity. Each client, being 200-300 lines, does not necessitate package-level organization, and this structure would introduce unnecessary nesting and more complex imports.

### Alternative 3: Monolithic clients.py File
**Rejected**: This represents the current problematic approach that this ADR aims to resolve.

## Consequences

### Positive

1.  **Improved Maintainability**: Each module is now under 400 lines, simplifying navigation.
2.  **Better Separation of Concerns**: Platform-specific logic is clearly separated from shared base infrastructure.
3.  **Faster Imports**: Only necessary client implementations are loaded, reducing import times.
4.  **Easier Testing**: Test files can import only the specific components they need.
5.  **Clearer Git History**: Changes to one client (e.g., `ZephyrClient`) do not appear in diffs for unrelated clients (e.g., `TestRailClient`).
6.  **Lower Review Burden**: Pull requests affecting a single client do not require reviewing unrelated client logic.

### Negative

1.  **Increased File Count**: The refactoring results in 6 files instead of 1, which is considered a manageable trade-off.
2.  **Import Path Changes**: Advanced users who directly import from sub-modules will need to update their import paths (as documented in the CHANGELOG).

### Migration Impact

**For 0.1.x users (none exist)**: No impact, as breaking changes are acceptable for pre-1.0 versions.

**For future 1.0 users**:
-   The public API remains unchanged; imports from `importobot.integrations.clients` function as before.
-   Advanced imports from sub-modules are documented with examples.
-   Typical migration time is estimated to be less than 5 minutes.

## Implementation Notes

### File Organization

**`base.py`** (shared infrastructure):
-   `BaseAPIClient`: Provides retry logic, circuit breaker, and rate limiting.
-   `APISource` protocol: Defines the interface that all clients must implement.
-   `_KeyBatch`, `_default_user_agent()`: Contains shared utility functions.

**Platform clients** (`zephyr.py`, `jira_xray.py`, `testrail.py`, `testlink.py`):
-   Each file encapsulates a single client class.
-   Includes authentication strategies specific to the platform.
-   Contains pagination logic tailored to the respective API.

**`__init__.py`** (public API):
-   Re-exports all public classes and functions.
-   Maintains backward compatibility.
-   Documents recommended usage patterns.

### Performance Impact

The module splitting is expected to have **negligible performance impact**:
-   Python's import system caches modules after the first load.
-   No additional runtime overhead is introduced.
-   Import time may slightly improve due to lazy loading.

Measured impact: Approximately 0-2ms difference in import time (within noise threshold).

## References

- Test suite quality improvements PR (November 2025)
- CHANGELOG.md "Unreleased" section
- PEP 8 - Style Guide for Python Code (module organization)

## Review & Updates

- **Created**: 2025-11-06
- **Last Updated**: 2025-11-06
- **Status**: Implemented
- **Related ADRs**: ADR-0003 (API Integration)
