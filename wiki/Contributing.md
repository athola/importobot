# Contributing

We welcome contributions. Follow the steps below to get set up and keep changes aligned with the project style.

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

All code must:
- Keep the test suite green.
- Maintain coverage targets.
- Pass linting (ruff/pylint/pycodestyle/pydocstyle).
- Update docs when behaviour changes.

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

## Repository structure

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

## Artifact management

- Run `make clean` during development; use `make deep-clean` before publishing branches.
- Review `git status` to ensure generated files are not committed.

## Reporting Issues

When reporting issues, please include:
- A clear description of the problem.
- Steps to reproduce the issue.
- The expected and actual behavior.
- Environment information (Python version, OS, etc.).
- Relevant code snippets or error messages.

## Feature Requests

New feature requests are welcomed! Please:
- Explain the problem the feature would solve.
- Provide use cases.
- If possible, suggest implementation approaches.
- Consider how the feature fits within the project's goals.
