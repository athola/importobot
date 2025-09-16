# Development tasks

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  init      - Install dependencies"
	@echo "  test      - Run tests"
	@echo "  coverage  - Run tests with coverage"
	@echo "  lint      - Run linting"
	@echo "  format    - Format code"
	@echo "  clean     - Clean temp files"
	@echo "  examples  - Run all example conversions"
	@echo "  example-user-registration   - Web form automation example"
	@echo "  example-file-transfer       - SSH file transfer example"
	@echo "  example-database-api        - Database and API testing example"

# Install dependencies
.PHONY: init
init:
	uv sync

# Run tests
.PHONY: test
test:
	uv run pytest tests/

# Coverage
.PHONY: coverage
coverage:
	uv run coverage run -m pytest && uv run coverage report

# Linting
.PHONY: lint
lint:
	uv run ruff check .
	uv run pylint .
	uv run pycodestyle .
	uv run pydocstyle .

# Format
.PHONY: format
format:
	uv run ruff format .

# Typecheck
.PHONY: typecheck
typecheck:
	uv run ty check .
	uv run mypy .

# Cleanup
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

# Examples
.PHONY: examples
examples: example-basic example-login example-suggestions example-user-registration example-file-transfer example-database-api

.PHONY: example-basic
example-basic:
	uv run importobot examples/json/basic_login.json examples/robot/basic_example.robot

.PHONY: example-login
example-login:
	uv run importobot examples/json/browser_login.json examples/robot/login_example.robot
	@cat examples/robot/login_example.robot
	uv run robot --dryrun examples/robot/login_example.robot

.PHONY: example-suggestions
example-suggestions:
	uv run importobot examples/json/hash_file.json examples/robot/hash_example.robot
	uv run importobot --apply-suggestions examples/json/hash_file.json examples/robot/hash_applied.robot
	@rm -f examples/robot/hash_example.robot examples/robot/hash_applied.robot

.PHONY: example-user-registration
example-user-registration:
	uv run importobot examples/json/user_registration.json examples/robot/user_registration.robot
	@cat examples/robot/user_registration.robot

.PHONY: example-file-transfer
example-file-transfer:
	uv run importobot examples/json/ssh_file_transfer.json examples/robot/ssh_file_transfer.robot
	@cat examples/robot/ssh_file_transfer.robot

.PHONY: example-database-api
example-database-api:
	uv run importobot examples/json/database_api_test.json examples/robot/database_api_test.robot
	@cat examples/robot/database_api_test.robot

# Enterprise demo - bulk conversion test
.PHONY: enterprise-demo
enterprise-demo:
	@echo "Generating test files..."
	uv run python scripts/generate_enterprise_tests.py --output-dir zephyr-tests --count 50
	@echo "Converting to Robot Framework..."
	uv run importobot --directory zephyr-tests robot-tests
	@echo "Conversion complete: $$(find robot-tests -name '*.robot' | wc -l) files generated"
	@rm -rf zephyr-tests robot-tests
