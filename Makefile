# Makefile for common development tasks

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  init      - Install development dependencies"
	@echo "  test      - Run all tests"
	@echo "  test-unit - Run unit tests only"
	@echo "  test-int  - Run integration tests only"
	@echo "  coverage  - Run tests with coverage report"
	@echo "  lint      - Run code linting with ruff and pylint"
	@echo "  format    - Format code with ruff"
	@echo "  check     - Run ruff check and format check"
	@echo "  clean     - Clean up temporary files"

# Install development dependencies
.PHONY: init
init:
	uv sync

# Run all tests
.PHONY: test
test:
	uv run pytest tests/

# Run unit tests only
.PHONY: test-unit
test-unit:
	uv run pytest tests/unit/

# Run integration tests only
.PHONY: test-int
test-int:
	uv run pytest tests/integration/

# Run tests with coverage report
.PHONY: coverage
coverage:
	uv run coverage run -m pytest && uv run coverage report

# Run code linting with ruff and pylint
.PHONY: lint
lint:
	uv run ruff check src/ tests/
	uv run pylint src/ tests/

# Format code with ruff
.PHONY: format
format:
	uv run ruff format src/ tests/

# Check code with ruff (linting and format check)
.PHONY: check
check:
	uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/

# Clean up temporary files
.PHONY: clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf *.egg-info/

# Run the converter with example data
.PHONY: example
example:
	uv run importobot example_zephyr.json example_output.robot