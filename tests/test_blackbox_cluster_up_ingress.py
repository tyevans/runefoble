"""Blackbox checks for `make cluster-up` ingress failure handling and the SpiceDB host mapping.

The tests run the real Makefile target with stub `kind`, `kubectl`, and `helm` binaries
on PATH. The stubs log every call and fail on demand. No real Kind cluster is touched.
"""

import subprocess
from pathlib import Path

import pytest

from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[1]
READY_MESSAGE = "Cluster is ready!"

STUB_SCRIPT = """#!/bin/sh
line="$(basename "$0") $*"
echo "$line" >> "$STUB_LOG"
if [ -n "$STUB_FAIL" ]; then
  case "$line" in
    *"$STUB_FAIL"*) echo "stub failure: $line" >&2; exit 1 ;;
  esac
fi
case "$line" in
  "kind get clusters"*) echo "runefoble-local" ;;
  "helm repo list"*) cat "$STUB_REPO_LIST" ;;
esac
exit 0
"""


def _write_stub(bin_dir: Path, name: str) -> None:
    stub = bin_dir / name
    stub.write_text(STUB_SCRIPT)
    stub.chmod(0o755)


@pytest.fixture
def stub_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kind", "kubectl", "helm"):
        _write_stub(bin_dir, tool)
    repo_list = tmp_path / "repo-list.txt"
    repo_list.write_text("NAME\tURL\n")
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "STUB_LOG": str(tmp_path / "calls.log"),
        "STUB_REPO_LIST": str(repo_list),
        "STUB_FAIL": "",
        "LANG": "C.UTF-8",
    }


def _run_cluster_up(env: dict[str, str], fail: str = "", repo_list: str | None = None):
    run_env = dict(env)
    run_env["STUB_FAIL"] = fail
    if repo_list is not None:
        Path(run_env["STUB_REPO_LIST"]).write_text(repo_list)
    proc = run_command(["make", "-C", str(REPO_ROOT), "cluster-up"], env=run_env, timeout=120)
    calls = Path(run_env["STUB_LOG"])
    call_log = calls.read_text().splitlines() if calls.exists() else []
    return proc, call_log


def _assert_failed_without_ready(proc: subprocess.CompletedProcess) -> None:
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"cluster-up must fail. Output:\n{output}"
    assert READY_MESSAGE not in output, f"ready message printed on failure:\n{output}"


def test_cluster_up_fails_when_traefik_crd_apply_fails(stub_env):
    proc, _ = _run_cluster_up(stub_env, fail="kubectl apply")
    _assert_failed_without_ready(proc)


def test_cluster_up_fails_when_traefik_helm_upgrade_fails(stub_env):
    proc, _ = _run_cluster_up(stub_env, fail="helm upgrade")
    _assert_failed_without_ready(proc)


def test_cluster_up_fails_when_helm_repo_update_fails(stub_env):
    proc, _ = _run_cluster_up(stub_env, fail="helm repo update")
    _assert_failed_without_ready(proc)


def test_cluster_up_fails_when_traefik_repo_is_new_and_add_fails(stub_env):
    proc, _ = _run_cluster_up(stub_env, fail="helm repo add", repo_list="NAME\tURL\n")
    _assert_failed_without_ready(proc)


def test_cluster_up_skips_repo_add_when_traefik_repo_already_exists(stub_env):
    proc, call_log = _run_cluster_up(
        stub_env,
        fail="helm repo add",
        repo_list="NAME\tURL\ntraefik\thttps://traefik.github.io/charts\n",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert READY_MESSAGE in proc.stdout
    assert not any(line.startswith("helm repo add") for line in call_log)


def test_cluster_up_fails_when_traefik_rollout_fails(stub_env):
    proc, _ = _run_cluster_up(stub_env, fail="rollout status")
    _assert_failed_without_ready(proc)


def test_cluster_up_reports_ready_only_after_rollout_succeeds(stub_env):
    proc, call_log = _run_cluster_up(stub_env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert READY_MESSAGE in proc.stdout

    upgrade_idx = next(i for i, line in enumerate(call_log) if line.startswith("helm upgrade"))
    rollout_idx = next(
        i for i, line in enumerate(call_log) if "rollout status deploy/traefik" in line
    )
    assert rollout_idx > upgrade_idx, call_log


def test_kind_config_has_no_spicedb_host_port_mapping():
    config = (REPO_ROOT / "deployments/kind/cluster-config.yaml").read_text()
    assert "hostPort: 50051" not in config
    assert "containerPort: 50051" not in config


def test_spicedb_host_access_is_documented_as_port_forward():
    """SpiceDB is ClusterIP only. Host gRPC access must use the documented port-forward."""
    spicedb_service = (REPO_ROOT / "deployments/helm/runefoble/templates/spicedb.yaml").read_text()
    assert 'default "ClusterIP"' in spicedb_service

    guide = (REPO_ROOT / "docs/how-to/define-spicedb-zanzibar-permissions.md").read_text()
    assert "kubectl port-forward svc/spicedb 50051:50051" in guide
