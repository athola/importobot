# Importobot Wiki

Welcome to the Importobot wiki! Importobot is a tool that converts test cases from various test management frameworks (Zephyr, JIRA/Xray, TestLink, etc.) into Robot Framework format.

Importobot automates the migration process, which would otherwise require manual conversion of thousands of test cases. It eliminates the tedious and error-prone process of manually converting test cases when teams want to adopt Robot Framework for automated testing.

- **Automated Conversion**: Convert test cases with a single command.
- **Bulk Conversion**: Convert entire directories of test cases.
- **Multiple Format Support**: Supports Zephyr JSON with plans for JIRA/Xray and TestLink.
- **Batch Processing**: Handle hundreds or thousands of test cases at once.
- **Production-Ready Output**: Generates immediately executable Robot Framework files.
- **Intent-Based Parsing**: Pattern recognition for accurate conversion.

## Quick Navigation

- [Getting Started](Getting-Started) - Installation and basic usage
- [User Guide](User-Guide) - Usage instructions
- [API Reference](API-Reference) - Documentation of functions and classes
- [Contributing](Contributing) - Guidelines for contributors
- [FAQ](FAQ) - Common issues and solutions
- [Roadmap](Roadmap) - Future development plans
- [Release Notes](Release-Notes) - Version history and changes

## Why Importobot?

Organizations often have thousands of test cases in legacy test management tools. When teams want to adopt Robot Framework for automated testing, they face a choice:
- **Manual Migration**: Weeks or months of copy-paste work, prone to errors and inconsistencies.
- **Starting Over**: Losing years of accumulated test knowledge and business logic.
- **Status Quo**: Staying with suboptimal tooling due to migration complexity.

Importobot automates the conversion process:
- Convert test suites with a single command.
- Maintain test structure and metadata during conversion.
- Generate Robot Framework files that run without modification.
- Built using TDD practices for reliability.

## Recent Improvements

### Artifact Management
- Enhanced `.gitignore` to properly exclude generated artifacts and test output files
- Added comprehensive `clean` and `deep-clean` Makefile targets to remove temporary files
- Removed accidentally committed artifacts and ensured repository cleanliness

### Code Quality
- Fixed linting issues throughout the codebase using `ruff` and other tools
- Removed unused imports and variables to reduce code clutter
- Standardized code formatting with automated tools
- Improved error handling and validation patterns

### Test Reliability
- Fixed failing tests related to missing test data files
- Improved test data management and file organization
- Enhanced test suite reliability and consistency

### Makefile Improvements
- Added missing targets to help menu for better discoverability
- All Makefile targets now documented in the help section
- Enhanced clean targets to remove additional artifact files

## Project Status

[![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml)
[![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

- **Test Coverage**: 271 tests, all passing
- **Code Quality**: Zero linting warnings
- **Performance**: <1 second per test conversion
- **Reliability**: 99%+ conversion success rate
