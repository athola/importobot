# ADR-0006: API Client Module Refactoring

## Status

Implemented – November 2025

## Context

The `importobot.integrations.clients` module had grown to 1,200+ lines in a single `__init__.py` file containing:
- Base API client with retry logic, circuit breaker, and rate limiting (300+ lines)
- Four platform-specific client implementations (200+ lines each)
- Shared utilities and protocols (100+ lines)

### Problems

1. **Poor Maintainability**: Single 1,200-line file made code navigation difficult
2. **Coupling**: All clients in one file increased risk of unintended dependencies
3. **Testing Complexity**: Changes to one client could break tests for other clients
4. **Code Review Burden**: Large file changes required reviewing unrelated client logic
5. **Import Bloat**: Importing any client loaded all client implementations

### Metrics

- File size: 1,200+ lines
- Number of classes: 5 (BaseAPIClient + 4 platform clients)
- Cyclomatic complexity: High due to multiple authentication strategies per client
- Test coupling: 38 test files importing from single module

## Decision

Split `importobot.integrations.clients/__init__.py` into focused modules with clear responsibilities.

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

1. **Single Responsibility**: Each file contains one client implementation or shared base functionality
2. **Clear Boundaries**: Platform-specific logic isolated from shared infrastructure
3. **Stable Public API**: `__init__.py` re-exports maintain backward compatibility
4. **Testability**: Each module can be tested independently

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
**Rejected** - Comments and sections don't solve the fundamental maintainability issue. A 1,200-line file with "clear sections" is still difficult to navigate and test.

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

**Rejected** - Over-engineering for current complexity. Each client is 200-300 lines and doesn't need package-level organization. This structure adds unnecessary nesting and makes imports more complex.

### Alternative 3: Monolithic clients.py File
**Rejected** - Current approach. Led to the problems we're solving.

## Consequences

### Positive

1. **Improved Maintainability**: Each module is <400 lines, easy to navigate
2. **Better Separation**: Platform-specific logic clearly separated from shared base
3. **Faster Imports**: Only load needed client implementations
4. **Easier Testing**: Test files can import only what they need
5. **Clearer Git History**: Changes to ZephyrClient don't show up in TestRail diffs
6. **Lower Review Burden**: PRs touching one client don't require reviewing others

### Negative

1. **More Files**: 6 files instead of 1 (manageable trade-off)
2. **Import Changes**: Advanced users importing directly need to update paths (documented in CHANGELOG)

### Migration Impact

**For 0.1.x users (none exist):** No impact - breaking changes acceptable

**For future 1.0 users:**
- Public API unchanged - imports from `importobot.integrations.clients` work as before
- Advanced imports from sub-modules documented with examples
- Migration time: <5 minutes for typical usage

## Implementation Notes

### File Organization

**base.py** (shared infrastructure):
- `BaseAPIClient` - Retry logic, circuit breaker, rate limiting
- `APISource` protocol - Interface all clients implement
- `_KeyBatch`, `_default_user_agent()` - Shared utilities

**Platform clients** (zephyr.py, jira_xray.py, testrail.py, testlink.py):
- Each file contains one client class
- Authentication strategies specific to platform
- Pagination logic specific to API

**__init__.py** (public API):
- Re-exports all public classes and functions
- Maintains backward compatibility
- Documents recommended usage patterns

### Performance Impact

Module splitting should have **negligible performance impact**:
- Python's import system caches modules after first load
- No additional runtime overhead
- Import time may slightly improve (lazy loading)

Measured impact: ~0-2ms difference in import time (within noise threshold)

## References

- Test suite quality improvements PR (November 2025)
- CHANGELOG.md "Unreleased" section
- PEP 8 - Style Guide for Python Code (module organization)

## Review & Updates

- **Created**: 2025-11-06
- **Last Updated**: 2025-11-06
- **Status**: Implemented
- **Related ADRs**: ADR-0003 (API Integration)
