# SIEM Integration Guide

Importobot can forward security events (credential detections, suspicious API payloads, template findings) to your SIEM so SOC teams receive the same telemetry that drives the built-in `SecurityMonitor`. This guide shows how to configure the three built-in connectors: Splunk, Elastic Security, and Microsoft Sentinel.

## Shared Setup

1. **Install the enterprise extras** (already included in `pip install importobot[enterprise]`).
2. **Collect secrets**:
   - Splunk: HTTPS base URL + HEC token.
   - Elastic: One or more HTTPS hosts plus either an API key or username/password.
   - Sentinel: Workspace ID + shared key obtained from the Azure portal.
3. **Export the secrets as environment variables** on the host that runs Importobot so you avoid hard-coding them in scripts:

```bash
export IMPORTOBOT_ENCRYPTION_KEY="$(openssl rand -base64 32)"
export SPLUNK_HEC_TOKEN="..."
export ELASTIC_API_KEY="id:secret"
export ELASTIC_HOSTS="https://elastic1.example.com:9243,https://elastic2.example.com:9243"
export SENTINEL_WORKSPACE_ID="00000000-0000-0000-0000-000000000000"
export SENTINEL_SHARED_KEY="base64-secret"
```

4. **Choose an integration strategy**:
   - *Declarative*: Pass a dict to `setup_siem_integration()` and let Importobot spin up the connectors.
   - *Imperative*: Create connectors manually and add them to `get_siem_manager()` when you need more control (e.g., unit tests, dry runs).

## Splunk Example

```python
import os
from importobot.security import create_splunk_connector, get_siem_manager

splunk = create_splunk_connector(
    host="https://splunk.internal.example.com",
    token=os.environ["SPLUNK_HEC_TOKEN"],
    port=8088,  # Optional; defaults to 8089
    index="importobot_security",
    ca_cert_path="/etc/ssl/certs/internal-ca.pem",
)

siem_manager = get_siem_manager()
siem_manager.add_connector(splunk)
siem_manager.start()
```

**Verification steps**

1. Create a dummy `SecurityEvent` (see `tests/unit/security/test_monitoring.py` for helpers) and call `siem_manager.send_security_event(event)`.
2. Check Splunk’s `_internal` index for HEC ingestion warnings. All connectors verify TLS; Splunk must be reachable over HTTPS.

## Elastic Security Example

```python
import os
from importobot.security import create_elastic_connector, get_siem_manager

hosts = os.environ["ELASTIC_HOSTS"].split(",")
elastic = create_elastic_connector(
    hosts=hosts,
    username=os.getenv("ELASTIC_USERNAME", ""),
    password=os.getenv("ELASTIC_PASSWORD", ""),
    api_key=os.getenv("ELASTIC_API_KEY"),  # Takes precedence over username/password
    index_pattern="importobot-security-*",
)

manager = get_siem_manager()
manager.add_connector(elastic)
manager.start()
```

**Verification steps**

1. Run `curl -u user:pass https://host/_cat/indices/importobot-security-*?v`.
2. Confirm the index receives new documents after sending a `SecurityEvent`.

## Microsoft Sentinel Example

```python
import os
from importobot.security import create_sentinel_connector, get_siem_manager

sentinel = create_sentinel_connector(
    workspace_id=os.environ["SENTINEL_WORKSPACE_ID"],
    shared_key=os.environ["SENTINEL_SHARED_KEY"],
    log_type="ImportobotSecurity",
)

manager = get_siem_manager()
manager.add_connector(sentinel)
manager.start()
```

**Verification steps**

1. Use the KQL query `ImportobotSecurity_CL | sort by TimeGenerated desc | limit 5` in Sentinel Logs.
2. Check the Azure Monitor “Failed log data uploads” metric; it should remain at zero once credentials are correct.

## Wiring the Security Monitor

The SIEM manager is queue-based. To ensure every security event is forwarded:

```python
from importobot.security import get_security_monitor, get_siem_manager

monitor = get_security_monitor()
siem = get_siem_manager()

def forward_all_events(event):
    siem.send_security_event(event)

monitor.subscribe(forward_all_events)
siem.start()
```

Attach the subscriber early in your process (e.g., CLI entry point or background worker) so ingestion begins before the first conversion. The queue drops events only when it is full (default 500); monitor the CLI logs for `SIEM event queue full` to tune `queue_max_size`.

## Operational Checklist

- Rotate Splunk/Sentinel secrets alongside `IMPORTOBOT_ENCRYPTION_KEY`.
- Store CA bundles in read-only directories and pass the path via `ca_cert_path`.
- Stop the SIEM manager (`get_siem_manager().stop()`) during shutdown to flush the queue.
- Record connector health: call `connector.test_connection()` during startup to fail fast.

Once configured, security warnings (template scan failures, credential detections, path traversal attempts) show up in the SIEM minutes after they are detected, keeping Importobot’s observability aligned with the broader SOC tooling.
