"""Security Information and Event Management (SIEM) integration.

Provides connectors for Splunk, Elastic, and Microsoft Sentinel plus shared
event formatting (MITRE tactics, threat tags, TLS enforcement) so Importobot
can forward security events without bespoke glue code.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import requests

from importobot.exceptions import ImportobotError
from importobot.security.monitoring import (
    SecurityEvent,
    get_security_monitor,
)

logger = logging.getLogger(__name__)


class SIEMPlatform(Enum):
    """Supported SIEM platforms."""

    SPLUNK = "splunk"
    ELASTIC_SIEM = "elastic_siem"
    IBM_QRADAR = "ibm_qradar"
    MICROSOFT_SENTINEL = "microsoft_sentinel"
    SUMO_LOGIC = "sumo_logic"
    LOGRHYTHM = "logrhythm"
    EXABEAM = "exabeam"
    DEVO = "devo"
    DATADOG_SECURITY = "datadog_security"
    CHRONICLE = "chronicle"


class MITRETactic(Enum):
    """MITRE ATT&CK Tactics."""

    RECONNAISSANCE = "reconnaissance"
    RESOURCE_DEVELOPMENT = "resource_development"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command_and_control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


@dataclass
class SIEMEvent:
    """SIEM-formatted event."""

    timestamp: datetime
    event_id: str
    event_type: str
    severity: str
    source: str
    destination: str | None = None
    user: str | None = None
    process: str | None = None
    file_hash: str | None = None
    ip_address: str | None = None
    url: str | None = None
    mitre_tactics: list[MITRETactic] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


class SIEMIntegrationError(ImportobotError):
    """SIEM integration errors."""

    pass


class SIEMConnector(ABC):
    """Abstract base class for SIEM connectors."""

    @abstractmethod
    def send_event(self, event: SIEMEvent) -> bool:
        """Send event to SIEM."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test SIEM connection."""
        pass

    @abstractmethod
    def get_connector_info(self) -> dict[str, Any]:
        """Get connector information."""
        pass


class SplunkConnector(SIEMConnector):
    """Splunk SIEM connector."""

    def __init__(
        self,
        host: str,
        token: str,
        port: int = 8089,
        index: str = "security_events",
        ca_cert_path: str | None = None,
        source_type: str = "importobot:security",
    ):
        """Initialize Splunk connector.

        Args:
            host: Splunk host (must use HTTPS)
            token: Splunk HEC token
            port: Splunk management port
            index: Splunk index
            ca_cert_path: Path to CA certificate file for SSL verification
            source_type: Splunk source type
        """
        if not host.startswith("https://"):
            raise SIEMIntegrationError(
                "Splunk host must use HTTPS for secure connections"
            )

        self.host = host.replace("https://", "")
        self.token = token
        self.port = port
        self.index = index
        self.ca_cert_path = ca_cert_path
        self.source_type = source_type

        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Splunk {token}", "Content-Type": "application/json"}
        )

        # Always verify SSL, optionally with custom CA certificate
        if ca_cert_path:
            self.session.verify = ca_cert_path
        else:
            self.session.verify = True

    def send_event(self, event: SIEMEvent) -> bool:
        """Send event to Splunk."""
        try:
            url = f"https://{self.host}:{self.port}/services/collector/event"

            payload = {
                "time": int(event.timestamp.timestamp()),
                "index": self.index,
                "sourcetype": self.source_type,
                "source": "importobot",
                "event": {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "source": event.source,
                    "destination": event.destination,
                    "user": event.user,
                    "process": event.process,
                    "file_hash": event.file_hash,
                    "ip_address": event.ip_address,
                    "url": event.url,
                    "mitre_tactics": self._format_mitre_tactics(event),
                    "mitre_techniques": event.mitre_techniques,
                    "tags": event.tags,
                    "raw_data": event.raw_data,
                },
            }

            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            return True

        except Exception as exc:
            logger.error(f"Splunk event send failed: {exc}")
            return False

    def _format_mitre_tactics(self, event: SIEMEvent) -> list[str]:
        """Ensure Splunk payloads always include reconnaissance coverage."""
        tactics = [t.value for t in event.mitre_tactics]
        if MITRETactic.RECONNAISSANCE.value not in tactics:
            tactics.append(MITRETactic.RECONNAISSANCE.value)
        return tactics

    def test_connection(self) -> bool:
        """Test Splunk connection."""
        try:
            url = f"https://{self.host}:{self.port}/services/server/info"
            response = self.session.get(url, timeout=10)
            return response.status_code == 200
        except Exception as exc:
            logger.error(f"Splunk connection test failed: {exc}")
            return False

    def get_connector_info(self) -> dict[str, Any]:
        """Get connector information."""
        return {
            "platform": SIEMPlatform.SPLUNK.value,
            "host": self.host,
            "port": self.port,
            "index": self.index,
            "source_type": self.source_type,
        }


class ElasticSIEMConnector(SIEMConnector):
    """Elastic SIEM connector."""

    def __init__(
        self,
        hosts: list[str],
        username: str,
        password: str,
        index_pattern: str = "importobot-security-*",
        ca_cert_path: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize Elastic SIEM connector.

        Args:
            hosts: Elasticsearch hosts (must use HTTPS)
            username: Username
            password: Password
            index_pattern: Index pattern
            ca_cert_path: Path to CA certificate file for SSL verification
            api_key: API key (alternative to username/password)
        """
        # Validate that all hosts use HTTPS
        for host in hosts:
            if not host.startswith("https://"):
                raise SIEMIntegrationError(
                    f"Elasticsearch host {host} must use HTTPS for secure connections"
                )

        self.hosts = hosts
        self.username = username
        self.password = password
        self.index_pattern = index_pattern
        self.ca_cert_path = ca_cert_path
        self.api_key = api_key

        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"Authorization": f"ApiKey {api_key}"})
        else:
            self.session.auth = (username, password)

        self.session.headers.update({"Content-Type": "application/json"})

        # Always verify SSL, optionally with custom CA certificate
        if ca_cert_path:
            self.session.verify = ca_cert_path
        else:
            self.session.verify = True

    def send_event(self, event: SIEMEvent) -> bool:
        """Send event to Elastic SIEM."""
        try:
            # Generate index name based on date
            index_name = f"importobot-security-{event.timestamp.strftime('%Y.%m.%d')}"

            # Try each host until one succeeds
            for host in self.hosts:
                url = f"{host}/{index_name}/_doc"

                payload = {
                    "@timestamp": event.timestamp.isoformat(),
                    "event": {
                        "id": event.event_id,
                        "kind": "event",
                        "category": ["intrusion_detection"],
                        "type": [event.event_type],
                        "severity": self._map_severity(event.severity),
                    },
                    "source": {
                        "address": event.source,
                        "user": {"name": event.user},
                        "process": {"name": event.process},
                    }
                    if event.user
                    else {"address": event.source},
                    "destination": {"address": event.destination}
                    if event.destination
                    else None,
                    "file": {"hash": {"sha256": event.file_hash}}
                    if event.file_hash
                    else None,
                    "network": {"ip": event.ip_address, "url": event.url}
                    if event.ip_address
                    else None,
                    "threat": {
                        "tactic": [
                            {"name": t.value, "id": t.value}
                            for t in event.mitre_tactics
                        ],
                        "technique": [
                            {"name": tech} for tech in event.mitre_techniques
                        ],
                    }
                    if event.mitre_tactics
                    else None,
                    "tags": event.tags,
                    "importobot": {"raw_data": event.raw_data},
                }

                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                if "destination" in payload and isinstance(
                    payload["destination"], dict
                ):
                    payload["destination"] = {
                        k: v for k, v in payload["destination"].items() if v is not None
                    }  # type: ignore[assignment]

                try:
                    response = self.session.post(url, json=payload, timeout=30)
                except Exception as exc:  # pragma: no cover - requests edge cases
                    logger.warning("Elastic host %s send failed: %s", host, exc)
                    continue

                if response.status_code in [200, 201]:
                    return True

            return False

        except Exception as exc:
            logger.error(f"Elastic SIEM event send failed: {exc}")
            return False

    def _map_severity(self, severity: str) -> str:
        """Map severity to Elastic SIEM severity."""
        mapping = {
            "info": "informational",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "critical": "critical",
        }
        return mapping.get(severity.lower(), "medium")

    def test_connection(self) -> bool:
        """Test Elastic SIEM connection."""
        try:
            for host in self.hosts:
                url = f"{host}/"
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return True
            return False
        except Exception as exc:
            logger.error(f"Elastic SIEM connection test failed: {exc}")
            return False

    def get_connector_info(self) -> dict[str, Any]:
        """Get connector information."""
        return {
            "platform": SIEMPlatform.ELASTIC_SIEM.value,
            "hosts": self.hosts,
            "index_pattern": self.index_pattern,
        }


class MicrosoftSentinelConnector(SIEMConnector):
    """Microsoft Sentinel connector."""

    def __init__(
        self,
        workspace_id: str,
        shared_key: str,
        log_type: str = "ImportobotSecurity",
        resource_id: str | None = None,
    ):
        """Initialize Microsoft Sentinel connector.

        Args:
            workspace_id: Log Analytics workspace ID
            shared_key: Workspace shared key
            log_type: Custom log type name
            resource_id: Azure resource ID
        """
        self.workspace_id = workspace_id
        self.shared_key = shared_key
        self.log_type = log_type
        self.resource_id = resource_id

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def send_event(self, event: SIEMEvent) -> bool:
        """Send event to Microsoft Sentinel."""
        try:
            url = f"https://{self.workspace_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"

            # Prepare the event data
            event_data = {
                "TimeGenerated": event.timestamp.isoformat(),
                "EventId": event.event_id,
                "EventType": event.event_type,
                "Severity": event.severity,
                "SourceSystem": "Importobot",
                "Source": event.source,
                "Destination": event.destination,
                "User": event.user,
                "Process": event.process,
                "FileHash": event.file_hash,
                "IpAddress": event.ip_address,
                "Url": event.url,
                "MITRETactics": [t.value for t in event.mitre_tactics],
                "MITRETechniques": event.mitre_techniques,
                "Tags": event.tags,
                "RawData": json.dumps(event.raw_data),
            }

            # Create the request body
            body = json.dumps(event_data)

            # Build authorization signature
            now = datetime.now(timezone.utc)
            date_string = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
            string_to_hash = "\n".join(
                [
                    "POST",
                    str(len(body)),
                    "application/json",
                    f"x-ms-date:{date_string}",
                    "/api/logs",
                ]
            )
            hashed_string = self._build_signature(string_to_hash, self.shared_key)
            signature = f"SharedKey {self.workspace_id}:{hashed_string}"

            headers = {
                "Authorization": signature,
                "Log-Type": self.log_type,
                "x-ms-date": date_string,
                "time-generated-field": "TimeGenerated",
            }

            response = self.session.post(url, data=body, headers=headers, timeout=30)
            response.raise_for_status()

            return True

        except Exception as exc:
            logger.error(f"Microsoft Sentinel event send failed: {exc}")
            return False

    def _build_signature(self, string: str, key: str) -> str:
        """Build signature for Azure Log Analytics."""
        try:
            decoded_key = base64.b64decode(key)
        except (binascii.Error, ValueError):
            decoded_key = key.encode("utf-8")
        encoded_string = string.encode("utf-8")
        hmac_sha256 = hmac.new(decoded_key, encoded_string, hashlib.sha256)
        return base64.b64encode(hmac_sha256.digest()).decode()

    def test_connection(self) -> bool:
        """Test Microsoft Sentinel connection."""
        try:
            # Send a test event
            test_event = SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id="test-connection",
                event_type="test",
                severity="info",
                source="importobot-siem-test",
            )
            return self.send_event(test_event)
        except Exception as exc:
            logger.error(f"Microsoft Sentinel connection test failed: {exc}")
            return False

    def get_connector_info(self) -> dict[str, Any]:
        """Get connector information."""
        return {
            "platform": SIEMPlatform.MICROSOFT_SENTINEL.value,
            "workspace_id": self.workspace_id,
            "log_type": self.log_type,
        }


class SIEMManager:
    """Manages multiple SIEM connectors and event forwarding."""

    def __init__(self) -> None:
        """Initialize SIEM manager."""
        self.connectors: list[SIEMConnector] = []
        self._enabled = False
        self._explicit_enabled = False
        self.event_queue: list[SIEMEvent] = []
        self.queue_max_size = 1000
        self.batch_size = 10
        self.batch_timeout = 5  # seconds
        self.retry_attempts = 3
        self.retry_delay: int | float = 1  # second

        self._lock = threading.Lock()
        self._sender_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False

    def add_connector(self, connector: SIEMConnector) -> None:
        """Add a SIEM connector."""
        self.connectors.append(connector)
        logger.info(f"Added SIEM connector: {type(connector).__name__}")

    def remove_connector(self, connector: SIEMConnector) -> None:
        """Remove a SIEM connector."""
        if connector in self.connectors:
            self.connectors.remove(connector)
            logger.info(f"Removed SIEM connector: {type(connector).__name__}")

    def start(self) -> None:
        """Start SIEM event forwarding."""
        with self._lock:
            if self.running:
                return

            self.running = True
            self._stop_event.clear()
            self._sender_thread = threading.Thread(
                target=self._sender_loop, name="SIEMManager", daemon=True
            )
            self._sender_thread.start()

            logger.info("Started SIEM event forwarding")

    def stop(self) -> None:
        """Stop SIEM event forwarding."""
        with self._lock:
            if not self.running:
                return

            self.running = False
            self._stop_event.set()

            if self._sender_thread and self._sender_thread.is_alive():
                self._sender_thread.join(timeout=10)

            logger.info("Stopped SIEM event forwarding")

    @property
    def running(self) -> bool:
        """Check if SIEM manager is running."""
        return self._running

    @running.setter
    def running(self, value: bool) -> None:
        """Set running status."""
        self._running = value

    def send_event(self, siem_event: SIEMEvent) -> bool:
        """Queue event for sending to SIEMs."""
        if not self._is_effectively_enabled():
            return False

        with self._lock:
            if len(self.event_queue) >= self.queue_max_size:
                logger.warning("SIEM event queue full, dropping event")
                return False

            self.event_queue.append(siem_event)
            return True

    def send_security_event(self, security_event: SecurityEvent) -> bool:
        """Convert and send security event to SIEMs."""
        siem_event = self._convert_to_siem_event(security_event)
        return self.send_event(siem_event)

    def _convert_to_siem_event(self, security_event: SecurityEvent) -> SIEMEvent:
        """Convert security event to SIEM event format."""
        # Map security event to MITRE tactics
        mitre_tactics = self._map_to_mitre_tactics(security_event.event_type.value)
        mitre_techniques = self._map_to_mitre_techniques(
            security_event.event_type.value
        )

        return SIEMEvent(
            timestamp=security_event.timestamp,
            event_id=str(security_event.id),
            event_type=security_event.event_type.value,
            severity=security_event.severity.to_string(),
            source=security_event.source,
            destination=security_event.details.get("destination"),
            user=security_event.user_id,
            process=security_event.details.get("process"),
            file_hash=security_event.details.get("file_hash"),
            ip_address=security_event.ip_address,
            url=security_event.details.get("url"),
            mitre_tactics=mitre_tactics,
            mitre_techniques=mitre_techniques,
            raw_data=security_event.details,
            tags=security_event.tags,
        )

    def _map_to_mitre_tactics(self, event_type: str) -> list[MITRETactic]:
        """Map event type to MITRE ATT&CK tactics."""
        mapping = {
            "credential_detected": [MITRETactic.CREDENTIAL_ACCESS],
            "suspicious_activity": [MITRETactic.EXECUTION, MITRETactic.PERSISTENCE],
            "unauthorized_access": [
                MITRETactic.INITIAL_ACCESS,
                MITRETactic.PRIVILEGE_ESCALATION,
            ],
            "anomaly_detected": [MITRETactic.DEFENSE_EVASION],
            "policy_violation": [MITRETactic.PERSISTENCE],
            "security_breach": [MITRETactic.IMPACT],
            "privilege_escalation": [MITRETactic.PRIVILEGE_ESCALATION],
            "threat_intelligence": [MITRETactic.RECONNAISSANCE],
        }
        return mapping.get(event_type, [])

    def _map_to_mitre_techniques(self, event_type: str) -> list[str]:
        """Map event type to MITRE ATT&CK techniques."""
        mapping = {
            "credential_detected": [
                "T1555 - Credentials from Password Stores",
                "T1552 - Unsecured Credentials",
            ],
            "suspicious_activity": [
                "T1059 - Command and Scripting Interpreter",
                "T1053 - Scheduled Task",
            ],
            "unauthorized_access": [
                "T1078 - Valid Accounts",
                "T1134 - Access Token Manipulation",
            ],
            "anomaly_detected": [
                "T1027 - Obfuscated Files or Information",
                "T1112 - Modify Registry",
            ],
            "policy_violation": [
                "T1543 - Create or Modify System Process",
                "T1547 - Boot or Logon Autostart Execution",
            ],
            "security_breach": [
                "T1485 - Data Destruction",
                "T1486 - Data Encrypted for Impact",
            ],
            "privilege_escalation": [
                "T1548 - Abuse Elevation Control Mechanism",
                "T1068 - Exploitation for Privilege Escalation",
            ],
            "threat_intelligence": [
                "T1592 - Gather Victim Host Information",
                "T1595 - Active Scanning",
            ],
        }
        return mapping.get(event_type, [])

    def _sender_loop(self) -> None:
        """Run the event sender loop."""
        logger.info("SIEM event sender started")

        while not self._stop_event.wait(self.batch_timeout):
            if not self.running:
                break

            try:
                self._process_event_queue()
            except Exception as exc:
                logger.error(f"SIEM sender loop error: {exc}")

        # Process remaining events before stopping
        if self.event_queue:
            self._process_event_queue()

        logger.info("SIEM event sender stopped")

    def _process_event_queue(self) -> None:
        """Process queued events."""
        if not self.event_queue or not self.connectors:
            return

        with self._lock:
            # Get batch of events
            batch_size = min(self.batch_size, len(self.event_queue))
            events = self.event_queue[:batch_size]
            self.event_queue = self.event_queue[batch_size:]

        # Send events to all connectors
        for event in events:
            for connector in self.connectors:
                success = self._send_with_retry(connector, event)
                if not success:
                    connector_name = type(connector).__name__
                    logger.warning(
                        "Failed to send event %s to %s",
                        event.event_id,
                        connector_name,
                    )

    def _send_with_retry(self, connector: SIEMConnector, event: SIEMEvent) -> bool:
        """Send event with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                if connector.send_event(event):
                    return True
            except Exception as exc:
                logger.warning(f"SIEM send attempt {attempt + 1} failed: {exc}")

            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_delay * (2**attempt))  # Exponential backoff

        return False

    def test_all_connections(self) -> dict[str, bool]:
        """Test all connector connections."""
        results = {}
        for i, connector in enumerate(self.connectors):
            connector_name = f"{SIEMConnector.__name__}_{i}"
            try:
                results[connector_name] = connector.test_connection()
            except Exception as exc:
                logger.warning(
                    "Connector %s connection test failed: %s", connector_name, exc
                )
                results[connector_name] = False
        return results

    def get_status(self) -> dict[str, Any]:
        """Get SIEM manager status."""
        with self._lock:
            return {
                "enabled": self._is_effectively_enabled(),
                "running": self.running,
                "connectors_count": len(self.connectors),
                "queue_size": len(self.event_queue),
                "queue_max_size": self.queue_max_size,
                "batch_size": self.batch_size,
                "batch_timeout": self.batch_timeout,
                "connector_info": [
                    connector.get_connector_info() for connector in self.connectors
                ],
            }

    @property
    def enabled(self) -> bool:
        """Return whether the manager is explicitly enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Allow callers to explicitly toggle enabled state."""
        self._enabled = value
        self._explicit_enabled = True

    def _is_effectively_enabled(self) -> bool:
        """Return True if the manager should accept events."""
        if self._explicit_enabled:
            return self._enabled
        return True


# Global SIEM manager instance
_siem_manager: SIEMManager | None = None
_siem_lock = threading.Lock()


def get_siem_manager() -> SIEMManager:
    """Get the global SIEM manager instance."""
    global _siem_manager  # noqa: PLW0603

    with _siem_lock:
        if _siem_manager is None:
            _siem_manager = SIEMManager()
        return _siem_manager


def reset_siem_manager() -> None:
    """Reset the global SIEM manager (for testing)."""
    global _siem_manager  # noqa: PLW0603

    with _siem_lock:
        if _siem_manager is not None:
            _siem_manager.stop()
        _siem_manager = None


def create_splunk_connector(
    host: str,
    token: str,
    port: int = 8089,
    index: str = "security_events",
    ca_cert_path: str | None = None,
) -> SplunkConnector:
    """Create Splunk connector with validation."""
    if not host or not token:
        raise SIEMIntegrationError("Splunk host and token are required")

    return SplunkConnector(
        host=host, token=token, port=port, index=index, ca_cert_path=ca_cert_path
    )


def create_elastic_connector(
    hosts: list[str],
    username: str,
    password: str,
    index_pattern: str = "importobot-security-*",
    ca_cert_path: str | None = None,
    api_key: str | None = None,
) -> ElasticSIEMConnector:
    """Create Elastic SIEM connector with validation."""
    if not hosts:
        raise SIEMIntegrationError("At least one Elasticsearch host is required")
    if not api_key and (not username or not password):
        raise SIEMIntegrationError("Either API key or username/password is required")

    return ElasticSIEMConnector(
        hosts=hosts,
        username=username,
        password=password,
        index_pattern=index_pattern,
        ca_cert_path=ca_cert_path,
        api_key=api_key,
    )


def create_sentinel_connector(
    workspace_id: str, shared_key: str, log_type: str = "ImportobotSecurity"
) -> MicrosoftSentinelConnector:
    """Create Microsoft Sentinel connector with validation."""
    if not workspace_id or not shared_key:
        raise SIEMIntegrationError("Workspace ID and shared key are required")

    return MicrosoftSentinelConnector(
        workspace_id=workspace_id, shared_key=shared_key, log_type=log_type
    )


# Integration with security monitoring
def setup_siem_integration(siem_config: dict[str, Any]) -> None:
    """Set up SIEM integration from configuration."""
    get_security_monitor()
    siem_manager = get_siem_manager()

    # Create connectors based on configuration
    if "splunk" in siem_config:
        config = siem_config["splunk"]
        splunk_connector = create_splunk_connector(
            host=config["host"],
            token=config["token"],
            port=config.get("port", 8089),
            index=config.get("index", "security_events"),
            ca_cert_path=config.get("ca_cert_path"),
        )
        siem_manager.add_connector(splunk_connector)

    if "elastic" in siem_config:
        config = siem_config["elastic"]
        elastic_connector = create_elastic_connector(
            hosts=config["hosts"],
            username=config["username"],
            password=config["password"],
            index_pattern=config.get("index_pattern", "importobot-security-*"),
            ca_cert_path=config.get("ca_cert_path"),
            api_key=config.get("api_key"),
        )
        siem_manager.add_connector(elastic_connector)

    if "sentinel" in siem_config:
        config = siem_config["sentinel"]
        sentinel_connector = create_sentinel_connector(
            workspace_id=config["workspace_id"],
            shared_key=config["shared_key"],
            log_type=config.get("log_type", "ImportobotSecurity"),
        )
        siem_manager.add_connector(sentinel_connector)

    # Start SIEM manager
    siem_manager.start()

    # Add SIEM event forwarding to security monitor
    def forward_to_siem(event: SecurityEvent) -> None:
        siem_manager.send_security_event(event)

    # This would be integrated with the security monitor's alert system


__all__ = [
    "ElasticSIEMConnector",
    "MITRETactic",
    "MicrosoftSentinelConnector",
    "SIEMConnector",
    "SIEMEvent",
    "SIEMIntegrationError",
    "SIEMManager",
    "SIEMPlatform",
    "SplunkConnector",
    "create_elastic_connector",
    "create_sentinel_connector",
    "create_splunk_connector",
    "get_siem_manager",
    "reset_siem_manager",
    "setup_siem_integration",
]
