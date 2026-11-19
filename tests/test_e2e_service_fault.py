"""Blackbox tests for the e2e service fault script (TASK-0909).

The script scales a Kind deployment with `kubectl` and waits on the gateway `/healthz`
report. Each test runs the script as a child process, as `make` does. A fake `kubectl` on
PATH records its arguments and stores the replica count in a file. A loopback gateway
double reads that file and reports the service as `unreachable` at 0 replicas and
`operational` at 1 replica. No test touches a real cluster.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI

from tests.helpers.live_services import serve

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "e2e_service_fault.py"
CONTEXT = "kind-runefoble-local"

FAKE_KUBECTL = """#!{python}
import json, sys
from pathlib import Path
state = Path({state!r})
log = Path({log!r})
with log.open("a") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")
if Path({fail!r}).exists():
    print("error: deployments.apps not found", file=sys.stderr)
    sys.exit(1)
args = sys.argv[1:]
if "scale" in args:
    replicas = next(a for a in args if a.startswith("--replicas="))
    state.write_text(replicas.split("=", 1)[1])
"""


@dataclass
class FakeCluster:
    """Paths that the fake kubectl and the gateway double share."""

    bin_dir: Path
    state: Path
    log: Path
    fail: Path
    frozen: Path

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]


def _gateway_double(cluster: FakeCluster, reported: tuple[str, ...]) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    def _healthz() -> dict:
        replicas = cluster.state.read_text() if cluster.state.exists() else "1"
        status = "unreachable" if replicas == "0" else "operational"
        if cluster.frozen.exists():
            status = cluster.frozen.read_text()
        return {"status": "healthy", "downstream_services": dict.fromkeys(reported, status)}

    return app


@pytest.fixture
def cluster(tmp_path: Path) -> FakeCluster:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = FakeCluster(
        bin_dir=bin_dir,
        state=tmp_path / "replicas",
        log=tmp_path / "kubectl.log",
        fail=tmp_path / "kubectl-fails",
        frozen=tmp_path / "frozen-status",
    )
    kubectl = bin_dir / "kubectl"
    kubectl.write_text(
        FAKE_KUBECTL.format(
            python=sys.executable, state=str(fake.state), log=str(fake.log), fail=str(fake.fail)
        )
    )
    kubectl.chmod(0o755)
    return fake


@pytest.fixture
def gateway(cluster: FakeCluster) -> Iterator[str]:
    with serve(_gateway_double(cluster, ("game_session", "campaign_lore"))) as url:
        yield url


def _run(cluster: FakeCluster, gateway_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{cluster.bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PLAYWRIGHT_BASE_URL": gateway_url,
        "RUNEFOBLE_E2E_FAULT_TIMEOUT_S": "3",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_down_scales_the_deployment_to_zero_and_waits_for_unreachable(cluster, gateway):
    result = _run(cluster, gateway, "campaign_lore", "down")

    assert result.returncode == 0, result.stderr
    assert cluster.calls() == [
        ["--context", CONTEXT, "scale", "deployment/campaign-lore", "--replicas=0"]
    ]
    assert "unreachable" in result.stdout


def test_up_scales_to_one_waits_for_the_rollout_and_for_operational(cluster, gateway):
    cluster.state.write_text("0")

    result = _run(cluster, gateway, "game_session", "up")

    assert result.returncode == 0, result.stderr
    assert cluster.calls() == [
        ["--context", CONTEXT, "scale", "deployment/game-session", "--replicas=1"],
        ["--context", CONTEXT, "rollout", "status", "deployment/game-session", "--timeout=3s"],
    ]
    assert "operational" in result.stdout


def test_a_failed_kubectl_call_fails_with_its_error(cluster, gateway):
    cluster.fail.write_text("yes")

    result = _run(cluster, gateway, "campaign_lore", "down")

    assert result.returncode == 1
    assert "deployments.apps not found" in result.stderr


def test_down_fails_when_the_gateway_never_reports_unreachable(cluster, gateway):
    cluster.frozen.write_text("operational")

    result = _run(cluster, gateway, "campaign_lore", "down")

    assert result.returncode == 1
    assert "campaign_lore" in result.stderr
    assert "operational" in result.stderr


def test_down_fails_when_the_gateway_does_not_report_the_service(cluster):
    with serve(_gateway_double(cluster, ("game_session",))) as url:
        result = _run(cluster, url, "campaign_lore", "down")

    assert result.returncode == 1
    assert "does not report campaign_lore" in result.stderr


def test_an_unknown_service_is_refused_without_a_kubectl_call(cluster, gateway):
    result = _run(cluster, gateway, "postgres", "down")

    assert result.returncode == 2
    assert "Usage" in result.stderr
    assert cluster.calls() == []
