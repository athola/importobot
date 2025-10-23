# Development tasks

export UV_CACHE_DIR := $(CURDIR)/.uv-cache

# Define newline variable for use in info messages
define NEWLINE


endef

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help         - Show this help menu"
	@echo "  init         - Install dependencies"
	@echo "  sync         - Sync environment and install dev dependencies"
	@echo "  test         - Run tests (~2 minutes)"
	@echo "  coverage     - Run tests with coverage"
	@echo "  lint         - Run all linting checks (~2 minutes)"

	@echo "  format       - Format code"
	@echo "  typecheck    - Run type checking (~5 seconds)"
	@echo "  validate     - Validate PR readiness (~5 minutes total)"
	@echo "  clean        - Clean temp files"
	@echo "  examples     - Run all example conversions and usage examples"
	@echo "  example-basic           - Basic login example"
	@echo "  example-login           - Browser login example"
	@echo "  example-suggestions     - Hash file example with suggestions"
	@echo "  example-hash-compare    - Hash compare example showing auto-added comparison step"
	@echo "  hash-compare            - Alias for example-hash-compare"
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
	@echo "  bench                   - Run performance benchmarks"
	@echo "  mutation               - Run mutation tests (mutmut)"
	@echo "  perf-test              - Run performance regression tests"
	@echo "  benchmark-dashboard    - Generate benchmark dashboard HTML"
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
	uv sync --dev
	uv pip install -e ./scripts

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
	$(info $(NEWLINE)==================== Running fast test suite ====================$(NEWLINE))
	uv run pytest -n auto -m "not slow" tests/

.PHONY: test-all
test-all:
	$(info $(NEWLINE)==================== Running full test suite ====================$(NEWLINE))
	uv run coverage run -m pytest -n auto --junitxml=test-results.xml tests/

# Coverage
.PHONY: coverage
coverage:
	$(info $(NEWLINE)==================== Generating coverage report ====================$(NEWLINE))
	uv run coverage report

# Linting
.PHONY: lint
lint:
	$(info $(NEWLINE)==================== Running linting ====================$(NEWLINE))
	@echo "→ Running ruff (fast)..."
	@uv run ruff check .
	@echo "→ Running pydocstyle..."
	@uv run pydocstyle .

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
	uv run pyright
	uv run mypy -p importobot
	uv run mypy tests
	cd scripts && uv run mypy -p importobot_scripts
	cd scripts && uv run mypy tests

# Validate PR readiness
# Expected timing breakdown (~5 minutes total):
#   - lint: ~115s (ruff + pydocstyle)
#   - typecheck: ~5s
#   - test: ~100s (1941 tests)
#   - detect-secrets: ~10s
#   - bandit: ~5s
#   - Total: ~235s (4 minutes)
.PHONY: validate
validate: lint typecheck test
	$(info $(NEWLINE)==================== Validating PR readiness ====================$(NEWLINE))
	@echo "→ [4/6] Checking for exposed secrets..."
	@uv run detect-secrets --version >/dev/null 2>&1 || { echo "⚠️  detect-secrets unavailable. Run 'uv sync' to install dev dependencies"; exit 1; }
	@uv run detect-secrets -c 1 scan --all-files . || { echo "⚠️  Secrets detected! Run 'UV_CACHE_DIR=$(CURDIR)/.uv-cache uv run detect-secrets -c 1 scan --all-files .' to see details"; exit 1; }
	@echo "→ [5/6] Checking dependency updates..."
	@uv pip list --outdated || true
	@echo "→ Checking for uncommitted changes..."
	@git status --porcelain | head -5 || true
	@echo "→ [6/6] Checking for security vulnerabilities..."
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
examples: example-basic example-login example-suggestions example-hash-compare example-user-registration example-file-transfer example-database-api example-usage-basic example-usage-advanced example-usage-cli

.PHONY: example-basic
example-basic:
	$(info $(NEWLINE)==================== Running basic login example ====================$(NEWLINE))
	@cat examples/json/basic_login.json
	uv run importobot --robot-template examples/resources/ examples/json/basic_login.json examples/robot/basic_example.robot
	@cat examples/robot/basic_example.robot
	uv run robot --dryrun examples/robot/basic_example.robot

.PHONY: example-login
example-login:
	$(info $(NEWLINE)==================== Running browser login example ====================$(NEWLINE))
	@cat examples/json/browser_login.json
	uv run importobot --robot-template examples/resources/ examples/json/browser_login.json examples/robot/login_example.robot
	@cat examples/robot/login_example.robot
	uv run robot --dryrun examples/robot/login_example.robot

.PHONY: example-suggestions
example-suggestions:
	$(info $(NEWLINE)==================== Running suggestions showcase examples ====================$(NEWLINE))
	@printf '---- hash_file suggestions ----\n'
	@cat examples/json/hash_file.json
	uv run importobot examples/json/hash_file.json examples/robot/hash_example.robot
	@cat examples/robot/hash_example.robot
	uv run importobot --apply-suggestions --robot-template examples/resources/ examples/json/hash_file.json examples/robot/hash_applied.robot
	@cat examples/robot/hash_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/hash_applied.robot
	@printf '\n---- cat_small_file suggestions ----\n'
	@cat examples/json/cat_small_file.json
	uv run importobot examples/json/cat_small_file.json examples/robot/cat_small_file_example.robot
	@cat examples/robot/cat_small_file_example.robot
	uv run importobot --apply-suggestions --robot-template examples/resources/ examples/json/cat_small_file.json examples/robot/cat_small_file_applied.robot
	@cat examples/robot/cat_small_file_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/cat_small_file_applied.robot
	@printf '\n---- chmod_file suggestions ----\n'
	@cat examples/json/chmod_file.json
	uv run importobot examples/json/chmod_file.json examples/robot/chmod_file_example.robot
	@cat examples/robot/chmod_file_example.robot
	uv run importobot --apply-suggestions --robot-template examples/resources/ examples/json/chmod_file.json examples/robot/chmod_file_applied.robot
	@cat examples/robot/chmod_file_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/chmod_file_applied.robot
	@printf '\n---- cp_file suggestions ----\n'
	@cat examples/json/cp_file.json
	uv run importobot examples/json/cp_file.json examples/robot/cp_file_example.robot
	@cat examples/robot/cp_file_example.robot
	uv run importobot --apply-suggestions --robot-template examples/resources/ examples/json/cp_file.json examples/robot/cp_file_applied.robot
	@cat examples/robot/cp_file_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/cp_file_applied.robot
	@printf '\n---- mkdir suggestions ----\n'
	@cat examples/json/mkdir.json
	uv run importobot examples/json/mkdir.json examples/robot/mkdir_example.robot
	@cat examples/robot/mkdir_example.robot
	uv run importobot --apply-suggestions --robot-template examples/resources/ examples/json/mkdir.json examples/robot/mkdir_applied.robot
	@cat examples/robot/mkdir_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/mkdir_applied.robot

.PHONY: example-hash-compare
example-hash-compare:
	$(info $(NEWLINE)==================== Running hash compare example ====================$(NEWLINE))
	@mkdir -p examples/robot
	@printf '---- hash_compare original ----\n'
	@cat examples/json/hash_compare.json
	IMPORTOBOT_DISABLE_BLUEPRINTS=1 uv run importobot examples/json/hash_compare.json examples/robot/hash_compare_example.robot
	@printf '\n---- hash_compare generated robot (no suggestions) ----\n'
	@cat examples/robot/hash_compare_example.robot
	@printf '\n---- hash_compare suggestions ----\n'
	IMPORTOBOT_DISABLE_BLUEPRINTS=1 uv run importobot --apply-suggestions examples/json/hash_compare.json examples/robot/hash_compare_applied.robot
	@cat examples/robot/hash_compare_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/hash_compare_applied.robot

.PHONY: hash-compare
hash-compare: example-hash-compare
	@printf '\n---- rm_file suggestions ----\n'
	@cat examples/json/rm_file.json
	uv run importobot examples/json/rm_file.json examples/robot/rm_file_example.robot
	@cat examples/robot/rm_file_example.robot
	uv run importobot --apply-suggestions --robot-template examples/resources/ examples/json/rm_file.json examples/robot/rm_file_applied.robot
	@cat examples/robot/rm_file_applied.robot
	uv run robot --pythonpath examples/resources --dryrun examples/robot/rm_file_applied.robot

.PHONY: example-user-registration
example-user-registration:
	$(info $(NEWLINE)==================== Running web form automation example ====================$(NEWLINE))
	@cat examples/json/user_registration.json
	uv run importobot --robot-template examples/resources/ examples/json/user_registration.json examples/robot/user_registration.robot
	@cat examples/robot/user_registration.robot
	uv run robot --dryrun examples/robot/user_registration.robot

.PHONY: example-file-transfer
example-file-transfer:
	$(info $(NEWLINE)==================== Running SSH file transfer example ====================$(NEWLINE))
	@cat examples/json/ssh_file_transfer.json
	uv run importobot --robot-template examples/resources/ examples/json/ssh_file_transfer.json examples/robot/ssh_file_transfer.robot
	@cat examples/robot/ssh_file_transfer.robot
	uv run robot --dryrun examples/robot/ssh_file_transfer.robot

.PHONY: example-database-api
example-database-api:
	$(info $(NEWLINE)==================== Running database and API testing example ====================$(NEWLINE))
	@cat examples/json/database_api_test.json
	uv run importobot --robot-template examples/resources/ examples/json/database_api_test.json examples/robot/database_api_test.robot
	@cat examples/robot/database_api_test.robot
	uv run robot --dryrun examples/robot/database_api_test.robot

.PHONY: example-parameters
example-parameters:
	$(info $(NEWLINE)==================== Running parameter mapping example ====================$(NEWLINE))
	@cat examples/json/cat_file.json
	uv run importobot --robot-template examples/resources/ examples/json/cat_file.json examples/robot/cat_file.robot
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

# Performance benchmark
.PHONY: bench
bench:
	$(info $(NEWLINE)==================== Running performance benchmarks ====================$(NEWLINE))
	uv run python -m importobot_scripts.benchmarks.performance_benchmark

# Mutation testing
.PHONY: mutation
mutation:
	$(info $(NEWLINE)==================== Running mutation tests ====================$(NEWLINE))
	uv run mutmut run
	uv run mutmut results --all 1 || true

# Performance regression tests
.PHONY: perf-test
perf-test:
	$(info $(NEWLINE)==================== Running performance regression tests ====================$(NEWLINE))
	uv run pytest tests/performance --maxfail=1 --durations=10
	uv run python -m importobot_scripts.benchmarks.performance_benchmark --ci-mode --ci-thresholds ci/performance_thresholds.json

# Benchmark dashboard
.PHONY: benchmark-dashboard
benchmark-dashboard:
	$(info $(NEWLINE)==================== Building benchmark dashboard ====================$(NEWLINE))
	uv run python -m importobot_scripts.benchmarks.benchmark_dashboard

# Enterprise demo - bulk conversion test
.PHONY: enterprise-demo
enterprise-demo:
	$(info $(NEWLINE)==================== Running enterprise demo - bulk conversion test ====================$(NEWLINE))
	@echo "Generating test files..."
	uv run generate-enterprise-tests --output-dir zephyr-tests --count 800
	@echo "Converting to Robot Framework..."
	uv run importobot --robot-template examples/resources/ --directory zephyr-tests --output robot-tests
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
