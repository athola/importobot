# ADR-0004: Adopt Application Context Pattern for Dependency Management

## Status

Accepted – October 2025

## Context

- Pre-context Importobot used module-level global variables for shared services (caches, telemetry, etc.)
- Global state caused test isolation issues and made multi-threading complex
- CI/CD integration needed clean dependency injection for testability
- Thread safety required explicit locking mechanisms around global state
- Multiple concurrent instances were impossible due to shared global state

## Decision

- Replace module-level globals with thread-local Application Context pattern
- Implement `ApplicationContext` class with lazy-loaded service properties
- Provide `get_context()` and `set_context()` helpers for context management
- Maintain backward compatibility through existing helper functions
- Add automatic context clearing fixtures for test isolation

## Consequences

- Eliminates global state pollution and improves test isolation
- Enables multiple concurrent instances per process
- Provides automatic thread safety via thread-local storage
- Makes dependency injection explicit and testable
- Maintains backward compatibility through existing helper functions
- Requires context awareness in new code development
- Improves overall code maintainability and testing reliability