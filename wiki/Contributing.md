# Contributing

We welcome contributions. This guide explains how to get set up and align your changes with the project's style.

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

# Install in editable mode (optional for local tooling)
uv pip install -e .
```

## Development Workflow

Importobot follows Test-Driven Development (TDD) and Extreme Programming (XP) principles.

### Red-Green-Refactor Cycle

1. **Red**: Write a failing test for a new feature.
2. **Green**: Implement the minimum code to pass the test.
3. **Refactor**: Improve the code while keeping tests green.

### Code Quality

All code must pass the test suite, maintain coverage targets, and pass all linting checks. Update the documentation if you change any behavior.

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

**Unit Tests** test isolated components, execute quickly with minimal dependencies, and use mocking for external dependencies. They are located in `tests/unit/`.

**Integration Tests** test the interaction between multiple components, perform file I/O operations, and verify end-to-end functionality. They are located in `tests/integration/`.

**CLI Tests** test command-line interface functionality, including argument parsing and handling. They are located in `tests/cli/`.

## Code Style

### General Guidelines

Follow the existing code style. Use descriptive names, keep functions small, and use 4 spaces for indentation.

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

1. Fork the repository and create a feature branch.
2. Make your changes, including tests.
3. Ensure all tests and linting checks pass.
4. Update documentation if needed.
5. Create a pull request and address any feedback.

## Artifact management

- Run `make clean` during development; use `make deep-clean` before publishing branches.
- Review `git status` to ensure generated files are not committed.

## Reporting Issues

When reporting issues, please include a clear description of the problem, steps to reproduce it, the expected and actual behavior, and environment information (Python version, OS, etc.).

## Feature Requests

For new feature requests, please explain the problem the feature would solve and provide use cases. If possible, suggest implementation approaches and consider how the feature fits within the project's goals.
