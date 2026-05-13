# Importobot

<div align="center">

| | |
| --- | --- |
| Testing | [![Test](https://github.com/athola/importobot/actions/workflows/test.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/test.yml) [![Lint](https://github.com/athola/importobot/actions/workflows/lint.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/lint.yml) [![Typecheck](https://github.com/athola/importobot/actions/workflows/typecheck.yml/badge.svg)](https://github.com/athola/importobot/actions/workflows/typecheck.yml) |
| Package | [![PyPI Version](https://img.shields.io/pypi/v/importobot.svg)](https://pypi.org/project/importobot/) [![PyPI Downloads](https://img.shields.io/pypi/dm/importobot.svg)](https://pypi.org/project/importobot/) |
| Meta | [![License](https://img.shields.io/pypi/l/importobot.svg)](./LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |

</div>

Convert Zephyr, TestRail, Xray, and TestLink test case exports into runnable Robot Framework suites — without manually rebuilding each test.

[Documentation](https://github.com/athola/importobot/wiki) · [Changelog](CHANGELOG.md) · [Issues](https://github.com/athola/importobot/issues)

## Highlights

- **Bulk conversion**: process entire directories of exports in one command (~6s for 1,000 tests, see [benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks))
- **Source-readable output**: preserves test names, priorities, and comments so reviewers can trace generated steps back to the original case
- **Multiple input formats**: Zephyr (JSON), TestRail, Xray, TestLink, plus direct API ingest via `--fetch-format`
- **Encrypted credentials**: optional Fernet encryption for API tokens via `importobot[security]`, with OS keyring support
- **Enterprise observability**: optional `importobot[enterprise]` ships SOC2/ISO27001 scoring, HSM adapters, and SIEM connectors (Splunk, Elastic, Sentinel)
- **Library or CLI**: drive conversions from Python via `JsonToRobotConverter`, or from the shell via the `importobot` command
- **Fail-fast validation**: schema and security checks run before long conversions; bad input never silently produces broken Robot output

## Installation

From PyPI:

```sh
pip install importobot
# or with uv
uv add importobot
```

Optional extras for security and enterprise features:

```sh
pip install 'importobot[security]'    # Fernet encryption + keyring support
pip install 'importobot[enterprise]'  # HSM, SIEM connectors, compliance scoring
```

For local development, see the [Getting Started](https://github.com/athola/importobot/wiki/Getting-Started#project-setup) guide in the wiki.

## Quick Start

### Command line

```sh
# Convert a single Zephyr export
importobot zephyr_export.json output.robot

# Convert an entire directory in bulk
importobot --directory ./exports --output ./converted

# Fetch from a TestRail instance and convert in one step
importobot --fetch-format testrail --api-url https://example.testrail.io \
  --tokens "$TESTRAIL_TOKEN" --project 12 --output ./converted
```

### Python API

```python
import importobot

converter = importobot.JsonToRobotConverter()

# Single file
summary = converter.convert_file("zephyr_export.json", "output.robot")

# Whole directory
result = converter.convert_directory("./exports", "./converted")
```

See the [User Guide](https://github.com/athola/importobot/wiki/User-Guide) for field mapping, schema overrides (`--input-schema`), and template learning (`--robot-template`).

## Security

Importobot's security features are opt-in via the `security` and `enterprise` extras. The CLI scans Robot templates automatically when `--robot-template` is passed and aborts on credential leaks.

```sh
pip install 'importobot[security]'
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

```python
import os

from importobot.security import CredentialManager, TemplateSecurityScanner

# Encrypt API tokens at rest
manager = CredentialManager()
encrypted = manager.encrypt_credential(os.environ["ZEPHYR_TOKEN"])
plain = manager.decrypt_credential(encrypted)

# Block credential leaks in Robot templates before conversion
report = TemplateSecurityScanner().scan_template_file("templates/login.robot")
assert report.is_safe, report.issues
```

Common environment variables:

| Variable | Purpose |
| --- | --- |
| `IMPORTOBOT_ENCRYPTION_KEY` | Fernet key (32-byte base64) for credential encryption |
| `IMPORTOBOT_KEYRING_SERVICE` / `IMPORTOBOT_KEYRING_USERNAME` | Load the encryption key from the OS keyring |
| `IMPORTOBOT_MIN_TOKEN_LENGTH` | Token length floor (default 12, hard floor 8) |
| `IMPORTOBOT_TOKEN_PLACEHOLDERS` | Comma-separated tokens to reject as placeholders |
| `IMPORTOBOT_SKIP_TOKEN_VALIDATION` | Set to `1` for trusted benchmarks only |

Deeper guides:

- [Key Rotation](https://github.com/athola/importobot/wiki/Key-Rotation): rotate `IMPORTOBOT_ENCRYPTION_KEY` and re-wrap stored ciphertexts
- [SIEM Integration](https://github.com/athola/importobot/wiki/SIEM-Integration): Splunk, Elastic, and Microsoft Sentinel connectors
- [Security Standards](https://github.com/athola/importobot/wiki/Security-Standards): coding standards and review process

## Documentation

The full wiki lives at [github.com/athola/importobot/wiki](https://github.com/athola/importobot/wiki). Common entry points:

**Users**

- [Getting Started](https://github.com/athola/importobot/wiki/Getting-Started): install and run a first conversion
- [User Guide](https://github.com/athola/importobot/wiki/User-Guide): CLI reference, API ingest, schema overrides
- [Blueprint Tutorial](https://github.com/athola/importobot/wiki/Blueprint-Tutorial): end-to-end migration walkthrough
- [Migration Guide](https://github.com/athola/importobot/wiki/Migration-Guide): version-to-version upgrade notes

**Developers**

- [How to Navigate this Codebase](https://github.com/athola/importobot/wiki/How-to-Navigate-this-Codebase): architecture and module map
- [API Reference](https://github.com/athola/importobot/wiki/API-Reference): public API surface
- [Contributing](https://github.com/athola/importobot/wiki/Contributing): development workflow and branch model
- [Architecture Decision Records](https://github.com/athola/importobot/blob/main/wiki/architecture/): design rationale (ADR-0001 through ADR-0007)

## Performance

Numbers from the in-tree benchmark suite ([wiki/Performance-Benchmarks](https://github.com/athola/importobot/wiki/Performance-Benchmarks)):

- **Conversion throughput**: ~6 seconds for 1,000 Zephyr test cases
- **Format detection**: ~55 ms average across the supported input formats
- **Import time**: ~56 ms for `import importobot` (target: <100 ms)
- **Token validation**: ~18 µs per `APIIngestConfig` creation

ASV charts publish on tagged releases; the workflow is in `.github/workflows/`.

## What's new

**0.1.5** (Feb 2026):

- New `importobot.security` subsystem with `CredentialManager`, `TemplateSecurityScanner`, and `SecurityValidator`
- New `importobot[enterprise]` extra: HSM, SIEM connectors, SOC2/ISO27001 scoring
- CI: `actions/checkout@v6`, PR coverage-delta gate (60% on modified files), pre-commit workflow
- Test suite: 2,860 tests including 23 new security/enterprise modules

See the [changelog](CHANGELOG.md) for the full history.

## Contributing

Issues and pull requests are welcome. Start with the [Contributing Guide](https://github.com/athola/importobot/wiki/Contributing) for the branch model (`feature → development → main`) and local dev setup.

## License

[BSD 2-Clause](./LICENSE)
