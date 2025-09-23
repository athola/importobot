"""Shared SSH patterns and indicators for consistent detection."""

# SSH operation indicators
SSH_STRONG_INDICATORS = [
    "ssh",
    "scp",
    "sftp",
    "keyfile:",
    "upload",
    "download",
    "put file",
    "get file",
]

# Additional SSH patterns
SSH_ADDITIONAL_PATTERNS = [
    "file transfer",
    "host:",
    "username:",
    "password:",
]

# Remote file path indicators
SSH_FILE_PATH_INDICATORS = ["/etc/", "/var/", "/opt/", "/home/", "/usr/", "/tmp/"]

# Combined list for convenience
ALL_SSH_INDICATORS = SSH_STRONG_INDICATORS + SSH_ADDITIONAL_PATTERNS
