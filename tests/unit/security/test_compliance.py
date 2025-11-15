"""Tests for compliance reporting system.

This module provides comprehensive test coverage for the compliance reporting
including unit tests, integration tests, performance tests, and compliance validation
following TDD and BDD principles.
"""

from __future__ import annotations

import json
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

import pytest

from importobot.security.compliance import (
    AuditTrail,
    ComplianceAssessment,
    ComplianceControl,
    ComplianceEngine,
    ComplianceError,
    ComplianceReport,
    ComplianceStandard,
    ComplianceStatus,
    ControlType,
    SOC2Assessment,
    assess_soc2_compliance,
    get_compliance_dashboard,
    get_compliance_engine,
    reset_compliance_engine,
)
from importobot.security.monitoring import (
    SecurityEvent,
    SecurityEventType,
    ThreatSeverity,
)


class TestComplianceControl:
    """Test compliance control data structure and behavior."""

    def test_compliance_control_creation_minimal(self) -> None:
        """Test compliance control creation with minimal fields."""
        control = ComplianceControl(
            id="CTRL-001",
            standard=ComplianceStandard.SOC_2,
            category="Security",
            title="Access Control",
            description="Test control description",
            control_type=ControlType.PREVENTIVE,
            requirement="CC6.1",
        )

        assert control.id == "CTRL-001"
        assert control.standard == ComplianceStandard.SOC_2
        assert control.category == "Security"
        assert control.title == "Access Control"
        assert control.implementation_status == ComplianceStatus.NOT_ASSESSED
        assert control.score == 0.0
        assert len(control.evidence) == 0
        assert len(control.gaps) == 0
        assert len(control.remediation_actions) == 0

    def test_compliance_control_creation_full(self) -> None:
        """Test compliance control creation with all fields."""
        now = datetime.now(timezone.utc)
        control = ComplianceControl(
            id="CTRL-FULL-001",
            standard=ComplianceStandard.ISO_27001,
            category="Access Control",
            title="Comprehensive Access Management",
            description="Full control description with all details",
            control_type=ControlType.DETECTIVE,
            requirement="A.9.1.1, A.9.1.2",
            implementation_status=ComplianceStatus.PARTIALLY_COMPLIANT,
            evidence=["Evidence 1", "Evidence 2"],
            last_assessment=now,
            next_assessment=now + timedelta(days=90),
            owner="security-team",
            score=75.5,
            gaps=["Gap 1", "Gap 2"],
            remediation_actions=["Action 1", "Action 2"],
            automation_available=True,
            metrics={"test_coverage": 85.0, "compliance_rate": 75.0},
        )

        assert control.id == "CTRL-FULL-001"
        assert control.standard == ComplianceStandard.ISO_27001
        assert control.implementation_status == ComplianceStatus.PARTIALLY_COMPLIANT
        assert len(control.evidence) == 2
        assert control.owner == "security-team"
        assert control.score == 75.5
        assert control.automation_available is True
        assert control.metrics["test_coverage"] == 85.0

    def test_compliance_control_serialization(self) -> None:
        """Test compliance control serialization."""
        control = ComplianceControl(
            id="SERIAL-001",
            standard=ComplianceStandard.SOC_2,
            category="Test",
            title="Serialization Test",
            description="Test serialization",
            control_type=ControlType.PREVENTIVE,
            requirement="TEST.001",
        )

        # Test JSON serialization
        control_dict = {
            "id": control.id,
            "standard": control.standard.value,
            "category": control.category,
            "title": control.title,
            "description": control.description,
            "control_type": control.control_type.value,
            "requirement": control.requirement,
            "implementation_status": control.implementation_status.value,
            "score": control.score,
        }

        assert control_dict["id"] == "SERIAL-001"
        assert control_dict["standard"] == "soc_2"
        assert control_dict["control_type"] == "preventive"
        assert control_dict["implementation_status"] == "not_assessed"

    def test_compliance_control_enums(self) -> None:
        """Test compliance control enum values."""
        # Test all standards
        for standard in ComplianceStandard:
            control = ComplianceControl(
                id=f"ENUM-{standard.value}",
                standard=standard,
                category="Test",
                title="Enum Test",
                description="Testing enums",
                control_type=ControlType.PREVENTIVE,
                requirement="TEST.001",
            )
            assert control.standard == standard

        # Test all statuses
        for status in ComplianceStatus:
            control = ComplianceControl(
                id=f"STATUS-{status.value}",
                standard=ComplianceStandard.SOC_2,
                category="Test",
                title="Status Test",
                description="Testing statuses",
                control_type=ControlType.PREVENTIVE,
                requirement="TEST.001",
                implementation_status=status,
            )
            assert control.implementation_status == status

        # Test all control types
        for control_type in ControlType:
            control = ComplianceControl(
                id=f"TYPE-{control_type.value}",
                standard=ComplianceStandard.SOC_2,
                category="Test",
                title="Control Type Test",
                description="Testing control types",
                control_type=control_type,
                requirement="TEST.001",
            )
            assert control.control_type == control_type


class TestComplianceReport:
    """Test compliance report data structure and behavior."""

    def test_compliance_report_creation_minimal(self) -> None:
        """Test compliance report creation with minimal fields."""
        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=85.5,
            status=ComplianceStatus.COMPLIANT,
        )

        assert report.standard == ComplianceStandard.SOC_2
        assert report.overall_score == 85.5
        assert report.status == ComplianceStatus.COMPLIANT
        assert report.risk_level == "low"  # Should be calculated from score
        assert isinstance(report.id, UUID)
        assert isinstance(report.timestamp, datetime)
        assert len(report.controls) == 0
        assert len(report.findings) == 0
        assert len(report.recommendations) == 0

    def test_compliance_report_creation_full(self) -> None:
        """Test compliance report creation with all fields."""
        controls = [
            ComplianceControl(
                id="CTRL-1",
                standard=ComplianceStandard.SOC_2,
                category="Security",
                title="Control 1",
                description="Test control 1",
                control_type=ControlType.PREVENTIVE,
                requirement="CC1.1",
            ),
            ComplianceControl(
                id="CTRL-2",
                standard=ComplianceStandard.SOC_2,
                category="Security",
                title="Control 2",
                description="Test control 2",
                control_type=ControlType.DETECTIVE,
                requirement="CC2.1",
            ),
        ]

        findings = [
            {
                "control_id": "CTRL-1",
                "title": "Control 1 Finding",
                "status": "non_compliant",
                "score": 50.0,
                "gaps": ["Gap 1"],
            }
        ]

        recommendations = ["Recommendation 1", "Recommendation 2"]

        now = datetime.now(timezone.utc)
        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=65.0,
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            controls=controls,
            findings=findings,
            recommendations=recommendations,
            period_start=now - timedelta(days=30),
            period_end=now,
            prepared_by="Test Assessor",
            reviewed_by="Security Manager",
            approved_by="CISO",
        )

        assert report.standard == ComplianceStandard.SOC_2
        assert report.overall_score == 65.0
        assert report.status == ComplianceStatus.PARTIALLY_COMPLIANT
        assert report.risk_level == "medium"  # Should be calculated from score
        assert len(report.controls) == 2
        assert len(report.findings) == 1
        assert len(report.recommendations) == 2
        assert report.prepared_by == "Test Assessor"
        assert report.reviewed_by == "Security Manager"
        assert report.approved_by == "CISO"

    def test_compliance_report_risk_level_calculation(self) -> None:
        """Test risk level calculation based on score."""
        # Test high risk
        high_risk_report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=45.0,
            status=ComplianceStatus.NON_COMPLIANT,
        )
        assert high_risk_report.risk_level == "high"

        # Test medium risk
        medium_risk_report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=75.0,
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
        )
        assert medium_risk_report.risk_level == "medium"

        # Test low risk
        low_risk_report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=95.0,
            status=ComplianceStatus.COMPLIANT,
        )
        assert low_risk_report.risk_level == "low"

    def test_compliance_report_serialization(self) -> None:
        """Test compliance report serialization."""
        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=80.0,
            status=ComplianceStatus.COMPLIANT,
            findings=[{"test": "finding"}],
            recommendations=["test recommendation"],
        )

        # Test JSON serialization
        report_dict: dict[str, object] = {
            "id": str(report.id),
            "timestamp": report.timestamp.isoformat(),
            "standard": report.standard.value,
            "overall_score": report.overall_score,
            "status": report.status.value,
            "risk_level": report.risk_level,
            "findings": report.findings,
            "recommendations": report.recommendations,
            "prepared_by": report.prepared_by,
        }

        # Type ignore for len() calls since we know these are lists
        assert len(report_dict["findings"]) == 1  # type: ignore
        assert len(report_dict["recommendations"]) == 1  # type: ignore

        assert isinstance(report_dict["id"], str)
        assert report_dict["standard"] == "soc_2"
        assert report_dict["status"] == "compliant"
        assert report_dict["risk_level"] == "low"


class TestAuditTrail:
    """Test audit trail functionality."""

    def test_audit_trail_creation(self) -> None:
        """Test audit trail entry creation."""
        entry = AuditTrail(
            user_id="user123",
            action="compliance_assessment",
            resource="soc_2",
            result="Score: 85%",
        )

        assert entry.user_id == "user123"
        assert entry.action == "compliance_assessment"
        assert entry.resource == "soc_2"
        assert entry.result == "Score: 85%"
        assert isinstance(entry.id, UUID)
        assert isinstance(entry.timestamp, datetime)
        assert entry.ip_address is None
        assert entry.session_id is None
        assert len(entry.details) == 0

    def test_audit_trail_creation_with_details(self) -> None:
        """Test audit trail entry creation with all details."""
        entry = AuditTrail(
            user_id="user456",
            action="control_update",
            resource="CTRL-001",
            result="Updated control status",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            session_id="session-123",
            details={
                "old_status": "not_assessed",
                "new_status": "compliant",
                "score_change": "+25%",
            },
        )

        assert entry.user_id == "user456"
        assert entry.ip_address == "192.168.1.100"
        assert entry.user_agent == "Mozilla/5.0"
        assert entry.session_id == "session-123"
        assert entry.details["old_status"] == "not_assessed"
        assert entry.details["new_status"] == "compliant"

    def test_audit_trail_order_invariant(self) -> None:
        """Test that audit trail maintains proper field order."""
        # This test ensures the dataclass field order is correct
        entry = AuditTrail(
            user_id="test", action="test", resource="test", result="test"
        )

        # Should be able to create without errors
        assert entry.user_id == "test"
        assert isinstance(entry.id, UUID)


class TestSOC2Assessment:
    """Test SOC 2 compliance assessment."""

    def test_soc2_assessment_initialization(self) -> None:
        """Test SOC 2 assessor initialization."""
        assessor = SOC2Assessment()
        assert isinstance(assessor, ComplianceAssessment)

    def test_soc2_security_control_assessment_compliant(self) -> None:
        """Test SOC 2 security control assessment - compliant case."""
        assessor = SOC2Assessment()

        # Create control with no high-severity events
        control = ComplianceControl(
            id="SOC2-SEC-001",
            standard=ComplianceStandard.SOC_2,
            category="Security",
            title="Security Control",
            description="Test security control",
            control_type=ControlType.PREVENTIVE,
            requirement="CC6.1",
        )

        # Mock security monitor with no high-severity events
        mock_monitor = Mock()
        mock_monitor.get_events.return_value = []

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            assessed_controls = assessor.assess_compliance([control])

        assessed_control = assessed_controls[0]
        assert assessed_control.score == 100.0
        assert assessed_control.implementation_status == ComplianceStatus.COMPLIANT
        assert len(assessed_control.evidence) == 1
        assert (
            "No high-severity security events detected" in assessed_control.evidence[0]
        )

    def test_soc2_security_control_assessment_partially_compliant(self) -> None:
        """Test SOC 2 security control assessment - partially compliant case."""
        assessor = SOC2Assessment()

        control = ComplianceControl(
            id="SOC2-SEC-002",
            standard=ComplianceStandard.SOC_2,
            category="Security",
            title="Security Control",
            description="Test security control",
            control_type=ControlType.PREVENTIVE,
            requirement="CC6.2",
        )

        # Mock security monitor with some high-severity events
        high_severity_event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=ThreatSeverity.HIGH,
            description="High severity event",
            source="scanner",
            timestamp=datetime.now(timezone.utc),
        )

        mock_monitor = Mock()
        mock_monitor.get_events.return_value = [high_severity_event]

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            assessed_controls = assessor.assess_compliance([control])

        assessed_control = assessed_controls[0]
        assert assessed_control.score == 75.0
        assert (
            assessed_control.implementation_status
            == ComplianceStatus.PARTIALLY_COMPLIANT
        )
        assert len(assessed_control.gaps) == 1
        assert "Some high-severity security events detected" in assessed_control.gaps[0]

    def test_soc2_security_control_assessment_non_compliant(self) -> None:
        """Test SOC 2 security control assessment - non-compliant case."""
        assessor = SOC2Assessment()

        control = ComplianceControl(
            id="SOC2-SEC-003",
            standard=ComplianceStandard.SOC_2,
            category="Security",
            title="Security Control",
            description="Test security control",
            control_type=ControlType.PREVENTIVE,
            requirement="CC6.3",
        )

        # Mock security monitor with many high-severity events
        high_severity_events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.HIGH if i < 3 else ThreatSeverity.CRITICAL,
                description=f"High severity event {i}",
                source="scanner",
                timestamp=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        mock_monitor = Mock()
        mock_monitor.get_events.return_value = high_severity_events

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            assessed_controls = assessor.assess_compliance([control])

        assessed_control = assessed_controls[0]
        assert assessed_control.score == 25.0
        assert assessed_control.implementation_status == ComplianceStatus.NON_COMPLIANT
        assert len(assessed_control.gaps) == 1
        assert "Excessive high-severity security events" in assessed_control.gaps[0]
        assert len(assessed_control.remediation_actions) == 2

    def test_soc2_availability_control_assessment(self) -> None:
        """Test SOC 2 availability control assessment."""
        assessor = SOC2Assessment()

        control = ComplianceControl(
            id="SOC2-AVAIL-001",
            standard=ComplianceStandard.SOC_2,
            category="Availability",
            title="Availability Control",
            description="Test availability control",
            control_type=ControlType.DETECTIVE,
            requirement="A1.1",
        )

        # Mock security monitor with availability-related events
        availability_event = SecurityEvent(
            event_type=SecurityEventType.ANOMALY_DETECTED,
            severity=ThreatSeverity.MEDIUM,
            description="Service availability issue",
            source="monitor",
            timestamp=datetime.now(timezone.utc),
        )

        mock_monitor = Mock()
        mock_monitor.get_events.return_value = [availability_event]

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            assessed_controls = assessor.assess_compliance([control])

        assessed_control = assessed_controls[0]
        assert (
            assessed_control.score == 60.0
        )  # Should be lower due to availability events
        assert (
            assessed_control.implementation_status
            == ComplianceStatus.PARTIALLY_COMPLIANT
        )

    def test_soc2_confidentiality_control_assessment(self) -> None:
        """Test SOC 2 confidentiality control assessment."""
        assessor = SOC2Assessment()

        control = ComplianceControl(
            id="SOC2-CONF-001",
            standard=ComplianceStandard.SOC_2,
            category="Confidentiality",
            title="Confidentiality Control",
            description="Test confidentiality control",
            control_type=ControlType.PREVENTIVE,
            requirement="C2.1",
        )

        # Mock security monitor with confidentiality violation
        confidentiality_event = SecurityEvent(
            event_type=SecurityEventType.SECURITY_BREACH,
            severity=ThreatSeverity.HIGH,
            description="Data confidentiality violation",
            source="ids",
            timestamp=datetime.now(timezone.utc),
        )

        mock_monitor = Mock()
        mock_monitor.get_events.return_value = [confidentiality_event]

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            assessed_controls = assessor.assess_compliance([control])

        assessed_control = assessed_controls[0]
        assert (
            assessed_control.score == 40.0
        )  # Low score due to confidentiality violation
        assert assessed_control.implementation_status == ComplianceStatus.NON_COMPLIANT

    def test_soc2_evidence_generation(self) -> None:
        """Test SOC 2 evidence generation."""
        assessor = SOC2Assessment()

        control = ComplianceControl(
            id="SOC2-EVIDENCE-001",
            standard=ComplianceStandard.SOC_2,
            category="Security",
            title="Evidence Test Control",
            description="Test evidence generation",
            control_type=ControlType.PREVENTIVE,
            requirement="CC6.1",
        )

        # Mock security monitor with events
        events = [
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.LOW,
                description="Normal event",
                source="monitor",
                timestamp=datetime.now(timezone.utc),
            ),
            SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.HIGH,
                description="Suspicious event",
                source="ids",
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        mock_monitor = Mock()
        mock_monitor.get_events.return_value = events

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            evidence = assessor.generate_evidence(control)

        assert len(evidence) >= 2  # Should have at least 2 evidence items
        assert "Security events analyzed: 2" in evidence
        assert "High-severity events: 1" in evidence
        assert any("Suspicious event" in e for e in evidence)


class TestComplianceEngine:
    """Test compliance engine functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_compliance_engine()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_compliance_engine()

    def test_compliance_engine_initialization(self) -> None:
        """Test compliance engine initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = ComplianceEngine(storage_path=Path(temp_dir))

            assert engine.storage_path == Path(temp_dir)
            assert len(engine.assessors) == 1  # Should have SOC2 assessor
            assert ComplianceStandard.SOC_2 in engine.assessors
            assert len(engine.controls) > 0  # Should have default SOC2 controls
            assert len(engine.reports) == 0
            assert len(engine.audit_trail) == 0

    def test_compliance_engine_add_control(self) -> None:
        """Test adding compliance controls."""
        engine = ComplianceEngine()

        control = ComplianceControl(
            id="CUSTOM-001",
            standard=ComplianceStandard.ISO_27001,
            category="Custom",
            title="Custom Control",
            description="Custom compliance control",
            control_type=ControlType.PREVENTIVE,
            requirement="CUSTOM.001",
        )

        engine.add_control(control)

        iso_controls = engine.get_controls(ComplianceStandard.ISO_27001)
        assert len(iso_controls) == 1
        assert iso_controls[0].id == "CUSTOM-001"

    def test_compliance_engine_duplicate_control_id(self) -> None:
        """Test handling duplicate control IDs."""
        engine = ComplianceEngine()

        control1 = ComplianceControl(
            id="DUPLICATE-001",
            standard=ComplianceStandard.SOC_2,
            category="Test",
            title="First Control",
            description="First control",
            control_type=ControlType.PREVENTIVE,
            requirement="TEST.001",
        )

        control2 = ComplianceControl(
            id="DUPLICATE-001",  # Same ID
            standard=ComplianceStandard.SOC_2,
            category="Test",
            title="Second Control",
            description="Second control",
            control_type=ControlType.DETECTIVE,
            requirement="TEST.002",
        )

        engine.add_control(control1)
        engine.add_control(control2)  # Should allow duplicate but warn

        # Should have both controls
        soc2_controls = engine.get_controls(ComplianceStandard.SOC_2)
        duplicate_controls = [c for c in soc2_controls if c.id == "DUPLICATE-001"]
        assert len(duplicate_controls) == 2

    def test_compliance_engine_assess_soc2_compliance(self) -> None:
        """Test SOC 2 compliance assessment."""
        engine = ComplianceEngine()

        # Mock security monitor to return no events
        mock_monitor = Mock()
        mock_monitor.get_events.return_value = []

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            report = engine.assess_compliance(ComplianceStandard.SOC_2)

        assert report.standard == ComplianceStandard.SOC_2
        assert isinstance(report.overall_score, float)
        assert 0 <= report.overall_score <= 100
        assert report.status in ComplianceStatus
        assert isinstance(report.controls, list)
        assert len(report.controls) > 0  # Should have SOC2 controls
        assert report.period_start <= report.period_end

        # Report should be saved
        assert len(engine.reports) == 1
        assert engine.reports[0].id == report.id

    def test_compliance_engine_assess_unsupported_standard(self) -> None:
        """Test assessment of unsupported compliance standard."""
        engine = ComplianceEngine()

        # Try to assess a standard without an assessor
        with pytest.raises(ComplianceError, match="No assessor available"):
            engine.assess_compliance(ComplianceStandard.PCI_DSS)

    def test_compliance_engine_get_reports(self) -> None:
        """Test retrieving compliance reports."""
        engine = ComplianceEngine()

        # Create some reports
        for i in range(3):
            report = ComplianceReport(
                standard=ComplianceStandard.SOC_2,
                overall_score=80.0 + i,
                status=ComplianceStatus.COMPLIANT,
            )
            engine.reports.append(report)

        # Get all reports
        all_reports = engine.get_reports(limit=10)
        assert len(all_reports) == 3

        # Get reports for specific standard
        soc2_reports = engine.get_reports(standard=ComplianceStandard.SOC_2, limit=5)
        assert len(soc2_reports) == 3

        # Get reports with limit
        limited_reports = engine.get_reports(limit=2)
        assert len(limited_reports) == 2

        # Reports should be sorted by timestamp descending
        timestamps = [r.timestamp for r in limited_reports]
        assert timestamps[0] >= timestamps[1]

    def test_compliance_engine_compliance_summary(self) -> None:
        """Test compliance summary generation."""
        engine = ComplianceEngine()

        # The default engine should have SOC 2 controls
        summary = engine.get_compliance_summary()

        assert isinstance(summary, dict)
        assert "soc_2" in summary

        soc2_summary = summary["soc_2"]
        assert "overall_score" in soc2_summary
        assert "total_controls" in soc2_summary
        assert "status_counts" in soc2_summary
        assert isinstance(soc2_summary["overall_score"], float)
        assert isinstance(soc2_summary["total_controls"], int)
        assert isinstance(soc2_summary["status_counts"], dict)

    def test_compliance_engine_export_json(self) -> None:
        """Test exporting compliance report as JSON."""
        engine = ComplianceEngine()

        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=85.5,
            status=ComplianceStatus.COMPLIANT,
            controls=[
                ComplianceControl(
                    id="EXPORT-001",
                    standard=ComplianceStandard.SOC_2,
                    category="Test",
                    title="Export Test Control",
                    description="Test control for export",
                    control_type=ControlType.PREVENTIVE,
                    requirement="EXPORT.001",
                    score=90.0,
                    evidence=["Evidence 1"],
                    gaps=[],
                    remediation_actions=[],
                )
            ],
            findings=[],
            recommendations=["Recommendation 1"],
        )

        engine.reports.append(report)

        json_export = engine.export_report(report.id, format="json")

        assert isinstance(json_export, str)
        export_data = json.loads(json_export)

        assert export_data["standard"] == "soc_2"
        assert export_data["overall_score"] == 85.5
        assert export_data["status"] == "compliant"
        assert len(export_data["controls"]) == 1
        assert export_data["controls"][0]["id"] == "EXPORT-001"
        assert export_data["controls"][0]["score"] == 90.0

    def test_compliance_engine_export_csv(self) -> None:
        """Test exporting compliance report as CSV."""
        engine = ComplianceEngine()

        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=75.0,
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            controls=[
                ComplianceControl(
                    id="CSV-001",
                    standard=ComplianceStandard.SOC_2,
                    category="Test",
                    title="CSV Export Control 1",
                    description="Test control 1",
                    control_type=ControlType.PREVENTIVE,
                    requirement="CSV.001",
                    score=80.0,
                    evidence=["Evidence 1", "Evidence 2"],
                    gaps=["Gap 1"],
                    remediation_actions=["Action 1"],
                ),
                ComplianceControl(
                    id="CSV-002",
                    standard=ComplianceStandard.SOC_2,
                    category="Test",
                    title="CSV Export Control 2",
                    description="Test control 2",
                    control_type=ControlType.DETECTIVE,
                    requirement="CSV.002",
                    score=70.0,
                    evidence=[],
                    gaps=["Gap 2", "Gap 3"],
                    remediation_actions=["Action 2", "Action 3"],
                ),
            ],
            findings=[],
            recommendations=[],
        )

        engine.reports.append(report)

        csv_export = engine.export_report(report.id, format="csv")

        assert isinstance(csv_export, str)
        lines = csv_export.strip().split("\n")

        # Should have header + data rows
        assert len(lines) >= 2

        # Check header
        header = lines[0].split(",")
        assert "Control ID" in header
        assert "Category" in header
        assert "Title" in header
        assert "Score" in header
        assert "Status" in header

    def test_compliance_engine_export_unsupported_format(self) -> None:
        """Test exporting with unsupported format."""
        engine = ComplianceEngine()

        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=85.0,
            status=ComplianceStatus.COMPLIANT,
        )

        engine.reports.append(report)

        with pytest.raises(ComplianceError, match="Unsupported format"):
            engine.export_report(report.id, format="unsupported")

    def test_compliance_engine_audit_trail_logging(self) -> None:
        """Test audit trail logging."""
        engine = ComplianceEngine()

        # Perform action that should log to audit trail
        initial_count = len(engine.audit_trail)

        engine._log_audit_event(
            user_id="test_user",
            action="test_action",
            resource="test_resource",
            result="success",
            details={"key": "value"},
        )

        assert len(engine.audit_trail) == initial_count + 1

        audit_entry = engine.audit_trail[-1]
        assert audit_entry.user_id == "test_user"
        assert audit_entry.action == "test_action"
        assert audit_entry.resource == "test_resource"
        assert audit_entry.result == "success"
        assert audit_entry.details["key"] == "value"

    def test_compliance_engine_get_audit_trail(self) -> None:
        """Test retrieving audit trail entries."""
        engine = ComplianceEngine()

        # Add some audit entries
        for i in range(5):
            engine._log_audit_event(
                user_id=f"user_{i}",
                action="test_action",
                resource="test_resource",
                result=f"result_{i}",
            )

        # Get all audit entries
        all_entries = engine.get_audit_trail(limit=10)
        assert len(all_entries) == 5

        # Filter by user
        user_0_entries = engine.get_audit_trail(user_id="user_0")
        assert len(user_0_entries) == 1
        assert user_0_entries[0].user_id == "user_0"

        # Filter by action
        action_entries = engine.get_audit_trail(action="test_action")
        assert len(action_entries) == 5

        # Test limit
        limited_entries = engine.get_audit_trail(limit=3)
        assert len(limited_entries) == 3

    def test_compliance_engine_persistence(self) -> None:
        """Test compliance engine data persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            # Create first engine and add control
            engine1 = ComplianceEngine(storage_path=storage_path)
            custom_control = ComplianceControl(
                id="PERSIST-001",
                standard=ComplianceStandard.SOC_2,
                category="Persistence",
                title="Persistence Test Control",
                description="Test persistence",
                control_type=ControlType.PREVENTIVE,
                requirement="PERSIST.001",
                score=85.0,
            )
            engine1.add_control(custom_control)

            # Log audit entry
            engine1._log_audit_event(
                user_id="persist_user",
                action="persist_test",
                resource="PERSIST-001",
                result="success",
            )

            # Create second engine and check persistence
            engine2 = ComplianceEngine(storage_path=storage_path)

            # Should have persisted control
            persisted_controls = engine2.get_controls(ComplianceStandard.SOC_2)
            persisted_control = next(
                (c for c in persisted_controls if c.id == "PERSIST-001"), None
            )
            assert persisted_control is not None
            assert persisted_control.score == 85.0

            # Should have persisted audit trail
            audit_entries = engine2.get_audit_trail(user_id="persist_user")
            assert len(audit_entries) == 1
            assert audit_entries[0].action == "persist_test"

    def test_global_compliance_engine_singleton(self) -> None:
        """Test global compliance engine singleton behavior."""
        reset_compliance_engine()

        engine1 = get_compliance_engine()
        engine2 = get_compliance_engine()

        # Should return the same instance
        assert engine1 is engine2

        # Reset and verify new instance
        reset_compliance_engine()
        engine3 = get_compliance_engine()
        assert engine3 is not engine1


class TestCompliancePerformance:
    """Performance tests for compliance reporting."""

    def test_compliance_assessment_performance(self) -> None:
        """Test compliance assessment performance."""
        engine = ComplianceEngine()

        # Mock security monitor for performance
        mock_monitor = Mock()
        mock_monitor.get_events.return_value = []

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            start_time = time.time()

            # Run multiple assessments
            for _i in range(10):
                report = engine.assess_compliance(ComplianceStandard.SOC_2)
                assert report.standard == ComplianceStandard.SOC_2

            assessment_time = time.time() - start_time

            # Should complete assessments efficiently (< 5 seconds for 10 assessments)
            assert assessment_time < 5.0
            assert len(engine.reports) == 10

    def test_control_management_performance(self) -> None:
        """Test control management performance."""
        engine = ComplianceEngine()

        start_time = time.time()

        # Add many controls
        for i in range(100):
            control = ComplianceControl(
                id=f"PERF-{i:03d}",
                standard=ComplianceStandard.SOC_2,
                category="Performance",
                title=f"Performance Test Control {i}",
                description=f"Control for performance testing {i}",
                control_type=ControlType.PREVENTIVE,
                requirement=f"PERF.{i:03d}",
            )
            engine.add_control(control)

        management_time = time.time() - start_time

        # Should handle control additions efficiently (< 2 seconds for 100 controls)
        assert management_time < 2.0

        # Verify controls were added
        soc2_controls = engine.get_controls(ComplianceStandard.SOC_2)
        assert len(soc2_controls) >= 100

        # Count performance test controls
        perf_controls = [c for c in soc2_controls if c.category == "Performance"]
        assert len(perf_controls) == 100

    def test_report_generation_performance(self) -> None:
        """Test report generation performance."""
        ComplianceEngine()

        # Create large report
        controls = []
        for i in range(50):
            control = ComplianceControl(
                id=f"REPORT-{i:03d}",
                standard=ComplianceStandard.SOC_2,
                category="Report",
                title=f"Report Test Control {i}",
                description=f"Control for report testing {i}",
                control_type=ControlType.DETECTIVE,
                requirement=f"REPORT.{i:03d}",
                score=50.0 + (i % 50),
                evidence=[f"Evidence {i}"],
                gaps=[f"Gap {i}"] if i % 10 == 0 else [],
                remediation_actions=[f"Action {i}"],
            )
            controls.append(control)

        findings = [
            {
                "control_id": controls[i].id,
                "title": controls[i].title,
                "status": "non_compliant" if i % 10 == 0 else "partially_compliant",
                "score": controls[i].score,
                "gaps": controls[i].gaps,
            }
            for i in range(len(controls))
        ]

        recommendations = [f"Recommendation {i}" for i in range(20)]

        start_time = time.time()

        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=75.0,
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            controls=controls,
            findings=findings,
            recommendations=recommendations,
        )

        generation_time = time.time() - start_time

        # Should generate report quickly (< 0.1 seconds for 50 controls)
        assert generation_time < 0.1
        assert len(report.controls) == 50
        assert len(report.findings) == 50
        assert len(report.recommendations) == 20

    def test_export_performance(self) -> None:
        """Test report export performance."""
        engine = ComplianceEngine()

        # Create large report
        controls = [
            ComplianceControl(
                id=f"EXPORT-{i:03d}",
                standard=ComplianceStandard.SOC_2,
                category="Export",
                title=f"Export Test Control {i}",
                description=f"Control for export testing {i}",
                control_type=ControlType.PREVENTIVE,
                requirement=f"EXPORT.{i:03d}",
                score=60.0 + (i % 40),
                evidence=[f"Evidence {i}", f"Evidence {i + 1}"],
                gaps=[f"Gap {i}"] if i % 5 == 0 else [],
            )
            for i in range(100)
        ]

        report = ComplianceReport(
            standard=ComplianceStandard.SOC_2,
            overall_score=70.0,
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            controls=controls,
            findings=[
                {
                    "control_id": controls[i].id,
                    "title": controls[i].title,
                    "status": "non_compliant",
                    "score": controls[i].score,
                    "gaps": controls[i].gaps,
                }
                for i in range(len(controls))
            ],
            recommendations=[f"Recommendation {i}" for i in range(30)],
        )

        engine.reports.append(report)

        # Test JSON export performance
        start_time = time.time()
        json_export = engine.export_report(report.id, format="json")
        json_time = time.time() - start_time

        # Should export JSON quickly (< 1 second for 100 controls)
        assert json_time < 1.0
        assert isinstance(json_export, str)
        assert len(json_export) > 0

        # Test CSV export performance
        start_time = time.time()
        csv_export = engine.export_report(report.id, format="csv")
        csv_time = time.time() - start_time

        # Should export CSV quickly (< 0.5 seconds for 100 controls)
        assert csv_time < 0.5
        assert isinstance(csv_export, str)
        assert len(csv_export.split("\n")) >= 2  # Header + data rows

    def test_concurrent_compliance_operations(self) -> None:
        """Test concurrent compliance operations."""
        engine = ComplianceEngine()

        def compliance_worker(worker_id: int) -> dict[str, int | str]:
            """Worker function for compliance operations."""
            results: dict[str, int | str] = {
                "controls_added": 0,
                "assessments_completed": 0,
                "errors": 0,
            }

            try:
                # Add controls
                for i in range(10):
                    control = ComplianceControl(
                        id=f"CONCURRENT-{worker_id:02d}-{i:03d}",
                        standard=ComplianceStandard.SOC_2,
                        category="Concurrent",
                        title=f"Concurrent Control {worker_id}-{i}",
                        description=f"Control from worker {worker_id}",
                        control_type=ControlType.PREVENTIVE,
                        requirement=f"CONCURRENT.{worker_id:02d}.{i:03d}",
                    )
                    engine.add_control(control)
                    results["controls_added"] = int(results["controls_added"]) + 1

                # Mock security monitor
                mock_monitor = Mock()
                mock_monitor.get_events.return_value = []

                with patch(
                    "importobot.security.compliance.get_security_monitor",
                    return_value=mock_monitor,
                ):
                    # Perform assessment
                    engine.assess_compliance(ComplianceStandard.SOC_2)
                    results["assessments_completed"] = (
                        int(results["assessments_completed"]) + 1
                    )

            except Exception as e:
                results["errors"] = int(results["errors"]) + 1
                results["error"] = str(e)

            return results

        # Run multiple threads
        threads = []
        start_time = time.time()

        for worker_id in range(5):
            thread = threading.Thread(target=compliance_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
            # In a real test, we'd collect results from threads

        concurrent_time = time.time() - start_time

        # Should handle concurrent operations efficiently (< 3 seconds for 5 workers)
        assert concurrent_time < 3.0

        # Verify that operations completed
        total_controls = len(engine.get_controls(ComplianceStandard.SOC_2))
        assert total_controls >= 50  # 5 workers * 10 controls each
        assert len(engine.reports) >= 5  # At least 5 assessments


class TestComplianceInvariants:
    """Invariant tests for compliance reporting system."""

    def test_compliance_score_invariant(self) -> None:
        """Test that compliance scores remain within valid bounds."""
        controls = []

        # Test various score values
        scores = [0.0, 25.5, 50.0, 75.5, 100.0]

        for score in scores:
            control = ComplianceControl(
                id=f"SCORE-TEST-{score}",
                standard=ComplianceStandard.SOC_2,
                category="Test",
                title=f"Score Test {score}",
                description=f"Testing score {score}",
                control_type=ControlType.PREVENTIVE,
                requirement=f"SCORE.{score}",
                score=score,
            )
            controls.append(control)

        # All scores should be within bounds
        for control in controls:
            assert 0.0 <= control.score <= 100.0

    def test_compliance_control_field_consistency(self) -> None:
        """Test that compliance control fields maintain consistency."""
        control = ComplianceControl(
            id="CONSISTENCY-TEST",
            standard=ComplianceStandard.SOC_2,
            category="Test",
            title="Consistency Test",
            description="Testing field consistency",
            control_type=ControlType.PREVENTIVE,
            requirement="CONSISTENCY.001",
            score=85.5,
            evidence=["Evidence 1"],
            gaps=["Gap 1"],
            remediation_actions=["Action 1"],
        )

        # Enum fields should match expected values
        assert control.standard in ComplianceStandard
        assert control.implementation_status in ComplianceStatus
        assert control.control_type in ControlType

        # List fields should be properly typed
        assert isinstance(control.evidence, list)
        assert all(isinstance(e, str) for e in control.evidence)
        assert isinstance(control.gaps, list)
        assert all(isinstance(g, str) for g in control.gaps)
        assert isinstance(control.remediation_actions, list)
        assert all(isinstance(a, str) for a in control.remediation_actions)

        # Score should be float within bounds
        assert isinstance(control.score, float)
        assert 0.0 <= control.score <= 100.0

    def test_compliance_report_calculation_invariant(self) -> None:
        """Test compliance report score calculation invariants."""
        # Test with different score distributions
        test_cases = [
            ([100.0, 100.0, 100.0], 100.0, "compliant", "low"),
            ([90.0, 80.0, 70.0], 80.0, "partially_compliant", "medium"),
            ([60.0, 50.0, 40.0], 50.0, "partially_compliant", "medium"),
            ([20.0, 10.0, 0.0], 10.0, "non_compliant", "high"),
        ]

        for scores, expected_avg, expected_status, expected_risk in test_cases:
            controls = [
                ComplianceControl(
                    id=f"SCORE-CALC-{i}",
                    standard=ComplianceStandard.SOC_2,
                    category="Test",
                    title=f"Score Calculation {i}",
                    description=f"Testing score calculation {i}",
                    control_type=ControlType.PREVENTIVE,
                    requirement=f"SC.{i}",
                    score=score,
                )
                for i, score in enumerate(scores)
            ]

            report = ComplianceReport(
                standard=ComplianceStandard.SOC_2,
                controls=controls,
                overall_score=expected_avg,
                status=ComplianceStatus(expected_status),
            )

            # Risk level should be calculated correctly
            assert report.risk_level == expected_risk

    def test_audit_trail_completeness_invariant(self) -> None:
        """Test that audit trail entries are complete."""
        engine = ComplianceEngine()

        # Required fields for audit trail entry
        required_user_id = "test_user"
        required_action = "test_action"
        required_resource = "test_resource"
        required_result = "test_result"

        engine._log_audit_event(
            user_id=required_user_id,
            action=required_action,
            resource=required_resource,
            result=required_result,
        )

        audit_entry = engine.audit_trail[0]

        # All required fields should be present
        assert audit_entry.user_id == required_user_id
        assert audit_entry.action == required_action
        assert audit_entry.resource == required_resource
        assert audit_entry.result == required_result

        # Optional fields should have valid types
        assert isinstance(audit_entry.id, UUID)
        assert isinstance(audit_entry.timestamp, datetime)
        assert audit_entry.ip_address is None or isinstance(audit_entry.ip_address, str)
        assert audit_entry.user_agent is None or isinstance(audit_entry.user_agent, str)
        assert audit_entry.session_id is None or isinstance(audit_entry.session_id, str)
        assert isinstance(audit_entry.details, dict)

    def test_compliance_data_integrity_invariant(self) -> None:
        """Test that compliance data maintains integrity across operations."""
        engine = ComplianceEngine()

        # Add control with specific values
        original_control = ComplianceControl(
            id="INTEGRITY-001",
            standard=ComplianceStandard.SOC_2,
            category="Integrity",
            title="Data Integrity Test",
            description="Testing data integrity",
            control_type=ControlType.DETECTIVE,
            requirement="INTEGRITY.001",
            score=85.5,
            evidence=["Original Evidence"],
            gaps=["Original Gap"],
            remediation_actions=["Original Action"],
        )

        engine.add_control(original_control)

        # Retrieve control
        controls = engine.get_controls(ComplianceStandard.SOC_2)
        retrieved_control = next((c for c in controls if c.id == "INTEGRITY-001"), None)

        # Data should be preserved exactly
        assert retrieved_control is not None
        assert retrieved_control.id == original_control.id
        assert retrieved_control.standard == original_control.standard
        assert retrieved_control.category == original_control.category
        assert retrieved_control.title == original_control.title
        assert retrieved_control.description == original_control.description
        assert retrieved_control.control_type == original_control.control_type
        assert retrieved_control.requirement == original_control.requirement
        assert retrieved_control.score == original_control.score
        assert retrieved_control.evidence == original_control.evidence
        assert retrieved_control.gaps == original_control.gaps
        assert (
            retrieved_control.remediation_actions
            == original_control.remediation_actions
        )

    def test_compliance_thread_safety_invariant(self) -> None:
        """Test compliance engine thread safety."""
        engine = ComplianceEngine()
        errors = []

        def compliance_worker(worker_id: int) -> None:
            """Worker thread for compliance operations."""
            try:
                for i in range(20):
                    # Add control
                    control = ComplianceControl(
                        id=f"THREAD-{worker_id:02d}-{i:03d}",
                        standard=ComplianceStandard.SOC_2,
                        category="Thread",
                        title=f"Thread Control {worker_id}-{i}",
                        description=f"Control from thread {worker_id}",
                        control_type=ControlType.PREVENTIVE,
                        requirement=f"THREAD.{worker_id:02d}.{i:03d}",
                    )
                    engine.add_control(control)

                    # Get controls
                    controls = engine.get_controls(ComplianceStandard.SOC_2)
                    assert isinstance(controls, list)

                    # Log audit entry
                    engine._log_audit_event(
                        user_id=f"worker_{worker_id}",
                        action="thread_test",
                        resource=f"THREAD-{worker_id:02d}-{i:03d}",
                        result="success",
                    )

                    # Get audit trail
                    audit_entries = engine.get_audit_trail(
                        user_id=f"worker_{worker_id}"
                    )
                    assert isinstance(audit_entries, list)

            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=compliance_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Should have added all controls
        controls = engine.get_controls(ComplianceStandard.SOC_2)
        thread_controls = [c for c in controls if c.category == "Thread"]
        assert len(thread_controls) >= 60  # 3 workers * 20 controls each

        # Should have audit entries for all operations
        audit_trail = engine.get_audit_trail()
        thread_audit_entries = [e for e in audit_trail if e.action == "thread_test"]
        assert len(thread_audit_entries) >= 60


class TestConvenienceFunctions:
    """Test convenience functions for compliance reporting."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_compliance_engine()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_compliance_engine()

    def test_assess_soc2_compliance_function(self) -> None:
        """Test assess_soc2_compliance convenience function."""
        # Mock security monitor
        mock_monitor = Mock()
        mock_monitor.get_events.return_value = []

        with patch(
            "importobot.security.compliance.get_security_monitor",
            return_value=mock_monitor,
        ):
            report = assess_soc2_compliance()

        assert report.standard == ComplianceStandard.SOC_2
        assert isinstance(report.overall_score, float)
        assert report.status in ComplianceStatus

    def test_get_compliance_dashboard_function(self) -> None:
        """Test get_compliance_dashboard convenience function."""
        # Mock compliance engine
        mock_engine = Mock()
        mock_engine.get_compliance_summary.return_value = {
            "soc_2": {
                "overall_score": 85.0,
                "total_controls": 10,
                "status_counts": {"compliant": 8, "partially_compliant": 2},
            }
        }
        mock_engine.get_reports.return_value = [
            Mock(id=UUID("11111111-1111-1111-1111-111111111111")),
            Mock(standard=ComplianceStandard.SOC_2),
        ]

        with patch(
            "importobot.security.compliance.get_compliance_engine",
            return_value=mock_engine,
        ):
            dashboard = get_compliance_dashboard()

        assert "summary" in dashboard
        assert "recent_reports" in dashboard
        assert dashboard["summary"]["soc_2"]["overall_score"] == 85.0
        assert len(dashboard["recent_reports"]) == 2
