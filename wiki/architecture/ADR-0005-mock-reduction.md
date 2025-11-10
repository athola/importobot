# ADR-0005: Mock Reduction Through Dependency Injection

## Status

Implemented – November 2025

## Context

-   The test suite currently contains 250 mock instances across 57 test files (34% of all test files).
-   Extensive mocking suggests architectural coupling, leading to brittle and difficult-to-maintain tests.
-   Logger mocking (34 instances) and module-level function patching (over 120 instances) are the primary areas of concern.
-   Many tests verify implementation details (e.g., logging behavior) rather than core business outcomes.

## Decision

We will adopt dependency injection, protocol-based design, and result objects to eliminate 80% of mocks, thereby improving testability and overall architecture.

### Core Approach

1.  **Dependency Injection**: Make dependencies explicit through constructor parameters.
2.  **Protocol-based Design**: Define clear interfaces using Python `Protocol` types.
3.  **Result Objects**: Return structured results instead of relying on logging for side effects.
4.  **Functional Core/Imperative Shell**: Separate pure business logic from I/O operations.

### Implementation Pattern

```python
# Before (heavy mocking)
class KeywordLibraryLoader:
    def __init__(self):
        self.logger = logger  # Instance attribute requires mocking

    def load_library(self, library_name: str) -> dict[str, Any]:
        if library_name not in filename_map:
            self.logger.warning("Configuration file not found...")  # Business + logging coupled
            return {}
        # Direct file I/O requires filesystem mocking
        with open(filepath) as f:
            return json.load(f)

# After (dependency injection)
class KeywordLibraryLoader:
    def __init__(
        self,
        file_reader: FileReader | None = None,
        cache: CacheStorage | None = None
    ):
        self.file_reader = file_reader or RealFileReader()
        self.cache = cache or SimpleCacheStorage()

    def load_library(self, library_name: str) -> LoadResult:
        # Pure business logic - no side effects
        result = self._load_from_cache_or_file(library_name)
        return result  # Caller decides whether/how to log
```

## Consequences

### Positive
-   **80% Mock Reduction**: Reduces mock instances from 250 to approximately 50.
-   **Improved Testability**: Tests now verify business behavior rather than implementation details.
-   **Cleaner Architecture**: Achieves lower coupling and higher cohesion.
-   **Easier Refactoring**: Tests are less prone to breaking when implementation changes.
-   **Faster Tests**: Eliminates mock setup/teardown overhead.

### Negative
-   **Increased Complexity**: Requires more protocol and interface definitions.
-   **Learning Curve**: The team must adapt to understanding and applying Dependency Injection (DI) patterns.
-   **Migration Effort**: Existing code requires gradual refactoring.

### Neutral
-   **Increased File Count**: Results in more files due to separate protocols, implementations, and result objects.
-   **Different Testing Patterns**: Encourages the use of fakes instead of mocks in tests.

## Implementation Strategy

### Phase 1: Foundation (Current Sprint)
1.  Create core protocols (e.g., `FileReader`, `CacheStorage`).
2.  Implement fake classes for testing (e.g., `InMemoryFileReader`, `SimpleCacheStorage`).
3.  Define structured result types (e.g., `LoadResult`, `ValidationResult`).
4.  Refactor `KeywordLibraryLoader` as a proof of concept.

### Phase 2: High-Value Targets (Next Sprint)
-   **ConversionStrategies**: Target modules with over 30 mock instances.
-   **ValidationServices**: Target modules with over 15 mock instances.
-   CLI handlers and core engine components.

### Phase 3: Gradual Migration (Ongoing)
-   Refactor modules when they are modified for new features.
-   Maintain backward compatibility throughout the transition.
-   Ensure all new code adheres to DI patterns from inception.

## Testing Guidelines

### When to Mock
**DO Mock**:
-   External HTTP/API calls.
-   System time (e.g., `datetime.now()`).
-   Random number generation.
-   Database connections.
-   True OS operations (e.g., file permissions).

**DON'T Mock**:
-   Logging (use result objects instead).
-   File I/O (use fixtures or fakes).
-   Internal business logic (test directly).
-   Pure functions (no side effects to mock).
-   Simple collaborators (use real or fake implementations).

### How to Avoid Mocks
1.  **Use Dependency Injection**: Pass collaborators as constructor parameters.
2.  **Use Protocols**: Define clear interfaces and inject implementations.
3.  **Use Fakes**: Provide simple, in-memory implementations for testing.
4.  **Separate I/O from Logic**: Test business logic independently of I/O operations.
5.  **Use Fixtures**: Utilize real files within `tmp_path` for file-based tests.
6.  **Return Results**: Allow the caller to handle logging and side effects.

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Mock instances | 250 | ~50 | 80% reduction |
| Logger mocks | 34 | 0 | 100% reduction |
| Module patching | 120+ | ~30 | 75% reduction |
| Test readability | Medium | High | Qualitative |
| Test brittleness | High | Low | Qualitative |
| Refactor safety | Low | High | Qualitative |

## Examples

### Before Test (Heavy Mocking)
```python
@patch("importobot.core.conversion_strategies.load_json_file")
@patch("importobot.core.conversion_strategies.get_conversion_suggestions")
def test_display_suggestions(mock_load_json, mock_get_suggestions):
    strategy = SingleFileStrategy()
    mock_load_json.return_value = {"test": "data"}
    mock_get_suggestions.return_value = ["suggestion1"]

    strategy._display_suggestions("test.json", no_suggestions=False)

    mock_load_json.assert_called_once_with("test.json")
    mock_get_suggestions.assert_called_once_with({"test": "data"})
```

### After Test (No Mocking)
```python
def test_display_suggestions(capsys):
    """Test with real collaborators - no mocks."""
    class SimpleSuggestionGenerator:
        def generate(self, data: dict) -> list[str]:
            return ["suggestion1", "suggestion2"]

    class SimpleJsonLoader:
        def load(self, filepath: str) -> dict:
            return {"test": "data"}

    strategy = SingleFileStrategy(
        json_loader=SimpleJsonLoader(),
        suggestion_generator=SimpleSuggestionGenerator(),
        file_converter=None
    )

    strategy.display_suggestions("test.json", no_suggestions=False)

    captured = capsys.readouterr()
    assert "Conversion Suggestions:" in captured.out
    assert "1. suggestion1" in captured.out
```

## Implementation Results

### DataIngestionService Refactoring

The Functional Core/Imperative Shell pattern was applied to `DataIngestionService` as the initial proof of concept.

#### Before (Tightly Coupled)
```python
def ingest_file(self, file_path: str) -> ProcessingResult:
    # Mixed I/O + Business Logic
    content = self._read_file_content(file_path)  # I/O
    data, json_validation = self._process_file_content(content)  # Business
    metadata = self._create_metadata(file_path, data)  # Business + I/O
    result = self.bronze_layer.ingest(data, metadata)  # I/O
    return result
```

#### After (Separated Concerns)
```python
# Functional Core - Pure Business Logic (src/importobot/services/ingestion_core.py)
def validate_and_parse_json(content: str, security_result: dict | None) -> tuple[Any, list[str]]:
    # Pure function - no I/O, deterministic
    # Returns parsed data and validation errors

def create_processing_metadata(inputs: ProcessingInputs, data: Any, security_result: dict | None) -> LayerMetadata:
    # Pure function - creates metadata from inputs
    # No side effects, fully testable without mocking

# Imperative Shell - I/O Orchestration (data_ingestion_service_refactored.py)
def ingest_file(self, file_path: str | Path) -> ProcessingResult:
    # Shell operations: file reading, security validation, bronze layer calls
    content = self.file_reader.read_text(file_path)  # I/O
    security_validation = self._validate_file_path_security(file_path, correlation_id)  # I/O

    # Delegate to functional core
    outputs = self._process_content_core(inputs)  # Pure business logic

    # Shell operations: persistence and result attachment
    bronze_result = self.bronze_layer.ingest(outputs.data, outputs.metadata)  # I/O
    return bronze_result
```

### Files Created

1.  `src/importobot/services/ingestion_core.py`: Contains pure functional core business logic.
2.  `src/importobot/services/data_ingestion_service_refactored.py`: Implements the imperative shell with dependency injection.
3.  `tests/unit/test_ingestion_core.py`: Tests the functional core without mocking.
4.  `tests/unit/test_data_ingestion_shell.py`: Tests the imperative shell using fakes instead of mocks.

### Measurable Improvements

#### Test Quality
-   **Determinism**: Functional core tests are 100% deterministic.
-   **Speed**: Eliminates mock setup/teardown overhead.
-   **Clarity**: Tests verify business behavior, not implementation details.
-   **Maintainability**: Tests are more robust to implementation changes.

#### Code Architecture
-   **Coupling**: Reduces tight coupling between I/O and business logic.
-   **Cohesion**: Achieves higher adherence to the single-responsibility principle.
-   **Testability**: Business logic can be tested in isolation.
-   **Flexibility**: Facilitates swapping implementations (e.g., different file readers).

### Success Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Functional core test coverage | 90%+ deterministic | Yes |
| Core test suite runtime | Sub-second | Yes |
| Zero mocking for business logic | 100% | Yes |
| Clear dependency boundaries | Explicit interfaces | Yes |
| Mock reduction (overall) | 80% | Target established |

### Quality Standards Established

**Code Requirements**
-   Specific naming (avoid generic variables like `data`, `value`, `result`).
-   Minimal abstractions (introduce complexity only when justified).
-   Explicit dependencies (all collaborators injected via constructors).
-   Result objects (return structured results instead of relying on logging for side effects).
-   Comprehensive error handling with specific error types.

**Testing Requirements**
-   No tutorial-style docstrings (tests should explain *what* is being tested, not *how*).
-   Aim for one assertion per test where possible.
-   Ensure deterministic behavior (same result every time).
-   Maintain a business focus (test behavior, not implementation).
-   Utilize dependency injection (prefer fakes over mocks).

### Next High-Value Targets

1.  **CLI Handlers**: Currently involve 85 mock instances and complex orchestration.
2.  **Conversion Strategies**: Involve 58 mock instances and significant business logic complexity.
3.  **Keyword Loader**: Involves 35 mock instances, primarily due to file I/O and validation.

## Conclusion

This architectural change addresses the underlying issues contributing to extensive mocking by improving system design, rather than merely altering test patterns. The investment in dependency injection and protocol-based design will yield significant benefits in:

-   **Maintainability**: Achieves clearer contracts and dependencies.
-   **Testability**: Enables business logic to be tested in isolation.
-   **Flexibility**: Facilitates easy swapping of implementations.
-   **Reliability**: Ensures tests focus on behavior rather than implementation details.

Mock reduction is a beneficial outcome of improved architecture, not the primary objective. The successful refactoring of `DataIngestionService` demonstrates that the 80% mock reduction target is achievable while simultaneously enhancing overall code quality.