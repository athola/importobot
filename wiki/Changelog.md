# Changelog

[CHANGELOG.md](../CHANGELOG.md) is the canonical record of versioned changes. This wiki entry highlights the supporting docs, diagrams, and assets that ship with each release so you can jump straight to the follow-up material.

## How to Use This Page
- Read the linked changelog for the detailed list of fixes and features.
- Use the release sections below to find the wiki articles, ADRs, and sample data that were added or updated alongside those changes.
- Verify that any new assets you reference here are committed and versioned with the matching release tag.
- Trim or archive bullets once their supporting docs become obsolete to keep this page focused.

## 0.1.3 (2025-10-23)
- Expanded remote retrieval with the new `--fetch-format` pipeline for Zephyr, TestRail, Jira/Xray, and TestLink, including shared credential flags and adaptive pagination.
- Hardened security by adding regression suites for token masking, configurable rate-limiter env vars, and documenting the new toggles alongside existing security guidance.
- Automated hash-comparison step generation with the shipped sample at `examples/json/hash_compare.json` and refreshed benchmark images under `wiki/benchmarks/`.
- Blueprint ingestion guidance moved to `wiki/architecture/Blueprint-Learning.md`, and API integration design captured in `wiki/architecture/ADR-0003-api-integration.md`.

## 0.1.2 (2025-10-21)
- Introduced the thread-local application context to eliminate global state races and documented the migration path in `wiki/Migration-Guide.md`.
- Delivered a unified caching module with blueprint-aware helpers, reflected in the updated `wiki/Blueprint-Tutorial.md` walkthrough.
- Added the schema parser and template-learning improvements for custom field naming, with performance notes in `wiki/Performance-Characteristics.md`.
- Polished docs around blueprint authoring and context setup in `wiki/architecture/Application-Context-Implementation.md`.

## 0.1.1 (2025-09-29)
- Debuted the medallion architecture (bronze/silver/gold) and validation service, setting the baseline for pipeline extensibility.
- Rolled out the Bayesian confidence scoring system covering Zephyr, Xray, TestRail, TestLink, and generic formats.
- Grew the automated test suite past 1,500 cases with property-based invariants and enterprise benchmarking harnesses.
- Published foundational documentation, including mathematical notes and expanded API references, to support the new architecture.

## 0.1.0 (2025-09-23)
- Initial Importobot release featuring the JSON-to-Robot conversion engine, CLI tooling, and pandas-inspired API surface.
- Supported bulk processing, intelligent field mapping, and security validation out of the box.
- Shipped with extensive documentation, CI/CD automation, and a 1,100+ test baseline establishing quality gates.

## Earlier Releases
For older history, rely on [CHANGELOG.md](../CHANGELOG.md). Add entries to this page only when a release introduces new wiki content or assets that benefit from a quick pointer.
