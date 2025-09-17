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
2. Send an email to our security team at security@importobot.com with the following information:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact of the vulnerability
   - Any possible mitigations you've identified
3. Encrypt your message with our PGP key if possible (key details below)

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

For any security-related questions or concerns not covered in this policy, please contact security@importobot.com.