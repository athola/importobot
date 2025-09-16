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

## Additional Security Resources

- [GitHub Security Advisories](https://github.com/athola/importobot/security/advisories)
- [GitHub Dependabot Alerts](https://github.com/athola/importobot/security/dependabot)

For any security-related questions or concerns not covered in this policy, please contact security@importobot.com.