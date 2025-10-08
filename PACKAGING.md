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
python -c "import importobot; print('✅ Package installed successfully')"

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

## Support

For package distribution issues:
- **PyPI Issues:** https://github.com/athola/importobot/issues
- **GitHub Packages Issues:** https://github.com/athola/importobot/issues
- **Documentation:** https://github.com/athola/importobot/wiki