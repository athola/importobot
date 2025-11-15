"""Security monitoring and alerting system.

Implements event capture, anomaly detection, alert channels, and threat
intelligence hooks for Importobot deployments.
"""

from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from importobot.exceptions import ImportobotError
from importobot.utils.runtime_paths import get_runtime_subdir

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events."""

    CREDENTIAL_DETECTED = "credential_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ANOMALY_DETECTED = "anomaly_detected"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_BREACH = "security_breach"
    THREAT_INTELLIGENCE = "threat_intelligence"
    COMPLIANCE_VIOLATION = "compliance_violation"
    CONFIGURATION_CHANGE = "configuration_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class ThreatSeverity(Enum):
    """Threat severity levels."""

    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __lt__(self, other: object) -> bool:
        """Enable less-than comparison."""
        if isinstance(other, ThreatSeverity):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other: object) -> bool:
        """Enable less-than-or-equal comparison."""
        if isinstance(other, ThreatSeverity):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        """Enable greater-than comparison."""
        if isinstance(other, ThreatSeverity):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        """Enable greater-than-or-equal comparison."""
        if isinstance(other, ThreatSeverity):
            return self.value >= other.value
        return NotImplemented

    def to_string(self) -> str:
        """Convert severity to lowercase string for serialization."""
        return self.name.lower()


class MonitoringStatus(Enum):
    """Monitoring system status."""

    ACTIVE = "active"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class SecurityEvent:
    """Security event record."""

    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: SecurityEventType = SecurityEventType.SUSPICIOUS_ACTIVITY
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    source: str = ""
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    resource_affected: str | None = None
    tags: list[str] = field(default_factory=list)
    false_positive: bool = False
    investigated: bool = False
    resolved: bool = False
    resolution_notes: str | None = None
    correlation_id: UUID | None = None


@dataclass
class ThreatIntelligence:
    """Threat intelligence data."""

    indicator: str
    indicator_type: str  # ip, domain, hash, url, etc.
    threat_types: list[str]
    confidence: float
    first_seen: datetime
    last_seen: datetime
    source: str
    severity: ThreatSeverity
    description: str
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


class SecurityMonitoringError(ImportobotError):
    """Security monitoring system errors."""

    pass


class EventCollector(ABC):
    """Abstract base class for event collectors."""

    @abstractmethod
    def collect_events(self) -> list[SecurityEvent]:
        """Collect security events."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if collector is healthy."""
        pass


class AlertChannel(ABC):
    """Abstract base class for alert channels."""

    @abstractmethod
    def send_alert(self, event: SecurityEvent) -> bool:
        """Send alert for security event."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test alert channel connectivity."""
        pass


class AnomalyDetector:
    """Machine learning-based anomaly detection for security events."""

    def __init__(self) -> None:
        """Initialize anomaly detector."""
        self.baseline_stats: dict[str, Any] = {}
        self.event_patterns: dict[str, Any] = {}
        self.learning_enabled = True
        self.anomaly_threshold = 0.85  # Confidence threshold

    def analyze_events(self, events: list[SecurityEvent]) -> list[SecurityEvent]:
        """Analyze events for anomalies."""
        anomalies: list[SecurityEvent] = []

        if not self.learning_enabled:
            return anomalies

        # Extract patterns from current events
        current_patterns = self._extract_patterns(events)

        # Compare with baseline
        for event in events:
            anomaly_score = self._calculate_anomaly_score(event, current_patterns)
            if anomaly_score >= self.anomaly_threshold:
                anomaly_event = SecurityEvent(
                    event_type=SecurityEventType.ANOMALY_DETECTED,
                    severity=self._severity_from_score(anomaly_score),
                    description=(
                        f"Anomalous activity detected (score: {anomaly_score:.2f})"
                    ),
                    details={
                        "anomaly_score": anomaly_score,
                        "original_event_id": str(event.id),
                        "pattern_deviation": self._explain_deviation(
                            event, current_patterns
                        ),
                    },
                    source="anomaly_detector",
                    correlation_id=event.id,
                )
                anomalies.append(anomaly_event)

        return anomalies

    def _extract_patterns(self, events: list[SecurityEvent]) -> dict[str, Any]:
        """Extract statistical patterns from events."""
        patterns: dict[str, Any] = {
            "event_types": {},
            "severity_distribution": {},
            "source_distribution": {},
            "hourly_distribution": {},
            "time_between_events": [],
        }

        # Explicit type hints for nested dictionaries
        event_types: dict[str, int] = patterns["event_types"]
        severity_dist: dict[str, int] = patterns["severity_distribution"]
        source_dist: dict[str, int] = patterns["source_distribution"]
        hourly_dist: dict[int, int] = patterns["hourly_distribution"]

        for i, event in enumerate(events):
            # Event type frequency
            event_type = event.event_type.value
            event_types[event_type] = event_types.get(event_type, 0) + 1
            description_token = (
                event.description.lower().strip().replace(" ", "_").replace("-", "_")
            )
            if description_token:
                event_types[description_token] = (
                    event_types.get(description_token, 0) + 1
                )

            # Severity distribution
            severity = event.severity.to_string()
            severity_dist[severity] = severity_dist.get(severity, 0) + 1

            # Source distribution
            source = event.source
            source_dist[source] = source_dist.get(source, 0) + 1

            # Hourly distribution
            hour = event.timestamp.hour
            hourly_dist[hour] = hourly_dist.get(hour, 0) + 1

            # Time between events
            if i > 0:
                time_diff = (event.timestamp - events[i - 1].timestamp).total_seconds()
                patterns["time_between_events"].append(time_diff)

        return patterns

    def _calculate_anomaly_score(
        self, event: SecurityEvent, current_patterns: dict[str, Any]
    ) -> float:
        """Calculate anomaly score for an event."""
        score = 0.0

        # Check for unusual event types
        event_type = event.event_type.value
        if event_type in self.baseline_stats.get("event_types", {}):
            baseline_freq = self.baseline_stats["event_types"][event_type]
            current_freq = current_patterns["event_types"].get(event_type, 0)
            if current_freq > baseline_freq * 3:  # 3x increase
                score += 0.4
        else:
            # New event type
            score += 0.3

        # Check for unusual severity patterns
        if event.severity == ThreatSeverity.CRITICAL:
            score += 0.3

        # Check for unusual sources
        if event.source not in self.baseline_stats.get("source_distribution", {}):
            score += 0.2

        # Check time-based anomalies
        hour = event.timestamp.hour
        if hour in self.baseline_stats.get("hourly_distribution", {}):
            baseline_hourly = self.baseline_stats["hourly_distribution"][hour]
            current_hourly = current_patterns["hourly_distribution"].get(hour, 0)
            if current_hourly > baseline_hourly * 5:  # 5x increase
                score += 0.3

        return min(score, 1.0)

    def _severity_from_score(self, score: float) -> ThreatSeverity:
        """Convert anomaly score to threat severity."""
        if score >= 0.9:
            return ThreatSeverity.CRITICAL
        elif score >= 0.8:
            return ThreatSeverity.HIGH
        elif score >= 0.7:
            return ThreatSeverity.MEDIUM
        else:
            return ThreatSeverity.LOW

    def _explain_deviation(
        self, event: SecurityEvent, current_patterns: dict[str, Any]
    ) -> str:
        """Explain why an event is considered anomalous."""
        explanations = []

        event_type = event.event_type.value
        if event_type in self.baseline_stats.get("event_types", {}):
            baseline_freq = self.baseline_stats["event_types"][event_type]
            current_freq = current_patterns["event_types"].get(event_type, 0)
            if current_freq > baseline_freq * 3:
                multiplier = current_freq / baseline_freq
                explanations.append(
                    f"Event type frequency increased by {multiplier:.1f}x"
                )

        if event.source not in self.baseline_stats.get("source_distribution", {}):
            explanations.append(f"New event source: {event.source}")

        if explanations:
            return "; ".join(explanations)
        return "Pattern deviation detected"

    def update_baseline(self, events: list[SecurityEvent]) -> None:
        """Update baseline patterns with new data."""
        new_patterns = self._extract_patterns(events)

        # Smooth update (weighted average)
        weight = 0.3  # Weight for new data
        for key in new_patterns:
            if key not in self.baseline_stats:
                self.baseline_stats[key] = new_patterns[key]
            elif isinstance(new_patterns[key], dict):
                for sub_key, value in new_patterns[key].items():
                    if sub_key in self.baseline_stats[key]:
                        self.baseline_stats[key][sub_key] = (
                            self.baseline_stats[key][sub_key] * (1 - weight)
                            + value * weight
                        )
                    else:
                        self.baseline_stats[key][sub_key] = value


class ThreatIntelligenceManager:
    """Threat intelligence management and correlation."""

    def __init__(self) -> None:
        """Initialize threat intelligence manager."""
        self.indicators: dict[str, ThreatIntelligence] = {}
        self.sources: dict[str, Any] = {}
        self.last_update = datetime.now(timezone.utc)
        self.update_interval = timedelta(hours=1)

    def add_indicator(self, indicator: ThreatIntelligence) -> None:
        """Add threat intelligence indicator."""
        self.indicators[indicator.indicator] = indicator
        logger.debug(f"Added threat indicator: {indicator.indicator}")

    def check_event(self, event: SecurityEvent) -> list[ThreatIntelligence]:
        """Check event against threat intelligence."""
        matches = []

        # Check IP addresses
        if event.ip_address and event.ip_address in self.indicators:
            matches.append(self.indicators[event.ip_address])

        # Check user agents
        if event.user_agent:
            matches.extend(
                indicator
                for indicator in self.indicators.values()
                if indicator.indicator_type == "user_agent"
                and indicator.indicator in event.user_agent
            )

        # Check descriptions and details
        event_text = f"{event.description} {json.dumps(event.details)}".lower()
        matches.extend(
            indicator
            for indicator in self.indicators.values()
            if indicator.indicator_type in {"hash", "url", "domain"}
            and indicator.indicator.lower() in event_text
        )

        return matches

    def is_expired(self) -> bool:
        """Check if threat intelligence needs updating."""
        return datetime.now(timezone.utc) - self.last_update > self.update_interval

    def cleanup_expired(self) -> None:
        """Remove expired threat intelligence."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        expired = [
            key
            for key, indicator in self.indicators.items()
            if indicator.last_seen < cutoff
        ]

        for key in expired:
            del self.indicators[key]
            logger.debug(f"Removed expired threat indicator: {key}")


class SecurityMonitor:
    """Main security monitoring system."""

    def __init__(self, storage_path: str | Path | None = None):
        """Initialize security monitor."""
        if storage_path is not None:
            self.storage_path = Path(storage_path)
            self.storage_path.mkdir(parents=True, exist_ok=True)
        else:
            self.storage_path = get_runtime_subdir("security_monitoring")

        self.event_collectors: list[EventCollector] = []
        self.alert_channels: list[AlertChannel] = []
        self.anomaly_detector = AnomalyDetector()
        self.threat_intel = ThreatIntelligenceManager()

        self.events: list[SecurityEvent] = []
        self.status = MonitoringStatus.ACTIVE
        self.running = False

        self._lock = threading.Lock()
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Configuration
        self.monitoring_interval = 30  # seconds
        self.max_events = 10000
        self.auto_cleanup_days = 90

        # Load existing data
        self._load_events()

    def add_event_collector(self, collector: EventCollector) -> None:
        """Add an event collector."""
        self.event_collectors.append(collector)
        logger.info(f"Added event collector: {type(collector).__name__}")

    def add_alert_channel(self, channel: AlertChannel) -> None:
        """Add an alert channel."""
        self.alert_channels.append(channel)
        logger.info(f"Added alert channel: {type(channel).__name__}")

    def create_event(
        self,
        event_type: SecurityEventType,
        severity: ThreatSeverity,
        description: str,
        source: str = "",
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        resource_affected: str | None = None,
        tags: list[str] | None = None,
    ) -> SecurityEvent:
        """Create and process a new security event."""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            source=source,
            details=details or {},
            user_id=user_id,
            ip_address=ip_address,
            resource_affected=resource_affected,
            tags=tags or [],
        )

        # Check against threat intelligence
        threat_matches = self.threat_intel.check_event(event)
        if threat_matches:
            event.details["threat_intelligence_matches"] = [
                {
                    "indicator": match.indicator,
                    "threat_types": match.threat_types,
                    "confidence": match.confidence,
                    "source": match.source,
                }
                for match in threat_matches
            ]
            # Upgrade severity if threat intelligence indicates high risk
            if any(
                match.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]
                for match in threat_matches
            ):
                event.severity = max(event.severity, ThreatSeverity.HIGH)

        self._process_event(event)
        return event

    def _process_event(self, event: SecurityEvent) -> None:
        """Process a security event."""
        with self._lock:
            self.events.append(event)

            # Maintain event limit
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events :]

        # Send alerts for high-severity events
        if event.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]:
            self._send_alerts(event)

        # Save to storage
        self._save_event(event)

        logger.info(f"Security event: {event.event_type.value} - {event.description}")

    def _send_alerts(self, event: SecurityEvent) -> None:
        """Send alerts through all configured channels."""
        for channel in self.alert_channels:
            self._send_alert(channel, event)

    def _send_alert(self, channel: AlertChannel, event: SecurityEvent) -> None:
        """Send an alert through a single channel with consistent logging."""
        try:
            success = channel.send_alert(event)
            if not success:
                logger.warning("Alert channel failed: %s", type(channel).__name__)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Alert channel error: %s", exc)

    def _monitor_loop(self) -> None:
        """Run the monitoring loop."""
        logger.info("Security monitoring started")

        while not self._stop_event.wait(self.monitoring_interval):
            if not self.running:
                break

            try:
                self._collect_and_analyze()
            except Exception as exc:
                logger.error(f"Monitoring loop error: {exc}")

        logger.info("Security monitoring stopped")

    def _collect_and_analyze(self) -> None:
        """Collect events and run analysis."""
        all_new_events = []

        # Collect events from all collectors
        for collector in self.event_collectors:
            if not collector.is_healthy():
                logger.warning(f"Collector unhealthy: {type(collector).__name__}")
                continue

            try:
                new_events = collector.collect_events()
                all_new_events.extend(new_events)
            except Exception as exc:
                logger.error(f"Event collection error: {exc}")

        # Process new events
        for event in all_new_events:
            self._process_event(event)

        # Run anomaly detection
        if all_new_events:
            anomalies = self.anomaly_detector.analyze_events(all_new_events)
            for anomaly in anomalies:
                self._process_event(anomaly)

        # Update anomaly detector baseline
        if all_new_events:
            self.anomaly_detector.update_baseline(all_new_events)

        # Cleanup old events
        self._cleanup_old_events()

        # Update threat intelligence if needed
        if self.threat_intel.is_expired():
            self._update_threat_intelligence()

    def start_monitoring(self) -> None:
        """Start security monitoring."""
        with self._lock:
            if self.running:
                return

            self.running = True
            self.status = MonitoringStatus.ACTIVE
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, name="SecurityMonitor", daemon=True
            )
            self._monitor_thread.start()

            logger.info("Started security monitoring")

    def stop_monitoring(self) -> None:
        """Stop security monitoring."""
        with self._lock:
            if not self.running:
                return

            self.running = False
            self.status = MonitoringStatus.PAUSED
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=10)

            logger.info("Stopped security monitoring")

    def get_events(
        self,
        event_type: SecurityEventType | None = None,
        severity: ThreatSeverity | None = None,
        source: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        """Get filtered events."""
        with self._lock:
            filtered_events = self.events

            if event_type:
                filtered_events = [
                    e for e in filtered_events if e.event_type == event_type
                ]

            if severity:
                filtered_events = [e for e in filtered_events if e.severity == severity]

            if source:
                filtered_events = [e for e in filtered_events if e.source == source]

            if start_time:
                filtered_events = [
                    e for e in filtered_events if e.timestamp >= start_time
                ]

            if end_time:
                filtered_events = [
                    e for e in filtered_events if e.timestamp <= end_time
                ]

            # Sort by timestamp descending
            filtered_events.sort(key=lambda e: e.timestamp, reverse=True)

            return filtered_events[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        with self._lock:
            total_events = len(self.events)
            last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            last_24h_events = [e for e in self.events if e.timestamp >= last_24h]

            # Event type distribution
            event_types: dict[str, int] = {}
            for event in self.events:
                event_type = event.event_type.value
                event_types[event_type] = event_types.get(event_type, 0) + 1

            # Severity distribution
            severities: dict[str, int] = {}
            for event in self.events:
                severity = event.severity.to_string()
                severities[severity] = severities.get(severity, 0) + 1

            return {
                "total_events": total_events,
                "events_last_24h": len(last_24h_events),
                "monitoring_status": self.status.value,
                "collectors_count": len(self.event_collectors),
                "alert_channels_count": len(self.alert_channels),
                "event_types": event_types,
                "severity_distribution": severities,
                "threat_indicators": len(self.threat_intel.indicators),
                "last_event": self.events[-1].timestamp.isoformat()
                if self.events
                else None,
            }

    def _cleanup_old_events(self) -> None:
        """Clean up old events."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.auto_cleanup_days)

        with self._lock:
            original_count = len(self.events)
            self.events = [e for e in self.events if e.timestamp >= cutoff]
            removed_count = original_count - len(self.events)

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old events")

        # Cleanup threat intelligence
        self.threat_intel.cleanup_expired()

    def _update_threat_intelligence(self) -> None:
        """Update threat intelligence (placeholder)."""
        # This would be implemented to fetch from actual threat feeds
        logger.debug("Updating threat intelligence")
        self.threat_intel.last_update = datetime.now(timezone.utc)

    def _save_event(self, event: SecurityEvent) -> None:
        """Save event to storage."""
        try:
            events_file = self.storage_path / "events.jsonl"
            with open(events_file, "a", encoding="utf-8") as f:
                event_data = {
                    "id": str(event.id),
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type.value,
                    "severity": event.severity.to_string(),
                    "source": event.source,
                    "description": event.description,
                    "details": event.details,
                    "user_id": event.user_id,
                    "ip_address": event.ip_address,
                    "resource_affected": event.resource_affected,
                    "tags": event.tags,
                    "false_positive": event.false_positive,
                    "investigated": event.investigated,
                    "resolved": event.resolved,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                }
                f.write(json.dumps(event_data) + "\n")
        except Exception as exc:
            logger.error(f"Failed to save event: {exc}")

    def _load_events(self) -> None:
        """Load events from storage."""
        try:
            events_file = self.storage_path / "events.jsonl"
            if events_file.exists():
                with open(events_file, encoding="utf-8") as f:
                    for line in f:
                        event = self._deserialize_event(line)
                        if event:
                            self.events.append(event)

                logger.info(f"Loaded {len(self.events)} events from storage")
        except Exception as exc:
            logger.warning(f"Failed to load events: {exc}")

    def _deserialize_event(self, line: str) -> SecurityEvent | None:
        """Deserialize a stored event line with consistent error handling."""
        try:
            event_data = json.loads(line.strip())
            severity_value = event_data["severity"]
            try:
                if isinstance(severity_value, str):
                    try:
                        severity = ThreatSeverity[severity_value.upper()]
                    except (KeyError, AttributeError):
                        severity = ThreatSeverity(int(severity_value))
                else:
                    severity = ThreatSeverity(severity_value)
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Unknown severity %s: %s", severity_value, exc)
                return None

            return SecurityEvent(
                id=UUID(event_data["id"]),
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                event_type=SecurityEventType(event_data["event_type"]),
                severity=severity,
                source=event_data["source"],
                description=event_data["description"],
                details=event_data["details"],
                user_id=event_data["user_id"],
                ip_address=event_data["ip_address"],
                resource_affected=event_data["resource_affected"],
                tags=event_data["tags"],
                false_positive=event_data["false_positive"],
                investigated=event_data["investigated"],
                resolved=event_data["resolved"],
                correlation_id=UUID(event_data["correlation_id"])
                if event_data["correlation_id"]
                else None,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to load event: %s", exc)
            return None


# Global security monitor instance
_security_monitor: SecurityMonitor | None = None
_monitor_lock = threading.Lock()


def get_security_monitor(storage_path: str | Path | None = None) -> SecurityMonitor:
    """Get the global security monitor instance."""
    global _security_monitor  # noqa: PLW0603

    with _monitor_lock:
        if _security_monitor is None:
            _security_monitor = SecurityMonitor(storage_path)
        return _security_monitor


def reset_security_monitor() -> None:
    """Reset the global security monitor (for testing)."""
    global _security_monitor  # noqa: PLW0603

    with _monitor_lock:
        if _security_monitor is not None:
            _security_monitor.stop_monitoring()
        _security_monitor = None


__all__ = [
    "AlertChannel",
    "AnomalyDetector",
    "EventCollector",
    "MonitoringStatus",
    "SecurityEvent",
    "SecurityEventType",
    "SecurityMonitor",
    "SecurityMonitoringError",
    "ThreatIntelligence",
    "ThreatIntelligenceManager",
    "ThreatSeverity",
    "get_security_monitor",
    "reset_security_monitor",
]
