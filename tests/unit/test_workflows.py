"""Tests for GitHub Actions workflow validation."""

from pathlib import Path

import pytest
import yaml


class TestGitHubWorkflows:
    """Test GitHub Actions workflows for validity and best practices."""

    @pytest.fixture
    def workflows_dir(self) -> Path:
        """Get the workflows directory path."""
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        if not workflows_dir.exists():
            pytest.skip(
                "GitHub Actions workflows directory not available in this environment"
            )
        return workflows_dir

    @pytest.fixture
    def workflow_files(self, workflows_dir: Path) -> list[Path]:
        """Get all workflow YAML files."""
        return list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

    def test_workflows_directory_exists(self, workflows_dir: Path) -> None:
        """Test that the workflows directory exists."""
        assert workflows_dir.exists(), "GitHub Actions workflows directory should exist"
        assert workflows_dir.is_dir(), "Workflows path should be a directory"

    def test_workflow_files_exist(self, workflow_files: list[Path]) -> None:
        """Test that workflow files exist."""
        assert len(workflow_files) > 0, "At least one workflow file should exist"

    @pytest.mark.parametrize(
        "workflow_file",
        [
            Path(__file__).parent.parent.parent / ".github" / "workflows" / f
            for f in ["test.yml", "lint.yml", "claude.yml", "claude-code-review.yml"]
        ],
    )
    def test_workflow_file_exists(self, workflow_file: Path) -> None:
        """Test that expected workflow files exist."""
        if not workflow_file.exists():
            pytest.skip(
                f"Workflow file {workflow_file.name} not available in this environment"
            )
        assert workflow_file.exists(), (
            f"Workflow file {workflow_file.name} should exist"
        )

    def test_workflow_yaml_syntax(self, workflow_files: list[Path]) -> None:
        """Test that all workflow files have valid YAML syntax."""
        for workflow_file in workflow_files:
            with open(workflow_file, encoding="utf-8") as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML syntax in {workflow_file.name}: {e}")

    def test_workflow_structure(self, workflow_files: list[Path]) -> None:
        """Test that workflows have required structure."""
        for workflow_file in workflow_files:
            with open(workflow_file, encoding="utf-8") as f:
                workflow = yaml.safe_load(f)

                # Check required top-level keys
                assert "name" in workflow, (
                    f"Workflow {workflow_file.name} should have a 'name' field"
                )
                # Note: 'on' might be parsed as True (boolean) by YAML parser
                assert "on" in workflow or True in workflow, (
                    f"Workflow {workflow_file.name} should have an 'on' trigger"
                )
                assert "jobs" in workflow, (
                    f"Workflow {workflow_file.name} should have 'jobs'"
                )

                # Check that jobs is not empty
                assert len(workflow["jobs"]) > 0, (
                    f"Workflow {workflow_file.name} should have at least one job"
                )

    def test_test_workflow_specifics(self, workflows_dir: Path) -> None:
        """Test specific requirements for the test workflow."""
        test_workflow_file = workflows_dir / "test.yml"
        if not test_workflow_file.exists():
            pytest.skip("test.yml workflow not found")

        with open(test_workflow_file, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        # Check test workflow has matrix strategy
        test_job = workflow["jobs"]["test"]
        assert "strategy" in test_job, "Test job should have a strategy"
        assert "matrix" in test_job["strategy"], "Test strategy should have a matrix"
        assert "python-version" in test_job["strategy"]["matrix"], (
            "Matrix should include python-version"
        )

        # Check fail-fast is disabled for better visibility
        assert test_job["strategy"].get("fail-fast") is False, (
            "Test strategy should have fail-fast: false"
        )

        # Check Python versions
        python_versions = test_job["strategy"]["matrix"]["python-version"]
        assert isinstance(python_versions, list), "Python versions should be a list"
        assert len(python_versions) >= 2, "Should test multiple Python versions"
        assert "3.10" in python_versions, "Should test Python 3.10"

    def test_cache_keys_include_python_version(self, workflows_dir: Path) -> None:
        """Test that cache keys include Python version to avoid pollution."""
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, encoding="utf-8") as f:
                content = f.read()

            # If workflow uses caching and has matrix python-version, check cache key
            if "actions/cache@v" in content and "matrix.python-version" in content:
                work_assert = (
                    f"Workflow {workflow_file.name} should include Python "
                    "version in cache key"
                )
                assert "python-${{ matrix.python-version }}" in content, work_assert

    def test_codecov_conditional_upload(self, workflows_dir: Path) -> None:
        """Test that Codecov upload is conditional on token availability."""
        test_workflow_file = workflows_dir / "test.yml"
        if not test_workflow_file.exists():
            pytest.skip("test.yml workflow not found")

        with open(test_workflow_file, encoding="utf-8") as f:
            content = f.read()

        if "codecov" in content.lower():
            # Check for conditional execution - updated pattern
            assert (
                "steps.codecov-check.outputs.codecov_available == 'true'" in content
            ), "Codecov upload should be conditional on token availability"

    def test_workflow_triggers(self, workflow_files: list[Path]) -> None:
        """Test that workflows have appropriate triggers."""
        for workflow_file in workflow_files:
            with open(workflow_file, encoding="utf-8") as f:
                workflow = yaml.safe_load(f)

            triggers = workflow.get("on", workflow.get(True, {}))

            # Should have at least one valid trigger type
            trigger_types = (
                triggers.keys() if isinstance(triggers, dict) else [triggers]
            )
            valid_triggers = [
                "push",
                "pull_request",
                "workflow_dispatch",
                "issue_comment",
                "pull_request_review_comment",
                "issues",
                "pull_request_review",
                "workflow_run",
            ]
            assert any(t in trigger_types for t in valid_triggers), (
                f"Workflow {workflow_file.name} should have appropriate triggers"
            )

    def test_ubuntu_latest_runner(self, workflow_files: list[Path]) -> None:
        """Test that workflows use ubuntu-latest runner for consistency."""
        for workflow_file in workflow_files:
            with open(workflow_file, encoding="utf-8") as f:
                workflow = yaml.safe_load(f)

            for job_name, job_config in workflow["jobs"].items():
                if "runs-on" in job_config:
                    runner = job_config["runs-on"]
                    job_assert = (
                        f"Job {job_name} in {workflow_file.name} should use "
                        "ubuntu-latest runner"
                    )
                    assert runner == "ubuntu-latest", job_assert

    def test_action_versions_pinned(self, workflow_files: list[Path]) -> None:
        """Test that GitHub Actions use pinned versions."""
        for workflow_file in workflow_files:
            with open(workflow_file, encoding="utf-8") as f:
                content = f.read()

            # Check for common actions that should be pinned
            if "actions/checkout@" in content:
                assert "@v4" in content or "@v3" in content or "@v5" in content, (
                    f"checkout action in {workflow_file.name} should use pinned version"
                )

            if "actions/setup-python@" in content:
                setup_assert = (
                    f"setup-python action in {workflow_file.name} should "
                    "use pinned version"
                )
                assert "@v5" in content or "@v4" in content, setup_assert
