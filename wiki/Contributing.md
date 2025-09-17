# Contributing

We welcome contributions to Importobot! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/athola/importobot.git
cd importobot

# Install project dependencies (including dev dependencies)
uv sync --dev

# Install the project in editable mode
uv pip install -e .
```

## Development Workflow

This project follows Test-Driven Development (TDD) and Extreme Programming (XP) principles.

### Red-Green-Refactor Cycle

1. **Red**: Write a failing test for a new feature.
2. **Green**: Implement the minimum code to pass the test.
3. **Refactor**: Improve the code while keeping tests green.

### Code Quality

All code must pass these quality gates:
- All tests must pass.
- Code coverage requirements must be maintained.
- Linting must pass with zero warnings.
- Documentation must be updated for new features.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/        # Fast, isolated component tests
uv run pytest tests/integration/ # End-to-end conversion validation
uv run pytest tests/cli/         # Command-line interface tests

# Run tests with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality Checks

```bash
# Run all linting tools (same as CI)
make lint

# Individual tools for specific checks
uv run ruff check .                    # Code linting and formatting checks
uv run pycodestyle .                   # PEP 8 style guide compliance
uv run pydocstyle .                    # Docstring standards
uv run pylint .                        # Static analysis

# Auto-fix common issues
uv run ruff check --fix .
uv run ruff format .

# Clean generated artifacts
make clean
make deep-clean  # For more thorough cleanup
```

## Recent Improvements

### Artifact Management
Contributors should be aware of the enhanced artifact management:
- Enhanced `.gitignore` to properly exclude generated artifacts and test output files
- Added comprehensive `clean` and `deep-clean` Makefile targets to remove temporary files
- Removed accidentally committed artifacts and ensured repository cleanliness

### Code Quality Standards
- Fixed linting issues throughout the codebase using `ruff` and other tools
- Removed unused imports and variables to reduce code clutter
- Standardized code formatting with automated tools
- Improved error handling and validation patterns

### Test Reliability
- Fixed failing tests related to missing test data files
- Improved test data management and file organization
- Enhanced test suite reliability and consistency

## Project Structure

```
src/importobot/
├── cli/                 # Command-line interface
│   ├── parser.py       # Argument parsing
│   └── handlers.py     # Command handlers
├── core/               # Core conversion logic
│   ├── engine.py       # Conversion engine
│   ├── converter.py    # File operations
│   └── parser.py       # Test case parsing
├── utils/              # Utility modules
└── __main__.py         # Entry point

tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
└── cli/               # CLI tests
```

## Testing Standards

### Unit Tests
- Test isolated components.
- Execute quickly with minimal dependencies.
- Use mocking for external dependencies.
- Located in `tests/unit/`.

### Integration Tests
- Test the interaction between multiple components.
- Perform file I/O operations.
- Verify end-to-end functionality.
- Located in `tests/integration/`.

### CLI Tests
- Test command-line interface functionality.
- Verify argument parsing and handling.
- Located in `tests/cli/`.

## Code Style

### General Guidelines
- Follow the existing code style and patterns.
- Use descriptive variable and function names.
- Keep functions small and focused.
- Use 4 spaces for indentation.

### Type Hints
- Use type hints for function parameters and return values.
- Follow PEP 484 guidelines.
- Use the `typing` module for complex types.

### Docstrings
- Follow PEP 257 guidelines.
- Use the imperative mood for function descriptions.
- Include parameter and return value descriptions.

### Example
```python
def convert_test_case(test_data: dict) -> str:
    """Convert a test case to Robot Framework format.
    
    Args:
        test_data: A dictionary containing test case data.
        
    Returns:
        A string containing the Robot Framework test case.
    """
    # Implementation
```

## Pull Request Process

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add tests for your changes.
5. Ensure all tests pass.
6. Update documentation as needed.
7. Create a pull request.
8. Address any feedback from reviewers.

## Artifact Management for Contributors

When working on Importobot, please be aware of the artifact management practices:
- Use `make clean` regularly during development to remove temporary files
- Use `make deep-clean` for more thorough cleanup when needed
- Check that no artifacts are accidentally committed by reviewing your changes
- Run tests after cleaning to ensure nothing was broken

## Reporting Issues

When reporting issues, please include:
- A clear description of the problem.
- Steps to reproduce the issue.
- The expected and actual behavior.
- Environment information (Python version, OS, etc.).
- Relevant code snippets or error messages.

## Feature Requests

We welcome feature requests! Please:
- Explain the problem the feature would solve.
- Provide use cases.
- If possible, suggest implementation approaches.
- Consider how the feature fits with the project's goals.
