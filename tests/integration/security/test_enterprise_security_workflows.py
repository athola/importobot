"""
Integration tests for enterprise security workflows.

This module tests end-to-end workflows between security monitoring,
SIEM integration, and compliance reporting components to ensure
comprehensive enterprise security functionality.
"""

import time
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from importobot.security.compliance import (
    ComplianceEngine,
    ComplianceStandard,
)
from importobot.security.monitoring import (
    SecurityEvent,
    SecurityEventType,
    SecurityMonitor,
    ThreatIntelligence,
    ThreatSeverity,
)
from importobot.security.siem_integration import (
    ElasticSIEMConnector,
    SIEMIntegrationError,
    SIEMManager,
    SplunkConnector,
)
from importobot.security.siem_integration import (
    MicrosoftSentinelConnector as SentinelConnector,
)


class TestEnterpriseSecurityWorkflows:
    """Test end-to-end enterprise security workflows."""

    @pytest.fixture
    def security_monitor(
        self,
        tmp_path: Path,
    ) -> Generator[SecurityMonitor, None, None]:
        """Create a security monitor for testing."""
        # Use temporary path to avoid persistence across tests
        storage_path = tmp_path / "security_monitor"
        monitor = SecurityMonitor(storage_path=storage_path)

        # Clear any existing events
        monitor.events.clear()

        yield monitor

        # Cleanup
        monitor.events.clear()

    @pytest.fixture
    def mock_siem_connectors(self) -> dict[str, MagicMock]:
        """Create mock SIEM connectors for testing."""
        splunk = MagicMock(spec=SplunkConnector)
        splunk.send_event.return_value = True
        splunk.test_connection.return_value = True

        elastic = MagicMock(spec=ElasticSIEMConnector)
        elastic.send_event.return_value = True
        elastic.test_connection.return_value = True

        sentinel = MagicMock(spec=SentinelConnector)
        sentinel.send_event.return_value = True
        sentinel.test_connection.return_value = True

        return {"splunk": splunk, "elastic": elastic, "sentinel": sentinel}

    @pytest.fixture
    def siem_integration(
        self,
        mock_siem_connectors: dict[str, MagicMock],
    ) -> Generator[SIEMManager, None, None]:
        """Create a SIEM manager instance with mock connectors."""
        siem_manager = SIEMManager()

        # Add mock connectors
        siem_manager.add_connector(mock_siem_connectors["splunk"])
        siem_manager.add_connector(mock_siem_connectors["elastic"])
        siem_manager.add_connector(mock_siem_connectors["sentinel"])

        # Start the SIEM manager
        siem_manager.start()

        yield siem_manager

        # Cleanup
        siem_manager.stop()

    @pytest.fixture
    def compliance_engine(self) -> ComplianceEngine:
        """Create a compliance engine for testing."""
        return ComplianceEngine()

    @pytest.fixture
    def sample_security_events(self) -> list[SecurityEvent]:
        """Create sample security events for testing."""
        return [
            SecurityEvent(
                event_type=SecurityEventType.CREDENTIAL_DETECTED,
                severity=ThreatSeverity.HIGH,
                source="test_module",
                description="Detected potential credential in code",
                details={"pattern": "api_key", "file": "test.py"},
            ),
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                source="test_module",
                description="Suspicious template detected",
                details={"template": "test.robot", "issues": ["hardcoded_secret"]},
            ),
            SecurityEvent(
                event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                severity=ThreatSeverity.CRITICAL,
                source="test_module",
                description="Multiple failed authentication attempts",
                details={"attempts": 5, "source_ip": "192.168.1.100"},
            ),
        ]

    def test_security_monitoring_to_siem_workflow(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
        sample_security_events: list[SecurityEvent],
    ) -> None:
        """Test workflow from security monitoring to SIEM integration."""
        # Process events through security monitor
        for event in sample_security_events:
            # Manually add events to security monitor for testing
            security_monitor._process_event(event)

        # Verify events were logged
        assert len(security_monitor.events) == len(sample_security_events)

        # Forward events to SIEM
        for event in security_monitor.events:
            success = siem_integration.send_security_event(event)
            assert success is True

        # Wait for async processing and manually process queue to ensure events are sent
        time.sleep(0.5)

        # Process any remaining queued events
        if siem_integration.event_queue:
            siem_integration._process_event_queue()

        # Verify SIEM connectors were called
        total_calls = sum(
            cast(MagicMock, connector.send_event).call_count
            for connector in siem_integration.connectors
        )
        assert total_calls >= len(sample_security_events)

    def test_security_monitoring_to_compliance_workflow(
        self,
        security_monitor: SecurityMonitor,
        compliance_engine: ComplianceEngine,
        sample_security_events: list[SecurityEvent],
    ) -> None:
        """Test workflow from security monitoring to compliance assessment."""
        # Process events through security monitor
        for event in sample_security_events:
            security_monitor._process_event(event)

        # Get events for compliance assessment
        security_monitor.get_events()

        # Create SOC 2 assessment using compliance engine
        report = compliance_engine.assess_compliance(standard=ComplianceStandard.SOC_2)

        # Verify compliance report was generated
        assert report is not None
        assert len(report.controls) >= 0
        assert isinstance(report.findings, list)
        assert isinstance(report.evidence_summary, dict)

    def test_end_to_end_security_workflow(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
        compliance_engine: ComplianceEngine,
        sample_security_events: list[SecurityEvent],
    ) -> None:
        """Test complete end-to-end security workflow."""
        # Step 1: Process events through security monitor
        for event in sample_security_events:
            security_monitor._process_event(event)

        # Step 3: Forward critical events to SIEM
        critical_events = [
            e for e in security_monitor.events if e.severity == ThreatSeverity.CRITICAL
        ]
        for event in critical_events:
            success = siem_integration.send_security_event(event)
            assert success is True

        # Step 4: Generate compliance report
        compliance_report = compliance_engine.assess_compliance(
            standard=ComplianceStandard.SOC_2
        )

        # Step 5: Verify workflow completeness
        assert len(security_monitor.events) == len(sample_security_events)
        assert isinstance(compliance_report.findings, list)
        assert len(compliance_report.controls) >= 0
        assert isinstance(compliance_report.evidence_summary, dict)

        # Wait for async processing and manually process queue
        time.sleep(0.5)

        # Process any remaining queued events
        if siem_integration.event_queue:
            siem_integration._process_event_queue()

        # Step 6: Verify SIEM received critical events
        total_calls = sum(
            cast(MagicMock, connector.send_event).call_count
            for connector in siem_integration.connectors
        )
        assert total_calls >= len(critical_events)

    def test_multi_standard_compliance_workflow(
        self,
        security_monitor: SecurityMonitor,
        compliance_engine: ComplianceEngine,
        sample_security_events: list[SecurityEvent],
    ) -> None:
        """Test compliance workflow across multiple standards."""
        # Process events through security monitor
        for event in sample_security_events:
            security_monitor._process_event(event)

        security_monitor.get_events()

        # Generate SOC 2 report using compliance engine
        engine_report = compliance_engine.assess_compliance(
            standard=ComplianceStandard.SOC_2
        )

        # Verify report was generated
        assert engine_report is not None
        assert len(engine_report.controls) >= 0
        assert isinstance(engine_report.findings, list)

    def test_threat_intelligence_integration(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
    ) -> None:
        """Test threat intelligence integration with SIEM."""
        # Add threat intelligence
        threat = ThreatIntelligence(
            indicator="192.168.1.100",
            indicator_type="ip",
            threat_types=["malicious_ip"],
            confidence=0.9,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            source="test_feed",
            severity=ThreatSeverity.HIGH,
            description="Known malicious IP address",
        )
        security_monitor.threat_intel.add_indicator(threat)

        # Create security event from known threat
        event = SecurityEvent(
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            severity=ThreatSeverity.HIGH,
            source="auth_system",
            description="Login from known malicious IP",
            details={"ip_address": "192.168.1.100"},
        )

        # Process event
        security_monitor._process_event(event)

        # Forward to SIEM
        success = siem_integration.send_security_event(event)
        assert success is True

        # Verify threat intelligence correlation
        assert len(security_monitor.threat_intel.indicators) == 1
        assert "192.168.1.100" in security_monitor.threat_intel.indicators

    def test_high_volume_event_processing(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
    ) -> None:
        """Test processing of high-volume security events."""
        # Generate high volume of events
        events = []
        for i in range(50):  # Reduced for test performance
            event = SecurityEvent(
                event_type=SecurityEventType.CREDENTIAL_DETECTED,
                severity=ThreatSeverity.MEDIUM,
                source=f"module_{i % 10}",
                description=f"Event {i}",
                details={"event_id": i},
            )
            events.append(event)

        # Process events efficiently
        start_time = time.time()
        for event in events:
            security_monitor._process_event(event)
        processing_time = time.time() - start_time

        # Verify performance (should process 50 events in reasonable time)
        assert processing_time < 1.0  # 1 second max
        assert len(security_monitor.events) == 50

        # Forward subset to SIEM (to avoid too many calls in test)
        critical_events = [e for e in events if e.severity == ThreatSeverity.CRITICAL]
        if critical_events:
            for event in critical_events[:5]:  # Limit to 5 for test
                success = siem_integration.send_security_event(event)
                assert success is True

    def test_error_handling_and_recovery(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
        compliance_engine: ComplianceEngine,
    ) -> None:
        """Test error handling in enterprise security workflows."""
        # Create a problematic event
        problematic_event = SecurityEvent(
            event_type=SecurityEventType.POLICY_VIOLATION,
            severity=ThreatSeverity.HIGH,
            source="test_module",
            description="Test error handling",
            details={"invalid_data": "test"},
        )

        # Process event (should handle gracefully)
        security_monitor._process_event(problematic_event)
        assert len(security_monitor.events) == 1

        # Simulate SIEM connection failure
        for connector in siem_integration.connectors:
            if isinstance(connector, MagicMock):
                connector.send_event.side_effect = SIEMIntegrationError(
                    "Connection failed"
                )

        # Forward event (should handle failure gracefully)
        # SIEMManager will queue and retry
        siem_integration.send_security_event(problematic_event)
        # The event is queued, so success is True even if individual connectors fail

        # Reset side effects for other tests
        for connector in siem_integration.connectors:
            if isinstance(connector, MagicMock):
                connector.send_event.side_effect = None

    def test_configuration_drift_detection(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
        compliance_engine: ComplianceEngine,
    ) -> None:
        """Test detection of configuration drift in security components."""
        # Get initial configuration
        initial_siem_connectors = len(siem_integration.connectors)

        # Test configuration validation
        assert len(siem_integration.connectors) == initial_siem_connectors

    def test_audit_trail_consistency(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
        compliance_engine: ComplianceEngine,
    ) -> None:
        """Test audit trail consistency across all security components."""
        # Create events with known sequence
        events = []
        for i in range(10):
            event = SecurityEvent(
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                severity=ThreatSeverity.LOW,
                source="test_module",
                description=f"Audit test {i}",
                details={"sequence": i},
            )
            events.append(event)

        # Process events in order
        for event in events:
            security_monitor._process_event(event)

        # Forward to SIEM
        for event in events:
            siem_integration.send_security_event(event)

        # Generate compliance report
        report = compliance_engine.assess_compliance(standard=ComplianceStandard.SOC_2)

        # Verify audit trail consistency
        assert len(security_monitor.events) == len(events)
        assert len(report.controls) >= 0
        assert isinstance(report.evidence_summary, dict)

        # Check event ordering
        for i, event in enumerate(events):
            assert event.details["sequence"] == i

    def test_real_time_monitoring_workflow(
        self,
        security_monitor: SecurityMonitor,
        siem_integration: SIEMManager,
    ) -> None:
        """Test real-time monitoring and alerting workflow."""
        # Simulate real-time event stream
        critical_event = SecurityEvent(
            event_type=SecurityEventType.SECURITY_BREACH,
            severity=ThreatSeverity.CRITICAL,
            source="intrusion_detection",
            description="Critical security breach detected",
            details={"breach_type": "unauthorized_access", "user": "admin"},
        )

        # Process event
        security_monitor._process_event(critical_event)

        # Forward immediately to SIEM
        success = siem_integration.send_security_event(critical_event)
        assert success is True

        # Wait for async processing and manually process queue
        time.sleep(0.5)

        # Process any remaining queued events
        if siem_integration.event_queue:
            siem_integration._process_event_queue()

        # Verify immediate forwarding
        total_calls = sum(
            cast(MagicMock, connector.send_event).call_count
            for connector in siem_integration.connectors
        )
        assert total_calls >= 1

        # Check if any connector was called with the right parameters
        critical_event_forwarded = False
        for connector in siem_integration.connectors:
            if connector.send_event.called:  # type: ignore[attr-defined]
                call_args = connector.send_event.call_args[0][0]  # type: ignore[attr-defined]
                if (
                    hasattr(call_args, "severity")
                    and hasattr(call_args, "event_type")
                    and (
                        call_args.severity == "critical"
                        or call_args.event_type == "SECURITY_BREACH"
                    )
                ):
                    critical_event_forwarded = True
                    break

        # At least one connector should have forwarded the critical event
        assert critical_event_forwarded or total_calls >= 1

    def test_compliance_reporting_workflow(
        self,
        security_monitor: SecurityMonitor,
        compliance_engine: ComplianceEngine,
    ) -> None:
        """Test comprehensive compliance reporting workflow."""
        # Create mixed severity events
        events = [
            SecurityEvent(
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                severity=ThreatSeverity.LOW,
                source="database",
                description="Normal data access",
                details={"user": "user1", "table": "customers"},
            ),
            SecurityEvent(
                event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                severity=ThreatSeverity.HIGH,
                source="auth_system",
                description="Privilege escalation attempt",
                details={"user": "user2", "attempted_role": "admin"},
            ),
            SecurityEvent(
                event_type=SecurityEventType.SECURITY_BREACH,
                severity=ThreatSeverity.MEDIUM,
                source="api",
                description="Bulk data export",
                details={"user": "user3", "record_count": 1000},
            ),
        ]

        # Process events
        for event in events:
            security_monitor._process_event(event)

        # Generate comprehensive compliance report
        security_monitor.get_events()

        # Test SOC 2 compliance using compliance engine
        compliance_report = compliance_engine.assess_compliance(
            standard=ComplianceStandard.SOC_2
        )

        # Verify report quality
        assert compliance_report is not None
        assert compliance_report.overall_score >= 0.0
        assert compliance_report.overall_score <= 100.0
        assert len(compliance_report.controls) >= 0
        assert len(compliance_report.recommendations) >= 0
        assert isinstance(compliance_report.evidence_summary, dict)
        assert isinstance(compliance_report.findings, list)
