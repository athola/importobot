# ADR-0004: Adopt Application Context Pattern for Dependency Management

## Status

Accepted – October 2025

## Context

-   Prior to this decision, Importobot relied on module-level global variables for shared services (e.g., caches, telemetry).
-   This global state led to test isolation issues and complicated multi-threading.
-   CI/CD integration required a cleaner dependency injection mechanism for improved testability.
-   Ensuring thread safety necessitated explicit locking around global state.
-   The shared global state prevented the creation of multiple concurrent instances within a single process.

## Decision

-   We will replace module-level global variables with a thread-local Application Context pattern.
-   An `ApplicationContext` class will be implemented, featuring lazy-loaded service properties.
-   Helper functions, `get_context()` and `set_context()`, will be provided for managing the application context.
-   Backward compatibility will be maintained through existing helper functions.
-   Automatic context-clearing fixtures will be added to ensure test isolation.

## Consequences

-   Eliminates global state pollution, thereby improving test isolation.
-   Enables the creation of multiple concurrent instances within a single process.
-   Provides automatic thread safety through the use of thread-local storage.
-   Makes dependency injection explicit and enhances testability.
-   Maintains backward compatibility via existing helper functions.
-   Requires new code development to be context-aware.
-   Improves overall code maintainability and testing reliability.