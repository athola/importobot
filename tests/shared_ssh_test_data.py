"""Shared SSH test data and expected keywords to reduce duplication."""

from typing import List

# SSH Connection Keywords
SSH_CONNECTION_KEYWORDS: List[str] = [
    "Open Connection",
    "Close Connection",
    "Close All Connections",
    "Switch Connection",
    "Get Connection",
    "Get Connections",
]

# SSH Authentication Keywords
SSH_AUTH_KEYWORDS: List[str] = [
    "Login",
    "Login With Public Key",
]

# SSH Configuration Keywords
SSH_CONFIG_KEYWORDS: List[str] = [
    "Set Default Configuration",
    "Set Client Configuration",
]

# SSH Verification Keywords
SSH_VERIFICATION_KEYWORDS: List[str] = [
    "File Should Exist",
    "File Should Not Exist",
    "Directory Should Exist",
    "Directory Should Not Exist",
]

# SSH Logging Keywords
SSH_LOGGING_KEYWORDS: List[str] = [
    "Enable Ssh Logging",
    "Disable Ssh Logging",
]

# SSH Command Keywords
SSH_COMMAND_KEYWORDS: List[str] = [
    "Execute Command",
    "Start Command",
    "Read Command Output",
    "Write",
    "Write Bare",
    "Read",
    "Read Until",
    "Read Until Prompt",
    "Read Until Regexp",
    "Write Until Expected Output",
]

# SSH File Transfer Keywords
SSH_FILE_KEYWORDS: List[str] = [
    "Put File",
    "Put Directory",
    "Get File",
    "Get Directory",
    "Create File",
    "Remove File",
    "Move File",
    "Get File Size",
    "Get File Permissions",
    "Set File Permissions",
]

# SSH Directory Keywords
SSH_DIRECTORY_KEYWORDS: List[str] = [
    "List Directory",
    "List Files In Directory",
    "List Directories In Directory",
    "Create Directory",
    "Remove Directory",
    "Move Directory",
]

# Combined lists for convenience
ALL_SSH_KEYWORDS: List[str] = (
    SSH_CONNECTION_KEYWORDS
    + SSH_AUTH_KEYWORDS
    + SSH_CONFIG_KEYWORDS
    + SSH_FILE_KEYWORDS
    + SSH_DIRECTORY_KEYWORDS
    + SSH_VERIFICATION_KEYWORDS
    + SSH_COMMAND_KEYWORDS
    + SSH_LOGGING_KEYWORDS
)

# Expected total count for validation
EXPECTED_SSH_KEYWORD_COUNT = len(ALL_SSH_KEYWORDS)

# Test generation constants
TESTS_PER_SSH_KEYWORD = 3
EXPECTED_TOTAL_SSH_TESTS = EXPECTED_SSH_KEYWORD_COUNT * TESTS_PER_SSH_KEYWORD

# Basic SSH connection test data


def get_basic_ssh_connection_keywords() -> List[str]:
    """Get basic SSH connection keywords."""
    return [
        "Open Connection",
        "Login",
        "Execute Command",
        "Put File",
        "Get File",
    ]
