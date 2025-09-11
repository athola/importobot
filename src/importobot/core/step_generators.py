"""Step generation strategies for different test case types."""

import json
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from ..config import TEST_LOGIN_URL
from ..utils.validation import sanitize_robot_string


class StepGenerator(ABC):
    """Abstract base class for step generators."""

    @abstractmethod
    def can_handle(self, action: str) -> bool:
        """Check if this generator can handle the given action."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        """Generate Robot Framework steps for the given action."""
        raise NotImplementedError


class NavigationStepGenerator(StepGenerator):
    """Generates navigation steps for web tests."""

    def can_handle(self, action: str) -> bool:
        return "navigate to" in action.lower()

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        return [
            f"    Go To    {TEST_LOGIN_URL}",
            f"    Page Should Contain    {sanitize_robot_string(expected)}",
        ]


class UsernameInputGenerator(StepGenerator):
    """Generates username input steps."""

    def can_handle(self, action: str) -> bool:
        action_lower = action.lower()
        return "enter" in action_lower and "username" in action_lower

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        username = "testuser@example.com"
        if "username:" in test_data:
            username = test_data.split("username:")[1].strip()

        return [
            f"    Input Text    id=username_field    {sanitize_robot_string(username)}",
            (
                f"    Textfield Value Should Be    id=username_field    "
                f"{sanitize_robot_string(username)}"
            ),
        ]


class PasswordInputGenerator(StepGenerator):
    """Generates password input steps."""

    def can_handle(self, action: str) -> bool:
        action_lower = action.lower()
        return "enter" in action_lower and "password" in action_lower

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        password = "password123"
        if "password:" in test_data:
            password = test_data.split("password:")[1].strip()

        return [
            f"    Input Text    id=password_field    {sanitize_robot_string(password)}",
            (
                f"    Textfield Value Should Be    id=password_field    "
                f"{sanitize_robot_string(password)}"
            ),
        ]


class ClickButtonGenerator(StepGenerator):
    """Generates button click steps."""

    def can_handle(self, action: str) -> bool:
        action_lower = action.lower()
        return "click" in action_lower and "button" in action_lower

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        return [
            "    Click Button    id=login_button",
            "    Sleep    1s    # Wait for JavaScript to execute",
            f"    Page Should Contain    {sanitize_robot_string(expected)}",
        ]


class SSHConnectionGenerator(StepGenerator):
    """Generates SSH connection steps."""

    def can_handle(self, action: str) -> bool:
        return "open an ssh connection" in action.lower()

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        return [
            "    Open Connection    ${REMOTE_HOST}    "
            "username=${USERNAME}    password=${PASSWORD}",
            "    Login    ${USERNAME}    ${PASSWORD}",
        ]


class SSHFileRetrievalGenerator(StepGenerator):
    """Generates SSH file retrieval steps."""

    def can_handle(self, action: str) -> bool:
        return "retrieve the specified file" in action.lower()

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        return ["    Get File    ${REMOTE_FILE_PATH}    ${LOCAL_DEST_PATH}"]


class SSHDisconnectionGenerator(StepGenerator):
    """Generates SSH disconnection steps."""

    def can_handle(self, action: str) -> bool:
        return "close the ssh connection" in action.lower()

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        return ["    Close Connection"]


class DefaultStepGenerator(StepGenerator):
    """Fallback generator for unrecognized actions."""

    def can_handle(self, action: str) -> bool:
        return True  # Always handles as fallback

    def generate(self, action: str, expected: str, test_data: str) -> List[str]:
        return ["    No Operation  # TODO: Implement step"]


class StepGeneratorFactory:
    """Factory for managing step generators."""

    def __init__(self):
        # Order matters - more specific generators should come first
        self.generators = [
            NavigationStepGenerator(),
            UsernameInputGenerator(),
            PasswordInputGenerator(),
            ClickButtonGenerator(),
            SSHConnectionGenerator(),
            SSHFileRetrievalGenerator(),
            SSHDisconnectionGenerator(),
            DefaultStepGenerator(),  # Always last as fallback
        ]

    def generate_step_keyword(
        self, action: Any, expected: str, test_data: str
    ) -> Tuple[List[str], bool]:
        """Generate Robot Framework keyword for a step.

        Returns:
            Tuple of (generated_lines, keyword_was_generated)
        """
        if action is None:
            return (["    No Operation  # No action specified"], False)

        action_str = str(action)

        for generator in self.generators:
            if generator.can_handle(action_str):
                lines = generator.generate(action_str, expected, test_data)
                is_default = isinstance(generator, DefaultStepGenerator)
                return (lines, not is_default)

        # This should never happen due to DefaultStepGenerator
        return (["    No Operation  # Error in step generation"], False)


# Module-level factory instance
_step_factory = StepGeneratorFactory()


def generate_web_step_keyword(
    action: Any, expected: str, test_data: str
) -> Tuple[List[str], bool]:
    """Generate Robot Framework keyword for a web test step.

    This is the main entry point for step generation.
    """
    return _step_factory.generate_step_keyword(action, expected, test_data)


# Pre-compiled regex patterns for performance
SSH_PATTERN_CACHE: List[re.Pattern] = [
    re.compile(r'\bssh\s+(?:connect|login|command|execute)', re.IGNORECASE),
    re.compile(r'\bremote\s+(?:connect|login|host|server)', re.IGNORECASE),
    re.compile(r'\bscp\b', re.IGNORECASE),
    re.compile(r'\bsftp\b', re.IGNORECASE),
    re.compile(r'\bconnect\s+to\s+(?:remote|host|server)', re.IGNORECASE),
    re.compile(r'\bexecute\s+(?:remote|ssh)\s+command', re.IGNORECASE),
    re.compile(r'\btransfer\s+file.*(?:remote|ssh)', re.IGNORECASE),
    re.compile(r'\bopen\s+(?:ssh\s+)?connection', re.IGNORECASE),
    re.compile(r'\bclose\s+(?:ssh\s+)?connection', re.IGNORECASE),
    re.compile(r'\bssh\b(?!\w)', re.IGNORECASE),
]


def needs_ssh_library_optimized(json_data: Dict[str, Any]) -> bool:
    """Optimized version of SSH library detection with pre-compiled patterns."""
    if json_data is None or not isinstance(json_data, dict):
        return False

    try:
        json_str = json.dumps(json_data).lower()
    except (TypeError, ValueError):
        return False

    # First check for exclusions
    if "retrieve file from remote host" in json_str:
        return False

    # Check pre-compiled patterns for better performance
    for pattern in SSH_PATTERN_CACHE:
        if pattern.search(json_str):
            return True

    return False


# Chrome options constant for performance
CHROME_OPTIONS_TEMPLATE = [
    "    ${chrome_options}=    Evaluate    "
    "sys.modules['selenium.webdriver'].ChromeOptions()    "
    "sys,selenium.webdriver",
    "    Call Method    ${chrome_options}    add_argument    "
    "argument=--headless",
    "    Call Method    ${chrome_options}    add_argument    "
    "argument=--no-sandbox",
    "    Call Method    ${chrome_options}    add_argument    "
    "argument=--disable-dev-shm-usage",
    "    Call Method    ${chrome_options}    add_argument    "
    "argument=--disable-gpu",
    "    Call Method    ${chrome_options}    add_argument    "
    "argument=--disable-extensions",
]


def generate_browser_setup_lines() -> List[str]:
    """Generate browser setup lines with unique user data directory."""
    unique_id = str(uuid.uuid4())[:8]
    lines = CHROME_OPTIONS_TEMPLATE.copy()
    lines.extend([
        f"    Call Method    ${{chrome_options}}    add_argument    "
        f"argument=--user-data-dir=/tmp/chrome_user_data_{unique_id}",
        f"    Open Browser    {TEST_LOGIN_URL}    chrome    "
        "options=${chrome_options}",
    ])
    return lines
