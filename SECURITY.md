# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported |
| ------- | --------- |
| 1.x     | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability within Importobot, please follow these steps:

1. **Do not create a public issue** - Vulnerabilities should be reported privately.
2. **Preferred:** Open a [private security advisory](https://github.com/athola/importobot/security/advisories/new) on GitHub so maintainers are paged immediately.
3. **Alternative Method:** If you must email, write to security@importobot.com *after* confirming the mailbox is monitored for your disclosure window (expect a human acknowledgement within one business day). Include:
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

When you report a vulnerability, our security team typically acknowledges reports within 48 hours and completes validation within 5 business days. We coordinate fix timing with you and notify you when patches are released. Security credits are included in release notes unless you prefer to remain anonymous.

### Responsible Disclosure Timeline

| Severity | Triage SLA | Fix/Advisory Target | Notes |
| --- | --- | --- | --- |
| Critical (RCE, key compromise) | 24 hours | 7 days or coordinated release | Maintainers stay in daily contact until patched |
| High (privilege escalation, data exfiltration) | 48 hours | 14 days | Hotfix branch prepared once repro confirmed |
| Medium (DoS, information disclosure) | 72 hours | Next scheduled release (≤30 days) | Documented workarounds shared if fix slips |
| Low (defense-in-depth gaps) | 5 business days | Backlog with quarterly review | Feedback folded into hardening roadmap |

## Security Considerations

### Data Handling
Importobot processes data from external test management systems. Keep your systems secure by validating imported test data, applying updates promptly, and reviewing permissions for any imported Robot Framework files.

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
  optional Fernet key (a warning is logged if a key is not provided) to keep plaintext secrets
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
We keep dependencies current with automated Dependabot updates and regular security audits. Critical CVEs in our dependencies are evaluated and patched promptly based on risk impact.

## Security Best Practices

Keep Importobot secure by running the latest stable version and applying minimal permissions to imported test content. Review converted Robot files for unusual commands and monitor execution logs for unexpected activity.

### SSH and Command Execution Security

Importobot can generate Robot Framework tests that include SSH operations and command execution. These features carry significant security implications:

#### SSH Security Considerations

** Authentication & Access Control:**
- **Never hardcode SSH credentials** in test files or source code
- Use key-based authentication instead of passwords whenever possible
- Implement connection timeouts (recommended: 30 seconds)
- Validate host key fingerprints to prevent man-in-the-middle attacks
- Use dedicated test environments, never production systems for automated testing

** Connection Management:**
- Always close SSH connections explicitly in test teardown
- Implement connection pooling limits to prevent resource exhaustion
- Use SSH connection multiplexing when appropriate
- Monitor active SSH connections and implement cleanup procedures

** Command Execution Safeguards:**
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

** Path Validation:**
- Always validate file paths to prevent directory traversal attacks
- Reject paths containing `..` or `//` sequences
- Implement allow-lists for accessible directories

## Security Limitations

Importobot's defenses are intentionally scoped so they remain understandable:

- **CredentialManager** protects secrets in memory and in configuration files but does not replace a hardware security module (HSM) or an enterprise vault. Store ciphertext in a managed secret store and rotate `IMPORTOBOT_ENCRYPTION_KEY` regularly.
- Use the [Key Rotation Guide](wiki/Key-Rotation.md) and the `importobot_enterprise.key_rotation` helpers to re-wrap ciphertexts when rotating Fernet keys.
- **TemplateSecurityScanner** flags hard-coded credentials, suspicious variables, and dangerous Robot keywords. It cannot interpret custom Python code or Jinja-like templating embedded in `.robot` files. Review rendered templates in CI/CD before execution.
- **SecurityValidator** governs commands Importobot emits. It does not police the downstream systems that eventually execute generated Robot suites. Continue to sandbox Robot test runs and restrict the accounts used for automation.
- **Secrets scanning** relies on regex detectors via `detect-secrets`. It will miss proprietary credential formats unless you add custom patterns (see `IMPORTOBOT_TOKEN_INDICATORS` and `IMPORTOBOT_TOKEN_PLACEHOLDERS`).

When you need to centralize encryption keys, set `IMPORTOBOT_KEYRING_SERVICE` and
`IMPORTOBOT_KEYRING_USERNAME` to fetch the Fernet key from the system keyring (install
the `security` extra to pull in the `keyring` dependency).

Documenting these bounds up-front helps adopters layer Importobot with existing HSM, SIEM, or EDR tooling rather than assuming one tool mitigates every risk.
- Use absolute paths when possible

** Sensitive File Protection:**
Importobot automatically detects and warns about access to sensitive files:
- `/etc/passwd`, `/etc/shadow` (Unix password files)
- `~/.ssh/`, `~/.aws/credentials` (Authentication keys)
- `/root/` directory access
- Windows system directories (`C:\Windows\System32`)

#### Database Security

** SQL Injection Prevention:**
- Use parameterized queries exclusively
- Never construct SQL from untrusted input
- Implement input validation for all database parameters
- Use minimal database privileges for test connections

** Connection Security:**
- Use encrypted connections (SSL/TLS) for database access
- Implement connection timeouts
- Store database credentials securely (environment variables, vaults)
- Use dedicated test databases with isolated data

#### Web Application Testing Security

** Authentication Testing:**
- Test authentication flows without exposing credentials
- Validate session management and timeout behaviors
- Test authorization boundaries and privilege escalation
- Implement CSRF protection testing

** Input Validation:**
- Test for XSS vulnerabilities in form inputs
- Validate file upload restrictions
- Test API endpoint security
- Verify proper error handling that doesn't leak information

#### Environment Isolation

** Test Environment Guidelines:**
- Use isolated test environments that mirror production architecture
- Implement network segmentation between test and production
- Use synthetic test data, never production data
- Implement proper cleanup procedures for test artifacts

** Secret Management:**
- Use environment variables or secret management systems
- Rotate test credentials regularly
- Implement audit logging for secret access
- Never commit secrets to version control

#### Security Monitoring and Auditing

** Logging and Monitoring:**
Log SSH connections and command executions to track test activities. Monitor for unusual test patterns that might indicate misuse and set up alerts for security policy violations. Conduct regular audits of generated test suites to ensure they follow security guidelines.

** Compliance Considerations:**
Test activities should align with your organization's security policies. Document test procedures for audit trails and implement approval workflows for high-risk test scenarios. Periodically review test permissions and access levels to maintain least privilege principles.

## Comprehensive Security Assessment

This section provides an in-depth analysis of Importobot's security module with identified strengths and documented limitations.

### Security Strengths

#### 1. Industry-Standard Encryption

**Implementation:** Fernet (AES-128-CBC + HMAC) from `cryptography` library

**Features:**
- Symmetric encryption with authentication
- Prevents tampering through HMAC-SHA256
- Time-based token expiration support
- Well-audited cryptographic primitives

**Usage:**
```python
from importobot.security import CredentialManager

manager = CredentialManager()
encrypted = manager.encrypt_credential("sensitive_api_key")
# Store encrypted.ciphertext safely
decrypted = manager.decrypt_credential(encrypted)
```

#### 2. Secure Memory Management

**Multi-Layer Protection:**
- Three-pass zeroization (zeros → random → zeros)
- SHA-256 integrity verification
- Locked state with access controls
- Context manager for automatic cleanup

**Best Practice:**
```python
from importobot.config import APIIngestConfig

# Recommended: Context manager ensures cleanup
with APIIngestConfig(...) as config:
    # Use config
    pass
# Tokens automatically zeroized
```

#### 3. Defense-in-Depth Validation

**Token Validation (NOT a security boundary):**
- Exact placeholder detection
- Configurable length requirements (default: 12 chars, min: 8 chars)
- Insecure indicator scanning
- Entropy analysis with warnings

**Note:** Validation catches obvious mistakes but can be bypassed. Use encryption as primary protection.

### Known Limitations and Mitigations

#### 1. Encryption Key Storage

**LIMITATION:** Built-in key storage still depends on optional OS services.

**CURRENT GUIDANCE:**
```bash
# Basic (insecure for production)
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

**RECOMMENDED: System Keyring Integration**

For desktop/development environments:

```bash
# Install the security extra so keyring is available
pip install 'importobot[security]'
```

```python
from importobot.security import CredentialManager

# One-liner: generate + store a Fernet key inside the OS keyring
CredentialManager.store_key_in_keyring(
    service="importobot-ci",
    username="automation",
    overwrite=False,
)

# Importobot automatically loads the key when
# IMPORTOBOT_KEYRING_SERVICE / IMPORTOBOT_KEYRING_USERNAME are set.
```

**Supported Platforms:**
- macOS: Keychain
- Windows: Credential Locker
- Linux: Secret Service (GNOME Keyring, KWallet)

**RECOMMENDED: Cloud KMS (Production)**

For production deployments, use managed key services:

```python
# AWS Secrets Manager
import boto3
client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='importobot/key')
os.environ['IMPORTOBOT_ENCRYPTION_KEY'] = response['SecretString']

# Azure Key Vault
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
client = SecretClient(vault_url="https://<vault>.vault.azure.net/",
                      credential=DefaultAzureCredential())
secret = client.get_secret("importobot-key")
os.environ['IMPORTOBOT_ENCRYPTION_KEY'] = secret.value

# Google Secret Manager
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
name = "projects/<proj>/secrets/importobot-key/versions/latest"
response = client.access_secret_version(request={"name": name})
os.environ['IMPORTOBOT_ENCRYPTION_KEY'] = response.payload.data.decode()
```

**Key Rotation Procedure:**

```python
# 1. Generate new key
new_key = Fernet.generate_key()

# 2. Re-encrypt all credentials
old_manager = CredentialManager()  # Uses current key
os.environ['IMPORTOBOT_ENCRYPTION_KEY'] = new_key.decode()
new_manager = CredentialManager()  # Uses new key

for encrypted_cred in load_all_credentials():
    plaintext = old_manager.decrypt_credential(encrypted_cred)
    new_encrypted = new_manager.encrypt_credential(plaintext)
    store_credential(new_encrypted)

# 3. Update key reference in keyring/KMS
# 4. Revoke old key
```

**Rotation Schedule:**
- Production: Every 90 days
- Development: Every 180 days
- After breach: Immediately

#### 2. Validation Bypasses

**LIMITATION:** Regex-based validation can be circumvented.

**What Validation Catches:**
- Exact placeholders (`"token"`, `"bearer_token"`)
- Test/demo indicators
- Short tokens (< min length)
- Very low entropy (warning)

**What It Misses:**
- Sophisticated fakes (`"sk_live_" + "0" * 32`)
- Obfuscated patterns (`"t" + "oken"`)
- Base64-encoded placeholders
- Context-aware attacks

**Security Model:**
```
┌─────────────────────────────────┐
│ Token Validation                │ ← Defense in depth
│ (Catches mistakes)              │   (NOT security boundary)
├─────────────────────────────────┤
│ Encryption at Rest              │ ← PRIMARY PROTECTION
│ (Fernet + HMAC)                 │   (SECURITY BOUNDARY)
├─────────────────────────────────┤
│ Secure Memory                   │ ← Runtime protection
│ (Zeroization)                   │   (Defense in depth)
├─────────────────────────────────┤
│ Access Controls                 │ ← Infrastructure
│ (File perms, IAM)               │   (SECURITY BOUNDARY)
└─────────────────────────────────┘
```

**Best Practices:**
1. **Never rely on validation for security** - Use encryption
2. **Assume validation can be bypassed** - Attackers will find edge cases
3. **Use real credentials in tests** - Validation is for catching honest mistakes
4. **Monitor token usage** - Audit logs, not validation, detect misuse

#### 3. Template Scanning Limitations

**LIMITATION:** Static analysis has inherent false negatives and positives.

**False Negatives (Missed Secrets):**

```robot
# Obfuscated - Not detected
*** Variables ***
${PART1}    sk_live_
${PART2}    abc123def456
${TOKEN}    ${PART1}${PART2}

# Dynamic - Not detected
${token}=    Get Token From Vault

# Encoded - Not detected
${b64}=    c2tfbGl2ZV9hYmMxMjNkZWY=  # Base64

# Low entropy - May not trigger
${PASS}=    password123
```

**False Positives (Flagged Non-Secrets):**

```robot
# Example in comment
# Example: sk_test_123 (not real)  # ← Flagged

# Valid placeholder syntax
${API_KEY}=    ${PLACEHOLDER}  # ← May flag
```

**Mitigation Strategies:**

1. **Layered Detection:**
```python
from importobot.security import TemplateSecurityScanner

scanner = TemplateSecurityScanner()
report = scanner.scan_template_file("template.robot")

# Risk-based decision
critical = [i for i in report.issues if i.severity == "CRITICAL"]
if critical:
    raise SecurityError("Critical secrets detected")
```

2. **Entropy Analysis:**
```python
import math
from collections import Counter

def shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    counter = Counter(data)
    length = len(data)
    return -sum((c/length) * math.log2(c/length) for c in counter.values())

# Flag low entropy
if shannon_entropy(token) < 3.0:
    logger.warning(f"Low entropy credential: {shannon_entropy(token):.2f} bits/char")
```

3. **CI/CD Integration:**
```yaml
# .github/workflows/security.yml
- name: External Secret Scan
  uses: trufflesecurity/trufflehog@main

- name: Importobot Template Scan
  run: importobot scan-templates --dir ./templates/ --strict
```

### Security Checklist

#### Development
- [ ] Store keys in system keyring or secure file (chmod 600)
- [ ] Enable token validation (default behavior)
- [ ] Use SecureString for all credentials
- [ ] Scan all Robot templates before use
- [ ] Never commit keys to version control

#### Production
- [ ] Use cloud KMS for key storage
- [ ] Rotate keys every 90 days
- [ ] Enable comprehensive audit logging
- [ ] Use context managers for cleanup
- [ ] Integrate secret scanning in CI/CD
- [ ] Document incident response procedures

#### High-Security
- [ ] Manual approval for template changes
- [ ] Entropy-based detection
- [ ] External scanners (TruffleHog, GitGuardian)
- [ ] Regular credential audits
- [ ] Principle of least privilege
- [ ] Air-gapped key generation

### Threat Model

**In Scope:**
1. Credential exposure via version control
2. Memory disclosure attacks
3. Encryption key compromise
4. Template injection attacks

**Out of Scope:**
1. Physical access attacks
2. Timing/side-channel attacks
3. Advanced persistent threats (APTs)
4. Hardware-level exploits

**Risk Assessment:**

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Hardcoded secrets | High | High | Template scanning |
| Memory disclosure | Medium | Medium | SecureString zeroization |
| Key exposure | Medium | High | KMS + rotation |
| Validation bypass | Low | Low | Defense-in-depth only |

### Enterprise Bloat Removed

**Previous security concerns that no longer apply:**

We removed 4,497 lines of enterprise security features that were out of scope:

- SIEM connectors (Splunk, Elastic, Sentinel) - No longer accept string credentials
- HSM integration (AWS CloudHSM, Azure, Thales) - Removed unnecessary complexity
- MITRE ATT&CK integration - Overkill for test conversion tool
- Compliance frameworks - SOC 2, ISO 27001, etc. not needed
- Key rotation automation - Users manage rotation manually

**Impact:** Reduced attack surface, simpler codebase, fewer dependencies.

## Additional Security Resources

- [GitHub Security Advisories](https://github.com/athola/importobot/security/advisories)
- [GitHub Dependabot Alerts](https://github.com/athola/importobot/security/dependabot)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

For security questions or concerns not covered in this policy, use GitHub's private advisory channel or contact security@importobot.com after verifying it is actively monitored.
