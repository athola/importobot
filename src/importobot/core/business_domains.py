"""
Business domain templates and enterprise scenarios for test generation.

Business domain templates for test generation and conversion suggestions.
"""

import random
from typing import Any, Dict, List, Optional


class BusinessDomainTemplates:
    """Business domain templates for test scenarios."""

    ENTERPRISE_SCENARIOS = {
        "web_automation": {
            "user_authentication": {
                "description": (
                    "User authentication workflow with multi-factor verification"
                ),
                "complexity": "high",
                "steps_count": (6, 12),
                "templates": [
                    "Navigate to application login portal at /auth/login",
                    "Enter primary credentials: username={username}, "
                    "password={password}",
                    "Initiate two-factor authentication process",
                    "Verify SMS code: {verification_code}",
                    "Complete biometric verification if enabled",
                    "Validate successful authentication and redirect to dashboard",
                    "Verify user session establishment and token generation",
                    "Test session persistence across browser refresh",
                    "Validate access control permissions for user role: {user_role}",
                    "Logout and verify session termination",
                ],
            },
            "e2e_workflow": {
                "description": "Business process automation testing",
                "complexity": "very_high",
                "steps_count": (10, 18),
                "templates": [
                    "Initialize browser session with enterprise security settings",
                    "Navigate to business portal: {portal_url}",
                    "Authenticate with enterprise SSO: {sso_provider}",
                    "Access module: {business_module}",
                    "Create new business entity: {entity_type}",
                    "Populate mandatory fields: {field_set}",
                    "Execute validation rules: {validation_set}",
                    "Submit for approval workflow: {approval_chain}",
                    "Track approval status through notification system",
                    "Generate business intelligence reports",
                    "Export data to external systems: {integration_targets}",
                    "Verify audit trail and compliance logging",
                    "Execute rollback scenario if needed",
                    "Validate system state consistency",
                    "Cleanup test data and reset environment",
                ],
            },
            "performance_testing": {
                "description": "Web application performance and load testing",
                "complexity": "high",
                "steps_count": (8, 14),
                "templates": [
                    "Configure performance monitoring tools",
                    "Initialize load simulation: {concurrent_users} users",
                    "Execute baseline performance test",
                    "Measure page load times for critical paths",
                    "Monitor server resource utilization",
                    "Test database query performance under load",
                    "Validate response times meet SLA: {sla_threshold}ms",
                    "Execute stress test scenarios",
                    "Monitor memory consumption and garbage collection",
                    "Test failover and recovery mechanisms",
                    "Generate performance report",
                ],
            },
        },
        "api_testing": {
            "microservices_integration": {
                "description": "Comprehensive microservices integration testing",
                "complexity": "very_high",
                "steps_count": (8, 16),
                "templates": [
                    "Initialize API test environment with service mesh",
                    "Configure authentication tokens for service-to-service "
                    "communication",
                    "Test service discovery and registration",
                    "Execute CRUD operations across microservice boundaries",
                    "Validate data consistency in distributed transactions",
                    "Test circuit breaker patterns and fault tolerance",
                    "Verify message queue integration: {queue_system}",
                    "Test API versioning and backward compatibility",
                    "Execute contract testing between services",
                    "Validate event-driven architecture patterns",
                    "Test observability and distributed tracing",
                    "Verify security boundaries and authorization",
                    "Execute chaos engineering scenarios",
                    "Validate service mesh configuration",
                ],
            },
            "data_pipeline_testing": {
                "description": "Data pipeline and ETL process validation",
                "complexity": "high",
                "steps_count": (10, 15),
                "templates": [
                    "Initialize data pipeline environment",
                    "Configure source system connections: {data_sources}",
                    "Validate data extraction processes",
                    "Test data transformation rules: {transformation_set}",
                    "Verify data quality and integrity checks",
                    "Execute incremental data loading",
                    "Test error handling and data recovery",
                    "Validate target system data consistency",
                    "Execute performance testing for large datasets",
                    "Test real-time streaming data processing",
                    "Verify data lineage and audit trails",
                    "Execute disaster recovery scenarios",
                ],
            },
        },
        "database_testing": {
            "enterprise_data_operations": {
                "description": "Enterprise database operations and integrity testing",
                "complexity": "high",
                "steps_count": (8, 14),
                "templates": [
                    "Establish secure database connections: {db_cluster}",
                    "Execute distributed transaction testing",
                    "Validate ACID properties across multiple databases",
                    "Test database sharding and partitioning strategies",
                    "Execute complex join operations and performance optimization",
                    "Validate data encryption at rest and in transit",
                    "Test backup and recovery procedures",
                    "Execute database migration scenarios",
                    "Validate referential integrity constraints",
                    "Test database replication and synchronization",
                    "Execute capacity planning and growth testing",
                    "Validate security access controls and row-level security",
                ],
            }
        },
        "infrastructure_testing": {
            "cloud_native_operations": {
                "description": "Cloud-native infrastructure and DevOps testing",
                "complexity": "very_high",
                "steps_count": (10, 20),
                "templates": [
                    "Initialize cloud infrastructure: {cloud_provider}",
                    "Deploy containerized applications using {orchestrator}",
                    "Configure auto-scaling policies and triggers",
                    "Test container lifecycle management",
                    "Validate service mesh configuration and routing",
                    "Execute infrastructure as code deployment",
                    "Test monitoring and alerting systems",
                    "Validate security scanning and compliance",
                    "Execute disaster recovery and backup procedures",
                    "Test multi-region deployment and failover",
                    "Validate cost optimization and resource management",
                    "Execute CI/CD pipeline integration testing",
                    "Test secrets management and configuration",
                    "Validate network policies and security groups",
                    "Execute performance testing under various loads",
                    "Test observability and log aggregation",
                    "Validate infrastructure security posture",
                ],
            },
            "security_testing": {
                "description": "Comprehensive security and penetration testing",
                "complexity": "very_high",
                "steps_count": (12, 20),
                "templates": [
                    "Initialize security testing environment",
                    "Execute vulnerability scanning: {scan_type}",
                    "Test authentication bypass scenarios",
                    "Validate authorization and access control",
                    "Execute SQL injection and XSS testing",
                    "Test API security and rate limiting",
                    "Validate encryption implementation",
                    "Execute penetration testing scenarios",
                    "Test security headers and CSP policies",
                    "Validate session management security",
                    "Execute privilege escalation testing",
                    "Test data protection and privacy compliance",
                    "Validate incident response procedures",
                    "Execute threat modeling validation",
                    "Test security monitoring and SIEM integration",
                ],
            },
        },
    }

    ENTERPRISE_DATA_POOLS = {
        "domains": [
            "enterprise.com",
            "corp-platform.org",
            "business-app.net",
            "company-portal.com",
        ],
        "usernames": [
            "admin.user",
            "john.doe",
            "service.account",
            "test.engineer",
            "business.user",
        ],
        "passwords": [
            "EnterprisePass123!",
            "SecureAccess456#",
            "CompliantPwd789$",
            "BusinessKey!23",
        ],
        "email_domains": [
            "company.com",
            "enterprise.org",
            "business.net",
            "corp-mail.com",
        ],
        "user_roles": [
            "administrator",
            "business_user",
            "power_user",
            "read_only",
            "audit_user",
        ],
        "business_modules": [
            "finance",
            "hr",
            "supply_chain",
            "customer_management",
            "analytics",
        ],
        "entity_types": [
            "customer",
            "order",
            "product",
            "invoice",
            "contract",
            "employee",
        ],
        "cloud_providers": ["AWS", "Azure", "GCP", "IBM Cloud"],
        "orchestrators": ["Kubernetes", "Docker Swarm", "OpenShift", "ECS"],
        "databases": ["PostgreSQL", "MySQL", "Oracle", "SQL Server", "MongoDB"],
        "queue_systems": ["RabbitMQ", "Apache Kafka", "Azure Service Bus", "AWS SQS"],
        "sso_providers": ["SAML", "OIDC", "Active Directory", "Okta"],
        "integration_targets": ["SAP", "Salesforce", "ServiceNow", "Workday"],
        "scan_types": ["OWASP ZAP", "Nessus", "Qualys", "Veracode"],
    }

    ENVIRONMENT_REQUIREMENTS = {
        "web_automation": ["Selenium Grid", "Browser Farm", "Test Data Environment"],
        "api_testing": ["Service Mesh", "Message Queue", "Database Cluster"],
        "database_testing": ["Database Cluster", "Backup Systems", "Monitoring Tools"],
        "infrastructure_testing": [
            "Cloud Environment",
            "Container Registry",
            "Monitoring Stack",
        ],
    }

    COMPLIANCE_REQUIREMENTS = {
        "web_automation": ["WCAG 2.1", "GDPR"],
        "api_testing": ["OAuth 2.0", "OpenAPI 3.0"],
        "database_testing": ["ACID Compliance", "Data Retention"],
        "infrastructure_testing": ["SOC 2", "ISO 27001", "Cloud Security"],
    }

    SETUP_INSTRUCTIONS = {
        "web_automation": [
            "Initialize browser automation environment",
            "Configure test data sets",
            "Establish secure connections to test systems",
        ],
        "api_testing": [
            "Configure API test environment",
            "Initialize service dependencies",
            "Setup authentication tokens and certificates",
        ],
        "database_testing": [
            "Establish database connections",
            "Initialize test data schemas",
            "Configure backup and recovery procedures",
        ],
        "infrastructure_testing": [
            "Provision cloud resources",
            "Configure monitoring and alerting",
            "Initialize security scanning tools",
        ],
    }

    TEARDOWN_INSTRUCTIONS = {
        "web_automation": [
            "Close browser sessions",
            "Clean up test data",
            "Reset application state",
        ],
        "api_testing": [
            "Cleanup API resources",
            "Invalidate test tokens",
            "Reset service configurations",
        ],
        "database_testing": [
            "Clean up test data",
            "Close database connections",
            "Reset database state",
        ],
        "infrastructure_testing": [
            "Deprovision test resources",
            "Clean up cloud resources",
            "Reset monitoring configurations",
        ],
    }

    @classmethod
    def get_scenario(cls, category: str, scenario: str) -> Dict[str, Any]:
        """Get specific scenario configuration."""
        return cls.ENTERPRISE_SCENARIOS.get(category, {}).get(scenario, {})

    @classmethod
    def get_all_scenarios(cls, category: str) -> Dict[str, Any]:
        """Get all scenarios for a category."""
        return cls.ENTERPRISE_SCENARIOS.get(category, {})

    @classmethod
    def get_data_pool(cls, pool_name: str) -> List[str]:
        """Get data pool by name."""
        return cls.ENTERPRISE_DATA_POOLS.get(pool_name, [])

    @classmethod
    def get_environment_requirements(cls, category: str) -> List[str]:
        """Get environment requirements for category."""
        return cls.ENVIRONMENT_REQUIREMENTS.get(category, ["Standard Test Environment"])

    @classmethod
    def get_compliance_requirements(cls, category: str) -> List[str]:
        """Get compliance requirements for category."""
        return cls.COMPLIANCE_REQUIREMENTS.get(category, ["Standard Compliance"])

    @classmethod
    def get_setup_instructions(cls, category: str) -> List[str]:
        """Get setup instructions for category."""
        return cls.SETUP_INSTRUCTIONS.get(category, ["Initialize test environment"])

    @classmethod
    def get_teardown_instructions(cls, category: str) -> List[str]:
        """Get teardown instructions for category."""
        return cls.TEARDOWN_INSTRUCTIONS.get(category, ["Clean up test environment"])


class TestCaseTemplates:
    """Templates for different test case structures and formats."""

    JSON_STRUCTURES = [
        "zephyr_basic",
        "zephyr_nested",
        "simple_tests_array",
        "test_suite_format",
        "single_test_object",
    ]

    ENTERPRISE_LABELS = [
        "enterprise",
        "integration",
        "security",
        "performance",
        "compliance",
        "automation",
        "critical_path",
        "regression",
        "api",
        "web",
        "database",
        "infrastructure",
        "cloud_native",
        "microservices",
        "ci_cd",
        "business_critical",
    ]

    TEST_PRIORITIES = ["Critical", "High", "Medium", "Low"]

    TEST_STATUSES = ["Approved", "Ready for Execution", "Under Review"]

    AUTOMATION_READINESS_LEVELS = {
        "very_high": "Partial - Manual verification required",
        "web_automation": "Full - Ready for CI/CD",
        "api_testing": "Full - Ready for CI/CD",
        "default": "High - Suitable for automation",
    }

    SECURITY_CLASSIFICATIONS = {
        "web_automation": "Internal",
        "api_testing": "Confidential",
        "database_testing": "Restricted",
        "infrastructure_testing": "Confidential",
    }

    @classmethod
    def get_available_structures(cls) -> List[str]:
        """Get available JSON structures."""
        return cls.JSON_STRUCTURES.copy()

    @classmethod
    def get_enterprise_labels(cls, count: Optional[int] = None) -> List[str]:
        """Get enterprise labels, optionally limited to count."""
        if count:
            return random.sample(
                cls.ENTERPRISE_LABELS, min(count, len(cls.ENTERPRISE_LABELS))
            )
        return cls.ENTERPRISE_LABELS.copy()

    @classmethod
    def get_automation_readiness(cls, category: str, complexity: str) -> str:
        """Get automation readiness assessment."""
        if complexity == "very_high":
            return cls.AUTOMATION_READINESS_LEVELS["very_high"]
        if category in ["web_automation", "api_testing"]:
            return cls.AUTOMATION_READINESS_LEVELS[category]
        return cls.AUTOMATION_READINESS_LEVELS["default"]

    @classmethod
    def get_security_classification(cls, category: str) -> str:
        """Get security classification for category."""
        return cls.SECURITY_CLASSIFICATIONS.get(category, "Internal")
