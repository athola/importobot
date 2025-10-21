# Application Context Implementation Guide

This document provides detailed implementation guidance for the Application Context pattern adopted in ADR-0004.

## Overview

The Application Context pattern replaces module-level global variables with thread-local context management for cleaner dependency injection, better test isolation, and improved concurrency support.

## Implementation Details

### Core Components

#### ApplicationContext Class
```python
class ApplicationContext:
    """Thread-local application context for managing dependencies."""

    @property
    def performance_cache(self) -> PerformanceCache:
        """Lazy-loaded performance cache instance."""
        if not hasattr(self, "_performance_cache"):
            self._performance_cache = PerformanceCache()
        return self._performance_cache

    @property
    def telemetry_client(self) -> TelemetryClient:
        """Lazy-loaded telemetry client instance."""
        if not hasattr(self, "_telemetry_client"):
            self._telemetry_client = TelemetryClient()
        return self._telemetry_client

    def clear_caches(self) -> None:
        """Clear all cached services."""
        for attr in list(self.__dict__.keys()):
            if attr.startswith("_"):
                delattr(self, attr)

    def reset(self) -> None:
        """Reset entire context to clean state."""
        self.__dict__.clear()
```

#### Context Management Functions
```python
import threading
from typing import Optional

_context_local = threading.local()

def get_context() -> ApplicationContext:
    """Get current thread's application context."""
    if not hasattr(_context_local, "context"):
        _context_local.context = ApplicationContext()
    return _context_local.context

def set_context(context: ApplicationContext) -> None:
    """Set current thread's application context."""
    _context_local.context = context

def clear_context() -> None:
    """Clear current thread's application context."""
    if hasattr(_context_local, "context"):
        delattr(_context_local, "context")
```

### Migration Strategy

#### Backward Compatibility
Existing helper functions continue to work but now use the context internally:

```python
# Before: Global variable approach
_global_cache: PerformanceCache | None = None

def get_performance_cache() -> PerformanceCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = PerformanceCache()
    return _global_cache

# After: Context-based approach
def get_performance_cache() -> PerformanceCache:
    """Get performance cache from current context."""
    return get_context().performance_cache
```

#### New Code Pattern
```python
def my_function(context: Optional[ApplicationContext] = None):
    """Function with optional context injection."""
    context = context or get_context()
    cache = context.performance_cache
    # Use cache...
```

## Usage Examples

### Basic Service Access
```python
from importobot.context import get_context

def process_data():
    context = get_context()
    cache = context.performance_cache
    telemetry = context.telemetry_client

    # Use services...
```

### Testing with Clean Context
```python
import pytest
from importobot.context import clear_context

@pytest.fixture(autouse=True)
def clean_context():
    """Ensure each test gets fresh context."""
    clear_context()
    yield
    clear_context()

def test_cache_behavior():
    # Test with isolated context
    pass
```

### Integration Testing with Custom Context
```python
from importobot.context import ApplicationContext, set_context

def test_integration():
    test_context = ApplicationContext()
    set_context(test_context)

    # Run code that uses context
    result = run_conversion()

    # Verify using same context
    stats = test_context.performance_cache.get_cache_stats()
    assert stats["cache_hits"] > 0
```

### Multi-threading Support
```python
import threading
from importobot.context import get_context

def worker_function():
    context = get_context()  # Each thread gets its own context
    cache = context.performance_cache
    # Thread-safe operations...

threads = []
for i in range(5):
    thread = threading.Thread(target=worker_function)
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## Benefits Achieved

### Test Isolation
- Each test gets fresh context via `clear_context()` fixture
- No shared state between test cases
- Deterministic test behavior

### Thread Safety
- Automatic isolation via thread-local storage
- No explicit locking required
- Concurrent access without race conditions

### Dependency Injection
- Explicit context parameters for testing
- Mock/override services in integration tests
- Clean separation of concerns

### Memory Management
- Lazy loading reduces memory footprint
- Automatic cleanup via context reset
- No lingering global state

### Cleanup Responsibilities
- Call `clear_context()` when a worker thread finishes to release thread-local state
- Web frameworks: register `clear_context` in teardown hooks (e.g., `finally` blocks or request middleware)
- Background executors: wrap job functions with `try/finally` to invoke `clear_context()`
- Tests: use the provided `clear_context` fixture to guarantee isolation between cases
- Long-running threads can periodically call `clear_context()` if they reset dependencies

### Size and Resource Guards
- Schemas: individual schema files are limited to `MAX_SCHEMA_FILE_SIZE_BYTES` (default 1&nbsp;MB) via `IMPORTOBOT_MAX_SCHEMA_BYTES` to prevent oversized metadata ingestion.
- Templates: blueprint sources respect `MAX_TEMPLATE_FILE_SIZE_BYTES` (default 2&nbsp;MB, env `IMPORTOBOT_MAX_TEMPLATE_BYTES`) during ingestion to block risky template payloads.
- Caches: in-memory detection cache payloads are capped by `MAX_CACHE_CONTENT_SIZE_BYTES` (default 50&nbsp;KB, env `IMPORTOBOT_MAX_CACHE_CONTENT_BYTES`) with explicit rejection logging when exceeded.

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Context lookup | O(1) | Thread-local dictionary access |
| Service creation | O(1) | Lazy initialization |
| Context cleanup | O(n) | n = number of cached services |
| Thread isolation | Automatic | No additional overhead |

## Migration Checklist

### For Existing Code
- [ ] Update global variable usage to use `get_context()`
- [ ] Add context clearing fixtures to test suites
- [ ] Verify thread safety in concurrent scenarios
- [ ] Update documentation to reflect new patterns

### For New Code
- [ ] Use `get_context()` for service access
- [ ] Add optional context parameters for testability
- [ ] Follow lazy loading pattern for new services
- [ ] Document context dependencies in function signatures

## Future Extensions

The context pattern enables easy addition of:
- Database connection pools
- API client configurations
- Logging context
- Metrics collectors
- Configuration providers
- Security contexts

All without introducing global state or breaking existing functionality.
