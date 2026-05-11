"""SIEM connector abstractions for Splunk/Elastic forwarding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from importobot.utils.logging import get_logger

logger = get_logger(__name__)


class BaseSIEMConnector(Protocol):
    """Protocol for SIEM connectors used by SIEMManager."""

    def send_event(self, event: dict[str, Any]) -> None:
        """Handle serialized events before they reach the backend."""
        ...


@dataclass
class SplunkHECConnector:
    """Simplified Splunk HEC connector (logs payloads locally)."""

    endpoint: str
    token: str

    def send_event(self, event: dict[str, Any]) -> None:
        """Log the event destined for Splunk HEC (simulated)."""
        logger.info("Splunk HEC %s :: %s", self.endpoint, event)


@dataclass
class ElasticConnector:
    """Simplified Elastic SIEM connector."""

    endpoint: str
    api_key: str

    def send_event(self, event: dict[str, Any]) -> None:
        """Log the event destined for Elastic SIEM (simulated)."""
        logger.info("Elastic SIEM %s :: %s", self.endpoint, event)


@dataclass
class SIEMManager:
    """Coordinates sending of structured events to multiple SIEM backends."""

    connectors: list[BaseSIEMConnector] = field(default_factory=list)

    def add_connector(self, connector: BaseSIEMConnector) -> None:
        """Register a connector that should receive future events."""
        self.connectors.append(connector)

    def emit_security_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send an enriched event to all connectors."""
        enriched = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        for connector in self.connectors:
            connector.send_event(enriched)
        logger.debug(
            "Dispatched SIEM event %s to %d connectors",
            event_type,
            len(self.connectors),
        )
