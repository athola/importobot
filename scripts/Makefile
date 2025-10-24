# Makefile for importobot-scripts subproject

.PHONY: help test lint format clean install dev demo

help:  ## Show this help message
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

install:  ## Install the scripts package
	uv sync

dev:  ## Install in development mode with all dependencies
	uv sync --dev

test:  ## Run tests
	@echo "==================== Running scripts tests ===================="
	uv run pytest tests/ -v

test-cov:  ## Run tests with coverage
	@echo "==================== Running scripts tests with coverage ===================="
	uv run pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

lint:  ## Run linting checks
	@echo "==================== Running scripts linting ===================="
	uv run ruff check .
	@echo "Linting complete ✓"

format:  ## Format code
	@echo "==================== Formatting scripts code ===================="
	uv run ruff format .
	@echo "Formatting complete ✓"

clean:  ## Clean temporary files
	@echo "==================== Cleaning scripts temporary files ===================="
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf visualizations/*.png
	rm -rf logs/*.log
	@echo "Clean complete ✓"

demo:  ## Run the interactive demo
	@echo "==================== Running interactive demo ===================="
	uv run interactive-demo

demo-non-interactive:  ## Run the demo in non-interactive mode
	@echo "==================== Running non-interactive demo ===================="
	uv run interactive-demo --non-interactive

generate-enterprise-tests:  ## Generate enterprise example test suites
	@echo "==================== Generating enterprise test suites ===================="
	uv run generate-enterprise-tests

generate-zephyr-tests:  ## Generate Zephyr example test suites
	@echo "==================== Generating Zephyr test suites ===================="
	uv run generate-zephyr-tests

generate-tests:  ## Generate test cases
	@echo "==================== Generating test cases ===================="
	$(MAKE) generate-enterprise-tests
	$(MAKE) generate-zephyr-tests

MCP_ARGS ?=

mcp:  ## Launch the Importobot MCP CLI (set MCP_ARGS=\"--help\" etc.)
	@echo "==================== Launching Importobot MCP CLI ===================="
	uv run importobot-mcp $(MCP_ARGS)

all:  ## Run all checks (lint, test, format)
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) format
