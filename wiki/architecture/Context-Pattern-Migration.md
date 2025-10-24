# Context Pattern Migration Guide

This guide expands on ADR-0004 and walks through migrating existing modules from module-level singletons to the thread-local application context introduced in Importobot v0.1.3. Follow these steps when upgrading legacy helpers, CLI commands, or integrations that still rely on globals.

## Before You Start

- Target version: Importobot v0.1.3 or later
- Read the [Application Context Implementation Guide](Application-Context-Implementation) for background and API references
- Confirm your tests can be run locally (`make test` or `pytest`)
- Identify modules that:
  - Import `get_*` helpers backed by module-level globals
  - Mutate shared state (e.g., caches, telemetry clients) without context arguments
  - Spawn worker threads without calling `clear_context()`

## Migration Workflow

1. **Inventory global access**
   - Search for assignments to `_global_*` variables or helpers that cache singletons.
   - Flag functions that mutate shared objects without accepting a context argument.

2. **Adopt context accessors**
   - Replace direct global usage with `get_context()` accessors.
   - Move lazy instantiation into the context object when needed.

3. **Thread-aware entry points**
   - For worker functions, call `get_context()` inside the thread and ensure `clear_context()` runs in a `finally` block.

4. **Expose optional context parameters**
   - Public functions should accept `context: ApplicationContext | None = None` and resolve `context = context or get_context()`.
   - Makes testing and integration overrides explicit.

5. **Update tests**
   - Add the shared `clear_context()` fixture (see `tests/unit/test_context.py`).
   - When mocking services, set them on the injected context instead of patching module globals.

6. **Remove deprecated globals**
   - Delete `_global_*` caches once all call sites use the context.
   - Update import paths so consumers pull dependencies from `importobot.context`.

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

- [ ] Unit tests succeed with the autouse `clear_context` fixture
- [ ] Integration tests that start new threads/tasks call `clear_context()` in `finally`
- [ ] Mocked services are attached to the context (`context.performance_cache = FakeCache()`)
- [ ] CLI entry points call `clear_context()` on exit (see `importobot.cli.main`)

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `AttributeError: 'ApplicationContext' object has no attribute ...` | Service property not defined on `ApplicationContext` | Add a lazily-evaluated property to `ApplicationContext` |
| Cache state shared across tests | Missing `clear_context()` in fixtures | Add autouse fixture to clear context before/after each test |
| Thread reuses stale services | Worker thread never clears its context | Wrap thread body in `try/finally` with `clear_context()` |

## Next Steps

- Review `wiki/architecture/Application-Context-Implementation.md` for deeper API details
- Update team onboarding docs to reference the context access pattern
- Remove any lingering test utilities that patch module-level singletons
