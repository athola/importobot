# Contributing

We welcome contributions from the community. This guide explains how to set up your development environment and align your changes with the project's standards.

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

### Pre-Commit Checklist

Before committing, ensure your changes meet the following criteria:

- All tests pass (`uv run pytest`).
- Code coverage has not decreased.
- All linting and formatting checks pass (`make lint`).
- Relevant documentation has been updated if behavior was changed.

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
# Run all linting and formatting checks (same as CI)
make lint

# Auto-fix common issues
uv run ruff check --fix .
uv run ruff format .

# Clean generated artifacts
make clean
make deep-clean  # For more thorough cleanup
```



## Project Structure

For a detailed breakdown of the codebase, including the layered architecture and key modules, please see the [How to Navigate this Codebase](How-to-Navigate-this-Codebase.md) guide.

## Testing Standards

The project uses unit, integration, and CLI tests. For a detailed description of each type and where to find them, see the [Test Structure](How-to-Navigate-this-Codebase.md#test-structure) section in the codebase navigation guide.

## Code Style

### General Guidelines

Follow the existing code style. Use descriptive names, keep functions small, and use 4 spaces for indentation.

### Type Hints
- Use type hints for function parameters and return values.
- Follow PEP 484 guidelines.
- Use the `typing` module for complex types.

### Docstrings
- Follow Google-style docstrings, as shown in the example below.
- The first line should be a concise, imperative summary (e.g., "Convert a...").
- If more detail is needed, add a blank line followed by more description.
- Use `Args:`, `Returns:`, and `Raises:` sections to describe parameters, return values, and exceptions.

### Example
```python
def convert_test_case(test_data: dict) -> str:
    """Converts a test case dictionary to a Robot Framework string.

    Args:
        test_data: A dictionary containing test case data, including
            'name', 'steps', and 'tags'.

    Returns:
        A string representing the test case in Robot Framework format.
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
