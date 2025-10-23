# Security Standards

This document outlines essential security practices for development, CI/CD, and runtime. It integrates optimization efforts and requires regular updates.

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
- Never write sensitive data to world-readable paths; prefer project-specific
  directories under `os.path.expanduser("~")` with `os.path.join`.
- Validate and normalise paths with `Path.resolve()` before use, and apply security validator checks where available.
- Restoration flows must use atomic move/copy/commit sequences with rollback to
  avoid partial state.

## Credential hygiene

- Disallow hard-coded credentials anywhere in source or tests.
- `SecurityValidator` inspects SSH and remote command parameters for exposure.
- Block credential-like patterns during validation and log structured warnings.
- Record security-relevant events with the structured logger (no raw secrets in
  output).

## Error handling

- Raise specific exception types (e.g., `ValidationError`, `SecurityError`);
  avoid bare `Exception`.
- Scrub sensitive details (paths, secrets) from user-facing error messages.
- Keep stack traces internal; surface actionable summaries externally.
- Log security failures with context to aid auditing.

## Dependency management

- Run Bandit and Safety scans weekly and for every PR.
- Avoid unsafe primitives such as `eval`, `exec`, or untrusted `pickle` loads in
  production code.
- Pin runtime dependencies in `pyproject.toml` (lockfiles kept under version
  control).
- Generate software bill of materials (SBOM) artifacts as part of release prep
  when required by compliance.

## CI/CD security gates

- `.github/workflows/security.yml` runs Bandit, Safety, SQL pattern detection,
  and credential leak checks on each push/PR; artifacts are uploaded to support audit
  trails.
- Treat security workflow failures as release blockers; investigate before
  merging.

## Operational checklist

1. **Development** – Use the security gateway helpers during feature work and
   keep new endpoints behind validation mechanisms.
2. **Code Review** – Confirm new filesystem, SQL, and JSON entry points follow
   these patterns; flag deviations early.
3. **Release Readiness** – Ensure security workflow results are attached to the
   release record; document residual risk or accepted exceptions.
4. **Incident Response** – Reference structured logs and workflow artifacts for
   triage; restore data using the atomic patterns outlined above.

## Related References

- [Optimization Implementation Summary](Optimization-Implementation)
- [Testing](Testing)
- [Deployment Guide](Deployment-Guide)
