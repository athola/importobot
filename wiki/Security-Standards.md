# Security Standards

This document outlines the mandatory security practices for this project. All contributions must adhere to these standards, which cover development, CI/CD, and runtime environments.

## Input Validation

All external input must be treated as untrusted and validated before use.

- **JSON Data**: Before parsing, all JSON input must be validated for size using `validate_json_size()`. The default limit is 10 MB. For more complex validation, use the `SecurityGateway` module.
- **File Paths**: Before any filesystem operations, file paths must be validated with `validate_file_path()` and `validate_safe_path()` to prevent directory traversal attacks.
- **SQL Queries**: To prevent SQL injection, all dynamic SQL statements must be checked with `_validate_sql_query()`. This function blocks common attack patterns like chained commands, `UNION SELECT`, and execution of stored procedures.
- **Size Limits**: Do not raise the default 10 MB JSON size limit without a security review.

## Secure File Operations

Careless file handling can lead to data exposure or corruption.

- **Temporary Files**: Always create temporary files with restrictive permissions (`0600`). Use helpers like `temporary_json_file` which handle this automatically.
- **File Permissions**: Never write sensitive data to world-readable paths (e.g., `/tmp`). When writing to user-specific locations, use project-specific subdirectories.
- **Path Normalization**: Before use, all file paths must be normalized with `Path.resolve()` to prevent symbolic link vulnerabilities.
- **Atomic Operations**: To prevent data corruption from partial writes, use atomic move/copy operations with rollback mechanisms.

## Credential Management

Never hard-code credentials (passwords, tokens, API keys) in source code or tests.
- The `SecurityValidator` module is used to inspect command parameters for accidentally exposed credentials.
- The validation system should reject inputs that match common credential patterns (e.g., `sk_live_...`).
- Use the structured logger to record security events, ensuring that raw secrets are never written to logs.

## Secure Error Handling

Error messages can be a source of information leakage.
- **Specific Exceptions**: Always raise specific exception types (e.g., `ValidationError`, `SecurityError`) instead of generic `Exception`.
- **Scrubbing Output**: Ensure that user-facing error messages do not contain sensitive details like file paths or secrets.
- **Stack Traces**: Never expose full stack traces in user output. Provide a concise, actionable summary and a correlation ID if possible.
- **Auditing**: Log security-related failures with enough context to support a future audit, but without logging the sensitive data itself.

## Dependency Management

Vulnerabilities in dependencies are a major risk.
- **Scanning**: We use Bandit and Safety to scan for vulnerabilities in our codebase and dependencies. These scans run weekly and on every pull request.
- **Unsafe Primitives**: Avoid dangerous Python primitives like `eval()`, `exec()`, and `pickle` with untrusted data.
- **Pinning**: All runtime dependencies must be pinned to specific versions in `pyproject.toml` and `uv.lock` to ensure reproducible and secure builds.
- **SBOM**: A Software Bill of Materials (SBOM) should be generated for each release to meet compliance requirements.

## CI/CD Security

Our CI/CD pipeline is a critical control point for security.
- The `.github/workflows/security.yml` workflow automatically runs multiple security checks (Bandit, Safety, SQL pattern detection, credential scanning) on every push and pull request.
- A failure in this workflow is a release blocker and must be investigated and fixed before merging. The artifacts from the scan are saved to provide an audit trail.

## Operational Checklist

1.  **During Development**: Use the provided security helpers (e.g., `SecurityGateway`) and ensure all new endpoints have input validation.
2.  **During Code Review**: Review all changes against these standards, especially those handling files, SQL, or user-provided data.
3.  **During Release**: Attach the security scan results from the CI/CD pipeline to the release notes. Any accepted risks must be documented.
4.  **For Incident Response**: Use the structured logs and CI/CD artifacts as the primary sources of information for investigation. Use the atomic file operations for data restoration if needed.
