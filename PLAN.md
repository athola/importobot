# Importobot Project Roadmap

This document outlines the planned roadmap for the Importobot project, focusing on expanding its capabilities to import a wider variety of test framework formats into Robot Framework.

## 1. Vision

To become a universal converter for various test framework formats into Robot Framework, enabling seamless migration and integration of existing test assets.

## 2. Current State

Importobot currently supports converting Zephyr JSON test cases to Robot Framework format. The project adheres to Test-Driven Development (TDD) and Extreme Programming (XP) principles, ensuring a robust and maintainable codebase.

## 3. Roadmap Phases

### Phase 1: Core Expansion (Q4 2024 - Q1 2025)

*   **Objective**: Integrate support for at least two new popular test framework formats.
*   **Key Features**:
    *   **Jira/Xray JSON Import**: Implement a parser and converter for Jira/Xray JSON exports, a common format for test management.
    *   **TestLink XML Import**: Develop a parser and converter for TestLink XML exports, another widely used test management tool.
    *   **Enhanced Error Handling**: Improve error reporting for unsupported formats or malformed input files.
    *   **CLI Enhancements**: Add options to specify input format explicitly (e.g., `--format zephyr`, `--format xray`, `--format testlink`).
*   **Technical Considerations**:
    *   Modularize existing Zephyr parser/converter to easily add new formats.
    *   Research and select appropriate Python libraries for parsing new formats (e.g., `xml.etree.ElementTree` for XML).
    *   Develop comprehensive unit and integration tests for each new format.

### Phase 2: Advanced Features & Usability (Q2 2025 - Q3 2025)

*   **Objective**: Improve the conversion process with advanced mapping options and enhance user experience.
*   **Key Features**:
    *   **Custom Field Mapping**: Allow users to define custom mappings for fields from source formats to Robot Framework keywords/metadata.
    *   **Test Case Filtering**: Implement options to filter test cases during import based on tags, status, or other criteria.
    *   **Reporting Enhancements**: Generate a summary report after conversion, detailing successful/failed conversions and any warnings.
    *   **Interactive CLI**: Potentially introduce an interactive mode for guided conversions.
*   **Technical Considerations**:
    *   Design a flexible configuration system for custom mappings.
    *   Explore options for dynamic keyword generation in Robot Framework.
    *   Implement robust validation for filtering criteria.

### Phase 3: Ecosystem Integration & Community (Q4 2025 onwards)

*   **Objective**: Expand integration with other tools and foster community contributions.
*   **Key Features**:
    *   **API Exposure**: Consider exposing core conversion logic as a Python library for programmatic use.
    *   **Web Interface (Stretch Goal)**: Develop a simple web-based interface for easier access and use.
    *   **Contribution Guidelines**: Establish clear guidelines for community contributions of new format converters.
    *   **Documentation**: Comprehensive documentation for all supported formats and features.
*   **Technical Considerations**:
    *   Define clear API contracts for the library.
    *   Choose a lightweight web framework (e.g., Flask, FastAPI) if pursuing a web interface.
    *   Set up a continuous integration pipeline for community contributions.

## 4. Non-Goals

*   Bidirectional conversion (Robot Framework to other formats).
*   Full-fledged test management system.
*   Support for all possible test framework formats (focus on popular and requested ones).

## 5. Feedback & Contributions

This roadmap is a living document and will evolve based on user feedback, community contributions, and project priorities. We welcome suggestions and contributions to help shape the future of Importobot.
