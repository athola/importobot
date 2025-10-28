# Roadmap

This document outlines our future development plans for Importobot.

## Near-Term (Q3 2025)

-   **Improved Bulk Conversion:** Enhance the tool to handle large, recursive Zephyr exports without requiring manual cleanup.
-   **Xray/TestLink Parser:** Review and merge the new parser for Xray and TestLink exports.
-   **Performance Profiling:** Add timing metrics and I/O profiling to identify and address performance bottlenecks.

## Mid-Term (Q4 2025 – Q1 2026)

-   **REST API:** Provide a REST API for CI/CD users who prefer a service over the CLI.
-   **Plugin Architecture:** Investigate a plugin architecture to allow for the addition of new formats without modifying the core converter.
-   **Lightweight Reporting:** Add reporting features to track conversion success/error rates and other metrics.

## Long-Term

-   **Additional Target Frameworks:** Explore the possibility of converting to frameworks other than Robot Framework.
-   **Machine Learning Suggestions:** Use machine learning to suggest improvements to tags and test steps.
-   **Hosted Version:** Investigate the feasibility of a hosted version of Importobot for teams that cannot run the CLI.

## Future Work

### Zephyr Scale Enhancements

-   **Improved Field Recognition:** Better support for Zephyr-specific fields and test structures.
-   **Advanced Test Analysis:** Enhanced classification of test levels and preconditions.
-   **Cross-Platform Generation:** Improved generation of Robot Framework tests that support platform variations.
-   **Complete API Integration:** Deeper integration with the Zephyr Scale API to extract more metadata and traceability information.

### Cloud Storage Backends

-   **S3 Backend:** Add support for storing and retrieving test data from Amazon S3 and S3-compatible services.
-   **Azure & GCP Backends:** Add support for Azure Blob Storage and Google Cloud Storage.

## Feedback

Please provide feedback on this roadmap! Open an issue on GitHub for specific feature requests.
