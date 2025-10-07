# Development tasks

# Define newline variable for use in info messages
define NEWLINE


endef

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help         - Show this help menu"
	@echo "  init         - Install dependencies"
	@echo "  test         - Run tests"
	@echo "  coverage     - Run tests with coverage"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  typecheck    - Run type checking"
	@echo "  validate     - Validate PR readiness (lint + typecheck + test)"
	@echo "  clean        - Clean temp files"
	@echo "  examples     - Run all example conversions and usage examples"
	@echo "  example-basic           - Basic login example"
	@echo "  example-login           - Browser login example"
	@echo "  example-suggestions     - Hash file example with suggestions"
	@echo "  example-parameters      - Parameter mapping example with cat_file.json"
	@echo "  example-user-registration   - Web form automation example"
	@echo "  example-file-transfer       - SSH file transfer example"
	@echo "  example-database-api        - Database and API testing example"
	@echo "  example-usage-basic         - Basic API usage examples"
	@echo "  example-usage-advanced      - Advanced features examples"
	@echo "  example-usage-cli           - CLI usage examples"
	@echo "  enterprise-demo         - Bulk conversion test"
	@echo "  interactive-demo        - Run interactive business benefits demo"
	@echo "  interactive-demo-test   - Run interactive demo in non-interactive mode"
	@echo "  mcp-query               - Query the Qwen model through MCP"
	@echo "  mcp-review              - Request a code review through MCP"
	@echo "  bench                   - Run performance benchmarks"
	@echo ""
	@echo "Scripts subproject commands:"
	@echo "  scripts-test            - Run tests for scripts subproject"
	@echo "  scripts-lint            - Run linting for scripts subproject"
	@echo "  scripts-format          - Format scripts subproject code"
	@echo "  scripts-clean           - Clean scripts subproject"
	@echo "  scripts-install         - Install scripts subproject dependencies"
	@echo "  scripts-demo            - Run scripts interactive demo"
	@echo "  scripts-demo-non-interactive - Run scripts non-interactive demo"
	@echo ""
	@echo "Workspace commands:"
	@echo "  workspace-test          - Run tests for entire workspace"
	@echo "  workspace-lint          - Run linting for entire workspace"
	@echo "  workspace-format        - Format entire workspace"
	@echo "  workspace-clean         - Clean entire workspace"

# Install dependencies
.PHONY: init
init:
	$(info $(NEWLINE)==================== Installing dependencies ====================$(NEWLINE))
	uv sync

# Sync and install all development dependencies
.PHONY: sync
sync:
	$(info $(NEWLINE)==================== Syncing environment and installing development dependencies ====================$(NEWLINE))
	# Sync the base environment
	uv sync
	# Install the scripts package in development mode
	uv pip install -e ./scripts
	# Install development dependencies required for scripts
	uv pip install PyQt5 seaborn

# Run tests
.PHONY: test
test:
	$(info $(NEWLINE)==================== Running tests ====================$(NEWLINE))
	uv run pytest tests/

# Coverage
.PHONY: coverage
coverage:
	$(info $(NEWLINE)==================== Running tests with coverage ====================$(NEWLINE))
	uv run coverage run -m pytest && uv run coverage report

# Linting
.PHONY: lint
lint:
	$(info $(NEWLINE)==================== Running linting ====================$(NEWLINE))
	uv run ruff check .
	uv run pylint .
	uv run pycodestyle .
	uv run pydocstyle .

# Format
.PHONY: format
format:
	$(info $(NEWLINE)==================== Formatting code ====================$(NEWLINE))
	uv run ruff format .

# Typecheck
.PHONY: typecheck
typecheck:
	$(info $(NEWLINE)==================== Running type checking ====================$(NEWLINE))
	uv run ty check .
	uv run mypy .

# Validate PR readiness
.PHONY: validate
validate: lint typecheck test
	$(info $(NEWLINE)==================== Validating PR readiness ====================$(NEWLINE))
	$(info $(NEWLINE)Checking for exposed secrets...$(NEWLINE))
	@uv run detect-secrets --version >/dev/null 2>&1 || { echo "⚠️  detect-secrets unavailable. Run 'uv sync' to install dev dependencies"; exit 1; }
	@uv run detect-secrets scan --all-files . || { echo "⚠️  Secrets detected! Run 'uv run detect-secrets scan --all-files .' to see details"; exit 1; }
	$(info $(NEWLINE)Checking dependency updates...$(NEWLINE))
	@uv pip list --outdated || true
	$(info $(NEWLINE)Checking for uncommitted changes...$(NEWLINE))
	@git status --porcelain | head -5 || true
	$(info $(NEWLINE)Checking for security vulnerabilities...$(NEWLINE))
	@uv run bandit --version >/dev/null 2>&1 || { echo "⚠️  bandit unavailable. Run 'uv sync' to install dev dependencies"; exit 1; }
	@uv run bandit -r src/ -ll -f json -o bandit-report.json || { echo "⚠️  Security issues found! Check bandit-report.json"; exit 1; }
	@rm -f bandit-report.json
	$(info $(NEWLINE)✅ All validation checks passed! Ready for PR review.$(NEWLINE))

# Cleanup
.PHONY: clean
clean:
	$(info $(NEWLINE)==================== Cleaning temp files ====================$(NEWLINE))
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf *.egg-info/
	rm -f examples/robot/*.robot
	rm -f output.xml log.html report.html selenium-screenshot-*.png
	rm -f compile.log coverage.xml test-results.xml texput.log
	rm -f *.xml *.html *.log
	rm -rf robot-tests/ zephyr-tests/
	rm -rf .ruff_cache/
	rm -rf visualizations/
	rm -rf examples/json/*improved.json

# Examples
.PHONY: examples
examples: example-basic example-login example-suggestions example-user-registration example-file-transfer example-database-api example-usage-basic example-usage-advanced example-usage-cli

.PHONY: example-basic
example-basic:
	$(info $(NEWLINE)==================== Running basic login example ====================$(NEWLINE))
	@cat examples/json/basic_login.json
	uv run importobot examples/json/basic_login.json examples/robot/basic_example.robot
	@cat examples/robot/basic_example.robot
	uv run robot --dryrun examples/robot/basic_example.robot

.PHONY: example-login
example-login:
	$(info $(NEWLINE)==================== Running browser login example ====================$(NEWLINE))
	@cat examples/json/browser_login.json
	uv run importobot examples/json/browser_login.json examples/robot/login_example.robot
	@cat examples/robot/login_example.robot
	uv run robot --dryrun examples/robot/login_example.robot

.PHONY: example-suggestions
example-suggestions:
	$(info $(NEWLINE)==================== Running hash file example with suggestions ====================$(NEWLINE))
	@cat examples/json/hash_file.json
	uv run importobot examples/json/hash_file.json examples/robot/hash_example.robot
	@cat examples/robot/hash_example.robot
	uv run importobot --apply-suggestions examples/json/hash_file.json examples/robot/hash_applied.robot
	@cat examples/robot/hash_applied.robot
	uv run robot --dryrun examples/robot/hash_applied.robot

.PHONY: example-user-registration
example-user-registration:
	$(info $(NEWLINE)==================== Running web form automation example ====================$(NEWLINE))
	@cat examples/json/user_registration.json
	uv run importobot examples/json/user_registration.json examples/robot/user_registration.robot
	@cat examples/robot/user_registration.robot
	uv run robot --dryrun examples/robot/user_registration.robot

.PHONY: example-file-transfer
example-file-transfer:
	$(info $(NEWLINE)==================== Running SSH file transfer example ====================$(NEWLINE))
	@cat examples/json/ssh_file_transfer.json
	uv run importobot examples/json/ssh_file_transfer.json examples/robot/ssh_file_transfer.robot
	@cat examples/robot/ssh_file_transfer.robot
	uv run robot --dryrun examples/robot/ssh_file_transfer.robot

.PHONY: example-database-api
example-database-api:
	$(info $(NEWLINE)==================== Running database and API testing example ====================$(NEWLINE))
	@cat examples/json/database_api_test.json
	uv run importobot examples/json/database_api_test.json examples/robot/database_api_test.robot
	@cat examples/robot/database_api_test.robot
	uv run robot --dryrun examples/robot/database_api_test.robot

.PHONY: example-parameters
example-parameters:
	$(info $(NEWLINE)==================== Running parameter mapping example ====================$(NEWLINE))
	@cat examples/json/cat_file.json
	uv run importobot examples/json/cat_file.json examples/robot/cat_file.robot
	@cat examples/robot/cat_file.robot
	uv run robot --dryrun examples/robot/cat_file.robot

.PHONY: example-usage-basic
example-usage-basic:
	$(info $(NEWLINE)==================== Running basic API usage examples ====================$(NEWLINE))
	uv run python scripts/src/importobot_scripts/example_basic_usage.py

.PHONY: example-usage-advanced
example-usage-advanced:
	$(info $(NEWLINE)==================== Running advanced features examples ====================$(NEWLINE))
	uv run python scripts/src/importobot_scripts/example_advanced_features.py

.PHONY: example-usage-cli
example-usage-cli:
	$(info $(NEWLINE)==================== Running CLI usage examples ====================$(NEWLINE))
	uv run python scripts/src/importobot_scripts/example_cli_usage.py


# Interactive demo
.PHONY: interactive-demo
interactive-demo:
	$(info $(NEWLINE)==================== Running interactive business benefits demo ====================$(NEWLINE))
	uv run interactive-demo

.PHONY: interactive-demo-test
interactive-demo-test:
	$(info $(NEWLINE)==================== Running interactive demo in non-interactive mode ====================$(NEWLINE))
	uv run interactive-demo --non-interactive

# MCP commands
.PHONY: mcp-query
mcp-query:
	$(info $(NEWLINE)==================== Querying Qwen model through MCP ====================$(NEWLINE))
	uv run importobot-mcp query

.PHONY: mcp-review
mcp-review:
	$(info $(NEWLINE)==================== Requesting code review through MCP ====================$(NEWLINE))
	uv run importobot-mcp review

# Performance benchmark
.PHONY: bench
bench:
	$(info $(NEWLINE)==================== Running performance benchmarks ====================$(NEWLINE))
	uv run python scripts/src/importobot_scripts/performance_benchmark.py

# Enterprise demo - bulk conversion test
.PHONY: enterprise-demo
enterprise-demo:
	$(info $(NEWLINE)==================== Running enterprise demo - bulk conversion test ====================$(NEWLINE))
	@echo "Generating test files..."
	uv run generate-enterprise-tests --output-dir zephyr-tests --count 800
	@echo "Converting to Robot Framework..."
	uv run importobot --directory zephyr-tests --output robot-tests
	@echo "Conversion complete: $(find robot-tests -name '*.robot' | wc -l | tr -d ' ') files generated"

# Scripts subproject commands
.PHONY: scripts-test
scripts-test:
	$(info $(NEWLINE)==================== Running scripts subproject tests ====================$(NEWLINE))
	$(MAKE) -C scripts test

.PHONY: scripts-lint
scripts-lint:
	$(info $(NEWLINE)==================== Running scripts subproject linting ====================$(NEWLINE))
	$(MAKE) -C scripts lint

.PHONY: scripts-format
scripts-format:
	$(info $(NEWLINE)==================== Formatting scripts subproject code ====================$(NEWLINE))
	$(MAKE) -C scripts format

.PHONY: scripts-clean
scripts-clean:
	$(info $(NEWLINE)==================== Cleaning scripts subproject ====================$(NEWLINE))
	$(MAKE) -C scripts clean

.PHONY: scripts-install
scripts-install:
	$(info $(NEWLINE)==================== Installing scripts subproject dependencies ====================$(NEWLINE))
	$(MAKE) -C scripts install

.PHONY: scripts-demo
scripts-demo:
	$(info $(NEWLINE)==================== Running scripts interactive demo ====================$(NEWLINE))
	$(MAKE) -C scripts demo

.PHONY: scripts-demo-non-interactive
scripts-demo-non-interactive:
	$(info $(NEWLINE)==================== Running scripts non-interactive demo ====================$(NEWLINE))
	$(MAKE) -C scripts demo-non-interactive

.PHONY: workspace-test
workspace-test:
	$(info $(NEWLINE)==================== Running tests for entire workspace ====================$(NEWLINE))
	$(MAKE) test
	$(MAKE) scripts-test

.PHONY: workspace-lint
workspace-lint:
	$(info $(NEWLINE)==================== Running linting for entire workspace ====================$(NEWLINE))
	$(MAKE) lint
	$(MAKE) scripts-lint

.PHONY: workspace-format
workspace-format:
	$(info $(NEWLINE)==================== Formatting entire workspace ====================$(NEWLINE))
	$(MAKE) format
	$(MAKE) scripts-format

.PHONY: workspace-clean
workspace-clean:
	$(info $(NEWLINE)==================== Cleaning entire workspace ====================$(NEWLINE))
	$(MAKE) clean
	$(MAKE) scripts-clean
