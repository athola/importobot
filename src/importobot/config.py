"""Configuration constants for Importobot."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

from importobot import exceptions
from importobot.cli.constants import FETCHABLE_FORMATS, SUPPORTED_FETCH_FORMATS
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import get_logger

# Module-level logger for configuration warnings
logger = get_logger()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"

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

# Numeric project identifiers must fit within a signed 64-bit integer to prevent
# overflow in downstream databases and APIs.
MAX_PROJECT_ID = 9_223_372_036_854_775_807

# Headless Chrome options for browser-based tests. These flags are necessary
# for running Chrome in a containerized or CI/CD environment.
CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--headless",
    "--disable-web-security",
    "--allow-running-insecure-content",
]

# Cache cleanup defaults (seconds). These can be overridden by importing them
# in other modules.
CACHE_MIN_CLEANUP_INTERVAL = 0.1
CACHE_DEFAULT_CLEANUP_INTERVAL = 5.0
CACHE_MAX_CLEANUP_INTERVAL = 300.0
CACHE_SHORT_TTL_THRESHOLD = 5.0


def _int_from_env(var_name: str, default: int, *, minimum: int | None = None) -> int:
    """Parse an integer from an environment variable."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("Invalid %s=%s; using default %d", var_name, raw_value, default)
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
    """Parse a boolean from an environment variable."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


# Configuration for maximum file sizes (in MB / bytes)
DEFAULT_MAX_JSON_SIZE_MB = 10
DEFAULT_MAX_SCHEMA_SECTIONS = 256
MAX_JSON_SIZE_MB = int(
    os.getenv("IMPORTOBOT_MAX_JSON_SIZE_MB", str(DEFAULT_MAX_JSON_SIZE_MB))
)
MAX_SCHEMA_FILE_SIZE_BYTES = _int_from_env(
    "IMPORTOBOT_MAX_SCHEMA_BYTES",
    1 * 1024 * 1024,
    minimum=1024,
)
MAX_SCHEMA_SECTIONS = _int_from_env(
    "IMPORTOBOT_MAX_SCHEMA_SECTIONS",
    DEFAULT_MAX_SCHEMA_SECTIONS,
    minimum=1,
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


def validate_global_limits() -> None:
    """Validate critical configuration limits."""
    issues: list[str] = []
    if MAX_SCHEMA_FILE_SIZE_BYTES <= 0:
        issues.append(
            "MAX_SCHEMA_FILE_SIZE_BYTES must be positive "
            f"(got {MAX_SCHEMA_FILE_SIZE_BYTES})"
        )
    if MAX_TEMPLATE_FILE_SIZE_BYTES <= 0:
        issues.append(
            "MAX_TEMPLATE_FILE_SIZE_BYTES must be positive "
            f"(got {MAX_TEMPLATE_FILE_SIZE_BYTES})"
        )
    if MAX_CACHE_CONTENT_SIZE_BYTES <= 0:
        issues.append(
            "MAX_CACHE_CONTENT_SIZE_BYTES must be positive "
            f"(got {MAX_CACHE_CONTENT_SIZE_BYTES})"
        )
    if issues:
        formatted = "; ".join(issues)
        raise exceptions.ConfigurationError(
            f"Configuration sanity checks failed: {formatted}"
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
DETECTION_CACHE_MIN_DELAY_MS = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_MIN_DELAY_MS", 0, minimum=0
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

# Bronze layer in-memory cache configuration.
# Default is 1024 records, using about 1MB of memory.
BRONZE_LAYER_MAX_IN_MEMORY_RECORDS = _int_from_env(
    "IMPORTOBOT_BRONZE_MAX_IN_MEMORY_RECORDS", 1024, minimum=1
)

# Default TTL is 0 (disabled) because most use cases are append-only.
# Enable TTL only when external updates require cache invalidation.
BRONZE_LAYER_IN_MEMORY_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_BRONZE_IN_MEMORY_TTL_SECONDS", 0, minimum=0
)


@dataclass(slots=True)
class APIIngestConfig:
    """Hold configuration for the API ingestion workflow."""

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
    """Split a comma-separated string of tokens into a list."""
    if not raw_tokens:
        return []
    return [token.strip() for token in raw_tokens.split(",") if token.strip()]


def _mask(tokens: list[str] | None) -> str:
    """Return a masked representation of tokens for logging."""
    if not tokens:
        return "***"
    return ", ".join("***" for _ in tokens)


def _resolve_output_dir(cli_path: str | None) -> Path:
    """Resolve the output directory from CLI arguments or environment variables."""
    env_dir = os.getenv("IMPORTOBOT_API_INPUT_DIR")
    candidate = cli_path or env_dir
    return Path(candidate).expanduser().resolve() if candidate else Path.cwd()


def _resolve_max_concurrency(cli_value: int | None) -> int | None:
    """Resolve the maximum concurrency from CLI arguments or environment variables."""
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
    """Resolve the TLS verification flag from CLI arguments or environment variables."""
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
    """Validate that all required API configuration fields are present."""
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
    """Parse a project identifier into a name or a numeric ID."""
    if not value:
        return None, None
    raw = value.strip()
    if not raw or raw.isspace():
        return None, None

    # Check ASCII first (cheaper operation) then digit status
    if raw.isascii() and raw.isdigit():
        try:
            project_id = int(raw)
        except ValueError:
            logger.warning(
                "Numeric project identifier %s failed to parse; treating as name",
                raw,
            )
            return raw, None
        if project_id > MAX_PROJECT_ID:
            raise exceptions.ConfigurationError(
                f"Project identifier {project_id} exceeds supported maximum "
                f"{MAX_PROJECT_ID} (signed 64-bit)."
            )
        return None, project_id

    # Non-ASCII input or non-digit ASCII string treated as project name
    if not raw.isascii():
        logger.warning(
            "Non-ASCII project identifier %s treated as project name (not numeric ID)",
            raw,
        )
    return raw, None


class _ProjectReferenceArgs(Protocol):
    """Define a protocol for arguments that contain a project reference."""

    @property
    def project(self) -> str | None:
        """The project identifier from CLI arguments."""
        ...


def _resolve_project_reference(
    args: _ProjectReferenceArgs,
    fetch_env: Callable[[str], str | None],
    prefix: str,
    fetch_format: SupportedFormat,
) -> tuple[str | None, int | None]:
    """Resolve project identifiers from CLI arguments or environment variables."""
    cli_project = getattr(args, "project", None)
    cli_invalid = False
    if cli_project is not None:
        project_name, project_id = _parse_project_identifier(cli_project)
        if project_name is None and project_id is None:
            logger.debug(
                "Ignoring invalid CLI project identifier %r for %s ingestion; "
                "%s_PROJECT default will be used if available",
                cli_project,
                fetch_format.value,
                prefix,
            )
            cli_invalid = True
        else:
            return project_name, project_id

    env_project = fetch_env(f"{prefix}_PROJECT")
    if env_project:
        if cli_invalid:
            # CLI was invalid, using environment variable default
            logger.warning(
                "Invalid CLI project identifier %r for %s ingestion; "
                "using %s_PROJECT=%s instead",
                cli_project,
                fetch_format.value,
                prefix,
                env_project,
            )
        else:
            # CLI was missing, using environment variable as default
            logger.debug(
                "CLI project identifier missing; falling back to %s_PROJECT=%s "
                "for %s ingestion",
                prefix,
                env_project,
                fetch_format.value,
            )
    project_name, project_id = _parse_project_identifier(env_project)
    if project_name is None and project_id is None and env_project:
        message = (
            f'Invalid project identifier "{env_project}" for '
            f"{fetch_format.value} ingestion. "
            "Provide a non-empty name or numeric ID."
        )
        raise exceptions.ConfigurationError(message)
    if cli_invalid and project_name is None and project_id is None:
        if env_project:
            # CLI was invalid and env was also invalid
            message = (
                f"Both CLI project identifier {cli_project!r} and "
                f"{prefix}_PROJECT={env_project!r} are invalid for "
                f"{fetch_format.value} ingestion. "
                "Provide a non-empty name or numeric ID."
            )
        else:
            # CLI was invalid and no environment variable was set
            message = (
                f"Invalid CLI project identifier {cli_project!r} for "
                f"{fetch_format.value} ingestion and no "
                f"{prefix}_PROJECT environment variable set. "
                "Provide a valid project identifier via CLI or environment variable."
            )
        raise exceptions.ConfigurationError(message)
    return project_name, project_id


def resolve_api_ingest_config(args: Any) -> APIIngestConfig:
    """Resolve API ingestion credentials from CLI args and environment variables."""
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
            f'Unsupported fetch format "{fetch_format.value}". Supported: {valid}'
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


def update_medallion_config(config: Any = None, **kwargs: Any) -> Any:
    """Update Medallion storage configuration with lazy dependency loading.

    This helper defers importing the Medallion storage stack until explicitly
    requested.
    """
    try:
        storage_module = import_module("importobot.medallion.storage.config")
        StorageConfig = storage_module.StorageConfig
    except ImportError as exc:  # pragma: no cover - exercised without medallion
        raise ImportError(
            "The medallion storage configuration is unavailable. "
            "Install the optional medallion extras to enable storage configuration."
        ) from exc
    except AttributeError as exc:
        raise ImportError(
            "StorageConfig is unavailable. Ensure the medallion extras are installed."
        ) from exc

    if config is None:
        config = StorageConfig()

    if not isinstance(config, StorageConfig):
        raise TypeError("config must be an instance of StorageConfig or None")

    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            logger.debug("Ignoring unknown storage config field '%s'", key)

    return config
