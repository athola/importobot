"""Unit tests for database SQL validation logic."""

import pytest

from importobot.core.keywords.generators.database_keywords import _validate_sql_query
from importobot.exceptions import ValidationError


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM users; DROP TABLE users;",
        "SELECT * FROM accounts -- delete everything",
        "SELECT * FROM payments /* suspicious block */",
        "SELECT * FROM users UNION SELECT password FROM secrets",
        'EXEC("sp_configure")',
        "SELECT * FROM xp_cmdshell_logs",
        "SELECT * FROM sp_helptext",
        "SELECT 1; SHUTDOWN;",
    ],
)
def test_sql_validation_blocks_dangerous_patterns(query: str) -> None:
    """Ensure dangerous SQL patterns raise a validation error."""
    with pytest.raises(ValidationError) as exc:
        _validate_sql_query(query)

    assert "Potentially dangerous SQL pattern detected" in str(exc.value)


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM users WHERE id = 1",
        "INSERT INTO logs (message) VALUES ('test value')",
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = 5",
    ],
)
def test_sql_validation_allows_safe_queries(query: str) -> None:
    """Ensure legitimate SQL queries pass validation."""
    assert _validate_sql_query(query) == query
