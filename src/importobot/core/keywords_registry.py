"""Manages Robot Framework keyword registry and library mappings.

This module centralizes keyword definitions, library patterns, and intent recognition
for Robot Framework conversion operations.
"""

import re
from typing import Any, ClassVar, cast

from importobot.core.pattern_matcher import IntentType, PatternMatcher
from importobot.utils.security import SSH_SECURITY_GUIDELINES, extract_security_warnings


class RobotFrameworkKeywordRegistry:
    """A centralized registry of Robot Framework keywords across major libraries."""

    # Comprehensive Robot Framework library coverage
    KEYWORD_LIBRARIES: ClassVar[dict[str, Any]] = {
        # BuiltIn Library (always available)
        "builtin": {
            "Log": {"args": ["message", "level=INFO"], "description": "Log a message"},
            "Set Variable": {"args": ["value"], "description": "Set a variable"},
            "Get Variable": {"args": ["name"], "description": "Get variable value"},
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
            "Convert To Integer": {
                "args": ["item"],
                "description": "Convert to integer",
            },
            "Convert To String": {"args": ["item"], "description": "Convert to string"},
            "Convert To Boolean": {
                "args": ["item"],
                "description": "Convert to boolean",
            },
            "Convert To Number": {"args": ["item"], "description": "Convert to number"},
            "Get Length": {"args": ["item"], "description": "Get length of item"},
            "Length Should Be": {
                "args": ["item", "length"],
                "description": "Verify length",
            },
            "Should Start With": {
                "args": ["string", "prefix"],
                "description": "Verify prefix",
            },
            "Should End With": {
                "args": ["string", "suffix"],
                "description": "Verify suffix",
            },
            "Should Match": {
                "args": ["string", "pattern"],
                "description": "Verify pattern match",
            },
            "Evaluate": {"args": ["expression"], "description": "Evaluate expression"},
            "Run Keyword If": {
                "args": ["condition", "keyword"],
                "description": "Run keyword if condition",
            },
            "Repeat Keyword": {
                "args": ["times", "keyword"],
                "description": "Repeat keyword",
            },
            "Get Count": {"args": ["item"], "description": "Get count of items"},
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
                "security_warning": "WARNING: Use key-based auth instead of passwords",
            },
            "Close Connection": {"args": [], "description": "Close SSH connection"},
            "Get File": {
                "args": ["source", "destination"],
                "description": "Download file via SSH",
                "security_warning": "Validate file paths to prevent dir traversal",
            },
            "Put File": {
                "args": ["source", "destination"],
                "description": "Upload file via SSH",
                "security_warning": "Validate destination paths and permissions",
            },
            "Execute Command": {
                "args": ["command"],
                "description": "Execute command via SSH",
                "security_warning": "WARNING: Sanitize commands to prevent injection",
            },
            "Login": {"args": ["username", "password"], "description": "Login to SSH"},
            "Login With Public Key": {
                "args": ["username", "keyfile"],
                "description": "Login with key",
            },
            "Read": {"args": [], "description": "Read command output"},
            "Write": {"args": ["text"], "description": "Write to SSH session"},
            "Create Directory": {
                "args": ["path"],
                "description": "Create directory via SSH",
            },
            "List Directory": {
                "args": ["path"],
                "description": "List directory contents via SSH",
            },
            "Read Until": {
                "args": ["expected"],
                "description": "Read until expected output",
            },
            "Enable Logging": {
                "args": ["logfile"],
                "description": "Enable SSH logging",
            },
            "Switch Connection": {
                "args": ["alias"],
                "description": "Switch to another SSH connection",
            },
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
        # Telnet Library
        "Telnet": {
            "Open Connection": {
                "args": ["host", "port=23"],
                "description": "Open Telnet connection",
            },
            "Close Connection": {"args": [], "description": "Close Telnet connection"},
            "Write": {"args": ["text"], "description": "Write to Telnet session"},
            "Read": {"args": [], "description": "Read from Telnet session"},
            "Read Until": {
                "args": ["expected"],
                "description": "Read until expected text",
            },
            "Execute Command": {
                "args": ["command"],
                "description": "Execute command via Telnet",
            },
            "Switch Connection": {
                "args": ["index_or_alias"],
                "description": "Switch to another Telnet connection",
            },
        },
        # AppiumLibrary - Mobile testing
        "AppiumLibrary": {
            "Open Application": {
                "args": ["remote_url", "desired_capabilities"],
                "description": "Open mobile application",
            },
            "Close Application": {
                "args": [],
                "description": "Close mobile application",
            },
            "Switch Application": {
                "args": ["index_or_alias"],
                "description": "Switch to another application",
            },
            "Click Element": {
                "args": ["locator"],
                "description": "Click mobile element",
            },
            "Input Text": {
                "args": ["locator", "text"],
                "description": "Input text to mobile element",
            },
            "Get Text": {"args": ["locator"], "description": "Get element text"},
            "Element Should Be Visible": {
                "args": ["locator"],
                "description": "Assert element visible",
            },
            "Wait Until Element Is Visible": {
                "args": ["locator", "timeout=None"],
                "description": "Wait for element",
            },
        },
        # FtpLibrary - FTP operations
        "FtpLibrary": {
            "Ftp Connect": {
                "args": ["host", "username", "password"],
                "description": "Connect to FTP server",
            },
            "Ftp Close": {"args": [], "description": "Close FTP connection"},
            "Ftp Put File": {
                "args": ["local_file", "remote_file"],
                "description": "Upload file via FTP",
            },
            "Ftp Get File": {
                "args": ["remote_file", "local_file"],
                "description": "Download file via FTP",
            },
            "Dir": {"args": [], "description": "List directory contents"},
            "Cwd": {"args": ["directory"], "description": "Change working directory"},
        },
        # MQTTLibrary - IoT messaging
        "MQTTLibrary": {
            "Connect": {
                "args": ["broker", "port=1883"],
                "description": "Connect to MQTT broker",
            },
            "Disconnect": {"args": [], "description": "Disconnect from MQTT broker"},
            "Publish": {
                "args": ["topic", "message"],
                "description": "Publish MQTT message",
            },
            "Subscribe": {"args": ["topic"], "description": "Subscribe to MQTT topic"},
            "Unsubscribe": {
                "args": ["topic"],
                "description": "Unsubscribe from MQTT topic",
            },
        },
        # RedisLibrary - Redis cache operations
        "RedisLibrary": {
            "Connect To Redis": {
                "args": ["host", "port=6379"],
                "description": "Connect to Redis",
            },
            "Disconnect From Redis": {
                "args": [],
                "description": "Disconnect from Redis",
            },
            "Get From Redis": {"args": ["key"], "description": "Get value from Redis"},
            "Append To Redis": {
                "args": ["key", "value"],
                "description": "Append to Redis key",
            },
            "Redis Key Should Exist": {
                "args": ["key"],
                "description": "Assert key exists",
            },
            "Delete From Redis": {
                "args": ["*keys"],
                "description": "Delete keys from Redis",
            },
        },
        # RobotMongoDBLibrary - MongoDB operations (standalone functions)
        "RobotMongoDBLibrary": {
            "InsertOne": {
                "args": ["connection_config", "data"],
                "description": "Insert one document into MongoDB collection",
            },
            "FindOneByID": {
                "args": ["connection_config", "id"],
                "description": "Find one document by ID from MongoDB collection",
            },
            "Find": {
                "args": ["connection_config", "filter"],
                "description": "Find documents in MongoDB collection using filter",
            },
            "Update": {
                "args": ["connection_config", "id", "data"],
                "description": "Update document by ID in MongoDB collection",
            },
            "DeleteOne": {
                "args": ["connection_config", "filter"],
                "description": (
                    "Delete one document from MongoDB collection using filter"
                ),
            },
            "DeleteOneByID": {
                "args": ["connection_config", "id"],
                "description": "Delete one document by ID from MongoDB collection",
            },
        },
    }
    # Intent to library keyword mapping
    INTENT_TO_LIBRARY_KEYWORDS: ClassVar[dict[str, tuple[str, str]]] = {
        # File operations
        "file_create": ("OperatingSystem", "Create File"),
        "file_remove": ("OperatingSystem", "Remove File"),
        "file_exists": ("OperatingSystem", "File Should Exist"),
        "file_read": ("OperatingSystem", "Get File"),
        "file_copy": ("OperatingSystem", "Copy File"),
        "file_move": ("OperatingSystem", "Move File"),
        "file_transfer": ("OperatingSystem", "Copy File"),
        "file_verification": ("OperatingSystem", "File Should Exist"),
        "file_removal": ("OperatingSystem", "Remove File"),
        "file_creation": ("OperatingSystem", "Create File"),
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
        "ssh_file_upload": ("SSHLibrary", "Put File"),
        "ssh_file_download": ("SSHLibrary", "Get File"),
        "ssh_directory_create": ("SSHLibrary", "Create Directory"),
        "ssh_directory_list": ("SSHLibrary", "List Directory"),
        "ssh_read_until": ("SSHLibrary", "Read Until"),
        "ssh_write": ("SSHLibrary", "Write"),
        "ssh_enable_logging": ("SSHLibrary", "Enable Logging"),
        "ssh_switch_connection": ("SSHLibrary", "Switch Connection"),
        # Web operations
        "web_open": ("SeleniumLibrary", "Open Browser"),
        "web_close": ("SeleniumLibrary", "Close Browser"),
        "web_navigate": ("SeleniumLibrary", "Go To"),
        # Mobile app operations
        "app_open": ("AppiumLibrary", "Open Application"),
        "web_input": ("SeleniumLibrary", "Input Text"),
        "web_input_password": ("SeleniumLibrary", "Input Password"),
        "web_click": ("SeleniumLibrary", "Click Element"),
        "web_verify_text": ("SeleniumLibrary", "Page Should Contain"),
        "web_verify_element": ("SeleniumLibrary", "Element Should Be Visible"),
        "web_get_text": ("SeleniumLibrary", "Get Text"),
        # New browser intents from PatternMatcher
        "browser_open": ("SeleniumLibrary", "Open Browser"),
        "browser_navigate": ("SeleniumLibrary", "Go To"),
        "input_username": ("SeleniumLibrary", "Input Text"),
        "input_password": ("SeleniumLibrary", "Input Password"),
        "click": ("SeleniumLibrary", "Click Element"),
        "element_verification": ("SeleniumLibrary", "Element Should Be Visible"),
        "content_verification": ("SeleniumLibrary", "Page Should Contain"),
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
        # New API intents from PatternMatcher
        "api_request": ("RequestsLibrary", "GET On Session"),
        "api_response": ("RequestsLibrary", "Status Should Be"),
        # Database operations
        "db_connect": ("DatabaseLibrary", "Connect To Database"),
        "db_disconnect": ("DatabaseLibrary", "Disconnect From Database"),
        "db_execute": ("DatabaseLibrary", "Execute Sql String"),
        "db_query": ("DatabaseLibrary", "Query"),
        "db_table_exists": ("DatabaseLibrary", "Table Must Exist"),
        "db_check_exists": ("DatabaseLibrary", "Check If Exists In Database"),
        # New database intents from PatternMatcher
        "db_modify": ("DatabaseLibrary", "Execute Sql String"),
        "db_row_count": ("DatabaseLibrary", "Check If Exists In Database"),
        # Built-in operations
        "log_message": ("builtin", "Log"),
        "set_variable": ("builtin", "Set Variable"),
        "get_variable": ("builtin", "Get Variable"),
        "assert_equal": ("builtin", "Should Be Equal"),
        "assert_contains": ("builtin", "Should Contain"),
        "assertion_contains": ("builtin", "Should Contain"),
        "sleep": ("builtin", "Sleep"),
        # Built-in conversion operations
        "convert_to_integer": ("builtin", "Convert To Integer"),
        "convert_to_string": ("builtin", "Convert To String"),
        "convert_to_boolean": ("builtin", "Convert To Boolean"),
        "convert_to_number": ("builtin", "Convert To Number"),
        # Built-in collection operations
        "create_list": ("Collections", "Create List"),
        "create_dictionary": ("Collections", "Create Dictionary"),
        "get_length": ("builtin", "Get Length"),
        "length_should_be": ("builtin", "Length Should Be"),
        "should_start_with": ("builtin", "Should Start With"),
        "should_end_with": ("builtin", "Should End With"),
        "should_match": ("builtin", "Should Match"),
        # Built-in evaluation and control flow
        "evaluate_expression": ("builtin", "Evaluate"),
        "run_keyword_if": ("builtin", "Run Keyword If"),
        "repeat_keyword": ("builtin", "Repeat Keyword"),
        "fail_test": ("builtin", "Fail"),
        "get_count": ("builtin", "Get Count"),
        # Command execution intent
        "command": ("Process", "Run Process"),
    }

    @classmethod
    def get_keyword_info(cls, library: str, keyword: str) -> dict[str, Any]:
        """Retrieve information about a specific keyword."""
        if library in cls.KEYWORD_LIBRARIES:
            return cast(dict[str, Any], cls.KEYWORD_LIBRARIES[library].get(keyword, {}))
        return {}

    @classmethod
    def get_required_libraries(cls, keywords: list[dict[str, Any]]) -> list[str]:
        """Retrieve the required libraries for a given set of keywords."""
        libraries = set()
        for kw in keywords:
            if kw.get("library") and kw["library"] != "builtin":
                libraries.add(kw["library"])
        return sorted(libraries)

    @classmethod
    def get_intent_keyword(cls, intent: str) -> tuple[str, str]:
        """Retrieve the library and keyword associated with a specific intent."""
        return cls.INTENT_TO_LIBRARY_KEYWORDS.get(intent, ("builtin", "No Operation"))

    @classmethod
    def validate_registry_integrity(cls) -> list[str]:
        """Validate that all intent mappings reference valid keywords.

        Returns:
            A list of validation errors found in the registry.
        """
        errors = []

        # Validate intent mappings reference valid libraries and keywords
        for intent, (library, keyword) in cls.INTENT_TO_LIBRARY_KEYWORDS.items():
            if library not in cls.KEYWORD_LIBRARIES:
                errors.append(
                    f"Intent '{intent}' references unknown library '{library}'"
                )
            elif keyword not in cls.KEYWORD_LIBRARIES[library]:
                errors.append(
                    f"Intent '{intent}' references unknown keyword "
                    f"'{keyword}' in library '{library}'"
                )

        # Note: LibraryDetector validation moved to avoid circular import
        # This can be validated separately or with a registry initialization check

        return errors

    @classmethod
    def get_registry_metrics(cls) -> dict[str, Any]:
        """Retrieve metrics regarding registry usage and coverage.

        Returns:
            A dictionary containing registry metrics.
        """
        total_libraries = len(cls.KEYWORD_LIBRARIES)
        total_keywords = sum(
            len(keywords) for keywords in cls.KEYWORD_LIBRARIES.values()
        )
        total_intents = len(cls.INTENT_TO_LIBRARY_KEYWORDS)

        # Count keywords by library
        keywords_by_library = {
            library: len(keywords)
            for library, keywords in cls.KEYWORD_LIBRARIES.items()
        }

        # Count intents by library
        intents_by_library: dict[str, int] = {}
        for library, _ in cls.INTENT_TO_LIBRARY_KEYWORDS.values():
            intents_by_library[library] = intents_by_library.get(library, 0) + 1

        # Count security warnings
        security_warnings_count = 0
        for library_keywords in cls.KEYWORD_LIBRARIES.values():
            for keyword_info in library_keywords.values():
                if "security_warning" in keyword_info:
                    security_warnings_count += 1

        return {
            "total_libraries": total_libraries,
            "total_keywords": total_keywords,
            "total_intents": total_intents,
            "keywords_by_library": keywords_by_library,
            "intents_by_library": intents_by_library,
            "security_warnings_count": security_warnings_count,
            "coverage_ratio": (
                total_intents / total_keywords if total_keywords > 0 else 0
            ),
        }


class IntentRecognitionEngine:
    """Provides centralized intent recognition capabilities using `PatternMatcher`."""

    _pattern_matcher: ClassVar[PatternMatcher] = PatternMatcher()

    @classmethod
    def recognize_intent(cls, text: str) -> IntentType | None:
        """Recognizes the intent from a text description using `PatternMatcher`.

        Returns:
            An `IntentType` enum if an intent is detected, otherwise `None`.
        """
        if not text:
            return None

        detected_intent = cls._pattern_matcher.detect_intent(text)
        return detected_intent  # Return enum directly, not .value

    @classmethod
    def detect_all_intents(cls, text: str) -> list[IntentType]:
        """Detect all matching intents from a text description using `PatternMatcher`.

        Returns:
            A list of `IntentType` enums for all detected intents.
        """
        detected_intents = cls._pattern_matcher.detect_all_intents(text)
        return detected_intents  # Return enums directly, not .value

    @classmethod
    def get_security_warnings_for_keyword(cls, library: str, keyword: str) -> list[str]:
        """Retrieve security warnings for a specific keyword."""
        warnings = []
        if library in RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES:
            keyword_info = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[library].get(
                keyword, {}
            )
            warnings.extend(extract_security_warnings(keyword_info))
        return warnings

    @classmethod
    def get_ssh_security_guidelines(cls) -> list[str]:
        """Retrieve comprehensive SSH security guidelines."""
        return SSH_SECURITY_GUIDELINES

    @classmethod
    def validate_command_security(cls, command: str) -> dict[str, Any]:
        """Validate a command for potential security issues."""
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
            "recommendation": (
                "Review and sanitize command before execution"
                if issues
                else "Command appears safe"
            ),
        }
