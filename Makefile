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
	@echo "  example   - Run converter with example data"
	@echo "  example-login - Convert login test and verify with Robot Framework"

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
	uv run ruff check .
	uv run pylint .
	uv run pycodestyle .
	uv run pydocstyle .

# Format code with ruff
.PHONY: format
format:
	uv run ruff format .

# Clean up temporary files
.PHONY: clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf *.egg-info/
	rm -f examples/robot/*.robot
	rm -f output.xml log.html report.html selenium-screenshot-*.png

# Run the converter with example data
.PHONY: example
example:
	uv run importobot examples/json/basic_login.json examples/robot/basic_example.robot

# Run the converter with login test example and demonstrate Robot Framework execution
.PHONY: example-login
example-login:
	@echo "Converting login test case to Robot Framework format..."
	uv run importobot examples/json/browser_login.json examples/robot/login_example.robot
	@echo "Conversion complete! Generated file: login_example.robot"
	@echo ""
	@echo "Generated Robot Framework test case:"
	@echo "======================================"
	@cat login_example.robot
	@echo ""
	@echo "Running Robot Framework test to verify it works:"
	@echo "================================================"
	uv run robot --dryrun examples/robot/login_example.robot
