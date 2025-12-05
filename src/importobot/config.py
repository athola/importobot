"""Configuration constants for Importobot."""

from __future__ import annotations

import os
import warnings
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from types import TracebackType
from typing import Any, Literal, Protocol, overload

from importobot import exceptions
from importobot.cli.constants import FETCHABLE_FORMATS, SUPPORTED_FETCH_FORMATS
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.security.secure_memory import SecureString, SecurityError
from importobot.utils.logging import get_logger

TokenLike = str | SecureString

_MIN_TOKEN_LENGTH_DEFAULT = 12
_MIN_TOKEN_LENGTH_FLOOR = 8
_TOKEN_PLACEHOLDER_MATCHES = {
    "token",
    "api-token",
    "bearer_token",
    "your_token",
}
_TOKEN_INSECURE_INDICATORS = (
    "password",
    "api_key",
    "apikey",
    "key",
    "test",
    "demo",
    "example",
    "secret",
    "sample",
    "default",
    "temp",
    "temporary",
    "token",
)


def _token_to_plaintext(token: TokenLike) -> str:
    """Return the plaintext value for either SecureString or raw strings."""
    if isinstance(token, SecureString):
        return token.value
    return token


def _resolve_min_token_length() -> int:
    """Resolve the configured minimum token length with sane defaults."""
    raw_value = os.getenv("IMPORTOBOT_MIN_TOKEN_LENGTH")
    if not raw_value:
        return _MIN_TOKEN_LENGTH_DEFAULT
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid IMPORTOBOT_MIN_TOKEN_LENGTH=%s; falling back to %d",
            raw_value,
            _MIN_TOKEN_LENGTH_DEFAULT,
        )
        return _MIN_TOKEN_LENGTH_DEFAULT
    return max(_MIN_TOKEN_LENGTH_FLOOR, parsed)


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

# Security scanning configuration
CREDENTIAL_CONTEXT_WINDOW = _int_from_env(
    "IMPORTOBOT_CREDENTIAL_CONTEXT_WINDOW", 100, minimum=10
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


@dataclass(slots=True, init=False)
class APIIngestConfig:
    """Hold configuration for the API ingestion workflow."""

    fetch_format: SupportedFormat
    api_url: str
    user: str | None
    project_name: str | None
    project_id: int | None
    output_dir: Path
    max_concurrency: int | None
    insecure: bool
    tokens: _SecureTokenListView = field(init=False)
    _secure_tokens: list[SecureString] = field(init=False, repr=False)
    _plaintext_view: _PlaintextTokenView = field(init=False, repr=False)

    def __init__(
        self,
        *,
        fetch_format: SupportedFormat,
        api_url: str,
        tokens: Sequence[TokenLike],
        user: str | None,
        project_name: str | None,
        project_id: int | None,
        output_dir: Path,
        max_concurrency: int | None,
        insecure: bool,
    ) -> None:
        """Create a secure ingestion config and normalize supplied tokens."""
        self.fetch_format = fetch_format
        self.api_url = api_url
        self.user = user
        self.project_name = project_name
        self.project_id = project_id
        self.output_dir = output_dir
        self.max_concurrency = max_concurrency
        self.insecure = insecure
        self._secure_tokens = self._build_secure_tokens(tokens)
        self.tokens = _SecureTokenListView(self._secure_tokens)
        self._plaintext_view = _PlaintextTokenView(self)

    def get_token(self, index: int) -> str:
        """Get a token by index."""
        if index < 0 or index >= len(self._secure_tokens):
            raise IndexError(f"Token index {index} out of range")
        return self._secure_tokens[index].value

    def get_all_tokens(self) -> list[str]:
        """Get a copy of all tokens."""
        return [token.value for token in self._secure_tokens]

    @property
    def plaintext_tokens(self) -> _PlaintextTokenView:
        """Return plaintext tokens (deprecated, migration compatibility)."""
        warnings.warn(
            "plaintext_tokens is deprecated and will be removed in a future version. "
            "Direct token access is discouraged for security reasons.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._plaintext_view

    def add_token(self, token: str) -> None:
        """Add a new token to the list."""
        position = len(self._secure_tokens) + 1
        normalized = self._enforce_token_rules(token, position)
        self._secure_tokens.append(SecureString(normalized))

    def cleanup(self) -> None:
        """Clean up sensitive information."""
        for token in self._secure_tokens:
            token.zeroize()
        self._secure_tokens.clear()

    def __enter__(self) -> APIIngestConfig:
        """Enter the runtime context for the config."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Exit the runtime context and cleanup."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def _build_secure_tokens(self, tokens: Sequence[TokenLike]) -> list[SecureString]:
        """Validate input tokens and return SecureString instances."""
        if not tokens:
            return []

        secure_tokens: list[SecureString] = []
        for position, token in enumerate(tokens, start=1):
            plaintext = self._extract_plaintext(token, position)
            normalized = self._enforce_token_rules(plaintext, position)
            if isinstance(token, SecureString) and token.value == normalized:
                secure_tokens.append(token)
            else:
                secure_tokens.append(SecureString(normalized))
        return secure_tokens

    @staticmethod
    def _extract_plaintext(token: TokenLike, position: int) -> str:
        """Extract plaintext value from supported token inputs."""
        try:
            return token if isinstance(token, str) else token.value
        except Exception as exc:  # pragma: no cover - defensive
            raise SecurityError(f"Failed to validate token {position}: {exc}") from exc

    def _enforce_token_rules(self, token_value: str, position: int) -> str:
        """Enforce enterprise token validation rules and return normalized value."""
        stripped_value = token_value.strip()
        lowered = stripped_value.lower()

        if lowered in _TOKEN_PLACEHOLDER_MATCHES:
            raise SecurityError(f"Token {position} is an exact placeholder match")

        indicator = self._find_insecure_indicator(lowered)
        if indicator:
            raise SecurityError(
                f"Token {position} contains insecure indicator '{indicator}'"
            )

        min_length = _resolve_min_token_length()
        skip_length_check = self._should_skip_length_check(lowered)
        if not skip_length_check and len(stripped_value) < min_length:
            raise SecurityError(
                f"Token {position} too short ({len(stripped_value)} chars); "
                f"min {min_length} chars required"
            )

        self._warn_low_entropy(stripped_value, position)
        return stripped_value

    def _warn_low_entropy(self, token_value: str, position: int) -> None:
        """Log a warning if the token has suspiciously low entropy."""
        unique_chars = len(set(token_value))
        min_unique = max(4, len(token_value) // 4)
        if unique_chars < min_unique:
            logger.warning(
                "Token %d has low entropy (%d unique chars, expected >= %d)",
                position,
                unique_chars,
                min_unique,
            )

    def _find_insecure_indicator(self, lowered_value: str) -> str | None:
        """Return the insecure indicator present in the token, if any."""
        for indicator in _TOKEN_INSECURE_INDICATORS:
            if indicator == "token":
                if self._has_token_indicator(lowered_value):
                    return indicator
            elif indicator in lowered_value:
                return indicator
        return None

    def _has_token_indicator(self, lowered_value: str) -> bool:
        """Detect token placeholder patterns embedded in identifiers."""
        needle = "token"
        index = lowered_value.find(needle)
        while index != -1:
            prev_char = lowered_value[index - 1] if index > 0 else ""
            next_index = index + len(needle)
            next_char = (
                lowered_value[next_index] if next_index < len(lowered_value) else ""
            )
            if prev_char.isalnum() or next_char.isalnum():
                return True
            index = lowered_value.find(needle, index + 1)
        return False

    def _should_skip_length_check(self, lowered_value: str) -> bool:
        """Allow sample tokens with hyphenated token fragments for compatibility."""
        if "token" not in lowered_value:
            return False
        return not self._has_token_indicator(lowered_value)


class _SecureTokenListView(Sequence[SecureString]):
    """Sequence wrapper that preserves SecureString semantics with list ergonomics."""

    def __init__(self, backing: list[SecureString]):
        self._backing = backing

    def __len__(self) -> int:
        return len(self._backing)

    @overload
    def __getitem__(self, item: int) -> SecureString:  # pragma: no cover - overload
        ...

    @overload
    def __getitem__(
        self, item: slice
    ) -> list[SecureString]:  # pragma: no cover - overload
        ...

    def __getitem__(
        self, item: int | slice
    ) -> SecureString | list[SecureString]:  # pragma: no cover - passthrough
        return self._backing[item]

    def __iter__(self) -> Iterator[SecureString]:  # pragma: no cover - delegated
        return iter(self._backing)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence):
            other_values = []
            for candidate in other:
                if isinstance(candidate, SecureString):
                    other_values.append(candidate.value)
                else:
                    other_values.append(str(candidate))
            return self._as_plaintext() == other_values
        return NotImplemented

    def _as_plaintext(self) -> list[str]:
        return [token.value for token in self._backing]

    def __hash__(self) -> int:
        return hash(tuple(self._as_plaintext()))


class _PlaintextTokenView:
    """Mutable plaintext token view that keeps SecureString storage in sync."""

    def __init__(self, owner: APIIngestConfig):
        self._owner = owner

    def __len__(self) -> int:
        return len(self._owner._secure_tokens)

    def __iter__(self) -> Iterator[str]:  # pragma: no cover - simple delegation
        for token in self._owner._secure_tokens:
            yield token.value

    def __getitem__(self, index: int) -> str:
        return self._owner._secure_tokens[index].value

    def __setitem__(self, index: int, value: str) -> None:
        normalized = self._owner._enforce_token_rules(value, index + 1)
        self._owner._secure_tokens[index].zeroize()
        self._owner._secure_tokens[index] = SecureString(normalized)

    def __delitem__(self, index: int) -> None:
        token = self._owner._secure_tokens.pop(index)
        token.zeroize()

    def insert(self, index: int, value: str) -> None:
        normalized = self._owner._enforce_token_rules(value, index + 1)
        self._owner._secure_tokens.insert(index, SecureString(normalized))

    def append(self, value: str) -> None:
        self.insert(len(self._owner._secure_tokens), value)

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"PlaintextTokenView(count={len(self)})"


def _split_tokens(raw_tokens: str | None) -> list[str]:
    """Split a comma-separated string of tokens into a list."""
    if not raw_tokens:
        return []
    return [token.strip() for token in raw_tokens.split(",") if token.strip()]


def _mask(tokens: Sequence[TokenLike] | None) -> str:
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
    tokens: Sequence[TokenLike],
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


__all__ = [
    "BRONZE_LAYER_IN_MEMORY_TTL_SECONDS",
    "BRONZE_LAYER_MAX_IN_MEMORY_RECORDS",
    "CACHE_DEFAULT_CLEANUP_INTERVAL",
    "CACHE_MAX_CLEANUP_INTERVAL",
    "CACHE_MIN_CLEANUP_INTERVAL",
    "CACHE_SHORT_TTL_THRESHOLD",
    "CHROME_OPTIONS",
    "CREDENTIAL_CONTEXT_WINDOW",
    "DEFAULT_TEST_SERVER_URL",
    "DETECTION_CACHE_COLLISION_LIMIT",
    "DETECTION_CACHE_MAX_SIZE",
    "DETECTION_CACHE_MIN_DELAY_MS",
    "DETECTION_CACHE_TTL_SECONDS",
    "FILE_CONTENT_CACHE_MAX_ENTRIES",
    "FILE_CONTENT_CACHE_MAX_MB",
    "FILE_CONTENT_CACHE_TTL_SECONDS",
    "FORMAT_DETECTION_CIRCUIT_RESET_SECONDS",
    "FORMAT_DETECTION_FAILURE_THRESHOLD",
    "MAX_CACHE_CONTENT_SIZE_BYTES",
    "MAX_JSON_SIZE_MB",
    "MAX_PROJECT_ID",
    "MAX_SCHEMA_FILE_SIZE_BYTES",
    "MAX_SCHEMA_SECTIONS",
    "MAX_TEMPLATE_FILE_SIZE_BYTES",
    "OPTIMIZATION_CACHE_TTL_SECONDS",
    "PERFORMANCE_CACHE_MAX_SIZE",
    "PERFORMANCE_CACHE_TTL_SECONDS",
    "TEST_SERVER_PORT",
    "ZEPHYR_MIN_TOKEN_COUNT",
    "APIIngestConfig",
    "resolve_api_ingest_config",
    "validate_global_limits",
]
