"""Tests for security monitoring and threat detection system.

This module provides comprehensive test coverage for the security monitoring
system including unit tests, integration tests, performance tests, and invariant
validation following TDD and BDD principles.
"""

from __future__ import annotations

import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from importobot.security.monitoring import (
    AlertChannel,
    AnomalyDetector,
    EventCollector,
    MonitoringStatus,
    SecurityEvent,
    SecurityEventType,
    SecurityMonitor,
    ThreatIntelligence,
    ThreatIntelligenceManager,
    ThreatSeverity,
    get_security_monitor,
    reset_security_monitor,
)


class TestSecurityEvent:
    """Test SecurityEvent dataclass behavior."""

    def test_event_creation_with_defaults(self) -> None:
        """Test security event creation with default values."""
        event = SecurityEvent(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.HIGH,
            description="Test event",
            source="test_module",
        )

        assert event.event_type.value == "credential_detected"
        assert event.severity.to_string() == "high"
        assert event.description == "Test event"
        assert event.source == "test_module"
        assert event.false_positive is False
        assert event.investigated is False
        assert event.resolved is False
        assert isinstance(event.id, type(uuid4()))
        assert isinstance(event.timestamp, datetime)

    def test_event_creation_with_all_fields(self) -> None:
        """Test security event creation with all fields specified."""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.CRITICAL,
            description="Critical security event",
            source="security_module",
            user_id="user123",
            ip_address="192.168.1.1",
            resource_affected="/etc/passwd",
            tags=["security", "critical"],
            details={"threat_type": "sql_injection"},
        )

        assert event.user_id == "user123"
        assert event.ip_address == "192.168.1.1"
        assert event.resource_affected == "/etc/passwd"
        assert "security" in event.tags
        assert "critical" in event.tags
        assert event.details["threat_type"] == "sql_injection"

    def test_event_serialization(self) -> None:
        """Test event serialization for storage."""
        event = SecurityEvent(
            event_type=SecurityEventType.ANOMALY_DETECTED,
            severity=ThreatSeverity.MEDIUM,
            description="Anomalous pattern detected",
            source="analyzer",
        )

        # Test that event can be serialized
        event_dict = {
            "id": str(event.id),
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "description": event.description,
            "source": event.source,
        }

        assert isinstance(event_dict["id"], str)
        assert isinstance(event_dict["timestamp"], str)
        assert "T" in event_dict["timestamp"]  # ISO format

    def test_event_correlation(self) -> None:
        """Test event correlation functionality."""
        parent_event = SecurityEvent(
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            severity=ThreatSeverity.HIGH,
            description="Unauthorized access attempt",
            source="auth_module",
        )

        child_event = SecurityEvent(
            event_type=SecurityEventType.PRIVILEGE_ESCALATION,
            severity=ThreatSeverity.CRITICAL,
            description="Privilege escalation detected",
            source="system_monitor",
            correlation_id=parent_event.id,
        )

        assert child_event.correlation_id == parent_event.id


class TestThreatIntelligence:
    """Test threat intelligence management."""

    def test_threat_intelligence_creation(self) -> None:
        """Test threat intelligence creation."""
        now = datetime.now(timezone.utc)
        indicator = ThreatIntelligence(
            indicator="192.168.1.100",
            indicator_type="ip",
            threat_types=["malware", "c2"],
            confidence=0.95,
            first_seen=now,
            last_seen=now,
            source="threat_feed",
            severity=ThreatSeverity.HIGH,
            description="Known malicious IP address",
        )

        assert indicator.indicator == "192.168.1.100"
        assert indicator.indicator_type == "ip"
        assert "malware" in indicator.threat_types
        assert "c2" in indicator.threat_types
        assert indicator.confidence == 0.95
        assert indicator.severity.to_string() == "high"

    def test_threat_intelligence_manager(self) -> None:
        """Test threat intelligence manager functionality."""
        manager = ThreatIntelligenceManager()

        # Add threat indicators
        indicator1 = ThreatIntelligence(
            indicator="malicious-domain.com",
            indicator_type="domain",
            threat_types=["phishing"],
            confidence=0.9,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            source="phish_tank",
            severity=ThreatSeverity.HIGH,
            description="Phishing domain",
        )

        indicator2 = ThreatIntelligence(
            indicator="user_agent_string",
            indicator_type="user_agent",
            threat_types=["scanner"],
            confidence=0.8,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            source="honeypot",
            severity=ThreatSeverity.MEDIUM,
            description="Known scanner user agent",
        )

        manager.add_indicator(indicator1)
        manager.add_indicator(indicator2)

        assert len(manager.indicators) == 2
        assert "malicious-domain.com" in manager.indicators
        assert "user_agent_string" in manager.indicators

    def test_threat_intelligence_event_correlation(self) -> None:
        """Test threat intelligence correlation with events."""
        manager = ThreatIntelligenceManager()

        # Add malicious IP indicator
        malicious_ip = ThreatIntelligence(
            indicator="10.0.0.50",
            indicator_type="ip",
            threat_types=["botnet"],
            confidence=0.95,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            source="botnet_tracker",
            severity=ThreatSeverity.CRITICAL,
            description="Known botnet C2 server",
        )
        manager.add_indicator(malicious_ip)

        # Create event with matching IP
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.MEDIUM,
            description="Suspicious network activity",
            source="firewall",
            ip_address="10.0.0.50",
        )

        # Check correlation
        matches = manager.check_event(event)
        assert len(matches) == 1
        assert matches[0].indicator == "10.0.0.50"
        assert "botnet" in matches[0].threat_types

    def test_threat_intelligence_cleanup(self) -> None:
        """Test automatic cleanup of expired threat intelligence."""
        manager = ThreatIntelligenceManager()

        # Add old indicator
        old_indicator = ThreatIntelligence(
            indicator="old-threat.com",
            indicator_type="domain",
            threat_types=["malware"],
            confidence=0.7,
            first_seen=datetime.now(timezone.utc) - timedelta(days=60),
            last_seen=datetime.now(timezone.utc) - timedelta(days=60),
            source="old_feed",
            severity=ThreatSeverity.LOW,
            description="Old threat indicator",
        )
        manager.add_indicator(old_indicator)

        # Should have one indicator
        assert len(manager.indicators) == 1

        # Cleanup expired indicators
        manager.cleanup_expired()

        # Should be removed
        assert len(manager.indicators) == 0


class TestAnomalyDetector:
    """Test anomaly detection functionality."""

    def test_anomaly_detector_initialization(self) -> None:
        """Test anomaly detector initialization."""
        detector = AnomalyDetector()

        assert detector.learning_enabled is True
        assert detector.anomaly_threshold == 0.85
        assert isinstance(detector.baseline_stats, dict)
        assert isinstance(detector.event_patterns, dict)

    def test_pattern_extraction(self) -> None:
        """Test pattern extraction from events."""
        detector = AnomalyDetector()

        # Create test events
        events = [
            SecurityEvent(
                event_type=SecurityEventType.CREDENTIAL_DETECTED,
                severity=ThreatSeverity.HIGH,
                description="Credential in code",
                source="scanner",
                timestamp=datetime.now(timezone.utc),
            ),
            SecurityEvent(
                event_type=SecurityEventType.CREDENTIAL_DETECTED,
                severity=ThreatSeverity.MEDIUM,
                description="Another credential",
                source="scanner",
                timestamp=datetime.now(timezone.utc),
            ),
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description="Suspicious pattern",
                source="analyzer",
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        patterns = detector._extract_patterns(events)

        assert "event_types" in patterns
        assert "severity_distribution" in patterns
        assert "source_distribution" in patterns
        assert patterns["event_types"]["credential_detected"] == 2
        assert patterns["event_types"]["suspicious_activity"] == 1
        assert patterns["source_distribution"]["scanner"] == 2
        assert patterns["source_distribution"]["analyzer"] == 1

    def test_anomaly_score_calculation(self) -> None:
        """Test anomaly score calculation."""
        detector = AnomalyDetector()

        # Set up baseline with normal patterns
        detector.baseline_stats = {
            "event_types": {"normal_event": 10},
            "source_distribution": {"normal_source": 10},
            "hourly_distribution": {14: 5},  # Current hour
        }

        # Current patterns showing anomaly
        current_patterns = {
            "event_types": {"normal_event": 10, "anomaly_event": 15},
            "source_distribution": {"normal_source": 10, "new_source": 5},
            "hourly_distribution": {14: 50},
        }

        # Create anomalous event
        event = SecurityEvent(
            event_type=SecurityEventType.ANOMALY_DETECTED,
            severity=ThreatSeverity.CRITICAL,
            description="Anomalous activity",
            source="new_source",
            timestamp=datetime.now(timezone.utc).replace(hour=14),
        )

        score = detector._calculate_anomaly_score(event, current_patterns)

        # Should detect anomaly due to new event type and source
        assert score > 0.5

    def test_anomaly_detection_with_normal_events(self) -> None:
        """Test anomaly detection with normal events."""
        detector = AnomalyDetector()

        # Create normal-looking events
        events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description=f"Normal event {i}",
                source="system_monitor",
                timestamp=datetime.now(timezone.utc),
            )
            for i in range(10)
        ]

        # Set baseline with similar patterns
        detector.baseline_stats = detector._extract_patterns(events)

        # Analyze similar events
        anomalies = detector.analyze_events(events)

        # Should detect no anomalies
        assert len(anomalies) == 0

    def test_anomaly_detection_with_anomalous_events(self) -> None:
        """Test anomaly detection with anomalous events."""
        detector = AnomalyDetector()

        # Set up normal baseline
        normal_events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description="Normal event",
                source="system_monitor",
                timestamp=datetime.now(timezone.utc),
            )
        ]
        detector.baseline_stats = detector._extract_patterns(normal_events)

        # Create anomalous events
        anomalous_events = [
            SecurityEvent(
                event_type=SecurityEventType.SECURITY_BREACH,
                severity=ThreatSeverity.CRITICAL,
                description="Critical security breach",
                source="unknown_attacker",
                timestamp=datetime.now(timezone.utc),
            ),
            SecurityEvent(
                event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                severity=ThreatSeverity.CRITICAL,
                description="Privilege escalation attempt",
                source="external_ip",
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        # Lower threshold for testing
        detector.anomaly_threshold = 0.5

        anomalies = detector.analyze_events(anomalous_events)

        # Should detect anomalies
        assert len(anomalies) > 0
        for anomaly in anomalies:
            assert anomaly.event_type == SecurityEventType.ANOMALY_DETECTED
            assert anomaly.severity.to_string() in ["high", "critical"]

    def test_baseline_update(self) -> None:
        """Test baseline updating with new data."""
        detector = AnomalyDetector()

        # Initial baseline
        initial_events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description="Initial event",
                source="initial_source",
                timestamp=datetime.now(timezone.utc),
            )
        ]
        detector.baseline_stats = detector._extract_patterns(initial_events)

        # Update baseline with new data
        new_events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.HIGH,
                description="New event",
                source="new_source",
                timestamp=datetime.now(timezone.utc),
            )
        ]
        detector.update_baseline(new_events)

        # Baseline should be updated
        assert "new_event" in detector.baseline_stats["event_types"]
        assert "new_source" in detector.baseline_stats["source_distribution"]


class TestSecurityMonitor:
    """Test security monitor functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_security_monitor()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_security_monitor()

    def test_monitor_initialization(self) -> None:
        """Test security monitor initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = SecurityMonitor(storage_path=Path(temp_dir))

            assert monitor.status == MonitoringStatus.ACTIVE
            assert not monitor.running
            assert len(monitor.event_collectors) == 0
            assert len(monitor.alert_channels) == 0
            assert monitor.max_events == 10000
            assert monitor.monitoring_interval == 30

    def test_monitor_with_storage_path(self, tmp_path: Path) -> None:
        """Test monitor with custom storage path."""
        storage_path = tmp_path / "importobot_test_monitoring"
        monitor = SecurityMonitor(storage_path=storage_path)

        assert monitor.storage_path == storage_path
        assert storage_path.exists()

    def test_create_security_event(self) -> None:
        """Test security event creation."""
        monitor = SecurityMonitor()

        event = monitor.create_event(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.HIGH,
            description="AWS access key detected",
            source="code_scanner",
            user_id="developer123",
            ip_address="192.168.1.100",
            resource_affected="config.py",
            details={"key_type": "aws_access_key"},
        )

        assert event.event_type.value == "credential_detected"
        assert event.severity.to_string() == "high"
        assert event.description == "AWS access key detected"
        assert event.source == "code_scanner"
        assert event.user_id == "developer123"
        assert event.ip_address == "192.168.1.100"
        assert event.resource_affected == "config.py"
        assert event.details["key_type"] == "aws_access_key"

    def test_event_storage_and_retrieval(self) -> None:
        """Test event storage and retrieval."""
        monitor = SecurityMonitor()

        # Create multiple events
        events = []
        for i in range(5):
            event = monitor.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description=f"Test event {i}",
                source="test_module",
            )
            events.append(event)

        # Retrieve events
        retrieved_events = monitor.get_events(limit=10)

        assert len(retrieved_events) >= 5
        # Should be sorted by timestamp descending
        assert retrieved_events[0].timestamp >= retrieved_events[-1].timestamp

    def test_event_filtering(self) -> None:
        """Test event filtering functionality."""
        monitor = SecurityMonitor()

        # Create events with different properties
        monitor.create_event(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.HIGH,
            description="High severity event",
            source="scanner_a",
        )
        monitor.create_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.LOW,
            description="Low severity event",
            source="scanner_b",
        )
        monitor.create_event(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.MEDIUM,
            description="Medium severity event",
            source="scanner_c",
        )

        # Filter by event type
        credential_events = monitor.get_events(
            event_type=SecurityEventType.CREDENTIAL_DETECTED
        )
        assert len(credential_events) == 2
        assert all(
            e.event_type.value == "credential_detected" for e in credential_events
        )

        # Filter by severity
        high_events = monitor.get_events(severity=ThreatSeverity.HIGH)
        assert len(high_events) == 1
        assert high_events[0].severity.to_string() == "high"

        # Filter by source
        scanner_a_events = monitor.get_events(source="scanner_a")
        assert len(scanner_a_events) == 1
        assert scanner_a_events[0].source == "scanner_a"

    def test_time_based_filtering(self) -> None:
        """Test time-based event filtering."""
        monitor = SecurityMonitor()

        now = datetime.now(timezone.utc)
        past_time = now - timedelta(hours=2)
        _ = now + timedelta(hours=1)

        # Create event at specific time
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.MEDIUM,
            description="Timed event",
            source="test_module",
        )
        event.timestamp = past_time
        monitor._process_event(event)

        # Filter by time range
        filtered_events = monitor.get_events(
            start_time=past_time - timedelta(minutes=30),
            end_time=past_time + timedelta(minutes=30),
        )

        assert len(filtered_events) == 1
        assert filtered_events[0].timestamp == past_time

    def test_event_limit_enforcement(self) -> None:
        """Test event limit enforcement."""
        monitor = SecurityMonitor()
        monitor.max_events = 3  # Set low limit for testing

        # Create more events than the limit
        for i in range(5):
            monitor.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description=f"Event {i}",
                source="test_module",
            )

        # Should only keep the most recent events
        all_events = monitor.get_events(limit=100)
        assert len(all_events) <= 3

    def test_monitoring_statistics(self) -> None:
        """Test monitoring statistics calculation."""
        monitor = SecurityMonitor()

        # Create events with different properties
        monitor.create_event(
            SecurityEventType.CREDENTIAL_DETECTED,
            ThreatSeverity.HIGH,
            "High event",
            "source1",
        )
        monitor.create_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            ThreatSeverity.MEDIUM,
            "Medium event",
            "source2",
        )
        monitor.create_event(
            SecurityEventType.CREDENTIAL_DETECTED,
            ThreatSeverity.LOW,
            "Low event",
            "source3",
        )
        monitor.create_event(
            SecurityEventType.ANOMALY_DETECTED,
            ThreatSeverity.CRITICAL,
            "Critical event",
            "source1",
        )

        stats = monitor.get_statistics()

        assert stats["total_events"] == 4
        assert stats["events_last_24h"] == 4
        assert stats["monitoring_status"] == "active"
        assert "event_types" in stats
        assert "severity_distribution" in stats

        # Check event type distribution
        assert stats["event_types"]["credential_detected"] == 2
        assert stats["event_types"]["suspicious_activity"] == 1
        assert stats["event_types"]["anomaly_detected"] == 1

        # Check severity distribution
        assert stats["severity_distribution"]["high"] == 1
        assert stats["severity_distribution"]["medium"] == 1
        assert stats["severity_distribution"]["low"] == 1
        assert stats["severity_distribution"]["critical"] == 1

    def test_event_collectors_management(self) -> None:
        """Test event collectors management."""
        monitor = SecurityMonitor()

        # Mock collector
        mock_collector = Mock(spec=EventCollector)
        mock_collector.is_healthy.return_value = True
        mock_collector.collect_events.return_value = []

        monitor.add_event_collector(mock_collector)

        assert len(monitor.event_collectors) == 1
        assert monitor.event_collectors[0] is mock_collector

    def test_alert_channels_management(self) -> None:
        """Test alert channels management."""
        monitor = SecurityMonitor()

        # Mock alert channel
        mock_channel = Mock(spec=AlertChannel)
        mock_channel.send_alert.return_value = True
        mock_channel.test_connection.return_value = True

        monitor.add_alert_channel(mock_channel)

        assert len(monitor.alert_channels) == 1
        assert monitor.alert_channels[0] is mock_channel

    def test_high_severity_alert_sending(self) -> None:
        """Test alert sending for high severity events."""
        monitor = SecurityMonitor()

        # Mock alert channel
        mock_channel = Mock(spec=AlertChannel)
        mock_channel.send_alert.return_value = True
        monitor.add_alert_channel(mock_channel)

        # Create high severity event (should trigger alert)
        event = monitor.create_event(
            event_type=SecurityEventType.SECURITY_BREACH,
            severity=ThreatSeverity.CRITICAL,
            description="Critical security breach",
            source="ids",
        )

        # Alert should have been sent
        mock_channel.send_alert.assert_called_once()
        call_args = mock_channel.send_alert.call_args[0][0]
        assert call_args == event

    def test_low_severity_no_alert(self) -> None:
        """Test that low severity events don't trigger alerts."""
        monitor = SecurityMonitor()

        # Mock alert channel
        mock_channel = Mock(spec=AlertChannel)
        monitor.add_alert_channel(mock_channel)

        # Create low severity event (should not trigger alert)
        monitor.create_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.LOW,
            description="Normal system activity",
            source="monitor",
        )

        # Alert should not have been sent
        mock_channel.send_alert.assert_not_called()

    def test_monitoring_start_stop(self) -> None:
        """Test monitoring start and stop functionality."""
        monitor = SecurityMonitor()

        assert not monitor.running

        # Start monitoring
        monitor.start_monitoring()
        assert monitor.running
        assert monitor.status == MonitoringStatus.ACTIVE

        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.running

    def test_monitoring_persistence(self) -> None:
        """Test event persistence across monitor instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            # Create first monitor and add event
            monitor1 = SecurityMonitor(storage_path=storage_path)
            monitor1.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description="Persistent event",
                source="test_module",
            )

            # Create second monitor and check if event persists
            monitor2 = SecurityMonitor(storage_path=storage_path)
            events = monitor2.get_events(limit=10)

            assert len(events) >= 1
            assert events[0].description == "Persistent event"

    def test_global_monitor_singleton(self) -> None:
        """Test global security monitor singleton behavior."""
        reset_security_monitor()

        # Get global monitor
        monitor1 = get_security_monitor()
        monitor2 = get_security_monitor()

        # Should return the same instance
        assert monitor1 is monitor2

        # Reset and verify new instance
        reset_security_monitor()
        monitor3 = get_security_monitor()
        assert monitor3 is not monitor1

    def test_monitoring_with_threat_intelligence(self) -> None:
        """Test monitoring integration with threat intelligence."""
        monitor = SecurityMonitor()

        # Add threat intelligence
        malicious_ip = ThreatIntelligence(
            indicator="10.0.0.100",
            indicator_type="ip",
            threat_types=["malware"],
            confidence=0.9,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            source="threat_feed",
            severity=ThreatSeverity.CRITICAL,
            description="Known malicious IP",
        )
        monitor.threat_intel.add_indicator(malicious_ip)

        # Create event with matching IP
        event = monitor.create_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.MEDIUM,
            description="Network connection established",
            source="firewall",
            ip_address="10.0.0.100",
        )

        # Event should be upgraded due to threat intelligence match
        assert event.severity.to_string() in {"high", "critical"}
        assert "threat_intelligence_matches" in event.details
        assert len(event.details["threat_intelligence_matches"]) > 0

    def test_error_handling_in_alert_channels(self) -> None:
        """Test error handling when alert channels fail."""
        monitor = SecurityMonitor()

        # Mock failing alert channel
        mock_channel = Mock(spec=AlertChannel)
        mock_channel.send_alert.side_effect = Exception("Connection failed")
        monitor.add_alert_channel(mock_channel)

        # Create critical event (should trigger alert)
        event = monitor.create_event(
            event_type=SecurityEventType.SECURITY_BREACH,
            severity=ThreatSeverity.CRITICAL,
            description="Critical breach",
            source="ids",
        )

        # Should handle the error gracefully
        assert event is not None  # Event should still be created


class TestMonitoringPerformance:
    """Performance tests for security monitoring."""

    def test_event_creation_performance(self) -> None:
        """Test event creation performance."""
        monitor = SecurityMonitor()

        start_time = time.time()

        # Create many events
        for i in range(1000):
            monitor.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description=f"Performance test event {i}",
                source="performance_test",
            )

        creation_time = time.time() - start_time

        # Should complete within reasonable time (< 1 second for 1000 events)
        assert creation_time < 1.0
        assert creation_time > 0  # Should take some time

    def test_event_filtering_performance(self) -> None:
        """Test event filtering performance."""
        monitor = SecurityMonitor()

        # Create many events with different properties
        for i in range(5000):
            severities = [
                ThreatSeverity.LOW,
                ThreatSeverity.MEDIUM,
                ThreatSeverity.HIGH,
                ThreatSeverity.CRITICAL,
            ]
            severity = severities[i % 4]
            event_type = [
                SecurityEventType.CREDENTIAL_DETECTED,
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                SecurityEventType.ANOMALY_DETECTED,
            ][i % 3]
            source = f"source_{i % 10}"

            monitor.create_event(
                event_type=event_type,
                severity=severity,
                description=f"Performance test event {i}",
                source=source,
            )

        start_time = time.time()

        # Perform filtered queries
        high_severity_events = monitor.get_events(
            severity=ThreatSeverity.HIGH, limit=100
        )
        credential_events = monitor.get_events(
            event_type=SecurityEventType.CREDENTIAL_DETECTED, limit=100
        )
        source_events = monitor.get_events(source="source_5", limit=100)

        filtering_time = time.time() - start_time

        # Should complete quickly (< 100ms for filtering)
        assert filtering_time < 0.1
        assert len(high_severity_events) > 0
        assert len(credential_events) > 0
        assert len(source_events) > 0

    def test_anomaly_detection_performance(self) -> None:
        """Test anomaly detection performance."""
        detector = AnomalyDetector()

        # Create many events
        events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description=f"Normal event {i}",
                source="performance_test",
                timestamp=datetime.now(timezone.utc),
            )
            for i in range(1000)
        ]

        # Set baseline
        detector.baseline_stats = detector._extract_patterns(events[:500])

        start_time = time.time()

        # Detect anomalies
        anomalies = detector.analyze_events(events[500:])

        detection_time = time.time() - start_time

        # Should complete quickly (< 50ms for 500 events)
        assert detection_time < 0.05
        assert isinstance(anomalies, list)

    def test_concurrent_event_creation(self) -> None:
        """Test concurrent event creation performance."""
        monitor = SecurityMonitor()
        monitor.max_events = 10000

        def create_events_worker(worker_id: int) -> int:
            """Worker function to create events."""
            count = 0
            for i in range(100):
                monitor.create_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    severity=ThreatSeverity.MEDIUM,
                    description=f"Worker {worker_id} event {i}",
                    source=f"worker_{worker_id}",
                )
                count += 1
            return count

        # Run multiple workers
        threads = []
        start_time = time.time()

        for worker_id in range(10):
            thread = threading.Thread(target=create_events_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        creation_time = time.time() - start_time
        total_events = len(monitor.get_events(limit=2000))

        # Should handle concurrent creation efficiently
        assert creation_time < 2.0  # Should complete within 2 seconds
        assert total_events >= 1000  # Should have created all events


class TestMonitoringInvariants:
    """Invariant tests for security monitoring system."""

    def test_event_id_uniqueness_invariant(self) -> None:
        """Test that all events have unique IDs."""
        monitor = SecurityMonitor()

        # Create many events
        events = []
        for i in range(100):
            event = monitor.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description=f"Uniqueness test {i}",
                source="test_module",
            )
            events.append(event)

        # Check that all IDs are unique
        event_ids = [event.id for event in events]
        assert len(event_ids) == len(set(event_ids))

    def test_event_timestamp_monotonicity_invariant(self) -> None:
        """Test that event timestamps are within reasonable bounds."""
        monitor = SecurityMonitor()
        now = datetime.now(timezone.utc)

        # Create event
        event = monitor.create_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.MEDIUM,
            description="Timestamp test",
            source="test_module",
        )

        # Timestamp should be close to now (within 1 minute)
        time_diff = abs((event.timestamp - now).total_seconds())
        assert time_diff < 60

        # Timestamp should not be in the future (allow small clock skew)
        assert event.timestamp <= now + timedelta(seconds=5)

    def test_event_field_consistency_invariant(self) -> None:
        """Test that event fields maintain consistency."""
        monitor = SecurityMonitor()

        event = monitor.create_event(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.HIGH,
            description="Consistency test",
            source="test_module",
            tags=["security", "test"],
            details={"key_type": "aws"},
        )

        # Event type should match enum
        assert event.event_type.value == "credential_detected"
        assert event.event_type in SecurityEventType

        # Severity should match enum
        assert event.severity.to_string() == "high"
        assert event.severity in ThreatSeverity

        # Lists should be properly typed
        assert isinstance(event.tags, list)
        assert all(isinstance(tag, str) for tag in event.tags)

        # Details should be properly typed
        assert isinstance(event.details, dict)
        assert event.details["key_type"] == "aws"

    def test_storage_consistency_invariant(self) -> None:
        """Test that storage operations maintain consistency."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)
            monitor = SecurityMonitor(storage_path=storage_path)

            # Create event
            original_event = monitor.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description="Storage consistency test",
                source="test_module",
            )

            # Save and reload
            monitor2 = SecurityMonitor(storage_path=storage_path)
            loaded_events = monitor2.get_events(limit=1)

            assert len(loaded_events) >= 1
            loaded_event = loaded_events[0]

            # Critical fields should match
            assert loaded_event.id == original_event.id
            assert loaded_event.event_type == original_event.event_type
            assert loaded_event.severity == original_event.severity
            assert loaded_event.description == original_event.description
            assert loaded_event.source == original_event.source

    def test_monitor_state_consistency_invariant(self) -> None:
        """Test that monitor state remains consistent."""
        monitor = SecurityMonitor()

        # Start monitoring
        monitor.start_monitoring()

        # State should be consistent
        assert monitor.running is True
        assert monitor.status == MonitoringStatus.ACTIVE

        # Stop monitoring
        monitor.stop_monitoring()

        # State should be consistent
        assert monitor.running is False

    def test_event_limit_enforcement_invariant(self) -> None:
        """Test that event limit is strictly enforced."""
        monitor = SecurityMonitor()
        monitor.max_events = 5

        # Create more events than the limit
        for i in range(10):
            monitor.create_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description=f"Limit test event {i}",
                source="test_module",
            )

        all_events = monitor.get_events(limit=100)

        # Should never exceed the limit
        assert len(all_events) <= monitor.max_events

    def test_thread_safety_invariant(self) -> None:
        """Test thread safety of monitor operations."""
        monitor = SecurityMonitor()
        errors = []

        def worker_thread(worker_id: int) -> None:
            """Worker thread that performs operations."""
            try:
                for i in range(50):
                    monitor.create_event(
                        event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                        severity=ThreatSeverity.MEDIUM,
                        description=f"Worker {worker_id} event {i}",
                        source=f"worker_{worker_id}",
                    )

                    # Try to retrieve events
                    events = monitor.get_events(limit=10)
                    assert isinstance(events, list)

            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker_thread, args=(worker_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Should have created all events
        total_events = len(monitor.get_events(limit=1000))
        assert total_events >= 200  # 5 workers * 50 events each


# UUID imported at top level
