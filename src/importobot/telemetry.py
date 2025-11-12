"""Provide lightweight telemetry helpers for emitting runtime metrics."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable

from importobot.utils.logging import get_logger

logger = get_logger()

TelemetryPayload = dict[str, object]
TelemetryExporter = Callable[[str, TelemetryPayload], None]


def _flag_from_env(var_name: str, default: bool = False) -> bool:
    """Get a boolean flag from an environment variable."""
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_from_env(var_name: str, default: float) -> float:
    """Get a float value from an environment variable."""
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_from_env(var_name: str, default: int) -> int:
    """Get an integer value from an environment variable."""
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class TelemetryClient:
    """Provide a simple telemetry client with basic rate limiting."""

    def __init__(
        self,
        *,
        min_emit_interval: float,
        min_sample_delta: int,
    ) -> None:
        """Initialize the telemetry client with rate limiting configuration."""
        self._min_emit_interval = min_emit_interval
        self._min_sample_delta = min_sample_delta
        self._lock = threading.Lock()
        self._last_emit: dict[str, tuple[int, float]] = {}
        self._exporters: list[TelemetryExporter] = [self._default_logger_exporter]

    def register_exporter(self, exporter: TelemetryExporter) -> None:
        """Register an exporter that receives telemetry events."""
        with self._lock:
            self._exporters.append(exporter)

    def clear_exporters(self) -> None:
        """Remove all exporters except the default logger exporter."""
        with self._lock:
            self._exporters = [self._default_logger_exporter]

    def restore_default_exporter(self) -> None:
        """Re-enable the built-in logger exporter."""
        with self._lock:
            if self._default_logger_exporter not in self._exporters:
                self._exporters.insert(0, self._default_logger_exporter)

    def record_cache_metrics(
        self,
        cache_name: str,
        *,
        hits: int,
        misses: int,
        extras: TelemetryPayload | None = None,
    ) -> None:
        """Record cache hit/miss information with basic throttling."""
        total_requests = hits + misses
        now = time.time()

        with self._lock:
            last_total, last_time = self._last_emit.get(cache_name, (0, 0.0))
            if (
                total_requests - last_total < self._min_sample_delta
                and now - last_time < self._min_emit_interval
            ):
                return
            self._last_emit[cache_name] = (total_requests, now)

        hit_rate = hits / total_requests if total_requests else 0.0
        payload: TelemetryPayload = {
            "cache_name": cache_name,
            "hits": hits,
            "misses": misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "timestamp": now,
        }
        if extras:
            for key, value in extras.items():
                if key in payload:
                    payload[f"extra_{key}"] = value
                else:
                    payload[key] = value

        self._emit("cache_metrics", payload)

    # ---------------------------------------------------------------------
    # Internals
    def _emit(self, event_name: str, payload: TelemetryPayload) -> None:
        """Emit a telemetry event to all registered exporters."""
        if not self._exporters:
            return
        for exporter in list(self._exporters):
            self._emit_with_exporter(exporter, event_name, payload)

    def _default_logger_exporter(
        self, event_name: str, payload: TelemetryPayload
    ) -> None:
        """Log telemetry events as warnings."""
        logger.warning("telemetry.%s %s", event_name, json.dumps(payload, default=str))

    def _emit_with_exporter(
        self,
        exporter: TelemetryExporter,
        event_name: str,
        payload: TelemetryPayload,
    ) -> None:
        """Invoke a single exporter while isolating failure handling."""
        try:
            exporter(event_name, payload)
        except Exception:  # pragma: no cover - telemetry failures shouldn't crash
            logger.exception("Telemetry exporter %s failed", exporter)


class _TelemetryClientHolder:
    """Thread-safe singleton holder for the telemetry client."""

    def __init__(self) -> None:
        self._client: TelemetryClient | None = None
        self._lock = threading.Lock()
        self._initialized = False

    def get_client(self) -> TelemetryClient | None:
        """Return the global telemetry client instance, or None if disabled.

        Returns None when IMPORTOBOT_ENABLE_TELEMETRY is false (default).
        """
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    enabled = _flag_from_env("IMPORTOBOT_ENABLE_TELEMETRY", False)
                    if enabled:
                        min_interval = _float_from_env(
                            "IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", 60.0
                        )
                        min_delta = _int_from_env(
                            "IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", 100
                        )
                        self._client = TelemetryClient(
                            min_emit_interval=min_interval,
                            min_sample_delta=min_delta,
                        )
                    else:
                        self._client = None
                    self._initialized = True
        return self._client

    def reset_client(self) -> None:
        """Reset the global telemetry client (useful in testing)."""
        with self._lock:
            self._client = None
            self._initialized = False


_HOLDER = _TelemetryClientHolder()


def get_telemetry_client() -> TelemetryClient | None:
    """Return the global telemetry client instance, or None if disabled."""
    return _HOLDER.get_client()


def reset_telemetry_client() -> None:
    """Reset the global telemetry client (useful in testing)."""
    _HOLDER.reset_client()


def register_telemetry_exporter(exporter: TelemetryExporter) -> None:
    """Register a custom telemetry exporter on the global client.

    No-op if telemetry is disabled.
    """
    client = get_telemetry_client()
    if client is not None:
        client.register_exporter(exporter)


def clear_telemetry_exporters() -> None:
    """Remove all custom exporters from the global client.

    No-op if telemetry is disabled.
    """
    client = get_telemetry_client()
    if client is not None:
        client.clear_exporters()


def restore_default_telemetry_exporter() -> None:
    """Re-enable the default logger exporter on the global client.

    No-op if telemetry is disabled.
    """
    client = get_telemetry_client()
    if client is not None:
        client.restore_default_exporter()
