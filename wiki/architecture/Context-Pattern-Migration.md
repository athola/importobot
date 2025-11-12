# Context Pattern Migration Guide

This guide expands on [ADR-0004](ADR-0004-application-context-pattern.md) and details the process of migrating existing modules from module-level singletons to the thread-local application context introduced in Importobot v0.1.3. These steps should be followed when upgrading legacy helpers, CLI commands, or integrations that still rely on global state.

## Before You Start

-   **Target Version**: Importobot v0.1.3 or later.
-   **Prerequisite Reading**: Review the [Application Context Implementation Guide](Application-Context-Implementation.md) for background information and API references.
-   **Local Test Execution**: Confirm that your tests can be run locally (e.g., using `make test` or `pytest`).
-   **Identify Modules**: Pinpoint modules that:
    -   Import `get_*` helpers backed by module-level globals.
    -   Mutate shared state (e.g., caches, telemetry clients) without accepting context arguments.
    -   Spawn worker threads without explicitly calling `clear_context()`.

## Migration Workflow

1.  **Inventory Global Access**:
    -   Search for assignments to `_global_*` variables or helpers that cache singletons.
    -   Flag functions that mutate shared objects without accepting a context argument.

2.  **Adopt Context Accessors**:
    -   Replace direct global usage with `get_context()` accessors.
    -   Move lazy instantiation into the context object as needed.

3.  **Implement Thread-Aware Entry Points**:
    -   For worker functions, call `get_context()` inside the thread and ensure `clear_context()` runs within a `finally` block.

4.  **Expose Optional Context Parameters**:
    -   Public functions should accept `context: ApplicationContext | None = None` and resolve `context = context or get_context()`.
    -   This makes testing and integration overrides explicit.

5.  **Update Tests**:
    -   Add the shared `clear_context()` fixture (see `tests/unit/test_context.py`).
    -   When mocking services, set them on the injected context instead of patching module globals.

6.  **Remove Deprecated Globals**:
    -   Delete `_global_*` caches once all call sites have been migrated to use the context.
    -   Update import paths so consumers retrieve dependencies from `importobot.context`.

## Example Refactor

```diff
-_performance_cache: PerformanceCache | None = None
-
-def get_performance_cache() -> PerformanceCache:
-    global _performance_cache
-    if _performance_cache is None:
-        _performance_cache = PerformanceCache()
-    return _performance_cache
+from importobot.context import ApplicationContext, get_context
+
+def get_performance_cache(
+    context: ApplicationContext | None = None,
+) -> PerformanceCache:
+    """Retrieve the performance cache via the active application context."""
+    context = context or get_context()
+    return context.performance_cache
```

### Worker Thread Template

```python
from importobot.context import clear_context, get_context

def run_worker(payload: dict[str, str]) -> None:
    context = get_context()
    try:
        cache = context.performance_cache
        cache.process(payload)
    finally:
        clear_context()
```

## Testing Checklist

-   [ ] Unit tests succeed with the autouse `clear_context` fixture.
-   [ ] Integration tests that start new threads/tasks call `clear_context()` in a `finally` block.
-   [ ] Mocked services are attached to the context (e.g., `context.performance_cache = FakeCache()`).
-   [ ] CLI entry points call `clear_context()` on exit (see `importobot.cli.main`).

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `AttributeError: 'ApplicationContext' object has no attribute ...` | Service property not defined on `ApplicationContext`. | Add a lazily-evaluated property to `ApplicationContext`. |
| Cache state shared across tests | Missing `clear_context()` in fixtures. | Add an autouse fixture to clear the context before/after each test. |
| Thread reuses stale services | Worker thread never clears its context. | Wrap the thread body in a `try/finally` block with `clear_context()`. |

## Next Steps

-   Review `wiki/architecture/Application-Context-Implementation.md` for deeper API details.
-   Update team onboarding documentation to reference the context access pattern.
-   Remove any lingering test utilities that patch module-level singletons.
