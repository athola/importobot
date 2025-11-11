# Application Context Implementation Guide

This document provides detailed guidance for implementing the Application Context pattern, as adopted in [ADR-0004](ADR-0004-application-context-pattern.md).

## Overview

The Application Context pattern replaces module-level global variables with thread-local context management, facilitating cleaner dependency injection, improved test isolation, and enhanced concurrency support.

## Implementation Details

### Core Components

#### `ApplicationContext` Class
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
        """Clears all cached services within the context."""
        for attr in list(self.__dict__.keys()):
            if attr.startswith("_"):
                delattr(self, attr)

    def reset(self) -> None:
        """Resets the entire context to a clean state."""
        self.__dict__.clear()
```

#### Context Management Functions
```python
import threading
from typing import Optional

_context_local = threading.local()

def get_context() -> ApplicationContext:
    """Retrieves the current thread's application context. If no context exists, a new one is created."""
    if not hasattr(_context_local, "context"):
        _context_local.context = ApplicationContext()
    return _context_local.context

def set_context(context: ApplicationContext) -> None:
    """Sets the current thread's application context."""
    _context_local.context = context

def clear_context() -> None:
    """Clears the current thread's application context."""
    if hasattr(_context_local, "context"):
        delattr(_context_local, "context")
```

### Migration Strategy

#### Backward Compatibility
Existing helper functions continue to operate, now leveraging the application context internally:

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
    """Retrieves the performance cache from the current context."""
    return get_context().performance_cache
```

#### New Code Pattern
```python
def my_function(context: Optional[ApplicationContext] = None):
    """Demonstrates a function with optional context injection."""
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

    # Access and use services from the context...
```

### Testing with Clean Context
```python
import pytest
from importobot.context import clear_context

@pytest.fixture(autouse=True)
def clean_context():
    """Ensures each test operates with a fresh, isolated context."""
    clear_context()
    yield
    clear_context()

def test_cache_behavior():
    # Test specific cache behavior within an isolated context
    pass
```

### Integration Testing with Custom Context
```python
from importobot.context import ApplicationContext, set_context

def test_integration():
    test_context = ApplicationContext()
    set_context(test_context)

    # Execute code that relies on the application context
    result = run_conversion()

    # Verify results using the same custom context
    stats = test_context.performance_cache.get_cache_stats()
    assert stats["cache_hits"] > 0
```

### Multi-threading Support
```python
import threading
from importobot.context import get_context

def worker_function():
    context = get_context()  # Each thread automatically receives its own isolated context
    cache = context.performance_cache
    # Perform thread-safe operations using the context...

threads = []
for i in range(5):
    thread = threading.Thread(target=worker_function)
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

### Context Manager Usage (Recommended)
The `ApplicationContext` supports Python's context manager protocol, enabling automatic cleanup and preventing memory leaks:

```python
from importobot.context import get_context, ApplicationContext

# Direct usage with automatic cleanup
def process_batch():
    with ApplicationContext() as context:
        cache = context.performance_cache
        telemetry = context.telemetry_client

        # Process items using services from the context...

    # The context is automatically cleaned up upon exiting the 'with' block.
    # No manual cleanup is required.

# Using with global context function
def api_handler():
    with get_context() as context:
        # The context is automatically set and cleaned up.
        result = process_request(context)
        return result
    # The global context is cleared automatically.

# Exception handling - cleanup always occurs
def risky_operation():
    with ApplicationContext() as context:
        try:
            result = perform_operation(context)
            return result
        except Exception:
            # Handle error
            raise
    # The context is cleaned up even if an exception occurs.

# Nested context managers for isolation
def isolated_work():
    with ApplicationContext() as outer_ctx:
        # Outer context setup
        outer_cache = outer_ctx.performance_cache

        with ApplicationContext() as inner_ctx:
            # Inner context is isolated from the outer context.
            inner_cache = inner_ctx.performance_cache
            # Perform work here with a clean inner context.

        # The inner context is automatically cleaned up.
        # Execution returns to the outer context.
```

**Benefits of Context Manager Usage:**
-   **Automatic Cleanup**: Eliminates the need for manual calls to `reset()` or `clear_context()`.
-   **Exception Safety**: Ensures cleanup occurs reliably, even when exceptions are raised.
-   **Memory Leak Prevention**: Prevents the accumulation of contexts in thread pools.
-   **Cleaner Code**: Provides clear resource management through the use of `with` statements.
-   **Thread Pool Safe**: Ideal for use in concurrent environments.

### Benefits Achieved

### Test Isolation
-   Each test receives a fresh context via the `clear_context()` fixture.
-   Ensures no shared state between test cases.
-   Promotes deterministic test behavior.

### Thread Safety
-   Achieves automatic isolation through thread-local storage.
-   Eliminates the need for explicit locking mechanisms.
-   Enables concurrent access without race conditions.

### Dependency Injection
-   Facilitates explicit context parameters for testing.
-   Allows for mocking or overriding services in integration tests.
-   Promotes a clean separation of concerns.

### Memory Management
-   Lazy loading effectively reduces the memory footprint.
-   Automatic cleanup is performed via context reset.
-   Prevents lingering global state.

### Cleanup Responsibilities
-   Invoke `clear_context()` when a worker thread completes to release thread-local state.
-   For web frameworks, register `clear_context` in teardown hooks (e.g., `finally` blocks or request middleware).
-   In background executors, wrap job functions with `try/finally` to ensure `clear_context()` is called.
-   Tests should utilize the provided `clear_context` fixture to guarantee isolation between test cases.
-   Long-running threads may periodically call `clear_context()` if their dependencies are reset.

### Size and Resource Guards
-   **Schemas**: Individual schema files are limited to `MAX_SCHEMA_FILE_SIZE_BYTES` (default 1 MB) via `IMPORTOBOT_MAX_SCHEMA_BYTES` to prevent oversized metadata ingestion.
-   **Templates**: Blueprint sources adhere to `MAX_TEMPLATE_FILE_SIZE_BYTES` (default 2 MB, environment variable `IMPORTOBOT_MAX_TEMPLATE_BYTES`) during ingestion to prevent risky template payloads.
-   **Caches**: In-memory detection cache payloads are capped by `MAX_CACHE_CONTENT_SIZE_BYTES` (default 50 KB, environment variable `IMPORTOBOT_MAX_CACHE_CONTENT_BYTES`), with explicit rejection logging when this limit is exceeded.

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Context lookup | O(1) | Thread-local dictionary access. |
| Service creation | O(1) | Lazy initialization. |
| Context cleanup | O(n) | n = number of cached services. |
| Thread isolation | Automatic | No additional overhead. |

## Migration Checklist

### For Existing Code
-   [ ] Update global variable usage to leverage `get_context()`.
-   [ ] Add context clearing fixtures to relevant test suites.
-   [ ] Verify thread safety in concurrent scenarios.
-   [ ] Update documentation to reflect new patterns.

### For New Code
-   [ ] Use `get_context()` for service access.
-   [ ] Add optional context parameters to enhance testability.
-   [ ] Follow the lazy loading pattern for new services.
-   [ ] Document context dependencies in function signatures.

## Future Extensions

The context pattern facilitates the straightforward addition of:
-   Database connection pools.
-   API client configurations.
-   Logging context.
-   Metrics collectors.
-   Configuration providers.
-   Security contexts.

This can be achieved without introducing global state or breaking existing functionality.
