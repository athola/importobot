#!/usr/bin/env bash
# Check for secrets in git-tracked and untracked files (respecting .gitignore)

set -e

# Check if detect-secrets is available
if ! uv run detect-secrets --version >/dev/null 2>&1; then
    echo "⚠️  detect-secrets unavailable. Run 'uv sync' to install dev dependencies"
    exit 1
fi

# Get list of files to scan (tracked + untracked, excluding gitignored)
FILES=$(git ls-files && git ls-files --others --exclude-standard | sort -u)

# Check if baseline exists
if [ -f .secrets.baseline ]; then
    echo "Using existing .secrets.baseline for validation..."
    # Scan with baseline - only flag NEW secrets
    if echo "$FILES" | xargs -r uv run detect-secrets scan --baseline .secrets.baseline --force-use-all-plugins; then
        echo "✓ No new secrets detected"
        exit 0
    else
        echo "⚠️  New secrets detected! Review the output above for details"
        exit 1
    fi
else
    echo "No baseline found. Creating .secrets.baseline..."
    # Create baseline file
    echo "$FILES" | xargs -r uv run detect-secrets scan --force-use-all-plugins > .secrets.baseline
    echo "✓ Created .secrets.baseline - please review and commit it"
    exit 0
fi
