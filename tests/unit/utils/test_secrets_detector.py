"""Tests for secrets detector."""

from importobot.utils.secrets_detector import SecretsDetector


def test_detector_identifies_password_exposure():
    detector = SecretsDetector()
    findings = detector.scan({"value": "password=SuperSecret123"})
    assert findings
    assert any(f.secret_type == "Password" for f in findings)


def test_detector_handles_safe_data():
    detector = SecretsDetector()
    findings = detector.scan({"value": "username=demo"})
    assert findings == []
