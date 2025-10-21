"""Configuration constants for Importobot."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from importobot import exceptions
from importobot.cli.constants import FETCHABLE_FORMATS, SUPPORTED_FETCH_FORMATS
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import get_logger


class StorageConfigProtocol(Protocol):
    """Minimal protocol for storage configuration objects."""

    backend_type: str
    base_path: Path

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation of the configuration."""
        ...

    def validate(self) -> list[str]:
        """Validate the configuration and return a list of issues."""
        ...


if TYPE_CHECKING:  # pragma: no cover
    from importobot.medallion.storage.config import (
        StorageConfig as StorageConfigRuntime,
    )
else:  # pragma: no cover

    class _StorageConfigStub:
        backend_type: str = "local"
        base_path: Path = Path("./medallion_data")

        def to_dict(self) -> dict[str, Any]:
            raise NotImplementedError("StorageConfig not available at runtime")

        def validate(self) -> list[str]:
            raise NotImplementedError("StorageConfig not available at runtime")

    StorageConfigRuntime = _StorageConfigStub


StorageConfig = StorageConfigRuntime


def _load_storage_config_cls() -> type[StorageConfigProtocol]:
    """Dynamically import StorageConfig to avoid circular import at module load."""
    module = importlib.import_module("importobot.medallion.storage.config")
    return cast(type[StorageConfigProtocol], module.StorageConfig)


# Module-level logger for configuration warnings
logger = get_logger()

# Default values
DEFAULT_TEST_SERVER_URL = "http://localhost:8000"
TEST_SERVER_PORT = 8000

# Environment-configurable values
TEST_SERVER_URL = os.getenv("IMPORTOBOT_TEST_SERVER_URL", DEFAULT_TEST_SERVER_URL)

# Test-specific URLs
LOGIN_PAGE_PATH = "/login.html"
TEST_LOGIN_URL = f"{TEST_SERVER_URL}{LOGIN_PAGE_PATH}"

# Authentication requirements
ZEPHYR_MIN_TOKEN_COUNT = 2

# Numeric project identifiers must stay within signed 64-bit bounds so downstream
# systems (e.g. external SDKs, databases) do not overflow.
MAX_PROJECT_ID = 9_223_372_036_854_775_807

# Chrome options for headless browser testing
CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--headless",
    "--disable-web-security",
    "--allow-running-insecure-content",
]


def _int_from_env(var_name: str, default: int, *, minimum: int | None = None) -> int:
    """Parse integer environment variable with validation."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid %s=%s; falling back to default %d", var_name, raw_value, default
        )
        return default
    if minimum is not None and value < minimum:
        logger.warning(
            "%s must be >= %d (received %d); using default %d",
            var_name,
            minimum,
            value,
            default,
        )
        return default
    return value


def _flag_from_env(var_name: str, default: bool = False) -> bool:
    """Parse boolean environment variable."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


# Configuration for maximum file sizes (in MB / bytes)
MAX_JSON_SIZE_MB = int(os.getenv("IMPORTOBOT_MAX_JSON_SIZE_MB", "10"))
MAX_SCHEMA_FILE_SIZE_BYTES = _int_from_env(
    "IMPORTOBOT_MAX_SCHEMA_BYTES",
    1 * 1024 * 1024,
    minimum=1024,
)
MAX_TEMPLATE_FILE_SIZE_BYTES = _int_from_env(
    "IMPORTOBOT_MAX_TEMPLATE_BYTES",
    2 * 1024 * 1024,
    minimum=1024,
)
MAX_CACHE_CONTENT_SIZE_BYTES = _int_from_env(
    "IMPORTOBOT_MAX_CACHE_CONTENT_BYTES",
    50_000,
    minimum=1024,
)


DETECTION_CACHE_MAX_SIZE = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_MAX_SIZE", 1000, minimum=1
)
DETECTION_CACHE_COLLISION_LIMIT = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT", 3, minimum=1
)
DETECTION_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_TTL_SECONDS", 0, minimum=0
)
FILE_CONTENT_CACHE_MAX_MB = _int_from_env(
    "IMPORTOBOT_FILE_CACHE_MAX_MB", 100, minimum=1
)
FILE_CONTENT_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_FILE_CACHE_TTL_SECONDS", 0, minimum=0
)
FILE_CONTENT_CACHE_MAX_ENTRIES = _int_from_env(
    "IMPORTOBOT_FILE_CACHE_MAX_ENTRIES", 2048, minimum=1
)
PERFORMANCE_CACHE_MAX_SIZE = _int_from_env(
    "IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE", 1000, minimum=1
)
PERFORMANCE_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_PERFORMANCE_CACHE_TTL_SECONDS", 0, minimum=0
)
OPTIMIZATION_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_OPTIMIZATION_CACHE_TTL_SECONDS", 0, minimum=0
)
FORMAT_DETECTION_FAILURE_THRESHOLD = _int_from_env(
    "IMPORTOBOT_DETECTION_FAILURE_THRESHOLD", 5, minimum=1
)
FORMAT_DETECTION_CIRCUIT_RESET_SECONDS = _int_from_env(
    "IMPORTOBOT_DETECTION_CIRCUIT_RESET_SECONDS", 30, minimum=1
)

# Bronze layer in-memory cache configuration
# Default 1024 records chosen based on:
# - Typical enterprise test suite size: 500-2000 test cases
# - Memory footprint: ~1MB (1KB per record average)
# - Performance: 50-80% query speedup for cached records
# - Balance: Reasonable for both small projects and large organizations
BRONZE_LAYER_MAX_IN_MEMORY_RECORDS = _int_from_env(
    "IMPORTOBOT_BRONZE_MAX_IN_MEMORY_RECORDS", 1024, minimum=1
)

# Default TTL=0 (disabled) chosen because:
# - Most use cases have single-writer append-only patterns
# - TTL adds GC overhead without benefit in immutable scenarios
# - Enable TTL only when external updates require cache invalidation
BRONZE_LAYER_IN_MEMORY_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_BRONZE_IN_MEMORY_TTL_SECONDS", 0, minimum=0
)


@dataclass(slots=True)
class APIIngestConfig:
    """Resolved configuration for API ingestion workflow."""

    fetch_format: SupportedFormat
    api_url: str
    tokens: list[str]
    user: str | None
    project_name: str | None
    project_id: int | None
    output_dir: Path
    max_concurrency: int | None
    insecure: bool


def _split_tokens(raw_tokens: str | None) -> list[str]:
    """Split comma separated tokens into a clean list."""
    if not raw_tokens:
        return []
    return [token.strip() for token in raw_tokens.split(",") if token.strip()]


def _mask(tokens: list[str] | None) -> str:
    """Return masked token representation for logging/errors."""
    if not tokens:
        return "***"
    return ", ".join("***" for _ in tokens)


def _resolve_output_dir(cli_path: str | None) -> Path:
    """Resolve output directory defaulting to environment and cwd."""
    env_dir = os.getenv("IMPORTOBOT_API_INPUT_DIR")
    candidate = cli_path or env_dir
    return Path(candidate).expanduser().resolve() if candidate else Path.cwd()


def _resolve_max_concurrency(cli_value: int | None) -> int | None:
    """Resolve max concurrency with environment defaults."""
    if cli_value is not None:
        return cli_value
    raw_env = os.getenv("IMPORTOBOT_API_MAX_CONCURRENCY")
    if raw_env is None:
        return None
    try:
        value = int(raw_env)
    except ValueError:
        logger.warning("Invalid IMPORTOBOT_API_MAX_CONCURRENCY=%s; ignoring", raw_env)
        return None
    return value if value > 0 else None


def _resolve_insecure_flag(args: Any, prefix: str) -> bool:
    """Resolve TLS verification flag from CLI arguments and environment."""
    cli_insecure = bool(getattr(args, "insecure", False))
    env_insecure = _flag_from_env(f"{prefix}_INSECURE", False)
    return cli_insecure or env_insecure


def _validate_required_fields(
    *,
    fetch_format: SupportedFormat,
    api_url: str | None,
    tokens: list[str],
    api_user: str | None,
) -> None:
    """Validate that required API configuration fields are present."""
    missing: list[str] = []
    if not api_url:
        missing.append("API URL")
    if not tokens:
        missing.append("authentication tokens")
    if fetch_format is SupportedFormat.TESTRAIL and not api_user:
        missing.append("API user")
    if missing:
        missing_fields = ", ".join(missing)
        raise exceptions.ConfigurationError(
            f"Missing {missing_fields} for {fetch_format.value} API ingestion "
            f"(tokens={_mask(tokens)})"
        )


def _parse_project_identifier(value: str | None) -> tuple[str | None, int | None]:
    """Split project identifier into name or numeric ID."""
    if not value:
        return None, None
    raw = value.strip()
    if not raw or raw.isspace():
        return None, None
    if raw.isdigit():
        if raw.isascii():
            try:
                project_id = int(raw)
            except ValueError:
                logger.warning(
                    "Numeric project identifier %s failed to parse; treating as name",
                    raw,
                )
                return raw, None
            if project_id > MAX_PROJECT_ID:
                logger.warning(
                    "Numeric project identifier %s exceeds max supported value %s; "
                    "treating as project name",
                    raw,
                    MAX_PROJECT_ID,
                )
                return raw, None
            return None, project_id
        logger.warning(
            "Non-ASCII numeric project identifier %s treated as project name",
            raw,
        )
        return raw, None
    return raw, None


def _resolve_project_reference(
    args: Any,
    fetch_env: Callable[[str], str | None],
    prefix: str,
    fetch_format: SupportedFormat,
) -> tuple[str | None, int | None]:
    """Determine project identifiers from CLI args or environment."""
    cli_project = getattr(args, "project", None)
    if cli_project is not None:
        project_name, project_id = _parse_project_identifier(cli_project)
        if project_name is None and project_id is None:
            message = (
                f"Invalid CLI project identifier '{cli_project}' for "
                f"{fetch_format.value} ingestion. "
                "Provide a non-empty name or numeric ID."
            )
            raise exceptions.ConfigurationError(message)
        return project_name, project_id

    env_project = fetch_env(f"{prefix}_PROJECT")
    if env_project:
        logger.debug(
            (
                "CLI project identifier missing; falling back to %s_PROJECT=%s "
                "for %s ingestion"
            ),
            prefix,
            env_project,
            fetch_format.value,
        )
    project_name, project_id = _parse_project_identifier(env_project)
    if project_name is None and project_id is None and env_project:
        message = (
            f"Invalid project identifier '{env_project}' for "
            f"{fetch_format.value} ingestion. "
            "Provide a non-empty name or numeric ID."
        )
        raise exceptions.ConfigurationError(message)
    return project_name, project_id


def resolve_api_ingest_config(args: Any) -> APIIngestConfig:
    """Resolve API ingestion credentials from CLI args and environment."""
    fetch_format = getattr(args, "fetch_format", None)
    if isinstance(fetch_format, str):
        fetch_format = FETCHABLE_FORMATS.get(fetch_format.lower())

    if not isinstance(fetch_format, SupportedFormat):
        valid = ", ".join(fmt.value for fmt in SUPPORTED_FETCH_FORMATS)
        raise exceptions.ConfigurationError(
            f"API ingestion requires --fetch-format. Supported: {valid}"
        )

    if fetch_format not in SUPPORTED_FETCH_FORMATS:
        valid = ", ".join(fmt.value for fmt in SUPPORTED_FETCH_FORMATS)
        raise exceptions.ConfigurationError(
            f"Unsupported fetch format '{fetch_format.value}'. Supported: {valid}"
        )

    args.fetch_format = fetch_format

    prefix = f"IMPORTOBOT_{fetch_format.name}"
    fetch_env = os.getenv

    api_url = getattr(args, "api_url", None) or fetch_env(f"{prefix}_API_URL")
    cli_tokens = getattr(args, "api_tokens", None)
    tokens = (
        list(cli_tokens) if cli_tokens else _split_tokens(fetch_env(f"{prefix}_TOKENS"))
    )
    api_user = getattr(args, "api_user", None) or fetch_env(f"{prefix}_API_USER")

    project_name, project_id = _resolve_project_reference(
        args,
        fetch_env,
        prefix,
        fetch_format,
    )

    output_dir = _resolve_output_dir(getattr(args, "input_dir", None))
    max_concurrency = _resolve_max_concurrency(getattr(args, "max_concurrency", None))
    insecure = _resolve_insecure_flag(args, prefix)

    _validate_required_fields(
        fetch_format=fetch_format,
        api_url=api_url,
        tokens=tokens,
        api_user=api_user,
    )

    if api_url is None:
        raise exceptions.ConfigurationError(
            f"API ingestion requires an API URL for {fetch_format.value}; "
            "validation should have raised earlier."
        )

    if fetch_format is SupportedFormat.ZEPHYR and len(tokens) < ZEPHYR_MIN_TOKEN_COUNT:
        logger.debug(
            "Zephyr configured with %s token(s); dual-token authentication can be "
            "enabled by providing multiple --tokens values.",
            len(tokens),
        )

    if insecure:
        logger.warning(
            "TLS certificate verification disabled for %s API requests. "
            "Only use --insecure with trusted endpoints.",
            fetch_format.value,
        )

    return APIIngestConfig(
        fetch_format=fetch_format,
        api_url=api_url,
        tokens=tokens,
        user=api_user,
        project_name=project_name,
        project_id=project_id,
        output_dir=output_dir,
        max_concurrency=max_concurrency,
        insecure=insecure,
    )


def update_medallion_config(
    config: StorageConfigProtocol | None = None, **kwargs: Any
) -> StorageConfigProtocol:
    """Update medallion configuration placeholder.

    Uses lazy import to avoid circular dependency with medallion.storage.config.
    """
    storage_config_cls = _load_storage_config_cls()

    # Placeholder implementation for testing
    if config is None:
        config = storage_config_cls()

    # kwargs used for potential future configuration updates
    _ = kwargs  # Mark as used for linting
    return config


def validate_medallion_config(_config: StorageConfigProtocol) -> bool:
    """Validate medallion configuration placeholder."""
    # Placeholder implementation for testing
    return True
