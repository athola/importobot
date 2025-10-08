"""Lightweight telemetry helpers for emitting runtime metrics."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable, Dict, Optional

from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)

TelemetryPayload = Dict[str, object]
TelemetryExporter = Callable[[str, TelemetryPayload], None]


def _flag_from_env(var_name: str, default: bool = False) -> bool:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_from_env(var_name: str, default: float) -> float:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_from_env(var_name: str, default: int) -> int:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class TelemetryClient:
    """Simple telemetry client with basic rate limiting."""

    def __init__(
        self,
        *,
        enabled: bool,
        min_emit_interval: float,
        min_sample_delta: int,
    ) -> None:
        """Initialize telemetry client with rate limiting configuration."""
        self.enabled = enabled
        self._min_emit_interval = min_emit_interval
        self._min_sample_delta = min_sample_delta
        self._lock = threading.Lock()
        self._last_emit: Dict[str, tuple[int, float]] = {}
        self._exporters: list[TelemetryExporter] = []
        if enabled:
            self.register_exporter(self._default_logger_exporter)

    def register_exporter(self, exporter: TelemetryExporter) -> None:
        """Register an exporter that receives telemetry events."""
        if not self.enabled:
            return
        with self._lock:
            self._exporters.append(exporter)

    def clear_exporters(self) -> None:
        """Remove all custom exporters (used in testing)."""
        with self._lock:
            self._exporters = [self._default_logger_exporter] if self.enabled else []

    def record_cache_metrics(
        self,
        cache_name: str,
        *,
        hits: int,
        misses: int,
        extras: Optional[TelemetryPayload] = None,
    ) -> None:
        """Record cache hit/miss information with basic throttling."""
        if not self.enabled:
            return

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
            payload.update(extras)

        self._emit("cache_metrics", payload)

    # ---------------------------------------------------------------------
    # Internals
    def _emit(self, event_name: str, payload: TelemetryPayload) -> None:
        for exporter in list(self._exporters):
            try:
                exporter(event_name, payload)
            except Exception:  # pragma: no cover - telemetry failures shouldn't crash
                logger.exception("Telemetry exporter %s failed", exporter)

    def _default_logger_exporter(
        self, event_name: str, payload: TelemetryPayload
    ) -> None:
        logger.info("telemetry.%s %s", event_name, json.dumps(payload, default=str))


class _TelemetryClientHolder:
    """Thread-safe singleton holder for the telemetry client."""

    def __init__(self) -> None:
        self._client: Optional[TelemetryClient] = None
        self._lock = threading.Lock()

    def get_client(self) -> TelemetryClient:
        """Return the global telemetry client instance."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    enabled = _flag_from_env("IMPORTOBOT_ENABLE_TELEMETRY", False)
                    min_interval = _float_from_env(
                        "IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", 60.0
                    )
                    min_delta = _int_from_env(
                        "IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", 100
                    )
                    self._client = TelemetryClient(
                        enabled=enabled,
                        min_emit_interval=min_interval,
                        min_sample_delta=min_delta,
                    )
        return self._client

    def reset_client(self) -> None:
        """Reset the global telemetry client (useful in testing)."""
        with self._lock:
            self._client = None


_HOLDER = _TelemetryClientHolder()


def get_telemetry_client() -> TelemetryClient:
    """Return the global telemetry client instance."""
    return _HOLDER.get_client()


def reset_telemetry_client() -> None:
    """Reset the global telemetry client (useful in testing)."""
    _HOLDER.reset_client()


def register_telemetry_exporter(exporter: TelemetryExporter) -> None:
    """Register a custom telemetry exporter on the global client."""
    get_telemetry_client().register_exporter(exporter)


def clear_telemetry_exporters() -> None:
    """Remove all custom exporters from the global client."""
    get_telemetry_client().clear_exporters()
