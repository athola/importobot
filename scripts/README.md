# Importobot Scripts

This subproject contains demo and utility scripts for the Importobot test migration tool.

## Contents

- **interactive_demo.py** - Interactive business benefits demonstration
- **demo_config.py** - Configuration management for demos
- **demo_logging.py** - Enhanced logging for demo scripts
- **demo_scenarios.py** - Business scenario modeling
- **demo_validation.py** - Input validation and security
- **generate_enterprise_tests.py** - Enterprise test case generator
- **generate_zephyr_tests.py** - Zephyr test case generator

## Installation

Install the scripts subproject:

```bash
cd scripts
uv sync
```

Or from the root workspace:

```bash
make scripts-install
```

## Usage

### Interactive Demo

Run the business benefits demonstration:

```bash
make demo                      # Interactive mode
make demo-non-interactive     # Non-interactive mode
```

### Test Generation

Generate test cases for demonstration:

```bash
make generate-tests
```

### Testing

Run the scripts tests:

```bash
make test
```

## Dependencies

The scripts subproject depends on:

- **importobot** (workspace dependency)
- **matplotlib** - For data visualizations
- **pandas** - For data manipulation
- **numpy** - For numerical operations
- **seaborn** - For statistical visualizations

## Development

This is a separate uv subproject within the Importobot workspace. It can be developed and tested independently from the main package while maintaining access to the core importobot functionality.