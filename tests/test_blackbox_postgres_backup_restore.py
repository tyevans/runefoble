"""Live restore test for the PostgreSQL backup (TASK-0961, PRD-0025 outcome 5). Marked requires_kind.

The test runs on a Kind cluster with the local chart. It does this:
1. Installs release A in namespace A with the backup on. The Silo service of the cluster is the
   S3 endpoint. This is a test value only. A hosted release uses a bucket outside the cluster.
2. Creates a campaign through the public gateway API (REST, no database write).
3. Starts one backup with `kubectl create job --from=cronjob/postgres-backup`, as the runbook does.
4. Installs release B in namespace B with restore.enabled and the logged object prefix.
5. Lists campaigns through the public gateway API of release B and checks the campaign.

Run it only on the orchestrator's Kind cluster, with the opt-in variables set:

    RUNEFOBLE_KIND_RESTORE_TEST=1 \
    RUNEFOBLE_RESTORE_TEST_TOKEN=<access token of the test user> \
    uv run pytest -q -p no:randomly tests/test_blackbox_postgres_backup_restore.py -m requires_kind

The token must be valid for both releases. It comes from the same sign-in that the Playwright suite
uses, so the Zitadel issuer, the signing key and the project audience match in release A and B.
The test creates the namespaces, the backup Secret and both releases. It deletes them at the end.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import time
import uuid
from collections.abc import Iterator

import httpx
import pytest
import yaml

from tests.helpers.helm import CHART_DIR, HOSTED_EXAMPLE
from tests.helpers.process import run_command

pytestmark = pytest.mark.requires_kind

OPT_IN = "RUNEFOBLE_KIND_RESTORE_TEST"
TOKEN_ENV = "RUNEFOBLE_RESTORE_TEST_TOKEN"
NS_A = "runefoble-backup-a"
NS_B = "runefoble-restore-b"
RELEASE_A = "runefoble-a"
RELEASE_B = "runefoble-b"
BUCKET = "runefoble-backups"
SECRET = "runefoble-backup-credentials"
BUCKETS = ["runefoble-assets", "runefoble-recordings", BUCKET]
TIMEOUT = 900
OBJECT_LINE = re.compile(r"backup-object (postgres/\S+)")


def _image() -> str:
    return yaml.safe_load(HOSTED_EXAMPLE.read_text(encoding="utf-8"))["backup"]["image"]


def _silo_keys() -> tuple[str, str]:
    """The Silo keys of the local chart. They are development defaults for a Kind cluster only."""
    creds = yaml.safe_load((CHART_DIR / "values.yaml").read_text(encoding="utf-8"))["credentials"]
    return creds["silo"]["accessKey"], creds["silo"]["secretKey"]


def _ok(args: list[str], timeout: float = TIMEOUT) -> str:
    proc = run_command(args, timeout=timeout)
    assert proc.returncode == 0, f"{' '.join(args[:4])} failed:\n{proc.stderr}"
    return proc.stdout


def _backup_values(endpoint: str) -> list[str]:
    return [
        "--set",
        "backup.enabled=true",
        "--set",
        f"backup.endpoint={endpoint}",
        "--set",
        f"backup.bucket={BUCKET}",
        "--set",
        f"backup.credentialsSecret={SECRET}",
        "--set",
        f"backup.image={_image()}",
        "--set",
        "silo.buckets={" + ",".join(BUCKETS) + "}",
    ]


def _create_secret(namespace: str) -> None:
    access, secret = _silo_keys()
    _ok(["kubectl", "create", "namespace", namespace])
    _ok(
        [
            "kubectl",
            "-n",
            namespace,
            "create",
            "secret",
            "generic",
            SECRET,
            f"--from-literal=access-key={access}",
            f"--from-literal=secret-key={secret}",
        ]
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _gateway_url(namespace: str) -> tuple[str, subprocess.Popen[bytes]]:
    """Open a port-forward to the gateway of one namespace. The caller stops the process."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            "kubectl",
            "-n",
            namespace,
            "port-forward",
            "svc/gateway-api",
            f"{port}:8000",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            httpx.get(f"{url}/healthz", timeout=2.0)
            return url, proc
        except httpx.HTTPError:
            time.sleep(1)
    proc.terminate()
    raise AssertionError(f"gateway port-forward in {namespace} did not answer")


@pytest.fixture
def live_token() -> str:
    if os.environ.get(OPT_IN) != "1":
        pytest.skip(f"set {OPT_IN}=1 on the Kind cluster to run the restore test")
    token = os.environ.get(TOKEN_ENV, "")
    if not token:
        pytest.fail(f"{TOKEN_ENV} must hold an access token of the test user")
    return token


@pytest.fixture
def releases(live_token: str) -> Iterator[None]:
    """Create the two namespaces. Remove the releases and the namespaces at the end."""
    yield
    for namespace in (NS_A, NS_B):
        run_command(["kubectl", "delete", "namespace", namespace, "--wait=false"], timeout=120)


def test_restore_recovers_a_campaign_in_a_fresh_release(live_token: str, releases: None) -> None:
    # 1. Release A, with the backup on. The S3 endpoint is the Silo service of namespace A.
    _create_secret(NS_A)
    silo_a = f"http://silo.{NS_A}.svc.cluster.local:9000"
    _ok(
        [
            "helm",
            "install",
            RELEASE_A,
            str(CHART_DIR),
            "-n",
            NS_A,
            *_backup_values(silo_a),
            "--wait",
            "--timeout",
            "15m",
        ]
    )

    # 2. A campaign, through the public gateway API of release A.
    title = f"Restore test {uuid.uuid4().hex[:8]}"
    url_a, forward_a = _gateway_url(NS_A)
    try:
        headers = {"Authorization": f"Bearer {live_token}"}
        created = httpx.post(
            f"{url_a}/api/v1/campaigns",
            headers=headers,
            json={
                "title": title,
                "description": "Restore test.",
                "setting": "Test",
                "system": "5e",
            },
            timeout=30.0,
        )
        assert created.status_code == 201, created.text
        campaign_id = created.json()["id"]
    finally:
        forward_a.terminate()

    # 3. One backup, as the runbook starts it. The Job logs the object prefix.
    _ok(["kubectl", "-n", NS_A, "create", "job", "--from=cronjob/postgres-backup", "backup-test"])
    _ok(
        [
            "kubectl",
            "-n",
            NS_A,
            "wait",
            "--for=condition=complete",
            "job/backup-test",
            f"--timeout={TIMEOUT}s",
        ],
        timeout=TIMEOUT + 60,
    )
    logs = _ok(["kubectl", "-n", NS_A, "logs", "job/backup-test", "-c", "dump"])
    match = OBJECT_LINE.search(logs)
    assert match is not None, f"the backup Job logged no object prefix:\n{logs}"
    prefix = match.group(1)

    # 4. Release B in a fresh namespace. It restores the prefix. The restore runs as a hook.
    _create_secret(NS_B)
    _ok(
        [
            "helm",
            "install",
            RELEASE_B,
            str(CHART_DIR),
            "-n",
            NS_B,
            *_backup_values(silo_a),
            "--set",
            "restore.enabled=true",
            "--set",
            f"restore.objectPrefix={prefix}",
            "--timeout",
            "30m",
        ],
        timeout=1860,
    )
    _ok(
        [
            "kubectl",
            "-n",
            NS_B,
            "wait",
            "--for=condition=complete",
            "job/postgres-restore",
            f"--timeout={TIMEOUT}s",
        ],
        timeout=TIMEOUT + 60,
    )
    # The restore replaces the rows under running services. Restart them so they read the restored data.
    for deployment in _ok(["kubectl", "-n", NS_B, "get", "deployments", "-o", "name"]).split():
        _ok(["kubectl", "-n", NS_B, "rollout", "restart", deployment])
        _ok(["kubectl", "-n", NS_B, "rollout", "status", deployment, "--timeout=600s"], timeout=660)

    # 5. The campaign is listed through the public gateway API of release B.
    url_b, forward_b = _gateway_url(NS_B)
    try:
        listed = httpx.get(
            f"{url_b}/api/v1/campaigns",
            headers={"Authorization": f"Bearer {live_token}"},
            timeout=30.0,
        )
        assert listed.status_code == 200, listed.text
        ids = {item["id"] for item in listed.json()}
    finally:
        forward_b.terminate()

    assert campaign_id in ids
