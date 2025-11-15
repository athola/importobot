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
- **Encrypted Credentials**: `CredentialManager` now enforces Fernet encryption via `cryptography>=42.0.0` and the `IMPORTOBOT_ENCRYPTION_KEY` environment variable (32-byte key or `openssl rand -base64 32` output).
- **Security Regression Suite**: 13 new security-focused test modules lift the total test count to 2,644 (`UV_CACHE_DIR=.uv-cache uv run pytest --collect-only --quiet`), covering SIEM forwarding, SOC 2 scoring, template scanning, and secure memory cleanup paths.

See the [changelog](CHANGELOG.md) for a full list of changes.

## Installation

For end-users, install from PyPI:
```sh
pip install importobot
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

- **Encrypt credentials**. Set a strong Fernet key and persist an encrypted blob instead of a plain string:

```bash
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

```python
from importobot.security import CredentialManager

manager = CredentialManager()
encrypted = manager.encrypt_credential(os.environ["ZEPHYR_TOKEN"])
# Store encrypted.ciphertext somewhere safe; decrypt only when needed
zephyr_token = manager.decrypt_credential(encrypted)
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

- **Forward alerts to SIEM**. Reuse the built-in connectors instead of re-implementing Splunk or Sentinel clients:

```python
from importobot.security import create_splunk_connector, get_siem_manager

splunk = create_splunk_connector(
    host="https://siem.internal",
    token=os.environ["SPLUNK_HEC_TOKEN"],
)
siem_manager = get_siem_manager()
siem_manager.add_connector(splunk)
siem_manager.start()
siem_manager.send_security_event(security_event)
```

Each of these modules records structured audit data so Compliance teams can pull SOC 2 / ISO 27001 reports without reverse-engineering the conversion pipeline.

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
