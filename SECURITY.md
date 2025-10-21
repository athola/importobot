# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within Importobot, please follow these steps:

1. **Do not create a public issue** - Vulnerabilities should be reported privately.
2. **Preferred:** Open a [private security advisory](https://github.com/athola/importobot/security/advisories/new) on GitHub so maintainers are paged immediately.
3. **Fallback:** If you must email, write to security@importobot.com *after* confirming the mailbox is monitored for your disclosure window (expect a human acknowledgement within one business day). Include:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact of the vulnerability
   - Any possible mitigations you've identified
4. Encrypt your message with our PGP key if possible (key details below)

### Alternative Reporting Methods

For critical vulnerabilities or if email is not accessible, you may also:
- Use GitHub's private vulnerability reporting feature (available through the Security tab)
- Contact project maintainers directly through coordinated disclosure platforms

All reports will be acknowledged and validated within 48 hours.

### PGP Key for Secure Communication

For sensitive vulnerability reports, you can encrypt your message using our PGP key:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----
...
-----END PGP PUBLIC KEY BLOCK-----
```

### Response Expectations

When you report a vulnerability, our security team will:

1. Acknowledge your report within 48 hours
2. Investigate and validate the issue within 5 business days
3. Work on a fix and coordinate a release date with you
4. Notify you when the fix is published
5. Credit you in our release notes (unless you prefer to remain anonymous)

## Security Considerations

### Data Handling
Importobot processes data from external sources. Users should:
- Validate and sanitize imported data
- Regularly update to the latest version
- Review permissions granted to imported content

### Security Gateway Scope
The `SecurityGateway` hardens API inputs against XSS and path traversal as data
enters Importobot. It does not execute SQL, LDAP, or XML payloads, so injection
defenses for those vectors are expected in downstream storage or directory
services. When integrating Importobot with databases or directory services,
continue to use parameterized queries and schema validation in those systems.

- **DoS protection:** Security-sensitive operations are throttled via a token
  bucket (`IMPORTOBOT_SECURITY_RATE_LIMIT` / `IMPORTOBOT_SECURITY_RATE_INTERVAL_SECONDS`)
  so bursts of malicious requests surface as rate-limit errors instead of
  exhausting CPU.

  Example hardening profile for CI environments:

  ```bash
  export IMPORTOBOT_SECURITY_RATE_LIMIT=40                # max 40 guarded ops
  export IMPORTOBOT_SECURITY_RATE_INTERVAL_SECONDS=60     # per 60-second window
  export IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=20            # queued requests before drop
  export IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2          # exponential backoff base
  export IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=8           # cap in seconds
  ```

  For on-prem deployments, settings can also be persisted in `.env`:

  ```ini
  # security.env
  IMPORTOBOT_SECURITY_RATE_LIMIT=25
  IMPORTOBOT_SECURITY_RATE_INTERVAL_SECONDS=30
  IMPORTOBOT_SECURITY_RATE_MAX_QUEUE=10
  IMPORTOBOT_SECURITY_RATE_BACKOFF_BASE=2
  IMPORTOBOT_SECURITY_RATE_BACKOFF_MAX=6
  ```

  Load the profile with `dotenv` tooling or by sourcing the file prior to
  launching Importobot services to ensure consistent throttling across hosts.

### Schema and Template Hardening

Schema ingestion and template rendering accept user-supplied files. As of
October&nbsp;2025, Importobot applies the following defenses:

- **Schema parser safeguards:** Only UTF-8 text files with approved extensions
  (`.md`, `.txt`, `.rst`, `.json`, `.yaml`) are parsed. Symbolic links, binary
  samples, or files above 1&nbsp;MiB are rejected before reading. Each schema
  payload is sanitized to strip control characters, capped at 2&nbsp;MiB of
  content, and limited to 256 sections to contain DoS-style payloads.
- **Template validation:** Template sources are scanned for inline Python
  (`${{ ... }}`), `Evaluate` keywords, and placeholders that begin with `__`.
  Any offending file is skipped. Templates must reside in regular files (no
  symlinks), stay under 2&nbsp;MiB, and pass a textual sniff test before
  ingestion.
- **Sandboxed rendering:** All blueprint renderers now rely on a sandboxed
  `string.Template` subclass that drops unsafe placeholders, coerces values to
  strings, strips control characters, and truncates substitutions to 4&nbsp;KiB
  per token. This prevents template injection through crafted test data.
- **Resource hygiene:** Robot resource imports discovered during ingestion are
  validated with the same controls, and binary or high-risk resources are
  ignored.
- **Credential handling:** Password parameters are encrypted in memory using an
  optional Fernet key (with a logged warning fallback) to keep plaintext secrets
  out of diagnostic logs.
- **Secrets detection:** Test generation performs regex-based scanning of
  templates and dynamic data, aborting when API keys, JWT tokens, or passwords
  are detected.
- **API rate limiting:** External API clients employ a token-bucket rate limiter
  to stay within upstream throttling thresholds and prevent service bans.

Downstream integrations that execute rendered templates should still run in
isolated automation accounts and apply command-level allow-lists.

#### Choosing a Security Level

Importobot ships three levels that tune pattern matching, sensitive path lists,
and validation strictness:

| Level | When to use it | Highlights |
| --- | --- | --- |
| `strict` | Production, regulated workloads, shared environments | Blocks network/`/proc` probes, container escapes, user enumeration; widest sensitive path list; enables verbose audit logging |
| `standard` *(default)* | CI pipelines, team development, staging | Balanced command/path blocking (rm -rf, sudo, shadow file access) without extra enterprise-only checks |
| `permissive` | Local experiments, trusted sandboxes, demos | Eases curl/wget pipe bans and `/dev/null` redirection while keeping core filesystem guards |

Pick the lowest level that satisfies policy and bump to `strict` anywhere
untrusted input can reach the gateway. Mix levels per process by instantiating
`SecurityGateway(security_level="…")`.

### Dependencies
We regularly update dependencies to address known vulnerabilities:
- Automated dependency updates via Dependabot
- Regular security audits of our codebase
- Prompt response to CVEs in our dependencies

## Security Best Practices

For users of Importobot, we recommend:
- Running the latest stable version
- Using minimal required permissions for imported content
- Regularly reviewing imported data for anomalies
- Monitoring logs for suspicious activity

### SSH and Command Execution Security

Importobot can generate Robot Framework tests that include SSH operations and command execution. These features carry significant security implications:

#### SSH Security Considerations

**🔒 Authentication & Access Control:**
- **Never hardcode SSH credentials** in test files or source code
- Use key-based authentication instead of passwords whenever possible
- Implement connection timeouts (recommended: 30 seconds)
- Validate host key fingerprints to prevent man-in-the-middle attacks
- Use dedicated test environments, never production systems for automated testing

**🔒 Connection Management:**
- Always close SSH connections explicitly in test teardown
- Implement connection pooling limits to prevent resource exhaustion
- Use SSH connection multiplexing when appropriate
- Monitor active SSH connections and implement cleanup procedures

**🔒 Command Execution Safeguards:**
- Validate all command parameters to prevent command injection
- Escape shell metacharacters in dynamic command construction
- Avoid using shell operators (`|`, `&`, `;`, `&&`, `||`) in untrusted input
- Implement command timeouts to prevent hanging processes

#### Dangerous Command Patterns

The following command patterns are automatically flagged by Importobot's security validator:

```bash
# Destructive operations
rm -rf /path/*
sudo rm -rf
chmod 777

# Command injection vectors
command | sh
command | bash
eval $(command)
`command`
$(command)

# Privilege escalation
sudo command
su - user

# Network operations with shell execution
curl url | sh
wget url | bash
```

#### File Access Security

**🔒 Path Validation:**
- Always validate file paths to prevent directory traversal attacks
- Reject paths containing `..` or `//` sequences
- Implement allow-lists for accessible directories
- Use absolute paths when possible

**🔒 Sensitive File Protection:**
Importobot automatically detects and warns about access to sensitive files:
- `/etc/passwd`, `/etc/shadow` (Unix password files)
- `~/.ssh/`, `~/.aws/credentials` (Authentication keys)
- `/root/` directory access
- Windows system directories (`C:\Windows\System32`)

#### Database Security

**🔒 SQL Injection Prevention:**
- Use parameterized queries exclusively
- Never construct SQL from untrusted input
- Implement input validation for all database parameters
- Use minimal database privileges for test connections

**🔒 Connection Security:**
- Use encrypted connections (SSL/TLS) for database access
- Implement connection timeouts
- Store database credentials securely (environment variables, vaults)
- Use dedicated test databases with isolated data

#### Web Application Testing Security

**🔒 Authentication Testing:**
- Test authentication flows without exposing credentials
- Validate session management and timeout behaviors
- Test authorization boundaries and privilege escalation
- Implement CSRF protection testing

**🔒 Input Validation:**
- Test for XSS vulnerabilities in form inputs
- Validate file upload restrictions
- Test API endpoint security
- Verify proper error handling that doesn't leak information

#### Environment Isolation

**🔒 Test Environment Guidelines:**
- Use isolated test environments that mirror production architecture
- Implement network segmentation between test and production
- Use synthetic test data, never production data
- Implement proper cleanup procedures for test artifacts

**🔒 Secret Management:**
- Use environment variables or secret management systems
- Rotate test credentials regularly
- Implement audit logging for secret access
- Never commit secrets to version control

#### Security Monitoring and Auditing

**🔒 Logging and Monitoring:**
- Log all SSH connections and command executions
- Monitor for unusual test patterns or failures
- Implement alerting for security policy violations
- Regular security audits of generated test suites

**🔒 Compliance Considerations:**
- Ensure test activities comply with organizational security policies
- Document test procedures for security audits
- Implement approval workflows for high-risk test scenarios
- Regular review of test permissions and access levels

## Additional Security Resources

- [GitHub Security Advisories](https://github.com/athola/importobot/security/advisories)
- [GitHub Dependabot Alerts](https://github.com/athola/importobot/security/dependabot)

For any security-related questions or concerns not covered in this policy, please either use GitHub's private advisory channel or contact security@importobot.com after verifying it is actively monitored.
