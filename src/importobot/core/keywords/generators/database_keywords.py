"""Database keyword generation for Robot Framework."""

import re
from typing import Any

from importobot.core.keywords.base_generator import BaseKeywordGenerator
from importobot.utils.step_comments import generate_step_comments
from importobot.utils.step_processing import extract_step_information

# Compiled regex patterns for performance optimization
_SQL_QUERY_PATTERN = re.compile(
    r"(?:sql|query|statement):\s*(.+?)(?:\s*(?:\n|$))", re.IGNORECASE | re.DOTALL
)
_MODULE_PATTERN = re.compile(r"(?:module|driver):\s*([^,\s]+)", re.IGNORECASE)
_DATABASE_PATTERN = re.compile(r"(?:database|db|dbname):\s*([^,\s]+)", re.IGNORECASE)
_USERNAME_PATTERN = re.compile(r"(?:username|user):\s*([^,\s]+)", re.IGNORECASE)
_PASSWORD_PATTERN = re.compile(r"(?:password|pass):\s*([^,\s]+)", re.IGNORECASE)
_HOST_PATTERN = re.compile(r"(?:host|server):\s*([^,\s]+)", re.IGNORECASE)
_TABLE_PATTERN = re.compile(r"(?:table|from):\s*([^\s,]+)", re.IGNORECASE)
_SELECT_PATTERN = re.compile(r"(SELECT\s+.+?);?", re.IGNORECASE | re.DOTALL)
_INSERT_PATTERN = re.compile(r"(INSERT\s+.+?);?", re.IGNORECASE | re.DOTALL)
_UPDATE_PATTERN = re.compile(r"(UPDATE\s+.+?);?", re.IGNORECASE | re.DOTALL)
_DELETE_PATTERN = re.compile(r"(DELETE\s+.+?);?", re.IGNORECASE | re.DOTALL)


class DatabaseKeywordGenerator(BaseKeywordGenerator):
    """Generates database-related Robot Framework keywords."""

    def generate_connect_keyword(self, test_data: str) -> str:
        """Generate database connection keyword."""
        # Extract database connection parameters
        module = self._extract_with_pattern(_MODULE_PATTERN, test_data)
        database = self._extract_with_pattern(_DATABASE_PATTERN, test_data)
        username = self._extract_with_pattern(_USERNAME_PATTERN, test_data)
        password = self._extract_with_pattern(_PASSWORD_PATTERN, test_data)
        host = self._extract_with_pattern(_HOST_PATTERN, test_data)

        args = []
        if module:
            args.append(module)
        if database:
            args.append(database)
        if username:
            args.append(username)
        if password:
            args.append(password)
        if host:
            args.append(host)

        return (
            f"Connect To Database    {'    '.join(args)}"
            if args
            else "Connect To Database    sqlite3    test.db"
        )

    def generate_query_keyword(self, test_data: str) -> str:
        """Generate database query keyword."""
        # Extract SQL query
        sql_match = _SQL_QUERY_PATTERN.search(test_data)
        if sql_match:
            sql = sql_match.group(1).strip()
            return f"Execute Sql String    {sql}"

        # Try to extract just the SQL part using compiled patterns
        for pattern in [
            _SELECT_PATTERN,
            _INSERT_PATTERN,
            _UPDATE_PATTERN,
            _DELETE_PATTERN,
        ]:
            sql_match = pattern.search(test_data)
            if sql_match:
                sql = sql_match.group(1).strip()
                return f"Execute Sql String    {sql}"

        # Execute Sql String requires at least one argument
        return "Execute Sql String    SELECT 1"

    def generate_modify_keyword(self, test_data: str) -> str:
        """Generate database modification keyword."""
        # Extract SQL modification statement
        sql_match = _SQL_QUERY_PATTERN.search(test_data)
        if sql_match:
            sql = sql_match.group(1).strip()
            return f"Execute Sql String    {sql}"
        # Execute Sql String requires at least one argument
        return "Execute Sql String    SELECT 1"

    def generate_row_count_keyword(self, test_data: str) -> str:
        """Generate database row count verification keyword."""
        # Extract table name if present
        table_name = self._extract_with_pattern(_TABLE_PATTERN, test_data)

        # Use Query keyword for row count verification since Row Count Should Be
        # is not a standard DatabaseLibrary keyword
        if not table_name:
            table_name = "users"  # Default table name

        # Query returns results, so we use SELECT COUNT(*) for row count
        select_statement = f"SELECT COUNT(*) FROM {table_name}"

        return f"Query    {select_statement}"

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        """Generate Robot Framework keywords for a database-related step."""
        lines = []

        # Add traceability comments
        lines.extend(generate_step_comments(step))

        # Extract step information for keyword generation
        description, test_data, _ = extract_step_information(step)

        # Generate Robot keyword based on step content
        combined = f"{description} {test_data}".lower()

        if "connect" in combined or "database" in combined:
            keyword = self.generate_connect_keyword(test_data)
        elif "query" in combined or "select" in combined:
            keyword = self.generate_query_keyword(test_data)
        elif "disconnect" in combined:
            keyword = "Disconnect From Database"
        elif "modify" in combined or "update" in combined or "insert" in combined:
            keyword = self.generate_modify_keyword(test_data)
        elif "count" in combined or "row" in combined:
            keyword = self.generate_row_count_keyword(test_data)
        else:
            keyword = "No Operation  # Database operation not recognized"

        lines.append(keyword)
        return lines

    def _extract_with_pattern(self, pattern: re.Pattern, text: str) -> str:
        """Extract using compiled pattern from text."""
        match = pattern.search(text)
        return match.group(1) if match else ""
