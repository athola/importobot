# Security Standards

This document outlines security practices for development, CI/CD, and runtime.

## Input Validation

- **JSON intake**: Process through `SecurityGateway` when enabled. Always call
  `validate_json_size(json_string, max_size_mb=10)` before parsing.
- **File paths**: Validate with `validate_file_path` and `validate_safe_path`
  before interacting with the filesystem.
- **SQL statements**: Validate with `_validate_sql_query` to reject dangerous
  patterns (chained commands, comments, `UNION SELECT`, `exec`, `xp_`, `sp_`,
  shutdown verbs).
- **Size limits**: Default JSON payload limit is 10 MB; adjust only with explicit
  review.

## File operations

- Temporary files must be created with restrictive permissions (`0600`) using
  `temporary_json_file` or equivalent wrappers.
- Do not write sensitive data to world-readable paths. Use project-specific
  directories under `os.path.expanduser("~")` with `os.path.join`.
- Validate and normalise paths with `Path.resolve()` before use, and apply security validator checks where available.
- Use atomic operations (move/copy/commit) with rollback for file restoration to prevent partial state.

## Credential hygiene

- Do not hard-code credentials in source code or tests.
- `SecurityValidator` inspects SSH and remote command parameters for exposure.
- Block credential-like patterns during validation and log structured warnings.
- Record security-relevant events with the structured logger (no raw secrets in
  output).

## Error handling

- Raise specific exception types (e.g., `ValidationError`, `SecurityError`);
  avoid bare `Exception`.
- Scrub sensitive details (paths, secrets) from user-facing error messages.
- Do not expose stack traces to users. Show actionable summaries instead.
- Log security failures with context to aid auditing.

## Dependency management

- Run Bandit and Safety scans weekly and for every PR.
- Avoid unsafe primitives such as `eval`, `exec`, or untrusted `pickle` loads in
  production code.
- Pin runtime dependencies in `pyproject.toml` (lockfiles kept under version
  control).
- Generate a Software Bill of Materials (SBOM) for each release if required for compliance.

## CI/CD security gates

- `.github/workflows/security.yml` runs Bandit, Safety, SQL pattern detection,
  and credential leak checks on each push/PR; artifacts are uploaded to support audit
  trails.
- Security workflow failures are release blockers. Investigate them before merging.

## Operational checklist

1. **Development**: Use security gateway helpers and keep new endpoints behind validation.
2. **Code Review**: Confirm that new code handling files, SQL, or JSON follows these standards. Flag any deviations.
3. **Release**: Attach security workflow results to the release record. Document any accepted risks.
4. **Incident Response**: Use structured logs and workflow artifacts to investigate incidents. Use the atomic patterns for data restoration.

## Related References

- [Optimization Implementation Summary](Optimization-Implementation)
- [Testing](Testing)
- [Deployment Guide](Deployment-Guide)
