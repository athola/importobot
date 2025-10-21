"""Tests for secrets detector."""

from pathlib import Path

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


def test_examples_directory_is_free_of_secrets():
    detector = SecretsDetector()
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / "examples" / "json",
        repo_root / "examples" / "resources",
        repo_root / "examples" / "robot",
    ]
    text_suffixes = {
        ".json",
        ".txt",
        ".robot",
        ".resource",
        ".yaml",
        ".yml",
        ".md",
        ".sh",
    }

    for directory in candidates:
        if not directory.exists():
            continue
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in text_suffixes:
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            findings = detector.scan({"content": content})
            assert findings == [], (
                f"Potential secrets detected in example file {file_path}: {findings}"
            )
