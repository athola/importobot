# Importobot

<div align="center">

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

</div>

Importobot converts test case exports from Zephyr, TestRail, Xray, and TestLink into runnable Robot Framework suites. Use it to automate the migration of large, manual test libraries.

## Recent Updates

- **Security Modules**: Added `src/importobot/security/` with credential management, HSM adapters, SIEM connectors, template scanning, and compliance reporting so the CLI no longer needs miscellaneous helpers scattered under `utils/`.
- **Encrypted Credentials**: `CredentialManager` now enforces Fernet encryption via the optional `security` extra (`pip install 'importobot[security]'`) and the `IMPORTOBOT_ENCRYPTION_KEY` environment variable (32-byte key or `openssl rand -base64 32` output).
- **Security Regression Suite**: 13 new security-focused test modules lift the total test count to 2,644 (`UV_CACHE_DIR=.uv-cache uv run pytest --collect-only --quiet`), covering SIEM forwarding, SOC 2 scoring, template scanning, and secure memory cleanup paths.

See the [changelog](CHANGELOG.md) for a full list of changes.

## Installation

For end-users, install from PyPI:
```sh
pip install importobot
```
Optional security features (encryption, secure memory helpers) live in an extra:
```sh
pip install 'importobot[security]'
```
For developers contributing to the project, see the [Project Setup](https://github.com/athola/importobot/wiki/Getting-Started#project-setup) instructions.

## Quick Start

To convert a single file or an entire directory of test case exports, use the `JsonToRobotConverter`.

```python
import importobot

# Convert a single file from Zephyr JSON to a Robot Framework file
converter = importobot.JsonToRobotConverter()
summary = converter.convert_file("zephyr_export.json", "output.robot")

# Convert an entire directory of exports
result = converter.convert_directory("./exports", "./converted")
```

## Security Controls

Security-sensitive deployments now opt into the dedicated security package.

- **Encrypt credentials**. Install the `security` extra, set a strong Fernet key, and persist an encrypted blob instead of a plain string:

```bash
pip install 'importobot[security]'
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
# Optional: fetch the key from the OS keyring instead of env vars
export IMPORTOBOT_KEYRING_SERVICE="importobot-ci"
export IMPORTOBOT_KEYRING_USERNAME="automation"
```

```python
from importobot.security import CredentialManager

manager = CredentialManager()
encrypted = manager.encrypt_credential(os.environ["ZEPHYR_TOKEN"])
# Store encrypted.ciphertext somewhere safe; decrypt only when needed
zephyr_token = manager.decrypt_credential(encrypted)
```

- **Let Importobot handle the keyring.** Skip manual key generation by letting
  `CredentialManager` create and store a Fernet key directly in the system
  keyring:

```python
from importobot.security import CredentialManager

CredentialManager.store_key_in_keyring(
    service="importobot-ci",
    username="automation",
    overwrite=True,        # optional, set when rotating keys
)
```

- **Scan Robot templates**. Block obvious credential leaks before invoking `--robot-template`:

```python
from importobot.security import TemplateSecurityScanner

scanner = TemplateSecurityScanner()
report = scanner.scan_template_file("templates/login.robot")
if not report.is_safe:
    for issue in report.issues:
        print(f"{issue.severity.upper()} {issue.issue_type}: {issue.description}")
```

- The CLI now runs this scan automatically when you pass `--robot-template` and exits if any template reports `report.is_safe == False`.

- **Legacy token compatibility**. `APIIngestConfig.tokens` now stores `SecureString` instances by default. Prefer `config.get_token()` or `config.secure_tokens` in new code. If you still need plaintext lists temporarily, call `config.plaintext_tokens` (emits a `DeprecationWarning`) and plan to migrate those callers to the secure APIs.
- **Rotate Fernet keys**. Follow the [Key Rotation Guide](wiki/Key-Rotation.md) and use
  `importobot_enterprise.key_rotation.rotate_credentials()` to re-wrap ciphertexts when
  replacing `IMPORTOBOT_ENCRYPTION_KEY`.

### Token Validation Settings

| Environment Variable | Purpose |
| --- | --- |
| `IMPORTOBOT_MIN_TOKEN_LENGTH` | Override the default 12-character minimum (hard floor of 8). |
| `IMPORTOBOT_TOKEN_PLACEHOLDERS` | Comma-separated list of exact placeholder tokens (normalized by stripping `-`/`_`). |
| `IMPORTOBOT_TOKEN_INDICATORS` | Comma-separated list of substrings that cause immediate rejection (matched case-insensitively). |
| `IMPORTOBOT_SKIP_TOKEN_VALIDATION` | Set to `1` only in trusted benchmarks to bypass validation entirely. |
| `IMPORTOBOT_KEYRING_SERVICE` / `IMPORTOBOT_KEYRING_USERNAME` | Load encryption keys from the OS keyring when the security extra is installed. |

### Enterprise Add-ons

Enterprise customers can install the optional package components that live under
`importobot_enterprise`:

```sh
pip install 'importobot[enterprise]'
```

This exposes:

- `SoftwareHSM` – an in-memory HSM adapter backed by `SecureString`
- `SIEMManager` plus Splunk/Elastic connectors – ship audit events to SOC tooling
- `EnterpriseComplianceEngine` – score SOC2/ISO27001 controls for audits
- `rotate_credentials()` – rewrap stored ciphertexts using new keys

### Performance Considerations

The security module adds minimal overhead:

- **Import time**: ~56ms for the top-level `import importobot` path (< 100ms target)
- **Token validation**: ~18 microseconds per config creation (negligible)
- **Memory**: SecureString adds ~200 bytes overhead per token

For performance-critical scenarios where you create thousands of configs per second, you can disable token validation:

```bash
export IMPORTOBOT_SKIP_TOKEN_VALIDATION=1
```

**Note**: Disabling validation is NOT recommended for production use. Only use in trusted environments where tokens are pre-validated. The performance gain is minimal (~0.018ms/config).

## Documentation

Project documentation is in the [wiki](https://github.com/athola/importobot/wiki).

- **[Getting Started](https://github.com/athola/importobot/wiki/Getting-Started)**: Install the tool and run a conversion.
- **[User Guide](https://github.com/athola/importobot/wiki/User-Guide)**: Learn common conversion commands and see detailed examples.
- **[How to Navigate this Codebase](https://github.com/athola/importobot/wiki/How-to-Navigate-this-Codebase)**: A developer's guide to the project structure and architecture.
- **[SIEM Integration](https://github.com/athola/importobot/wiki/SIEM-Integration)**: Configure Splunk, Elastic Security, or Microsoft Sentinel connectors for security event forwarding.

## Community

For questions and discussions, please use the [GitHub issue tracker](https://github.com/athola/importobot/issues).

## Contributing

Contributions are welcome. Please see the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for more information.

## License

[BSD 2-Clause](./LICENSE)
