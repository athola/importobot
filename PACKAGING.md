# Package Distribution Guide

This document explains how importobot is distributed and published.

## Package Registry

### PyPI (Python Package Index)
The distribution channel for importobot is PyPI.

**Installation:**
```bash
pip install importobot
```

**Package URL:** https://pypi.org/project/importobot/

### GitHub Packages
**Note:** GitHub Packages does not support Python/PyPI packages. Python packages must be distributed through PyPI or alternative Python package indexes.

## Automated Publishing

### Prerequisites
Before automated publishing works, configure these repository secrets:

1. **PYPI_API_TOKEN**:
   - Go to [PyPI Account Settings](https://pypi.org/manage/account/token/)
   - Create a new API token (scope: entire account or specific to importobot)
   - Add as repository secret at `https://github.com/athola/importobot/settings/secrets/actions`

2. **GITHUB_TOKEN**:
   - Automatically provided by GitHub Actions (no setup required)

### Release Process
When a new release is created on GitHub:
1. The `publish-packages.yml` workflow automatically triggers
2. Package is built using `uv build`
3. Package is published to PyPI (if PYPI_API_TOKEN is configured)

### First-Time Setup
For the initial PyPI publication:
1. Manually publish the first version to establish the package
2. Configure the PYPI_API_TOKEN secret
3. Future releases will be automatically published

### Manual Publishing
For manual publishing or testing:

```bash
# Build the package
uv build

# Publish to PyPI (requires PYPI_API_TOKEN)
uv tool install twine
uv tool run twine upload dist/*

# Publish to GitHub Packages (requires GITHUB_TOKEN)
uv tool run twine upload --repository-url https://upload.pypi.org/legacy/ dist/*
```

## Package Verification

### Verify Installation
```bash
# Test basic import
python -c "import importobot; print(' Package installed successfully')"

# Check version
python -c "import importobot; print(f'Version: {getattr(importobot, \"__version__\", \"0.1.1\")}')"

# Test CLI command
importobot --help
```

### Package Integrity
Both PyPI and GitHub Packages distributions:
- Use identical source code and build process
- Include the same dependencies and optional extras
- Provide the same CLI interface and API

## Enterprise Package Split

Enterprise-only helpers (HSM, SIEM, compliance, key rotation) have been moved
into the `importobot_enterprise` namespace so the default wheel can remain
lightweight. The shared distribution exposes both packages, and the
`publish-packages` workflow smoke-tests their extras before uploading:

```bash
pip install 'importobot[enterprise]'
python - <<'PY'
from importobot_enterprise import SIEMManager
print(SIEMManager.__name__)
PY
```

This split keeps optional analytics/cloud dependencies out of the base install
while giving regulated teams a documented import path for enterprise features.

## Key Management & Rotation

The `security` extra bundles `cryptography` and `keyring` so Importobot can
store Fernet keys in the operating system instead of plain environment
variables. Use the helper methods when provisioning or rotating keys:

```python
from importobot.security import CredentialManager

# Generate + store a key directly in the OS keyring
CredentialManager.store_key_in_keyring(
    service="importobot-ci",
    username="automation",
    overwrite=True,
)

# Later, rotate ciphertext without decrypting everything by hand
from importobot_enterprise.key_rotation import rotate_credentials
```

For full runbooks (CI snippets, HSM mirroring, rollback guidance) see
[wiki/Key-Rotation.md](wiki/Key-Rotation.md).

## Development Setup

For developers working with the package:

```bash
# Clone repository
git clone https://github.com/athola/importobot.git
cd importobot

# Install with development dependencies
uv sync --dev

# Install in editable mode
uv pip install -e .
```

## Security

### Package Signing
- PyPI packages are published using secure API tokens
- GitHub Packages use GitHub's built-in authentication
- All publishing happens through automated CI/CD workflows

### Verification
Users can verify package authenticity by:
1. Checking the GitHub repository source
2. Comparing PyPI and GitHub Packages checksums
3. Reviewing the automated publishing workflow logs

### Runtime Security Dependencies
- `cryptography>=42.0.0` ships with the base wheel to enable Fernet encryption for `importobot.security.CredentialManager`. Installing from PyPI automatically provides the wheel; no extra extras are needed.
- Importobot will raise `SecurityError` if `cryptography` is missing. Install it manually with `pip install cryptography` only if building from minimal environments.
- Security modules expect a 32-byte Fernet key in `IMPORTOBOT_ENCRYPTION_KEY`. Generate one once and export it before running CI/CD jobs:

```bash
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

- Tests and local tooling can reuse the same key; avoid committing it to `.env` files.

## Support

For package distribution issues:
- **PyPI Issues:** https://github.com/athola/importobot/issues
- **GitHub Packages Issues:** https://github.com/athola/importobot/issues
- **Documentation:** https://github.com/athola/importobot/wiki
