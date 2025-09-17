# Roadmap

This document outlines the future development plans for Importobot.

## Near-term (Q3 2025)

- **Bulk Conversion**: Enhance bulk conversion capabilities.
- **Additional Format Support**: Add support for JIRA/Xray and TestLink.
- **Enhanced Intent Detection**: Improve test step pattern recognition.
- **Expanded Library Coverage**: Expand Robot Framework library mappings.
- **Performance Optimization**: Optimize conversion speed for large test suites.
- **Timing Metrics**: Add timing metrics for conversion operations.
- **Configuration Optimization**: Externalize large configuration data structures.
- **I/O Optimization**: Optimize batch file I/O operations.

## Medium-term (Q4 2025-Q1 2026)

- **API Interface**: Create a REST API for CI/CD integration and a web interface.
- **Plugin System**: Develop a plugin system for format converters.
- **Quality Metrics**: Add conversion analytics and reporting.
- **Enterprise Features**: Implement advanced validation, error recovery, and audit trails.

## Long-term

- **Multi-framework Support**: Support conversion to and from other frameworks.
- **AI-enhanced Conversion**: Add smart suggestions and predictive analysis.
- **Cloud Integration**: Create a cloud-based version of Importobot.

## Recent Improvements

### Artifact Management
- Enhanced `.gitignore` to properly exclude generated artifacts and test output files
- Added comprehensive `clean` and `deep-clean` Makefile targets to remove temporary files
- Removed accidentally committed artifacts and ensured repository cleanliness

### Code Quality Improvements
- Fixed linting issues throughout the codebase
- Removed unused imports and variables
- Standardized code formatting with automated tools
- Improved error handling and validation

### Test Coverage Enhancements
- Fixed failing tests related to missing test data files
- Improved test data management and file organization
- Enhanced test suite reliability and consistency

### Makefile Improvements
- Added missing targets to help menu for better discoverability
- All Makefile targets now documented in the help section
- Enhanced clean targets to remove additional artifact files

## Feedback

We welcome feedback on our roadmap! Please open an issue on GitHub for specific feature requests.