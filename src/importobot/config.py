"""Configuration constants for Importobot."""

from __future__ import annotations

import contextlib
import os
import re
import warnings
from collections.abc import Callable, Iterable, Iterator, MutableSequence
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast, overload

from importobot.cli.constants import FETCHABLE_FORMATS, SUPPORTED_FETCH_FORMATS
from importobot.exceptions import ConfigurationError
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.security.secure_memory import (
    SecureString,
    SecurityError,
    create_secure_string,
)
from importobot.utils.logging import get_logger

# Module-level logger for configuration warnings
logger = get_logger()


@dataclass
class TokenValidationRules:
    """Runtime-configurable token validation parameters."""

    min_length: int
    placeholder_tokens: tuple[str, ...]
    insecure_indicators: tuple[str, ...]


def _parse_env_list(
    env_var: str,
    default: tuple[str, ...],
    *,
    normalizer: Callable[[str], str] | None = None,
) -> tuple[str, ...]:
    raw_value = os.getenv(env_var)
    if not raw_value:
        return default
    parts = [item.strip() for item in raw_value.split(",") if item.strip()]
    if normalizer:
        parts = [normalizer(part) for part in parts]
    return tuple(parts) if parts else default


def _get_token_validation_rules() -> TokenValidationRules:
    min_length = int(os.getenv("IMPORTOBOT_MIN_TOKEN_LENGTH", "12"))
    min_length = max(8, min_length)

    placeholder_tokens = _parse_env_list(
        "IMPORTOBOT_TOKEN_PLACEHOLDERS",
        ("token", "apitoken", "bearertoken", "yourtoken"),
        normalizer=lambda value: value.replace("-", "").replace("_", "").lower(),
    )

    insecure_indicators = _parse_env_list(
        "IMPORTOBOT_TOKEN_INDICATORS",
        (
            "password",
            "secret",
            "token",
            "key",
            "test",
            "demo",
            "example",
            "sample",
            "default",
            "temp",
            "temporary",
        ),
        normalizer=lambda value: value.lower(),
    )

    return TokenValidationRules(
        min_length=min_length,
        placeholder_tokens=placeholder_tokens,
        insecure_indicators=insecure_indicators,
    )

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
        raise ConfigurationError(
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
    """Hold configuration for the API ingestion workflow with secure token management.

    Configuration includes API endpoints, authentication tokens, and workflow
    settings.
    """

    fetch_format: SupportedFormat
    api_url: str
    tokens: list[SecureString] | list[str]  # Accept strings, convert in __post_init__
    user: str | None
    project_name: str | None
    project_id: int | None
    output_dir: Path
    max_concurrency: int | None
    insecure: bool
    _plaintext_tokens: LegacyPlaintextTokenView | None = field(
        init=False, repr=False, default=None
    )
    _legacy_tokens_warned: bool = field(init=False, repr=False, default=False)

    # Class-level flag to avoid duplicate legacy warnings across instances
    _legacy_tokens_global_warning_emitted = False

    def __post_init__(self) -> None:
        """Post-initialization security validation and token conversion."""
        # Convert non-secure tokens to SecureString for backward compatibility
        if self.tokens:
            converted_tokens: list[SecureString] = []
            for token in self.tokens:
                if isinstance(token, SecureString):
                    converted_tokens.append(token)
                else:
                    converted_tokens.append(create_secure_string(str(token)))
            self.tokens = converted_tokens

        # Immediate security validation (can be disabled for testing/perf experiments)
        if not os.getenv("IMPORTOBOT_SKIP_TOKEN_VALIDATION"):
            self._validate_token_security()

        self._plaintext_tokens = None

    @property
    def secure_tokens(self) -> list[SecureString]:
        """Return tokens as `SecureString` (guaranteed after `__post_init__`)."""
        return cast(list[SecureString], self.tokens)

    @property
    def plaintext_tokens(self) -> LegacyPlaintextTokenView:
        """Return a legacy plaintext token view with deprecation warnings."""
        self._mark_legacy_tokens_used()
        if self._plaintext_tokens is None:
            self._plaintext_tokens = LegacyPlaintextTokenView(self)
        return self._plaintext_tokens

    def _mark_legacy_tokens_used(self) -> None:
        """Emit deprecation warnings for plaintext token access."""
        if self._legacy_tokens_warned:
            return

        warnings.warn(
            "APIIngestConfig.tokens now store SecureString instances. Access "
            "config.plaintext_tokens only when migration is impossible.",
            DeprecationWarning,
            stacklevel=3,
        )

        if not type(self)._legacy_tokens_global_warning_emitted:
            logger.warning(
                "APIIngestConfig plaintext_tokens accessed; migrate callers to "
                "get_token() or secure_tokens to keep secrets encrypted."
            )
            type(self)._legacy_tokens_global_warning_emitted = True

        self._legacy_tokens_warned = True

    def _validate_token_security(self) -> None:
        """Perform immediate security validation on tokens."""
        for position, token in enumerate(self.secure_tokens, start=1):
            self._validate_single_token(token, position)

    def _validate_single_token(self, token: SecureString, position: int) -> None:
        """Validate a single token with configurable rules."""
        try:
            token_value = token.value
            token_lower = token_value.lower()
            rules = _get_token_validation_rules()

            normalized_token = token_lower.replace("-", "").replace("_", "")
            if normalized_token in rules.placeholder_tokens:
                raise SecurityError(
                    f"Token {position} is an exact placeholder match '{token_value}'"
                )

            if len(token_value) < rules.min_length:
                raise SecurityError(
                    f"Token {position} too short (min {rules.min_length} chars, "
                    f"got {len(token_value)})"
                )

            self._validate_insecure_indicators(
                token_value,
                token_lower,
                position,
                rules=rules,
            )

            unique_chars = len(set(token_value))
            min_unique = max(4, len(token_value) // 4)
            if unique_chars < min_unique:
                logger.warning(
                    "Token %d has low entropy (%d unique chars in %d total). "
                    "Consider using a more random token.",
                    position,
                    unique_chars,
                    len(token_value),
                )

        except SecurityError:
            raise
        except Exception as exc:
            raise SecurityError(f"Failed to validate token {position}: {exc}") from exc

    def get_token(self, index: int) -> str:
        """Securely retrieve a token by index.

        Args:
            index: Index of token to retrieve

        Returns:
            Token value as string

        Raises:
            IndexError: If index out of range
            SecurityError: If token access fails
        """
        secure_tokens = self.secure_tokens
        if index >= len(secure_tokens):
            raise IndexError(
                f"Token index {index} out of range (0-{len(secure_tokens) - 1})"
            )

        return secure_tokens[index].value

    def get_all_tokens(self) -> list[str]:
        """Retrieve all tokens securely.

        Returns:
            List of token values

        Warning:
            Use with caution - returned strings remain in memory
        """
        return [token.value for token in self.secure_tokens]

    def add_token(self, token: str) -> None:
        """Add a new token securely.

        Args:
            token: Token value to add

        Raises:
            SecurityError: If token validation fails
        """
        secure_token = create_secure_string(token)

        secure_tokens = self.secure_tokens
        try:
            self._validate_single_token(secure_token, len(secure_tokens) + 1)
        except SecurityError:
            secure_token.zeroize()
            raise

        # If validation passes, add to existing tokens
        secure_tokens_list = self.secure_tokens
        secure_tokens_list.append(secure_token)
        self.tokens = secure_tokens_list  # Update the reference

    def cleanup(self) -> None:
        """Explicitly zeroize all secure tokens."""
        if not hasattr(self, "secure_tokens"):
            return

        for token in self.secure_tokens:
            try:
                if hasattr(token, "zeroize"):
                    token.zeroize()
            except Exception as exc:  # noqa: PERF203
                logger.error("Failed to zeroize token: %s", exc)

    def __enter__(self) -> APIIngestConfig:
        """Return this config for use in a `with` block."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure sensitive tokens are destroyed when leaving the context."""
        self.cleanup()

    def __del__(self) -> None:
        """Cleanup tokens on destruction."""
        with contextlib.suppress(Exception):
            secure_tokens = getattr(self, "secure_tokens", [])
            for token in secure_tokens:
                if hasattr(token, "zeroize"):
                    token.zeroize()

    @staticmethod
    def _indicator_has_boundary(token: str, indicator: str) -> bool:
        """Return True when indicator appears as a separate token segment."""
        pattern = rf"(?:^|[^a-z0-9]){re.escape(indicator)}(?:[^a-z0-9]|$)"
        return re.search(pattern, token) is not None

    def _validate_insecure_indicators(
        self,
        token_value: str,
        token_lower: str,
        position: int,
        *,
        rules: TokenValidationRules | None = None,
    ) -> None:
        """Raise when token contains insecure indicators."""
        if rules is None:
            rules = _get_token_validation_rules()

        insecure_indicators = rules.insecure_indicators
        boundary_indicators = {"key"}
        uppercase_only_indicators = {"token"}

        for indicator in insecure_indicators:
            if indicator in boundary_indicators:
                if self._indicator_has_boundary(token_lower, indicator):
                    raise SecurityError(
                        f"Token {position} contains insecure indicator '{indicator}'"
                    )
                continue

            if indicator in uppercase_only_indicators:
                matches = [
                    match.start() for match in re.finditer(indicator, token_lower)
                ]
                if any(
                    token_value[idx : idx + len(indicator)].isupper() for idx in matches
                ):
                    raise SecurityError(
                        f"Token {position} contains insecure indicator '{indicator}'"
                    )
                continue

            if indicator in token_lower:
                raise SecurityError(
                    f"Token {position} contains insecure indicator '{indicator}'"
                )


class LegacyPlaintextTokenView(MutableSequence[str]):
    """Mutable list-like view exposing plaintext tokens with validation."""

    __slots__ = ("_config",)

    def __init__(self, config: APIIngestConfig) -> None:
        """Bind the view to an APIIngestConfig instance."""
        self._config = config

    def __len__(self) -> int:  # pragma: no cover - trivial wrapper
        """Return the number of tokens tracked by the parent config."""
        return len(self._config.secure_tokens)

    @overload
    def __getitem__(self, index: int) -> str:  # pragma: no cover - simple proxy
        """Return the plaintext token at the requested index."""
        ...

    @overload
    def __getitem__(
        self, index: slice
    ) -> MutableSequence[str]:  # pragma: no cover - simple proxy
        """Return a mutable copy of the requested token slice."""
        ...

    def __getitem__(
        self, index: int | slice
    ) -> str | MutableSequence[str]:  # pragma: no cover - simple proxy
        """Return one or more plaintext tokens."""
        secure_tokens = self._config.secure_tokens
        if isinstance(index, slice):
            return [token.value for token in secure_tokens[index]]
        return secure_tokens[index].value

    @overload
    def __setitem__(self, index: int, value: str) -> None:
        """Replace a single plaintext token."""
        ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[str]) -> None:
        """Replace a slice of tokens with new plaintext values."""
        ...

    def __setitem__(
        self, index: int | slice, value: str | Iterable[str]
    ) -> None:
        """Replace one or more tokens with new plaintext values."""
        secure_tokens = self._config.secure_tokens
        if isinstance(index, slice):
            normalized_values = self._normalize_sequence(value)
            start, _, _ = index.indices(len(secure_tokens))
            replacements = self._create_secure_tokens(normalized_values, start)
            self._replace_slice(index, replacements)
            return

        secure_token = self._create_secure_token(str(value), index + 1)
        secure_tokens[index].zeroize()
        secure_tokens[index] = secure_token

    def __delitem__(self, index: int | slice) -> None:
        """Delete one or more tokens, ensuring the old values are zeroized."""
        secure_tokens = self._config.secure_tokens
        if isinstance(index, slice):
            start, stop, step = index.indices(len(secure_tokens))
            if step != 1:
                raise ValueError(
                    "Extended slice deletion is not supported for plaintext tokens"
                )
            for token in secure_tokens[start:stop]:
                token.zeroize()
            del secure_tokens[index]
            return

        secure_tokens[index].zeroize()
        del secure_tokens[index]

    def insert(self, index: int, value: str) -> None:
        """Insert a plaintext token at a specific position."""
        secure_tokens = self._config.secure_tokens
        target_index = max(0, min(index, len(secure_tokens)))
        secure_token = self._create_secure_token(str(value), target_index + 1)
        secure_tokens.insert(target_index, secure_token)

    # pragma: no cover - iteration exercised in config security tests
    def __iter__(self) -> Iterator[str]:
        """Yield plaintext tokens without exposing SecureString internals."""
        for token in self._config.secure_tokens:
            yield token.value

    def _normalize_sequence(self, value: Iterable[str]) -> list[str]:
        return [str(item) for item in value]

    def _create_secure_tokens(
        self, values: list[str], start_offset: int
    ) -> list[SecureString]:
        replacements: list[SecureString] = []
        for position, token in enumerate(values, start=start_offset + 1):
            replacements.append(self._create_secure_token(token, position))
        return replacements

    def _replace_slice(
        self, index: slice, replacements: list[SecureString]
    ) -> None:
        secure_tokens = self._config.secure_tokens
        start, stop, step = index.indices(len(secure_tokens))
        if step != 1:
            for token in replacements:
                token.zeroize()
            raise ValueError(
                "Extended slice assignment is not supported for plaintext tokens"
            )

        for token in secure_tokens[start:stop]:
            token.zeroize()

        secure_tokens[index] = replacements

    def _create_secure_token(self, token: str, position: int) -> SecureString:
        secure_token = create_secure_string(token)
        try:
            self._config._validate_single_token(secure_token, position)
        except SecurityError:
            secure_token.zeroize()
            raise
        return secure_token
def _split_tokens(raw_tokens: str | None) -> list[str]:
    """Split a comma-separated string of tokens into a list."""
    if not raw_tokens:
        return []
    return [token.strip() for token in raw_tokens.split(",") if token.strip()]


def _mask(
    tokens: list[str] | list[SecureString] | list[str | SecureString] | None,
) -> str:
    """Return a masked representation of tokens for logging."""
    if not tokens:
        return "***"

    # Handle both string and SecureString tokens
    count = len(tokens)
    return ", ".join("***" for _ in range(count))


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
        raise ConfigurationError(
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
            raise ConfigurationError(
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
        """Return the project identifier from CLI arguments."""
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
        raise ConfigurationError(message)
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
        raise ConfigurationError(message)
    return project_name, project_id


def resolve_api_ingest_config(args: Any) -> APIIngestConfig:
    """Resolve API ingestion credentials from CLI args and environment variables."""
    fetch_format = getattr(args, "fetch_format", None)
    if isinstance(fetch_format, str):
        fetch_format = FETCHABLE_FORMATS.get(fetch_format.lower())

    if not isinstance(fetch_format, SupportedFormat):
        valid = ", ".join(fmt.value for fmt in SUPPORTED_FETCH_FORMATS)
        raise ConfigurationError(
            f"API ingestion requires --fetch-format. Supported: {valid}"
        )

    if fetch_format not in SUPPORTED_FETCH_FORMATS:
        valid = ", ".join(fmt.value for fmt in SUPPORTED_FETCH_FORMATS)
        raise ConfigurationError(
            f'Unsupported fetch format "{fetch_format.value}". Supported: {valid}'
        )

    args.fetch_format = fetch_format

    prefix = f"IMPORTOBOT_{fetch_format.name}"
    fetch_env = os.getenv

    api_url = getattr(args, "api_url", None) or fetch_env(f"{prefix}_API_URL")
    cli_tokens = getattr(args, "api_tokens", None)
    # Explicit type annotation for type checker
    tokens: list[str] = (
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
        raise ConfigurationError(
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
