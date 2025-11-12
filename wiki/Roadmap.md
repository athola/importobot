# Roadmap

This document outlines the planned future development for Importobot.

## Near-Term (Q3 2025)

-   **Bulk Conversion Improvements**: Optimize the tool to handle large, recursive Zephyr exports efficiently, reducing the need for manual cleanup.
-   **Xray/TestLink Parser Integration**: Integrate the new parser for Xray and TestLink exports.
-   **Performance Profiling**: Implement timing metrics and I/O profiling to identify and resolve performance bottlenecks.

## Mid-Term (Q4 2025 – Q1 2026)

-   **REST API**: Develop a REST API to allow CI/CD systems and other services to interact with Importobot programmatically.
-   **Plugin Architecture**: Design and implement a plugin architecture to enable adding new input/output formats without modifying the core converter.
-   **Conversion Reporting**: Implement lightweight reporting features to track conversion success rates, error rates, and other key metrics.

## Long-Term

-   **Support for Other Frameworks**: Expand conversion capabilities to target test automation frameworks beyond Robot Framework.
-   **AI-Powered Suggestions**: Implement machine learning models to suggest improvements for test tags and step descriptions.
-   **Hosted Service**: Evaluate the feasibility of offering a hosted version of Importobot for teams unable to deploy the CLI locally.

## Future Work

### Zephyr Scale Enhancements

-   **Enhanced Field Recognition**: Provide more robust support for Zephyr-specific fields and test structures.
-   **Refined Test Analysis**: Improve the classification of test levels and preconditions within Zephyr exports.
-   **Cross-Platform Test Generation**: Generate Robot Framework tests that adapt more effectively to different execution platforms.
-   **Deeper API Integration**: Achieve more comprehensive integration with the Zephyr Scale API to extract additional metadata and traceability information.

### Cloud Storage Backends

-   **Amazon S3 Integration**: Add support for storing and retrieving test data directly from Amazon S3 and S3-compatible services.
-   **Azure & GCP Integration**: Extend support to include Azure Blob Storage and Google Cloud Storage.

## Feedback

We welcome your feedback on this roadmap. Please open a GitHub issue for specific feature requests or general comments.
