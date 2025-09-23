# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-09-23

### Added
- **Initial release** of Importobot - Test Framework Converter
- **Core conversion engine** for transforming test cases from JSON format to Robot Framework
- **Automated bulk processing** for handling hundreds or thousands of test cases
- **Intelligent field mapping** with automatic detection of test steps, expected results, tags, and priorities
- **Pandas-inspired API** with `JsonToRobotConverter` as the primary interface
- **Enterprise toolkit** via `importobot.api` module for validation, converters, and suggestions
- **Comprehensive CLI interface** with `importobot` command-line tool
- **Security validation** with SSH parameter extraction and security compliance checks
- **Interactive demo system** with business case visualization and ROI calculations
- **Performance benchmarking** infrastructure for enterprise-scale validation
- **Modular architecture** with extensible design for supporting additional input formats
- **Quality assurance** with 1153+ tests achieving comprehensive coverage
- **Professional documentation** with complete API reference and usage examples

### Technical Features
- **Multi-format support** for Zephyr, JIRA/Xray, and TestLink test management systems
- **Robust error handling** with fail-fast principles and comprehensive validation
- **Type safety** with full mypy compliance and runtime type checking
- **Code quality** achieving 10.00/10.00 pylint score with comprehensive linting
- **CI/CD integration** with GitHub Actions for automated testing and quality checks
- **Package management** using modern uv tooling with lock file dependency management

### Dependencies
- **Core**: Robot Framework ecosystem (SeleniumLibrary, SSHLibrary, RequestsLibrary, DatabaseLibrary)
- **Optional**: matplotlib, numpy, pandas for analytics and visualization features
- **Development**: Comprehensive testing and linting toolchain
