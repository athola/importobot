# Testing Guidelines

This guide explains how to write effective tests in Importobot with minimal mocking through dependency injection and good architectural patterns.

## Philosophy

Importobot follows Test-Driven Development (TDD) with these principles:

- **Test behavior, not implementation.** Focus on what the code does, not how it does it.
- **One assertion per test.** Keep tests focused and readable.
- **Tests must be deterministic.** They must produce the same result every time.
- **All tests must pass before proceeding.** Never commit broken tests.
- **Minimize mocking.** Use dependency injection instead of patches.

## Current State

- **2,105 total tests** passing with 0 skips
- **250 mock instances** across 57 test files (34% of test files)
- **Primary issues**: Logger mocking (34 instances) and module-level patching (120+ instances)

Our goal is to reduce mocking by 80% through better architecture.

## Dependency Injection Pattern

### Protocols Define Interfaces

```python
# Define what collaborators need
class FileReader(Protocol):
    def read_json(self, filepath: Path) -> dict[str, Any]: ...

class CacheStorage(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any]) -> None: ...
```

### Implementations Provide Behavior

```python
# Production implementation
class RealFileReader:
    def read_json(self, filepath: Path) -> dict[str, Any]:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

# Test implementation (fake, not mock)
class InMemoryFileReader:
    def __init__(self, files: dict[str, dict[str, Any]]):
        self.files = files

    def read_json(self, filepath: Path) -> dict[str, Any]:
        key = str(filepath)
        if key not in self.files:
            raise FileNotFoundError(f"File not found: {filepath}")
        return self.files[key]
```

### Classes Accept Dependencies

```python
class KeywordLibraryLoader:
    def __init__(
        self,
        file_reader: FileReader | None = None,
        cache: CacheStorage | None = None
    ):
        self.file_reader = file_reader or RealFileReader()
        self.cache = cache or SimpleCacheStorage()
```

## Result Objects Instead of Logging

### Separate Business Logic from Side Effects

```python
@dataclass
class LoadResult:
    """Encapsulates result and diagnostics."""
    success: bool
    data: dict[str, Any]
    message: str | None = None
    level: Literal["info", "warning", "error"] | None = None

class KeywordLibraryLoader:
    def load_library(self, library_name: str) -> LoadResult:
        if library_name not in filename_map:
            return LoadResult(
                success=False,
                data={},
                message=f"No configuration file found for library: '{library_name}'",
                level="warning"
            )
        # ... business logic
        return LoadResult(success=True, data=config)

# Caller handles logging
def load_and_log(loader: KeywordLibraryLoader, library_name: str) -> dict[str, Any]:
    result = loader.load_library(library_name)
    if result.message and result.level:
        getattr(logger, result.level)(result.message)
    return result.data
```

## Testing Without Mocks

### Use Fakes for Collaborators

```python
def test_load_library_success():
    """Test with fake file reader - no mocking."""
    # Arrange - create fake filesystem
    fake_files = {
        "/keywords/builtin.json": {
            "library_name": "BuiltIn",
            "keywords": {"Log": {"description": "Logs a message"}}
        }
    }

    loader = KeywordLibraryLoader(
        data_dir=Path("/keywords"),
        file_reader=InMemoryFileReader(fake_files)
    )

    # Act
    result = loader.load_library("BuiltIn")

    # Assert - test business behavior
    assert result.success is True
    assert result.data["library_name"] == "BuiltIn"
    assert "Log" in result.data["keywords"]
    assert result.message is None  # No diagnostic for success
```

### Test Error Paths with Real Behavior

```python
def test_load_library_not_found():
    """Test error path - no mocks needed."""
    # Arrange - empty filesystem
    loader = KeywordLibraryLoader(
        data_dir=Path("/keywords"),
        file_reader=InMemoryFileReader({})
    )

    # Act
    result = loader.load_library("UnknownLibrary")

    # Assert - verify business outcome
    assert result.success is False
    assert result.data == {}
    assert result.level == "warning"
    assert "No configuration file found" in result.message
    assert "UnknownLibrary" in result.message
```

### Use Fixtures for Real Files

```python
def test_load_real_file(tmp_path):
    """Test with actual file - no mocks."""
    # Arrange - create real file
    config_file = tmp_path / "test.json"
    config_file.write_text('{"library_name": "Test", "keywords": {}}')

    loader = KeywordLibraryLoader(
        data_dir=tmp_path,
        file_reader=RealFileReader()
    )

    # Act
    result = loader.load_library("test")

    # Assert
    assert result.success is True
    assert result.data["library_name"] == "Test"
```

## When to Mock

Mock only when you have no other choice:

###  DO Mock
- **External HTTP/API calls** - Network requests
- **System time** - `datetime.now()`, time functions
- **Random generation** - Random numbers, UUIDs
- **Database connections** - Real database interactions
- **OS operations** - File permissions, system calls

###  DON'T Mock
- **Logging** - Use result objects instead
- **File I/O** - Use fixtures or fakes
- **Business logic** - Test directly
- **Pure functions** - No side effects to mock
- **Simple collaborators** - Use real or fake implementations

## Common Anti-Patterns

### Logger Testing (Avoid)

```python
#  Anti-pattern - testing logging implementation
with patch.object(loader.logger, "warning") as mock_warning:
    result = loader.load_library("missing")
    mock_warning.assert_called_once()
    assert "Configuration file not found" in mock_warning.call_args[0][0]
```

### Module Patching (Avoid)

```python
#  Anti-pattern - knowing internal collaborators
@patch("importobot.core.conversion_strategies.load_json_file")
@patch("importobot.core.conversion_strategies.get_conversion_suggestions")
def test_conversion(mock_load_json, mock_get_suggestions):
    # Tests implementation details, not behavior
```

### Good Patterns (Prefer)

```python
#  Test business outcomes
result = loader.load_library("missing")
assert result.success is False
assert result.level == "warning"
assert "Configuration file not found" in result.message

#  Test with real collaborators
strategy = SingleFileStrategy(
    json_loader=SimpleJsonLoader(),
    suggestion_generator=SimpleSuggestionGenerator()
)
```

## Migration Strategy

### Phase 1: New Code
- All new classes use dependency injection
- All new methods return result objects
- Tests use fakes instead of mocks

### Phase 2: High-Value Targets
- **KeywordLibraryLoader** - Most logger mocks (11 instances)
- **ConversionStrategies** - Most module patches (30+ instances)
- **ValidationServices** - Mix of both (15 instances)

### Phase 3: Gradual Improvement
- Refactor when touching modules for features
- Maintain backward compatibility during transition
- Don't refactor just for the sake of it

## Test Organization

### Use Existing Fixtures

```python
# Reuse fixtures from tests/fixtures/ instead of copying setup
@pytest.fixture
def sample_zephyr_data():
    return load_fixture("sample_zephyr_export.json")

def test_conversion_with_sample_data(sample_zephyr_data):
    converter = JsonToRobotConverter()
    result = converter.convert(sample_zephyr_data)
    assert result.success
```

### One Assertion Per Test

```python
#  Good - focused, readable
def test_loads_library_name():
    result = loader.load_library("BuiltIn")
    assert result.data["library_name"] == "BuiltIn"

def test_loads_keywords():
    result = loader.load_library("BuiltIn")
    assert "Log" in result.data["keywords"]

#  Avoid - multiple assertions hide intent
def test_load_library_complex():
    result = loader.load_library("BuiltIn")
    assert result.success
    assert result.data["library_name"] == "BuiltIn"
    assert "Log" in result.data["keywords"]
    assert result.message is None
```

## Running Tests

```bash
# All tests (quiet output)
make test --quiet

# Unit tests only
make test-unit --quiet

# Coverage analysis
make test-coverage --quiet

# Specific test file
pytest tests/unit/test_keyword_loader.py -v

# Specific test with verbose output
pytest tests/unit/test_keyword_loader.py::TestKeywordLibraryLoader::test_load_library_success -v
```

## Quality Standards

Every test must:
- [ ] Test business behavior, not implementation
- [ ] Use descriptive names that explain what is being tested
- [ ] Have clear arrange/act/assert structure
- [ ] Be deterministic (same result every time)
- [ ] Run independently (no test order dependencies)
- [ ] Minimize mocking (prefer DI and fakes)
- [ ] Follow project naming conventions

Remember: Tests are documentation. A good test explains how the system should behave to future developers.