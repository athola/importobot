#!/usr/bin/env bash
# Check for secrets in git-tracked and untracked files (respecting .gitignore)

set -e

# Check if detect-secrets is available
if ! .venv/bin/detect-secrets --version >/dev/null 2>&1; then
    echo "WARNING: detect-secrets unavailable. Run 'uv sync' to install dev dependencies"
    exit 1
fi

# Get list of files to scan (tracked + untracked, excluding gitignored)
FILES=$(git ls-files && git ls-files --others --exclude-standard | sort -u)

# Check if baseline exists
if [ -f .secrets.baseline ]; then
    echo "Using existing .secrets.baseline for validation..."
    # Scan with baseline one file at a time to avoid multiprocessing semlock issues
    scan_status=0
    while IFS= read -r file; do
        if [ -n "$file" ]; then
            if ! .venv/bin/detect-secrets scan --baseline .secrets.baseline --force-use-all-plugins "$file"; then
                scan_status=1
            fi
        fi
    done <<< "$FILES"

    if [ $scan_status -eq 0 ]; then
        echo "PASS: No new secrets detected"
        exit 0
    fi

    echo "WARNING: New secrets detected! Review the output above for details"
    exit 1
else
    echo "No baseline found. Creating .secrets.baseline..."
    # Create baseline file
    echo "$FILES" | xargs -r .venv/bin/detect-secrets scan --force-use-all-plugins > .secrets.baseline
    echo "PASS: Created .secrets.baseline - please review and commit it"
    exit 0
fi
