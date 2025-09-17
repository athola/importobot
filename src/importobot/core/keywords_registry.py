"""
Comprehensive Robot Framework keyword registry and library mappings.

This module provides centralized keyword definitions, library patterns,
and intent recognition patterns used throughout the conversion system.
"""

import re
from typing import Any, Dict, List, Set, Tuple

from importobot.utils.security import SSH_SECURITY_GUIDELINES, extract_security_warnings


class RobotFrameworkKeywordRegistry:
    """Centralized registry of Robot Framework keywords across major libraries."""

    # Comprehensive Robot Framework library coverage
    KEYWORD_LIBRARIES = {
        # BuiltIn Library (always available)
        "builtin": {
            "Log": {"args": ["message", "level=INFO"], "description": "Log a message"},
            "Set Variable": {"args": ["value"], "description": "Set a variable"},
            "Should Be Equal": {
                "args": ["first", "second"],
                "description": "Assert equality",
            },
            "Should Contain": {
                "args": ["container", "item"],
                "description": "Assert contains",
            },
            "Sleep": {"args": ["time"], "description": "Sleep for specified time"},
            "No Operation": {"args": [], "description": "Do nothing"},
            "Fail": {"args": ["message"], "description": "Fail test with message"},
            "Pass Execution": {
                "args": ["message"],
                "description": "Pass test with message",
            },
            "Set Test Variable": {
                "args": ["name", "value"],
                "description": "Set test variable",
            },
        },
        # OperatingSystem Library
        "OperatingSystem": {
            "Create File": {
                "args": ["path", "content"],
                "description": "Create file with content",
            },
            "Remove File": {"args": ["path"], "description": "Remove file"},
            "File Should Exist": {
                "args": ["path"],
                "description": "Assert file exists",
            },
            "File Should Not Exist": {
                "args": ["path"],
                "description": "Assert file not exists",
            },
            "Create Directory": {"args": ["path"], "description": "Create directory"},
            "Remove Directory": {
                "args": ["path", "recursive=False"],
                "description": "Remove directory",
            },
            "Directory Should Exist": {
                "args": ["path"],
                "description": "Assert directory exists",
            },
            "Get File": {"args": ["path"], "description": "Read file content"},
            "Append To File": {
                "args": ["path", "content"],
                "description": "Append to file",
            },
            "Copy File": {
                "args": ["source", "destination"],
                "description": "Copy file",
            },
            "Move File": {
                "args": ["source", "destination"],
                "description": "Move file",
            },
            "Get File Size": {"args": ["path"], "description": "Get file size"},
            "List Directory": {
                "args": ["path"],
                "description": "List directory contents",
            },
        },
        # SSHLibrary
        "SSHLibrary": {
            "Open Connection": {
                "args": ["host", "username", "password"],
                "description": "Open SSH connection",
                "security_warning": "⚠️  Use key-based auth instead of passwords",
            },
            "Close Connection": {"args": [], "description": "Close SSH connection"},
            "Get File": {
                "args": ["source", "destination"],
                "description": "Download file via SSH",
                "security_warning": "⚠️  Validate file paths to prevent dir traversal",
            },
            "Put File": {
                "args": ["source", "destination"],
                "description": "Upload file via SSH",
                "security_warning": "⚠️  Validate destination paths and permissions",
            },
            "Execute Command": {
                "args": ["command"],
                "description": "Execute command via SSH",
                "security_warning": "⚠️  Sanitize commands to prevent injection",
            },
            "Login": {"args": ["username", "password"], "description": "Login to SSH"},
            "Login With Public Key": {
                "args": ["username", "keyfile"],
                "description": "Login with key",
            },
            "Read": {"args": [], "description": "Read command output"},
            "Write": {"args": ["text"], "description": "Write to SSH session"},
        },
        # SeleniumLibrary (Web automation)
        "SeleniumLibrary": {
            "Open Browser": {
                "args": ["url", "browser"],
                "description": "Open web browser",
            },
            "Close Browser": {"args": [], "description": "Close web browser"},
            "Go To": {"args": ["url"], "description": "Navigate to URL"},
            "Input Text": {
                "args": ["locator", "text"],
                "description": "Input text to element",
            },
            "Input Password": {
                "args": ["locator", "text"],
                "description": "Input password to element",
            },
            "Click Element": {"args": ["locator"], "description": "Click element"},
            "Click Button": {"args": ["locator"], "description": "Click button"},
            "Click Link": {"args": ["locator"], "description": "Click link"},
            "Page Should Contain": {
                "args": ["text"],
                "description": "Assert page contains text",
            },
            "Element Should Be Visible": {
                "args": ["locator"],
                "description": "Assert element visible",
            },
            "Element Should Not Be Visible": {
                "args": ["locator"],
                "description": "Assert element not visible",
            },
            "Title Should Be": {"args": ["title"], "description": "Assert page title"},
            "Location Should Be": {
                "args": ["url"],
                "description": "Assert current URL",
            },
            "Wait Until Element Is Visible": {
                "args": ["locator", "timeout=None"],
                "description": "Wait for element",
            },
            "Select From List By Label": {
                "args": ["locator", "label"],
                "description": "Select from dropdown",
            },
            "Get Text": {"args": ["locator"], "description": "Get element text"},
            "Get Element Attribute": {
                "args": ["locator", "attribute"],
                "description": "Get attribute",
            },
        },
        # Process Library
        "Process": {
            "Run Process": {
                "args": ["command", "*args"],
                "description": "Run external process",
            },
            "Start Process": {
                "args": ["command", "*args"],
                "description": "Start process",
            },
            "Wait For Process": {
                "args": ["handle", "timeout=None"],
                "description": "Wait for process",
            },
            "Process Should Be Running": {
                "args": ["handle"],
                "description": "Assert process running",
            },
            "Process Should Be Stopped": {
                "args": ["handle"],
                "description": "Assert process stopped",
            },
            "Get Process Result": {
                "args": ["handle"],
                "description": "Get process result",
            },
            "Terminate Process": {
                "args": ["handle"],
                "description": "Terminate process",
            },
        },
        # RequestsLibrary - API operations
        "RequestsLibrary": {
            "GET On Session": {
                "args": ["alias", "url"],
                "description": "Make GET request",
            },
            "POST On Session": {
                "args": ["alias", "url", "json"],
                "description": "Make POST request",
            },
            "PUT On Session": {
                "args": ["alias", "url", "json"],
                "description": "Make PUT request",
            },
            "DELETE On Session": {
                "args": ["alias", "url"],
                "description": "Make DELETE request",
            },
            "Create Session": {
                "args": ["alias", "url"],
                "description": "Create HTTP session",
            },
            "Status Should Be": {
                "args": ["expected"],
                "description": "Verify response status",
            },
        },
        # DatabaseLibrary - Database operations
        "DatabaseLibrary": {
            "Connect To Database": {
                "args": ["dbapiModuleName", "database", "username", "password"],
                "description": "Connect to database",
            },
            "Disconnect From Database": {
                "args": [],
                "description": "Disconnect from database",
            },
            "Execute Sql String": {
                "args": ["sqlString"],
                "description": "Execute SQL query",
            },
            "Query": {
                "args": ["selectStatement"],
                "description": "Execute SELECT query",
            },
            "Table Must Exist": {
                "args": ["tableName"],
                "description": "Verify table exists",
            },
            "Check If Exists In Database": {
                "args": ["selectStatement"],
                "description": "Check if data exists",
            },
        },
        # Collections Library
        "Collections": {
            "Create List": {
                "args": ["*items"],
                "description": "Create a list",
            },
            "Create Dictionary": {
                "args": ["*items"],
                "description": "Create a dictionary",
            },
            "Get From List": {
                "args": ["list", "index"],
                "description": "Get item from list",
            },
            "Get From Dictionary": {
                "args": ["dictionary", "key"],
                "description": "Get value from dictionary",
            },
            "Append To List": {
                "args": ["list", "value"],
                "description": "Append to list",
            },
        },
        # String Library
        "String": {
            "Convert To Uppercase": {
                "args": ["string"],
                "description": "Convert to uppercase",
            },
            "Convert To Lowercase": {
                "args": ["string"],
                "description": "Convert to lowercase",
            },
            "Replace String": {
                "args": ["string", "search_for", "replace_with"],
                "description": "Replace string",
            },
            "Split String": {
                "args": ["string", "separator"],
                "description": "Split string",
            },
            "Strip String": {
                "args": ["string"],
                "description": "Strip whitespace",
            },
        },
    }

    # Intent to library keyword mapping
    INTENT_TO_LIBRARY_KEYWORDS = {
        # File operations
        "file_create": ("OperatingSystem", "Create File"),
        "file_remove": ("OperatingSystem", "Remove File"),
        "file_exists": ("OperatingSystem", "File Should Exist"),
        "file_read": ("OperatingSystem", "Get File"),
        "file_copy": ("OperatingSystem", "Copy File"),
        "file_move": ("OperatingSystem", "Move File"),
        # Directory operations
        "dir_create": ("OperatingSystem", "Create Directory"),
        "dir_remove": ("OperatingSystem", "Remove Directory"),
        "dir_exists": ("OperatingSystem", "Directory Should Exist"),
        "dir_list": ("OperatingSystem", "List Directory"),
        # SSH operations
        "ssh_connect": ("SSHLibrary", "Open Connection"),
        "ssh_disconnect": ("SSHLibrary", "Close Connection"),
        "ssh_get_file": ("SSHLibrary", "Get File"),
        "ssh_put_file": ("SSHLibrary", "Put File"),
        "ssh_execute": ("SSHLibrary", "Execute Command"),
        "ssh_login": ("SSHLibrary", "Login"),
        # Web operations
        "web_open": ("SeleniumLibrary", "Open Browser"),
        "web_close": ("SeleniumLibrary", "Close Browser"),
        "web_navigate": ("SeleniumLibrary", "Go To"),
        "web_input": ("SeleniumLibrary", "Input Text"),
        "web_input_password": ("SeleniumLibrary", "Input Password"),
        "web_click": ("SeleniumLibrary", "Click Element"),
        "web_verify_text": ("SeleniumLibrary", "Page Should Contain"),
        "web_verify_element": ("SeleniumLibrary", "Element Should Be Visible"),
        "web_get_text": ("SeleniumLibrary", "Get Text"),
        # Process operations
        "process_run": ("Process", "Run Process"),
        "process_start": ("Process", "Start Process"),
        "process_wait": ("Process", "Wait For Process"),
        # API operations
        "api_get": ("RequestsLibrary", "GET On Session"),
        "api_post": ("RequestsLibrary", "POST On Session"),
        "api_put": ("RequestsLibrary", "PUT On Session"),
        "api_delete": ("RequestsLibrary", "DELETE On Session"),
        "api_session": ("RequestsLibrary", "Create Session"),
        "api_verify_status": ("RequestsLibrary", "Status Should Be"),
        # Database operations
        "db_connect": ("DatabaseLibrary", "Connect To Database"),
        "db_disconnect": ("DatabaseLibrary", "Disconnect From Database"),
        "db_execute": ("DatabaseLibrary", "Execute Sql String"),
        "db_query": ("DatabaseLibrary", "Query"),
        "db_table_exists": ("DatabaseLibrary", "Table Must Exist"),
        "db_check_exists": ("DatabaseLibrary", "Check If Exists In Database"),
        # Built-in operations
        "log_message": ("builtin", "Log"),
        "set_variable": ("builtin", "Set Variable"),
        "assert_equal": ("builtin", "Should Be Equal"),
        "assert_contains": ("builtin", "Should Contain"),
        "sleep": ("builtin", "Sleep"),
    }

    @classmethod
    def get_keyword_info(cls, library: str, keyword: str) -> Dict[str, Any]:
        """Get information about a specific keyword."""
        if library in cls.KEYWORD_LIBRARIES:
            return cls.KEYWORD_LIBRARIES[library].get(keyword, {})
        return {}

    @classmethod
    def get_required_libraries(cls, keywords: List[Dict[str, Any]]) -> List[str]:
        """Get required libraries for keyword set."""
        libraries = set()
        for kw in keywords:
            if kw.get("library") and kw["library"] != "builtin":
                libraries.add(kw["library"])
        return sorted(libraries)

    @classmethod
    def get_intent_keyword(cls, intent: str) -> Tuple[str, str]:
        """Get library and keyword for an intent."""
        return cls.INTENT_TO_LIBRARY_KEYWORDS.get(intent, ("builtin", "No Operation"))


class LibraryDetector:
    """Unified library detection based on text patterns."""

    # Library detection patterns consolidated from both modules
    LIBRARY_PATTERNS = {
        "SeleniumLibrary": (
            r"\b(?:browser|navigate|click|input|page|web|url|login|button|element"
            r"|selenium|page.*should.*contain|should.*contain.*page|verify.*content"
            r"|check.*content|ensure.*content|page.*contains|contains.*page"
            r"|verify.*text|check.*text|ensure.*text|title.*should|"
            r"location.*should)\b"
        ),
        "SSHLibrary": (
            r"\b(?:ssh|remote|connection|host|server|ssh.*connect"
            r"|ssh.*disconnect|execute.*command|open.*connection|close.*connection)\b"
        ),
        "Process": (
            r"\b(?:command|execute|run|curl|wget|bash|process|run.*process"
            r"|start.*process|terminate.*process|wait.*for.*process)\b"
        ),
        "OperatingSystem": (
            r"\b(?:file|directory|exists|remove|delete|filesystem|create.*file"
            r"|copy.*file|move.*file|file.*should.*exist|create.*directory"
            r"|remove.*directory|list.*directory|get.*file)\b"
        ),
        "DatabaseLibrary": (
            r"\b(?:database|sql|query|table|connect.*database|db_|execute.*sql"
            r"|row.*count|insert.*into|update.*table|delete.*from|select.*from"
            r"|database.*connection|db.*query|db.*execute|table.*exist"
            r"|row.*count|verify.*row|check.*database|"
            r"disconnect.*from.*database)\b"
        ),
        "RequestsLibrary": (
            r"\b(?:api|rest|request|response|session|get.*request|post.*request"
            r"|put.*request|delete.*request|http|create.*session|make.*request"
            r"|send.*request|api.*call|rest.*api|http.*request|verify.*response"
            r"|check.*status|get.*response|status.*should.*be)\b"
        ),
        "Collections": (
            r"\b(?:list|dictionary|collection|append|get.*from.*list"
            r"|get.*from.*dict|create.*list|create.*dictionary|dictionary.*key"
            r"|list.*item|collections|dict.*update|append.*to.*list)\b"
        ),
        "String": (
            r"\b(?:string|uppercase|lowercase|replace.*string|split.*string|strip"
            r"|string.*operation|string.*manipulation|convert.*case"
            r"|format.*string|convert.*to.*uppercase|convert.*to.*lowercase)\b"
        ),
    }

    @classmethod
    def detect_libraries_from_text(cls, text: str) -> Set[str]:
        """Detect required Robot Framework libraries from text content."""
        if not text:
            return set()

        libraries = set()
        text_lower = text.lower()

        for library, pattern in cls.LIBRARY_PATTERNS.items():
            if re.search(pattern, text_lower):
                libraries.add(library)

        return libraries

    @classmethod
    def detect_libraries_from_steps(cls, steps: List[Dict[str, Any]]) -> Set[str]:
        """Detect required libraries from step content."""
        combined_text = []
        for step in steps:
            for value in step.values():
                if isinstance(value, str):
                    combined_text.append(value.lower())

        return cls.detect_libraries_from_text(" ".join(combined_text))


class IntentRecognitionEngine:
    """Centralized intent recognition patterns."""

    # Intent patterns consolidated from multiple modules
    INTENT_PATTERNS = {
        # Command execution (check first for curl/wget)
        r"\b(?:initiate.*download|execute.*curl|run.*wget|curl|wget)\b": (
            "command_execution"
        ),
        # General command execution (for echo, hash, etc.)
        r"\b(?:echo|hash|sha256sum)\b": "command_execution",
        # File operations (most specific patterns first)
        r"\b(?:verify|check|ensure).*file.*exists?\b": "file_verification",
        r"\b(?:remove|delete|clean).*file\b": "file_removal",
        r"\b(?:get|retrieve).*file\b": "file_transfer",
        r"\btransfer.*file\b": "file_transfer",
        r"\b(?:create|write).*file\b": "file_creation",
        r"\b(?:copy|move).*file\b": "file_operation",
        # SSH operations
        r"\b(?:open|establish|create).*(?:ssh|connection|remote)\b": "ssh_connect",
        r"\b(?:close|disconnect|terminate).*(?:connection|ssh)\b": "ssh_disconnect",
        r"\b(?:execute|run).*(?:command|ssh)\b": "ssh_execute",
        # Browser operations
        r"\b(?:open|navigate|visit).*(?:browser|page|url|application)\b": (
            "web_navigation"
        ),
        r"\b(?:go to|navigate to)\b.*\b(?:url|page|site)\b": "web_navigation",
        r"\b(?:enter|input|type|fill).*username\b": "web_input_username",
        r"\b(?:enter|input|type|fill).*password\b": "web_input_password",
        r"\b(?:click|press|tap).*(?:button|element)\b": "web_click",
        # Specific patterns for builtin assertions
        r"\bassert.*contains?\b": "assertion_contains",
        # Content verification
        r"\b(?:verify|check|ensure|assert).*(?:content|contains|displays)\b": (
            "content_verification"
        ),
        # Database operations
        r"\b(?:connect|establish|open).*(?:database|db connection)\b": "db_connect",
        r"\b(?:execute|run).*(?:sql|query)\b": "db_execute",
        r"\b(?:disconnect|close|terminate).*(?:database|db)\b": "db_disconnect",
        r"\b(?:insert|update|delete).*(?:record|row)\b": "db_modify",
        r"\b(?:verify|check|validate).*(?:row|record).*count\b": "db_row_count",
        # API operations
        r"\b(?:make|send|perform).*(?:get|post|put|delete).*(?:request|api)\b": (
            "api_request"
        ),
        r"\b(?:create|establish).*(?:session|api connection)\b": "api_session",
        r"\b(?:verify|check|validate).*(?:response|status)\b": "api_response",
        # Monitoring and performance
        r"\b(?:monitor|measure|track).*(?:performance|metrics|load)\b": (
            "performance_monitoring"
        ),
        r"\b(?:test|execute).*(?:performance|load|stress)\b": "performance_testing",
        # Security operations
        r"\b(?:security|authenticate|authorization|vulnerability)\b": (
            "security_testing"
        ),
        r"\b(?:scan|penetration|security.*test)\b": "security_scanning",
    }

    @classmethod
    def recognize_intent(cls, text: str) -> str:
        """Recognize intent from text description."""
        if not text:
            return "unknown"

        text_lower = text.lower()

        for pattern, intent in cls.INTENT_PATTERNS.items():
            if re.search(pattern, text_lower):
                return intent

        return "unknown"

    @classmethod
    def get_intent_patterns(cls) -> Dict[str, str]:
        """Get all intent patterns."""
        return cls.INTENT_PATTERNS.copy()

    @classmethod
    def get_security_warnings_for_keyword(cls, library: str, keyword: str) -> List[str]:
        """Get security warnings for a specific keyword."""
        warnings = []

        if library in RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES:
            keyword_info = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[library].get(
                keyword, {}
            )
            warnings.extend(extract_security_warnings(keyword_info))

        return warnings

    @classmethod
    def get_ssh_security_guidelines(cls) -> List[str]:
        """Get comprehensive SSH security guidelines."""
        return SSH_SECURITY_GUIDELINES

    @classmethod
    def validate_command_security(cls, command: str) -> Dict[str, Any]:
        """Validate command for security issues."""
        dangerous_patterns = [
            (r"rm\s+-rf", "Dangerous recursive delete command"),
            (r"sudo\s+", "Elevated privileges command"),
            (r"chmod\s+777", "Overly permissive file permissions"),
            (r"\|\s*sh", "Command piping to shell"),
            (r"eval\s*\(", "Dynamic code evaluation"),
            (r"`[^`]*`", "Command substitution"),
            (r"&&\s*rm", "Chained delete command"),
            (r"curl.*\|\s*sh", "Download and execute pattern"),
        ]

        issues = []
        for pattern, description in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                issues.append(
                    {"pattern": pattern, "description": description, "severity": "high"}
                )

        return {
            "is_safe": len(issues) == 0,
            "issues": issues,
            "recommendation": "Review and sanitize command before execution"
            if issues
            else "Command appears safe",
        }
