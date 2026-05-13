"""SIEM connector abstractions for Splunk/Elastic forwarding.

PR #90 review C1: the connectors shipped here log events to stdout
rather than performing real HTTP forwarding. They are renamed to
``LoggingSplunkSink`` / ``LoggingElasticSink`` so callers cannot
mistake them for production-grade exports. The previous
``SplunkHECConnector`` / ``ElasticConnector`` names remain as aliases
for transitional compatibility but are scheduled for removal in 0.2.0.

Secret material (tokens, API keys) is wrapped in
:class:`~importobot.security.SecureString` with ``repr=False`` so
audit logs do not leak credentials through ``%s``-style formatters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from importobot.security import SecureString
from importobot.utils.logging import get_logger

logger = get_logger(__name__)


class BaseSIEMConnector(Protocol):
    """Protocol for SIEM connectors used by SIEMManager."""

    def send_event(self, event: dict[str, Any]) -> None:
        """Handle serialized events before they reach the backend."""
        ...


def _to_secure_string(value: Any) -> SecureString:
    """Coerce a plain ``str`` token into a :class:`SecureString`."""
    if isinstance(value, SecureString):
        return value
    return SecureString(value)


@dataclass
class LoggingSplunkSink:
    """Logging-only Splunk HEC sink (no network calls).

    NOT FOR PRODUCTION: every ``send_event`` call writes the payload to
    the local logger and returns. Wire up a real connector when audit
    events must reach a Splunk indexer.
    """

    endpoint: str
    token: SecureString | str = field(repr=False)

    def __post_init__(self) -> None:
        """Promote plaintext tokens to SecureString on construction."""
        if not isinstance(self.token, SecureString):
            self.token = _to_secure_string(self.token)

    def send_event(self, event: dict[str, Any]) -> None:
        """Log the event destined for Splunk HEC (simulated)."""
        logger.info("LoggingSplunkSink %s :: %s", self.endpoint, event)


@dataclass
class LoggingElasticSink:
    """Logging-only Elastic SIEM sink (no network calls).

    NOT FOR PRODUCTION: see :class:`LoggingSplunkSink`.
    """

    endpoint: str
    api_key: SecureString | str = field(repr=False)

    def __post_init__(self) -> None:
        """Promote plaintext keys to SecureString on construction."""
        if not isinstance(self.api_key, SecureString):
            self.api_key = _to_secure_string(self.api_key)

    def send_event(self, event: dict[str, Any]) -> None:
        """Log the event destined for Elastic SIEM (simulated)."""
        logger.info("LoggingElasticSink %s :: %s", self.endpoint, event)


# Backwards-compatible aliases (PR #90 review C1). Scheduled for
# removal in 0.2.0 - update callers to the explicit ``Logging*Sink``
# names so the simulated nature is impossible to miss at a glance.
SplunkHECConnector = LoggingSplunkSink
ElasticConnector = LoggingElasticSink


@dataclass
class SIEMManager:
    """Coordinates sending of structured events to multiple SIEM backends."""

    connectors: list[BaseSIEMConnector] = field(default_factory=list)

    def add_connector(self, connector: BaseSIEMConnector) -> None:
        """Register a connector that should receive future events."""
        self.connectors.append(connector)

    def emit_security_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send an enriched event to all connectors.

        Per-connector failures are caught and logged so a single broken
        sink cannot prevent later sinks from receiving the event
        (PR #90 review C1).
        """
        enriched = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        for connector in self.connectors:
            self._dispatch_one(connector, event_type, enriched)
        logger.debug(
            "Dispatched SIEM event %s to %d connectors",
            event_type,
            len(self.connectors),
        )

    @staticmethod
    def _dispatch_one(
        connector: BaseSIEMConnector,
        event_type: str,
        enriched: dict[str, Any],
    ) -> None:
        """Deliver one event and contain failures (PR #90 review C1)."""
        try:
            connector.send_event(enriched)
        except Exception as exc:
            logger.error(
                "SIEM connector %s failed to deliver %s: %s",
                type(connector).__name__,
                event_type,
                exc,
            )
