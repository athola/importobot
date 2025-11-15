"""Security utilities and components for Importobot.

This package groups credential management, secure memory, template scanning,
SIEM forwarding, compliance reporting, key rotation, and monitoring helpers so
callers no longer depend on scattered `utils` modules.
"""

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
from importobot.security.credential_manager import (
    CredentialManager,
    SecurityError,
)
from importobot.security.credential_patterns import (
    CredentialPattern,
    CredentialPatternRegistry,
    CredentialType,
    get_credential_registry,
    scan_for_credentials,
)
from importobot.security.hsm_integration import (
    HSMInterface,
    HSMKeyMetadata,
    HSMManager,
    HSMProvider,
    HSMProviderUnavailableError,
    get_hsm_manager,
    reset_hsm_manager,
)
from importobot.security.key_rotation import (
    KeyRotator,
    RotationConfig,
    RotationEvent,
    RotationPolicy,
    RotationStatus,
    configure_90_day_rotation,
    configure_compliance_rotation,
    configure_usage_based_rotation,
    get_key_rotator,
    reset_key_rotator,
)
from importobot.security.monitoring import (
    AlertChannel,
    AnomalyDetector,
    EventCollector,
    MonitoringStatus,
    SecurityEvent,
    SecurityMonitor,
    SecurityMonitoringError,
    ThreatIntelligence,
    ThreatIntelligenceManager,
    ThreatSeverity,
    get_security_monitor,
    reset_security_monitor,
)
from importobot.security.secure_memory import (
    SecureMemory,
    SecureString,
)
from importobot.security.security_validator import (
    SecurityValidator,
)
from importobot.security.siem_integration import (
    MITRETactic,
    SIEMEvent,
    SIEMIntegrationError,
    SIEMManager,
    SIEMPlatform,
    create_elastic_connector,
    create_sentinel_connector,
    create_splunk_connector,
    get_siem_manager,
    reset_siem_manager,
    setup_siem_integration,
)
from importobot.security.template_scanner import (
    TemplateSecurityScanner,
    scan_template_file_for_security,
)

__all__ = [
    "AlertChannel",
    "AnomalyDetector",
    "AuditTrail",
    "ComplianceAssessment",
    # Compliance reporting
    "ComplianceControl",
    "ComplianceEngine",
    "ComplianceError",
    "ComplianceReport",
    "ComplianceStandard",
    "ComplianceStatus",
    "ControlType",
    "CredentialManager",
    # Credential pattern detection
    "CredentialPattern",
    "CredentialPatternRegistry",
    "CredentialType",
    "EventCollector",
    # HSM integration
    "HSMInterface",
    "HSMKeyMetadata",
    "HSMManager",
    "HSMProvider",
    "HSMProviderUnavailableError",
    # Key rotation
    "KeyRotator",
    "MITRETactic",
    "MonitoringStatus",
    "RotationConfig",
    "RotationEvent",
    "RotationPolicy",
    "RotationStatus",
    # SIEM integration
    "SIEMEvent",
    "SIEMIntegrationError",
    "SIEMManager",
    "SIEMPlatform",
    "SOC2Assessment",
    "SecureMemory",
    "SecureString",
    # Core security classes
    "SecurityError",
    # Security monitoring
    "SecurityEvent",
    "SecurityMonitor",
    "SecurityMonitoringError",
    "SecurityValidator",
    # Template security scanning
    "TemplateSecurityScanner",
    "ThreatIntelligence",
    "ThreatIntelligenceManager",
    "ThreatSeverity",
    "assess_soc2_compliance",
    "configure_90_day_rotation",
    "configure_compliance_rotation",
    "configure_usage_based_rotation",
    "create_elastic_connector",
    "create_sentinel_connector",
    "create_splunk_connector",
    "get_compliance_dashboard",
    "get_compliance_engine",
    "get_credential_registry",
    "get_hsm_manager",
    "get_key_rotator",
    "get_security_monitor",
    "get_siem_manager",
    "reset_compliance_engine",
    "reset_hsm_manager",
    "reset_key_rotator",
    "reset_security_monitor",
    "reset_siem_manager",
    "scan_for_credentials",
    "scan_template_file_for_security",
    "setup_siem_integration",
]
