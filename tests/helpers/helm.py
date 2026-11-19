"""Render the umbrella Helm chart for tests. This is the only `helm template` call in `tests/`.

On a developer machine without helm, a chart test skips. In CI (`CI` is set), the same
test fails, so a host without helm never passes chart checks with no assertion (TASK-0869).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[2]
CHART_DIR = REPO_ROOT / "deployments" / "helm" / "runefoble"
RELEASE_NAME = "runefoble"
TEMPLATE_TIMEOUT_SECONDS = 240.0


def require_helm() -> None:
    """Skip the test when helm is missing. Fail it instead when `CI` is set."""
    if shutil.which("helm") is not None:
        return
    message = "helm CLI not available"
    if os.environ.get("CI"):
        pytest.fail(f"{message}: CI must install helm before the Python test job runs")
    pytest.skip(message)


def helm_template_result(*extra_args: str) -> subprocess.CompletedProcess[str]:
    """Run `helm template` on the chart and return the process. The caller checks the exit code."""
    require_helm()
    args: Sequence[str] = ["helm", "template", RELEASE_NAME, str(CHART_DIR), *extra_args]
    return run_command(args, timeout=TEMPLATE_TIMEOUT_SECONDS)


def render_chart(*extra_args: str) -> list[dict]:
    """Render the chart and return every non-empty YAML document. The render must succeed."""
    result = helm_template_result(*extra_args)
    assert result.returncode == 0, f"helm template failed:\n{result.stderr}"
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]
