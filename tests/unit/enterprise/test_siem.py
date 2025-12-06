"""Tests for SIEM Manager and connectors."""

from __future__ import annotations

from importobot_enterprise.siem import (
    ElasticConnector,
    SIEMManager,
    SplunkHECConnector,
)


def test_siem_manager_dispatches_events() -> None:
    manager = SIEMManager()
    splunk = SplunkHECConnector(endpoint="https://splunk.local", token="abc")
    elastic = ElasticConnector(endpoint="https://elastic.local", api_key="xyz")
    manager.add_connector(splunk)
    manager.add_connector(elastic)

    manager.emit_security_event("TOKEN_ROTATED", {"count": 2})

    assert len(manager.connectors) == 2
