# ADR-0005: Mock Reduction Through Dependency Injection

## Status

Implemented – November 2025

## Context

- Current test suite has 250 mock instances across 57 test files (34% of test files)
- Heavy mocking indicates architectural coupling that makes tests brittle and hard to maintain
- Logger mocking (34 instances) and module-level function patching (120+ instances) are the primary concerns
- Tests verify implementation details (like logging behavior) instead of business outcomes

## Decision

Adopt dependency injection, protocol-based design, and result objects to eliminate 80% of mocks while improving testability and architecture.

### Core Approach

1. **Dependency Injection** - Make dependencies explicit through constructor parameters
2. **Protocol-based Design** - Define clear interfaces using Python `Protocol` types
3. **Result Objects** - Return structured results instead of logging side effects
4. **Functional Core/Imperative Shell** - Separate pure business logic from I/O operations

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
- **80% mock reduction** - From 250 to ~50 mock instances
- **Better testability** - Tests verify business behavior, not implementation
- **Cleaner architecture** - Lower coupling, higher cohesion
- **Easier refactoring** - Tests don't break when implementation changes
- **Faster tests** - No mock setup/teardown overhead

### Negative
- **Additional complexity** - More protocol/interface definitions
- **Learning curve** - Team must understand DI patterns
- **Migration effort** - Existing code requires gradual refactoring

### Neutral
- **More files** - Separate protocols, implementations, and results
- **Different patterns** - Tests use fakes instead of mocks

## Implementation Strategy

### Phase 1: Foundation (This Sprint)
1. Create core protocols (`FileReader`, `CacheStorage`, etc.)
2. Implement fake classes for testing (`InMemoryFileReader`, `SimpleCacheStorage`)
3. Define result types (`LoadResult`, `ValidationResult`)
4. Refactor `KeywordLibraryLoader` as proof of concept

### Phase 2: High-Value Targets (Next Sprint)
- **ConversionStrategies** (30+ mock instances)
- **ValidationServices** (15 mock instances)
- CLI handlers and core engine components

### Phase 3: Gradual Migration (Ongoing)
- Refactor modules when touched for features
- Maintain backward compatibility during transition
- Focus on new code using DI patterns from day one

## Testing Guidelines

### When to Mock
 **DO Mock**:
- External HTTP/API calls
- System time (`datetime.now()`)
- Random number generation
- Database connections
- True OS operations (permissions, etc.)

 **DON'T Mock**:
- Logging
- File I/O that can use fixtures
- Internal business logic
- Pure functions
- Simple collaborators

### How to Avoid Mocks
1. **Use Dependency Injection** - Pass collaborators as parameters
2. **Use Protocols** - Define interfaces, inject implementations
3. **Use Fakes** - Simple in-memory implementations
4. **Separate I/O from logic** - Test logic without I/O
5. **Use fixtures** - Real files in `tmp_path`
6. **Return results** - Let caller handle logging/side effects

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

Applied the Functional Core/Imperative Shell pattern to `DataIngestionService` as the first proof of concept.

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

1. `src/importobot/services/ingestion_core.py` - Pure functional core business logic
2. `src/importobot/services/data_ingestion_service_refactored.py` - Imperative shell with dependency injection
3. `tests/unit/test_ingestion_core.py` - Tests for functional core (no mocking)
4. `tests/unit/test_data_ingestion_shell.py` - Tests for imperative shell (fakes instead of mocks)

### Measurable Improvements

#### Test Quality
- **Determinism**: Functional core tests are 100% deterministic
- **Speed**: No mock setup/teardown overhead
- **Clarity**: Tests verify business behavior, not implementation details
- **Maintainability**: Tests don't break when implementation changes

#### Code Architecture
- **Coupling**: Reduced tight coupling between I/O and business logic
- **Cohesion**: Higher single-responsibility principle adherence
- **Testability**: Business logic can be tested in isolation
- **Flexibility**: Easy to swap implementations (e.g., different file readers)

### Success Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Functional core test coverage | 90%+ deterministic |  Yes |
| Core test suite runtime | Sub-second |  Yes |
| Zero mocking for business logic | 100% |  Yes |
| Clear dependency boundaries | Explicit interfaces |  Yes |
| Mock reduction (overall) | 80% |  Target established |

### Quality Standards Established

**Code Requirements**
- Specific naming (no generic `data`, `value`, `result` variables)
- Minimal abstractions (only add complexity when justified)
- Explicit dependencies (all collaborators injected through constructors)
- Result objects (return structured results instead of logging side effects)
- Comprehensive error handling with specific error types

**Testing Requirements**
- No tutorial docstrings (tests explain what, not how)
- One assertion per test when possible
- Deterministic behavior (same result every time)
- Business focus (test behavior, not implementation)
- Dependency injection (use fakes instead of mocks)

### Next High-Value Targets

1. **CLI Handlers** - 85 mock instances, complex orchestration
2. **Conversion Strategies** - 58 mock instances, business logic complexity
3. **Keyword Loader** - 35 mock instances, file I/O + validation

## Conclusion

This architectural change addresses the root cause of heavy mocking by improving system design, not just test patterns. The investment in dependency injection and protocol-based design will pay dividends in:

- **Maintainability** - Clearer contracts and dependencies
- **Testability** - Business logic tested in isolation
- **Flexibility** - Easy to swap implementations
- **Reliability** - Tests focus on behavior, not implementation details

The mock reduction is a side effect of better architecture, not the primary goal. The successful refactoring of `DataIngestionService` demonstrates that the 80% mock reduction target is achievable while improving overall code quality.