"""Blackbox tests for GitHub Actions CI Playwright BDD Quality Gate Integration.

Governed by ADR-0010, ADR-0014, and Hard Invariant 7.
Part of TASK-0364.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LOCAL_CI_SCRIPT_PATH = REPO_ROOT / "scripts" / "test_ci_e2e.sh"
PLAYWRIGHT_CONFIG_PATH = REPO_ROOT / "playwright.config.ts"


def test_ci_workflow_valid_yaml() -> None:
    """Verify .github/workflows/ci.yml exists and is valid YAML."""
    assert CI_WORKFLOW_PATH.is_file(), f"Missing {CI_WORKFLOW_PATH}"
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    assert isinstance(parsed, dict)
    assert parsed.get("name") == "CI"
    assert "jobs" in parsed


def test_e2e_playwright_job_structure() -> None:
    """Verify e2e-playwright job definition meets ADR-0010 and ADR-0014 invariants."""
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    jobs = parsed.get("jobs", {})

    assert "e2e-playwright" in jobs, "e2e-playwright job is missing from ci.yml"
    job = jobs["e2e-playwright"]

    assert job.get("runs-on") == "ubuntu-latest"

    # 1. Service container for Redis
    services = job.get("services", {})
    assert "redis" in services
    assert "redis:7-alpine" in services["redis"]["image"]
    assert 6379 in [int(str(p).split(":")[0]) for p in services["redis"]["ports"]]

    # 2. Inspect steps
    steps = job.get("steps", [])
    step_uses = [s.get("uses", "") for s in steps]
    step_runs = [s.get("run", "") for s in steps]

    # Checkout
    assert any("actions/checkout" in u for u in step_uses)

    # UV & Python setup
    assert any("astral-sh/setup-uv" in u for u in step_uses)
    py_step = next(s for s in steps if "actions/setup-python" in s.get("uses", ""))
    assert "3.13" in str(py_step.get("with", {}).get("python-version", ""))

    # Node setup
    node_step = next(s for s in steps if "actions/setup-node" in s.get("uses", ""))
    assert "24" in str(node_step.get("with", {}).get("node-version", ""))

    # Pnpm setup
    assert any("pnpm/action-setup" in u for u in step_uses)

    # Playwright browser cache
    cache_step = next(
        s for s in steps if "actions/cache" in s.get("uses", "") and "playwright" in s.get("id", "")
    )
    assert "~/.cache/ms-playwright" in cache_step.get("with", {}).get("path", "")

    # Playwright install with system dependencies
    assert any("playwright install --with-deps" in r for r in step_runs)

    # Background service launch
    bg_step = next(s for s in steps if "make dev &" in s.get("run", ""))
    bg_env = bg_step.get("env", {})
    assert bg_env.get("SPICEDB_ENDPOINT") == "mock"
    assert "6379" in bg_env.get("REDIS_URL", "")

    # Health & readiness polling
    readiness_step = next(s for s in steps if "api/v1/health" in s.get("run", ""))
    run_cmd = readiness_step.get("run", "")
    assert "http://localhost:8000/api/v1/health" in run_cmd
    assert "http://localhost:5173" in run_cmd
    assert "timeout 60" in run_cmd

    # Playwright BDD test execution
    exec_step = next(s for s in steps if "make test-e2e" in s.get("run", ""))
    assert "--reporter=github,html" in exec_step.get("run", "")

    # Failure artifact upload
    artifact_step = next(s for s in steps if "actions/upload-artifact" in s.get("uses", ""))
    assert artifact_step.get("if") == "failure()"
    artifact_paths = artifact_step.get("with", {}).get("path", "")
    assert "playwright-report/" in artifact_paths
    assert "test-results/" in artifact_paths
    assert int(artifact_step.get("with", {}).get("retention-days", 0)) == 14


def test_local_ci_simulation_script() -> None:
    """Verify local CI simulation script exists, is executable, and passes bash syntax check."""
    assert LOCAL_CI_SCRIPT_PATH.is_file(), f"Missing {LOCAL_CI_SCRIPT_PATH}"

    # Executable permissions check
    file_stat = os.stat(LOCAL_CI_SCRIPT_PATH)
    assert bool(file_stat.st_mode & stat.S_IXUSR), "test_ci_e2e.sh is not executable"

    # Bash syntax validation
    res = subprocess.run(["bash", "-n", str(LOCAL_CI_SCRIPT_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"Bash syntax check failed: {res.stderr}"

    content = LOCAL_CI_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "make test-e2e" in content
    assert "api/v1/health" in content
    assert "http://localhost:5173" in content
    assert "trap cleanup" in content


def test_playwright_config_invariants() -> None:
    """Verify playwright.config.ts has workers=1, reuseExistingServer=true, and CI reporters."""
    content = PLAYWRIGHT_CONFIG_PATH.read_text(encoding="utf-8")
    assert "workers: 1" in content
    assert "reuseExistingServer: true" in content
    assert "github" in content
    assert "html" in content
