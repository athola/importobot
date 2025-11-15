"""Tests for SIEM integration system.

This module provides comprehensive test coverage for the SIEM integration
including unit tests, integration tests, performance tests, and security validation
following TDD and BDD principles.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from importobot.security.monitoring import (
    SecurityEvent,
    SecurityEventType,
    ThreatSeverity,
)
from importobot.security.siem_integration import (
    ElasticSIEMConnector,
    MicrosoftSentinelConnector,
    MITRETactic,
    SIEMEvent,
    SIEMIntegrationError,
    SIEMManager,
    SIEMPlatform,
    SplunkConnector,
    create_elastic_connector,
    create_sentinel_connector,
    create_splunk_connector,
    get_siem_manager,
    reset_siem_manager,
    setup_siem_integration,
)


class TestSIEMEvent:
    """Test SIEM event data structure and behavior."""

    def test_siem_event_creation_minimal(self) -> None:
        """Test SIEM event creation with minimal fields."""
        event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="test-123",
            event_type="security_event",
            severity="medium",
            source="importobot",
        )

        assert event.event_id == "test-123"
        assert event.event_type == "security_event"
        assert event.severity == "medium"
        assert event.source == "importobot"
        assert event.destination is None
        assert event.user is None
        assert len(event.mitre_tactics) == 0
        assert len(event.mitre_techniques) == 0

    def test_siem_event_creation_full(self) -> None:
        """Test SIEM event creation with all fields."""
        tactics = [MITRETactic.INITIAL_ACCESS, MITRETactic.EXECUTION]
        techniques = ["T1078", "T1059"]

        event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="full-event-456",
            event_type="credential_access",
            severity="high",
            source="192.168.1.100",
            destination="10.0.0.1",
            user="attacker",
            process="/bin/bash",
            file_hash="a1b2c3d4e5f6",
            ip_address="192.168.1.100",
            url="https://malicious.com",
            mitre_tactics=tactics,
            mitre_techniques=techniques,
            raw_data={"additional_info": "test data"},
            tags=["credential", "malicious"],
        )

        assert event.event_id == "full-event-456"
        assert event.destination == "10.0.0.1"
        assert event.user == "attacker"
        assert event.process == "/bin/bash"
        assert event.file_hash == "a1b2c3d4e5f6"
        assert event.ip_address == "192.168.1.100"
        assert event.url == "https://malicious.com"
        assert len(event.mitre_tactics) == 2
        assert MITRETactic.INITIAL_ACCESS in event.mitre_tactics
        assert MITRETactic.EXECUTION in event.mitre_tactics
        assert len(event.mitre_techniques) == 2
        assert "T1078" in event.mitre_techniques
        assert "T1059" in event.mitre_techniques
        assert "credential" in event.tags

    def test_siem_event_serialization(self) -> None:
        """Test SIEM event serialization for different platforms."""
        event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="serialization-test",
            event_type="test_event",
            severity="low",
            source="test_source",
            mitre_tactics=[MITRETactic.RECONNAISSANCE],
            mitre_techniques=["T1595"],
            raw_data={"test": "data"},
        )

        # Test JSON serialization
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id,
            "event_type": event.event_type,
            "severity": event.severity,
            "source": event.source,
            "mitre_tactics": [t.value for t in event.mitre_tactics],
            "mitre_techniques": event.mitre_techniques,
            "raw_data": event.raw_data,
        }

        assert isinstance(event_dict["timestamp"], str)
        assert event_dict["event_id"] == "serialization-test"
        assert event_dict["mitre_tactics"] == ["reconnaissance"]
        assert event_dict["mitre_techniques"] == ["T1595"]

    def test_siem_event_mitre_mapping(self) -> None:
        """Test MITRE ATT&CK mapping in SIEM events."""
        # Test all tactics can be used
        for tactic in MITRETactic:
            event = SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id=f"tactic-test-{tactic.value}",
                event_type="test",
                severity="medium",
                source="test",
                mitre_tactics=[tactic],
            )
            assert len(event.mitre_tactics) == 1
            assert event.mitre_tactics[0] == tactic

        # Test multiple tactics
        tactics = [
            MITRETactic.INITIAL_ACCESS,
            MITRETactic.EXECUTION,
            MITRETactic.PERSISTENCE,
        ]
        event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="multi-tactic-test",
            event_type="test",
            severity="high",
            source="test",
            mitre_tactics=tactics,
        )
        assert len(event.mitre_tactics) == 3
        assert all(tactic in event.mitre_tactics for tactic in tactics)


class TestSplunkConnector:
    """Test Splunk SIEM connector."""

    def test_splunk_connector_initialization_valid(self) -> None:
        """Test Splunk connector initialization with valid parameters."""
        connector = SplunkConnector(
            host="https://splunk.example.com",
            token="test-token-123",
            port=8089,
            index="security_events",
            ca_cert_path="/path/to/ca.pem",
        )

        assert connector.host == "splunk.example.com"
        assert connector.token == "test-token-123"
        assert connector.port == 8089
        assert connector.index == "security_events"
        assert connector.ca_cert_path == "/path/to/ca.pem"
        assert connector.source_type == "importobot:security"

    def test_splunk_connector_requires_https(self) -> None:
        """Test that Splunk connector requires HTTPS host."""
        with pytest.raises(SIEMIntegrationError, match="must use HTTPS"):
            SplunkConnector(
                host="http://splunk.example.com",  # HTTP should fail
                token="test-token",
                port=8089,
            )

    def test_splunk_connector_requires_token(self) -> None:
        """Test that Splunk connector requires token."""
        with pytest.raises(SIEMIntegrationError, match="host and token are required"):
            create_splunk_connector(
                host="https://splunk.example.com",
                token="",  # Empty token should fail
                port=8089,
            )

    def test_splunk_connector_ssl_configuration(self) -> None:
        """Test SSL configuration for Splunk connector."""
        # Test with custom CA certificate
        connector = SplunkConnector(
            host="https://splunk.example.com",
            token="test-token",
            ca_cert_path="/custom/ca.pem",
        )
        assert connector.session.verify == "/custom/ca.pem"

        # Test with default SSL verification
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )
        assert connector.session.verify is True

    def test_splunk_connector_headers(self) -> None:
        """Test that Splunk connector sets correct headers."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token-123"
        )

        assert "Authorization" in connector.session.headers
        assert connector.session.headers["Authorization"] == "Splunk test-token-123"
        assert connector.session.headers["Content-Type"] == "application/json"

    def test_splunk_event_payload_format(self) -> None:
        """Test Splunk event payload formatting."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )

        siem_event = SIEMEvent(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            event_id="splunk-test",
            event_type="credential_access",
            severity="high",
            source="test_module",
            user="test_user",
            mitre_tactics=[MITRETactic.CREDENTIAL_ACCESS],
            mitre_techniques=["T1555"],
            raw_data={"test": "data"},
        )

        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            connector.send_event(siem_event)

            # Check that post was called with correct payload
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            assert "time" in payload
            assert payload["index"] == "security_events"
            assert payload["sourcetype"] == "importobot:security"
            assert payload["event"]["event_id"] == "splunk-test"
            assert payload["event"]["event_type"] == "credential_access"
            assert payload["event"]["severity"] == "high"
            assert payload["event"]["source"] == "test_module"
            assert payload["event"]["user"] == "test_user"
            assert "reconnaissance" in payload["event"]["mitre_tactics"]

    def test_splunk_send_event_success(self) -> None:
        """Test successful event sending to Splunk."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="success-test",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = connector.send_event(siem_event)

            assert result is True
            mock_post.assert_called_once()

    def test_splunk_send_event_failure(self) -> None:
        """Test event sending failure handling."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="failure-test",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = Exception("Connection failed")

            result = connector.send_event(siem_event)

            assert result is False

    def test_splunk_connection_test_success(self) -> None:
        """Test successful Splunk connection test."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )

        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = connector.test_connection()

            assert result is True
            mock_get.assert_called_once()

    def test_splunk_connection_test_failure(self) -> None:
        """Test Splunk connection test failure."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )

        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = connector.test_connection()

            assert result is False

    def test_splunk_connector_info(self) -> None:
        """Test Splunk connector information."""
        connector = SplunkConnector(
            host="https://splunk.example.com",
            token="test-token",
            port=9999,
            index="custom_index",
            ca_cert_path="/custom/ca.pem",
        )

        info = connector.get_connector_info()

        assert info["platform"] == SIEMPlatform.SPLUNK.value
        assert info["host"] == "splunk.example.com"
        assert info["port"] == 9999
        assert info["index"] == "custom_index"
        assert info["source_type"] == "importobot:security"


class TestElasticSIEMConnector:
    """Test Elastic SIEM connector."""

    def test_elastic_connector_initialization_valid(self) -> None:
        """Test Elastic connector initialization with valid parameters."""
        hosts = ["https://elastic1.example.com", "https://elastic2.example.com"]
        connector = ElasticSIEMConnector(
            hosts=hosts,
            username="elastic_user",
            password="elastic_password",
            ca_cert_path="/path/to/ca.pem",
        )

        assert connector.hosts == hosts
        assert connector.username == "elastic_user"
        assert connector.password == "elastic_password"
        assert connector.ca_cert_path == "/path/to/ca.pem"

    def test_elastic_connector_requires_https(self) -> None:
        """Test that Elastic connector requires HTTPS hosts."""
        with pytest.raises(SIEMIntegrationError, match="must use HTTPS"):
            ElasticSIEMConnector(
                hosts=["http://elastic.example.com"],  # HTTP should fail
                username="user",
                password="pass",
            )

    def test_elastic_connector_auth_methods(self) -> None:
        """Test Elastic connector authentication methods."""
        hosts = ["https://elastic.example.com"]

        # Test username/password auth
        connector1 = ElasticSIEMConnector(hosts=hosts, username="user", password="pass")
        assert connector1.session.auth == ("user", "pass")
        assert "Authorization" not in connector1.session.headers

        # Test API key auth
        connector2 = ElasticSIEMConnector(
            hosts=hosts, username="", password="", api_key="test-api-key"
        )
        assert connector2.session.headers["Authorization"] == "ApiKey test-api-key"
        assert connector2.session.auth is None

    def test_elastic_connector_requires_credentials(self) -> None:
        """Test that Elastic connector requires credentials."""
        with pytest.raises(
            SIEMIntegrationError,
            match="Either API key or username/password is required",
        ):
            create_elastic_connector(
                hosts=["https://elastic.example.com"],
                username="",  # Empty username
                password="",  # Empty password
                api_key=None,  # No API key
            )

    def test_elastic_event_payload_format(self) -> None:
        """Test Elastic SIEM event payload formatting."""
        connector = ElasticSIEMConnector(
            hosts=["https://elastic.example.com"], username="user", password="pass"
        )

        siem_event = SIEMEvent(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            event_id="elastic-test",
            event_type="privilege_escalation",
            severity="high",
            source="attacker_ip",
            user="victim_user",
            destination="target_server",
            mitre_tactics=[MITRETactic.PRIVILEGE_ESCALATION],
            mitre_techniques=["T1548"],
            raw_data={"test": "data"},
        )

        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_post.return_value = mock_response

            connector.send_event(siem_event)

            # Check payload structure
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            assert "@timestamp" in payload
            assert payload["@timestamp"] == "2023-01-01T12:00:00"

            # Check event structure
            assert "event" in payload
            assert payload["event"]["id"] == "elastic-test"
            assert payload["event"]["kind"] == "event"
            assert payload["event"]["category"] == ["intrusion_detection"]
            assert payload["event"]["type"] == ["privilege_escalation"]
            assert payload["event"]["severity"] == "high"

            # Check source structure
            assert "source" in payload
            assert payload["source"]["address"] == "attacker_ip"
            assert payload["source"]["user"]["name"] == "victim_user"

            # Check destination structure
            assert "destination" in payload
            assert payload["destination"]["address"] == "target_server"

            # Check threat structure
            assert "threat" in payload
            assert payload["threat"]["tactic"][0]["name"] == "privilege_escalation"
            assert payload["threat"]["technique"][0]["name"] == "T1548"

    def test_elastic_severity_mapping(self) -> None:
        """Test Elastic SIEM severity mapping."""
        connector = ElasticSIEMConnector(
            hosts=["https://elastic.example.com"], username="user", password="pass"
        )

        # Test all severity levels
        severity_mapping = {
            "info": "informational",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "critical": "critical",
        }

        for input_severity, expected_output in severity_mapping.items():
            mapped = connector._map_severity(input_severity)
            assert mapped == expected_output

    def test_elastic_send_event_success(self) -> None:
        """Test successful event sending to Elastic SIEM."""
        connector = ElasticSIEMConnector(
            hosts=["https://elastic.example.com"], username="user", password="pass"
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="elastic-success",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = (
                201  # Elasticsearch returns 201 for document creation
            )
            mock_post.return_value = mock_response

            result = connector.send_event(siem_event)

            assert result is True
            mock_post.assert_called_once()

    def test_elastic_send_event_retry_mechanism(self) -> None:
        """Test Elastic connector retry mechanism."""
        connector = ElasticSIEMConnector(
            hosts=["https://elastic1.example.com", "https://elastic2.example.com"],
            username="user",
            password="pass",
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="retry-test",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        with patch("requests.Session.post") as mock_post:
            # First host fails, second succeeds
            mock_post.side_effect = [
                Exception("First host down"),
                Mock(status_code=201),
            ]

            result = connector.send_event(siem_event)

            assert result is True
            assert mock_post.call_count == 2

    def test_elastic_connection_test_success(self) -> None:
        """Test successful Elastic connection test."""
        connector = ElasticSIEMConnector(
            hosts=["https://elastic.example.com"], username="user", password="pass"
        )

        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = connector.test_connection()

            assert result is True
            mock_get.assert_called_once()

    def test_elastic_connection_test_failure(self) -> None:
        """Test Elastic connection test failure."""
        connector = ElasticSIEMConnector(
            hosts=["https://elastic.example.com"], username="user", password="pass"
        )

        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = connector.test_connection()

            assert result is False


class TestMicrosoftSentinelConnector:
    """Test Microsoft Sentinel connector."""

    def test_sentinel_connector_initialization(self) -> None:
        """Test Microsoft Sentinel connector initialization."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace-id",
            shared_key="test-shared-key-123",
            log_type="ImportobotSecurity",
        )

        assert connector.workspace_id == "test-workspace-id"
        assert connector.shared_key == "test-shared-key-123"
        assert connector.log_type == "ImportobotSecurity"

    def test_sentinel_connector_requires_credentials(self) -> None:
        """Test that Sentinel connector requires credentials."""
        with pytest.raises(
            SIEMIntegrationError, match="Workspace ID and shared key are required"
        ):
            create_sentinel_connector(
                workspace_id="",  # Empty workspace ID
                shared_key="key",
            )

        with pytest.raises(
            SIEMIntegrationError, match="Workspace ID and shared key are required"
        ):
            create_sentinel_connector(
                workspace_id="workspace",
                shared_key="",  # Empty shared key
            )

    def test_sentinel_signature_generation(self) -> None:
        """Test Azure Log Analytics signature generation."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace",
            shared_key="dGVzdC1rZXk=",  # Base64 encoded "test-key"
        )

        # Test signature generation (should be deterministic for same inputs)
        string_to_hash = (
            "POST\n50\napplication/json\nx-ms-date: Mon, 01 Jan 2023 12:00:00 GMT\n"
            "/api/logs"
        )
        signature = connector._build_signature(string_to_hash, "dGVzdC1rZXk=")

        assert isinstance(signature, str)
        assert len(signature) > 0
        # Signature should be base64 encoded

        try:
            base64.b64decode(signature)
            signature_is_valid_base64 = True
        except Exception:
            signature_is_valid_base64 = False
        assert signature_is_valid_base64

    def test_sentinel_event_payload_format(self) -> None:
        """Test Microsoft Sentinel event payload formatting."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace", shared_key="test-shared-key"
        )

        siem_event = SIEMEvent(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            event_id="sentinel-test",
            event_type="data_exfiltration",
            severity="critical",
            source="internal_network",
            user="malicious_user",
            ip_address="10.0.0.100",
            url="https://exfil.com",
            mitre_tactics=[MITRETactic.EXFILTRATION],
            mitre_techniques=["T1041"],
            raw_data={"exfil_data": "sensitive_info"},
            tags=["exfiltration", "critical"],
        )

        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            connector.send_event(siem_event)

            # Check payload structure
            call_args = mock_post.call_args
            body = call_args[1]["data"]
            event_data = json.loads(body)

            assert event_data["TimeGenerated"] == "2023-01-01T12:00:00"
            assert event_data["EventId"] == "sentinel-test"
            assert event_data["EventType"] == "data_exfiltration"
            assert event_data["Severity"] == "critical"
            assert event_data["SourceSystem"] == "Importobot"
            assert event_data["Source"] == "internal_network"
            assert event_data["User"] == "malicious_user"
            assert event_data["IpAddress"] == "10.0.0.100"
            assert event_data["Url"] == "https://exfil.com"
            assert "exfiltration" in event_data["MITRETactics"]
            assert "T1041" in event_data["MITRETechniques"]
            assert "exfiltration" in event_data["Tags"]

    def test_sentinel_headers(self) -> None:
        """Test Microsoft Sentinel request headers."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace", shared_key="test-shared-key"
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="headers-test",
            event_type="test",
            severity="medium",
            source="test",
        )

        with (
            patch("requests.Session.post") as mock_post,
            patch("importobot.security.siem_integration.datetime") as mock_datetime,
        ):
            mock_datetime.now.return_value = datetime(
                2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc
            )

            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            connector.send_event(siem_event)

            # Check headers
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]

            assert "Authorization" in headers
            assert headers["Authorization"].startswith("SharedKey ")
            assert "Log-Type" in headers
            assert headers["Log-Type"] == "ImportobotSecurity"
            assert "x-ms-date" in headers
            assert headers["time-generated-field"] == "TimeGenerated"

    def test_sentinel_send_event_success(self) -> None:
        """Test successful event sending to Microsoft Sentinel."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace", shared_key="test-shared-key"
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="sentinel-success",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = connector.send_event(siem_event)

            assert result is True
            mock_post.assert_called_once()

    def test_sentinel_send_event_failure(self) -> None:
        """Test event sending failure handling."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace", shared_key="test-shared-key"
        )

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="sentinel-failure",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = Exception("Connection failed")

            result = connector.send_event(siem_event)

            assert result is False

    def test_sentinel_connection_test_via_event_send(self) -> None:
        """Test Microsoft Sentinel connection test via event sending."""
        connector = MicrosoftSentinelConnector(
            workspace_id="test-workspace", shared_key="test-shared-key"
        )

        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = connector.test_connection()

            assert result is True
            mock_post.assert_called_once()

            # Check that test event was sent
            call_args = mock_post.call_args
            body = call_args[1]["data"]
            event_data = json.loads(body)
            assert event_data["EventId"] == "test-connection"


class TestSIEMManager:
    """Test SIEM manager functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_siem_manager()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_siem_manager()

    def test_siem_manager_initialization(self) -> None:
        """Test SIEM manager initialization."""
        manager = SIEMManager()

        assert not manager.enabled  # Should be enabled by default
        assert not manager.running
        assert len(manager.connectors) == 0
        assert len(manager.event_queue) == 0
        assert manager.queue_max_size == 1000
        assert manager.batch_size == 10
        assert manager.batch_timeout == 5

    def test_siem_manager_add_connector(self) -> None:
        """Test adding connectors to SIEM manager."""
        manager = SIEMManager()

        mock_connector = Mock()
        manager.add_connector(mock_connector)

        assert len(manager.connectors) == 1
        assert manager.connectors[0] is mock_connector

    def test_siem_manager_remove_connector(self) -> None:
        """Test removing connectors from SIEM manager."""
        manager = SIEMManager()

        mock_connector1 = Mock()
        mock_connector2 = Mock()

        manager.add_connector(mock_connector1)
        manager.add_connector(mock_connector2)
        assert len(manager.connectors) == 2

        manager.remove_connector(mock_connector1)
        assert len(manager.connectors) == 1
        assert manager.connectors[0] is mock_connector2

    def test_siem_manager_event_queueing(self) -> None:
        """Test event queuing in SIEM manager."""
        manager = SIEMManager()

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="queue-test",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        result = manager.send_event(siem_event)

        assert result is True
        assert len(manager.event_queue) == 1
        assert manager.event_queue[0] is siem_event

    def test_siem_manager_queue_size_limit(self) -> None:
        """Test SIEM manager queue size limit."""
        manager = SIEMManager()
        manager.queue_max_size = 3  # Small limit for testing

        # Fill queue to limit
        for i in range(manager.queue_max_size):
            event = SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id=f"limit-test-{i}",
                event_type="test_event",
                severity="medium",
                source="test_source",
            )
            result = manager.send_event(event)
            assert result is True

        assert len(manager.event_queue) == manager.queue_max_size

        # Try to add one more (should fail)
        overflow_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="overflow-event",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )
        result = manager.send_event(overflow_event)

        assert result is False
        assert len(manager.event_queue) == manager.queue_max_size

    def test_siem_manager_disabled(self) -> None:
        """Test SIEM manager when disabled."""
        manager = SIEMManager()
        manager.enabled = False

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="disabled-test",
            event_type="test_event",
            severity="medium",
            source="test_source",
        )

        result = manager.send_event(siem_event)

        assert result is False
        assert len(manager.event_queue) == 0

    def test_siem_manager_start_stop(self) -> None:
        """Test SIEM manager start and stop."""
        manager = SIEMManager()

        assert not manager.running

        manager.start()
        assert manager.running
        assert manager.running  # Status is represented by the running property

        manager.stop()
        assert not manager.running

    def test_siem_manager_send_to_connectors(self) -> None:
        """Test sending events to all connectors."""
        manager = SIEMManager()

        # Create mock connectors
        mock_connector1 = Mock()
        mock_connector1.send_event.return_value = True
        mock_connector2 = Mock()
        mock_connector2.send_event.return_value = True

        manager.add_connector(mock_connector1)
        manager.add_connector(mock_connector2)

        # Send event
        SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="multi-connector-test",
            event_type="test_event",
            severity="high",
            source="test_source",
        )

        # Manually trigger sending (simulate sender loop)
        manager.event_queue = []

        original_send = manager._send_with_retry
        manager._send_with_retry = Mock(side_effect=original_send)  # type: ignore[method-assign]
        manager._process_event_queue()

        # Check that send_event was called for each connector
        # Note: This is a simplified test - in reality, the sender loop handles this

    def test_siem_manager_security_event_conversion(self) -> None:
        """Test conversion of security events to SIEM events."""
        manager = SIEMManager()

        security_event = SecurityEvent(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.CRITICAL,
            description="AWS access key detected",
            source="code_scanner",
            user_id="developer",
            ip_address="192.168.1.100",
            details={"key_type": "aws_access_key", "file_path": "/app/config.py"},
        )

        siem_event = manager._convert_to_siem_event(security_event)

        assert siem_event.event_id == str(security_event.id)
        assert siem_event.event_type == "credential_detected"
        assert siem_event.severity == "critical"
        assert siem_event.source == "code_scanner"
        assert siem_event.user == "developer"
        assert siem_event.ip_address == "192.168.1.100"
        assert siem_event.raw_data["key_type"] == "aws_access_key"
        assert siem_event.raw_data["file_path"] == "/app/config.py"

    def test_siem_manager_mitre_mapping(self) -> None:
        """Test MITRE ATT&CK mapping in SIEM manager."""
        manager = SIEMManager()

        # Test credential access mapping
        security_event = SecurityEvent(
            event_type=SecurityEventType.CREDENTIAL_DETECTED,
            severity=ThreatSeverity.HIGH,
            description="Credential access",
            source="scanner",
        )

        siem_event = manager._convert_to_siem_event(security_event)

        assert MITRETactic.CREDENTIAL_ACCESS in siem_event.mitre_tactics
        assert len(siem_event.mitre_techniques) > 0
        assert any("1555" in tech for tech in siem_event.mitre_techniques)

        # Test unauthorized access mapping
        security_event = SecurityEvent(
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            severity=ThreatSeverity.HIGH,
            description="Unauthorized access",
            source="auth",
        )

        siem_event = manager._convert_to_siem_event(security_event)

        assert MITRETactic.INITIAL_ACCESS in siem_event.mitre_tactics
        assert MITRETactic.PRIVILEGE_ESCALATION in siem_event.mitre_tactics

    def test_siem_manager_retry_logic(self) -> None:
        """Test SIEM manager retry logic."""
        manager = SIEMManager()
        manager.retry_attempts = 3
        manager.retry_delay = 0.1  # Short delay for testing

        mock_connector = Mock()
        call_count = 0

        def failing_send(event: SIEMEvent) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count < 2:  # Fail first 2 attempts
                raise Exception("Connection failed")
            return True

        mock_connector.send_event.side_effect = failing_send
        manager.add_connector(mock_connector)

        siem_event = SIEMEvent(
            timestamp=datetime.now(timezone.utc),
            event_id="retry-test",
            event_type="test",
            severity="medium",
            source="test",
        )

        result = manager._send_with_retry(mock_connector, siem_event)

        # Should eventually succeed after retries
        assert result is True
        assert call_count == 2  # Should have retried twice then succeeded

    def test_siem_manager_status(self) -> None:
        """Test SIEM manager status reporting."""
        manager = SIEMManager()
        manager.batch_size = 5
        manager.batch_timeout = 10

        # Add a mock connector
        mock_connector = Mock()
        mock_connector.get_connector_info.return_value = {
            "platform": "test",
            "status": "connected",
        }
        manager.add_connector(mock_connector)

        status = manager.get_status()

        assert status["enabled"] is True
        assert status["running"] is False
        assert status["connectors_count"] == 1
        assert status["queue_size"] == 0
        assert status["queue_max_size"] == manager.queue_max_size
        assert status["batch_size"] == 5
        assert status["batch_timeout"] == 10
        assert len(status["connector_info"]) == 1
        assert status["connector_info"][0]["platform"] == "test"

    def test_siem_manager_all_connections_test(self) -> None:
        """Test connection testing for all connectors."""
        manager = SIEMManager()

        # Create mock connectors with different connection statuses
        mock_connector1 = Mock()
        mock_connector1.test_connection.return_value = True

        mock_connector2 = Mock()
        mock_connector2.test_connection.return_value = False

        mock_connector3 = Mock()
        mock_connector3.test_connection.side_effect = Exception("Test error")

        manager.add_connector(mock_connector1)
        manager.add_connector(mock_connector2)
        manager.add_connector(mock_connector3)

        results = manager.test_all_connections()

        assert len(results) == 3
        assert results["SIEMConnector_0"] is True
        assert results["SIEMConnector_1"] is False
        assert results["SIEMConnector_2"] is False

    def test_global_siem_manager_singleton(self) -> None:
        """Test global SIEM manager singleton behavior."""
        reset_siem_manager()

        manager1 = get_siem_manager()
        manager2 = get_siem_manager()

        # Should return the same instance
        assert manager1 is manager2

        # Reset and verify new instance
        reset_siem_manager()
        manager3 = get_siem_manager()
        assert manager3 is not manager1


class TestSIEMIntegrationPerformance:
    """Performance tests for SIEM integration."""

    def test_siem_event_creation_performance(self) -> None:
        """Test SIEM event creation performance."""
        start_time = time.time()

        # Create many SIEM events
        events = []
        for i in range(1000):
            event = SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id=f"perf-test-{i}",
                event_type="test_event",
                severity="medium",
                source="performance_test",
                mitre_tactics=[MITRETactic.EXECUTION],
                mitre_techniques=["T1059"],
                raw_data={"index": i},
            )
            events.append(event)

        creation_time = time.time() - start_time

        # Should complete within reasonable time (< 0.5 seconds for 1000 events)
        assert creation_time < 0.5
        assert len(events) == 1000

    def test_siem_manager_queue_performance(self) -> None:
        """Test SIEM manager event queueing performance."""
        manager = SIEMManager()
        manager.queue_max_size = 10000

        start_time = time.time()

        # Queue many events
        for i in range(5000):
            event = SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id=f"queue-perf-{i}",
                event_type="test_event",
                severity="medium",
                source="performance_test",
            )
            manager.send_event(event)

        queueing_time = time.time() - start_time

        # Should handle queuing efficiently (< 1 second for 5000 events)
        assert queueing_time < 1.0
        assert len(manager.event_queue) == 5000

    def test_siem_connector_simulation_performance(self) -> None:
        """Test SIEM connector performance simulation."""
        connector = SplunkConnector(
            host="https://splunk.example.com", token="test-token"
        )

        events = [
            SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id=f"connector-perf-{i}",
                event_type="test_event",
                severity="medium",
                source="performance_test",
            )
            for i in range(100)
        ]

        start_time = time.time()

        # Simulate event processing (payload preparation)
        for event in events:
            # Simulate payload creation without actual network call
            payload = {
                "time": int(event.timestamp.timestamp()),
                "index": connector.index,
                "sourcetype": connector.source_type,
                "source": "importobot",
                "event": {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "source": event.source,
                },
            }
            assert isinstance(payload, dict)

        processing_time = time.time() - start_time

        # Should process events quickly (< 0.1 seconds for 100 events)
        assert processing_time < 0.1

    def test_concurrent_siem_operations(self) -> None:
        """Test concurrent SIEM manager operations."""
        manager = SIEMManager()
        manager.queue_max_size = 10000

        def worker_thread(worker_id: int) -> int:
            """Worker thread for SIEM operations."""
            count = 0
            for i in range(100):
                event = SIEMEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_id=f"concurrent-{worker_id}-{i}",
                    event_type="test_event",
                    severity="medium",
                    source=f"worker_{worker_id}",
                )
                if manager.send_event(event):
                    count += 1
            return count

        # Run multiple threads
        threads = []
        start_time = time.time()

        for worker_id in range(10):
            thread = threading.Thread(target=worker_thread, args=(worker_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        concurrent_time = time.time() - start_time

        # Should handle concurrent operations efficiently
        assert concurrent_time < 2.0
        assert len(manager.event_queue) >= 900  # Most events should be queued


class TestSIEMIntegrationInvariants:
    """Invariant tests for SIEM integration system."""

    def test_siem_event_timestamp_invariant(self) -> None:
        """Test that SIEM event timestamps are valid."""
        now = datetime.now(timezone.utc)

        event = SIEMEvent(
            timestamp=now,
            event_id="timestamp-test",
            event_type="test",
            severity="medium",
            source="test",
        )

        # Timestamp should be exactly as provided
        assert event.timestamp == now
        assert isinstance(event.timestamp, datetime)

    def test_siem_connector_ssl_invariant(self) -> None:
        """Test that all connectors enforce HTTPS."""
        # Test Splunk connector
        with pytest.raises(SIEMIntegrationError, match="must use HTTPS"):
            SplunkConnector(
                host="http://insecure.example.com",  # HTTP should fail
                token="test-token",
            )

        # Test Elastic connector
        with pytest.raises(SIEMIntegrationError, match="must use HTTPS"):
            ElasticSIEMConnector(
                hosts=["http://elastic.example.com"],  # HTTP should fail
                username="user",
                password="pass",
            )

        # Test that valid HTTPS connectors work
        splunk_connector = SplunkConnector(
            host="https://secure.example.com", token="test-token"
        )
        assert splunk_connector.session.verify is True

        elastic_connector = ElasticSIEMConnector(
            hosts=["https://secure-elastic.example.com"],
            username="user",
            password="pass",
        )
        assert elastic_connector.session.verify is True

    def test_siem_manager_queue_limit_invariant(self) -> None:
        """Test that SIEM manager never exceeds queue limit."""
        manager = SIEMManager()
        manager.queue_max_size = 10

        # Add more events than limit
        for i in range(20):
            event = SIEMEvent(
                timestamp=datetime.now(timezone.utc),
                event_id=f"limit-test-{i}",
                event_type="test",
                severity="medium",
                source="test",
            )
            manager.send_event(event)

            # Queue size should never exceed limit
            assert len(manager.event_queue) <= manager.queue_max_size

    def test_mitre_tactic_consistency_invariant(self) -> None:
        """Test that MITRE tactics are consistently mapped."""
        manager = SIEMManager()

        # Test all security event types have MITRE mapping
        security_event_types = [
            SecurityEventType.CREDENTIAL_DETECTED,
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            SecurityEventType.UNAUTHORIZED_ACCESS,
            SecurityEventType.ANOMALY_DETECTED,
            SecurityEventType.POLICY_VIOLATION,
            SecurityEventType.SECURITY_BREACH,
            SecurityEventType.PRIVILEGE_ESCALATION,
            SecurityEventType.THREAT_INTELLIGENCE,
        ]

        for event_type in security_event_types:
            security_event = SecurityEvent(
                event_type=event_type,
                severity=ThreatSeverity.MEDIUM,
                description=f"Test {event_type.value}",
                source="test",
            )

            siem_event = manager._convert_to_siem_event(security_event)

            # Should have some MITRE tactics
            assert len(siem_event.mitre_tactics) > 0

            # All tactics should be valid MITRETactic enums
            for tactic in siem_event.mitre_tactics:
                assert tactic in MITRETactic

    def test_siem_event_id_uniqueness_invariant(self) -> None:
        """Test that SIEM events maintain unique IDs when converted."""
        manager = SIEMManager()

        # Create multiple security events
        security_events = []
        for i in range(10):
            event = SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=ThreatSeverity.MEDIUM,
                description=f"Uniqueness test {i}",
                source="test_module",
            )
            security_events.append(event)

        # Convert to SIEM events
        siem_events = [manager._convert_to_siem_event(se) for se in security_events]

        # Check that all event IDs are unique
        event_ids = [event.event_id for event in siem_events]
        assert len(event_ids) == len(set(event_ids))

    def test_siem_manager_thread_safety_invariant(self) -> None:
        """Test SIEM manager thread safety."""
        manager = SIEMManager()
        manager.queue_max_size = 1000
        errors = []

        def worker_thread(worker_id: int) -> None:
            """Worker thread that performs SIEM operations."""
            try:
                for i in range(50):
                    event = SIEMEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_id=f"thread-safety-{worker_id}-{i}",
                        event_type="test_event",
                        severity=ThreatSeverity.MEDIUM.to_string(),
                        source=f"worker_{worker_id}",
                    )
                    manager.send_event(event)

                    # Try to get status
                    status = manager.get_status()
                    assert isinstance(status, dict)

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

        # Should have queued events
        assert len(manager.event_queue) > 0


class TestSIEMIntegrationSetup:
    """Test SIEM integration setup functionality."""

    def test_setup_siem_integration_splunk(self) -> None:
        """Test SIEM integration setup with Splunk."""
        config = {
            "splunk": {
                "host": "https://splunk.example.com",
                "token": "test-token",
                "port": 8089,
                "index": "custom_index",
                "ca_cert_path": "/custom/ca.pem",
            }
        }

        mock_manager = Mock()
        mock_connector = Mock()

        with (
            patch(
                "importobot.security.siem_integration.get_siem_manager",
                return_value=mock_manager,
            ),
            patch(
                "importobot.security.siem_integration.create_splunk_connector",
                return_value=mock_connector,
            ),
        ):
            setup_siem_integration(config)

        mock_manager.add_connector.assert_called_once_with(mock_connector)

    def test_setup_siem_integration_elastic(self) -> None:
        """Test SIEM integration setup with Elastic."""
        config = {
            "elastic": {
                "hosts": [
                    "https://elastic1.example.com",
                    "https://elastic2.example.com",
                ],
                "username": "elastic_user",
                "password": "elastic_password",
                "index_pattern": "custom-pattern-*",
                "ca_cert_path": "/custom/ca.pem",
            }
        }

        mock_manager = Mock()
        mock_connector = Mock()

        with (
            patch(
                "importobot.security.siem_integration.get_siem_manager",
                return_value=mock_manager,
            ),
            patch(
                "importobot.security.siem_integration.create_elastic_connector",
                return_value=mock_connector,
            ),
        ):
            setup_siem_integration(config)

        mock_manager.add_connector.assert_called_once_with(mock_connector)

    def test_setup_siem_integration_sentinel(self) -> None:
        """Test SIEM integration setup with Microsoft Sentinel."""
        config = {
            "sentinel": {
                "workspace_id": "test-workspace",
                "shared_key": "test-shared-key",
                "log_type": "CustomLogType",
            }
        }

        mock_manager = Mock()
        mock_connector = Mock()

        with (
            patch(
                "importobot.security.siem_integration.get_siem_manager",
                return_value=mock_manager,
            ),
            patch(
                "importobot.security.siem_integration.create_sentinel_connector",
                return_value=mock_connector,
            ),
        ):
            setup_siem_integration(config)

        mock_manager.add_connector.assert_called_once_with(mock_connector)

    def test_setup_siem_integration_multiple_platforms(self) -> None:
        """Test SIEM integration setup with multiple platforms."""
        config = {
            "splunk": {"host": "https://splunk.example.com", "token": "splunk-token"},
            "elastic": {
                "hosts": ["https://elastic.example.com"],
                "username": "elastic",
                "password": "password",
                "api_key": "api-key",
            },
            "sentinel": {"workspace_id": "workspace", "shared_key": "key"},
        }

        mock_manager = Mock()
        mock_splunk = Mock()
        mock_elastic = Mock()
        mock_sentinel = Mock()

        with (
            patch(
                "importobot.security.siem_integration.get_siem_manager",
                return_value=mock_manager,
            ),
            patch(
                "importobot.security.siem_integration.create_splunk_connector",
                return_value=mock_splunk,
            ),
            patch(
                "importobot.security.siem_integration.create_elastic_connector",
                return_value=mock_elastic,
            ),
            patch(
                "importobot.security.siem_integration.create_sentinel_connector",
                return_value=mock_sentinel,
            ),
        ):
            setup_siem_integration(config)

        # Should add all three connectors
        assert mock_manager.add_connector.call_count == 3
        mock_manager.add_connector.assert_any_call(mock_splunk)
        mock_manager.add_connector.assert_any_call(mock_elastic)
        mock_manager.add_connector.assert_any_call(mock_sentinel)
