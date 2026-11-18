"""Blackbox checks for chart credentials in the rendered Helm output.

The tests render the umbrella chart with `helm template` and read only the public
manifest output. They take the credential values from the rendered Secret, so no test
hardcodes a dev default. They check that no container carries a credential as a plain
value, that each credential env var reads a Secret key, and that a non-local render needs
`credentials.existingSecret`.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

HELM_CHART = Path("deployments/helm/runefoble")
SECRET_NAME = "runefoble-credentials"

# Env var names that carry a credential. Any such var must read a Secret, or stay empty.
CREDENTIAL_ENV_NAME = re.compile(r"(PASSWORD|SECRET_KEY|PRESHARED_KEY|MASTERKEY|ACCESS_KEY|TOKEN)$")


def _require_helm() -> None:
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")


def _helm_template(*extra_args: str) -> subprocess.CompletedProcess:
    _require_helm()
    return subprocess.run(
        ["helm", "template", "runefoble", str(HELM_CHART), *extra_args],
        capture_output=True,
        text=True,
    )


def _rendered_docs(*extra_args: str) -> list[dict]:
    proc = _helm_template(*extra_args)
    assert proc.returncode == 0, f"helm template failed:\n{proc.stderr}"
    return [doc for doc in yaml.safe_load_all(proc.stdout) if doc]


def _containers(docs: list[dict]) -> list[tuple[str, dict]]:
    """Return (workload name, container) for every container in every workload and job."""
    found: list[tuple[str, dict]] = []
    for doc in docs:
        if doc.get("kind") not in {"Deployment", "Job", "StatefulSet", "DaemonSet"}:
            continue
        pod_spec = doc["spec"]["template"]["spec"]
        for container in pod_spec.get("initContainers", []) + pod_spec.get("containers", []):
            found.append((doc["metadata"]["name"], container))
    return found


def _credential_secret(docs: list[dict]) -> dict[str, str]:
    secret = next(
        doc
        for doc in docs
        if doc.get("kind") == "Secret" and doc["metadata"]["name"] == SECRET_NAME
    )
    return secret["stringData"]


def test_rendered_secret_holds_every_chart_credential():
    """The chart renders one Secret that holds each credential under a stable key."""
    secret_keys = set(_credential_secret(_rendered_docs()))

    assert secret_keys == {
        "silo-access-key",
        "silo-secret-key",
        "zitadel-masterkey",
        "zitadel-admin-password",
        "spicedb-preshared-key",
        "postgres-password",
        "grafana-admin-password",
    }


def test_no_container_carries_a_credential_as_a_plain_value():
    """No plain env value is a credential under its own name or embeds one in a URL."""
    docs = _rendered_docs()
    credentials = [value for value in _credential_secret(docs).values() if value]

    leaks = []
    for workload, container in _containers(docs):
        for item in container.get("env", []):
            value = item.get("value")
            if not isinstance(value, str):
                continue
            for secret_value in credentials:
                named = CREDENTIAL_ENV_NAME.search(item["name"]) and value == secret_value
                embedded = f":{secret_value}@" in value
                if named or embedded:
                    leaks.append(f"{workload}/{container['name']}: {item['name']}")
    assert leaks == [], f"credential rendered as a plain value: {leaks}"


def test_no_container_argument_carries_a_credential():
    """Container args and commands hold no credential, because argv shows in kubectl describe."""
    docs = _rendered_docs()
    credentials = [value for value in _credential_secret(docs).values() if value]

    leaks = []
    for workload, container in _containers(docs):
        for part in container.get("args", []) + container.get("command", []):
            for secret_value in credentials:
                if secret_value in str(part):
                    leaks.append(f"{workload}/{container['name']}")
    assert leaks == [], f"credential rendered in args or command: {leaks}"


def test_credential_env_vars_read_the_secret_or_stay_empty():
    """A credential env var reads a Secret key. A plain value is allowed only when empty."""
    offenders = []
    for workload, container in _containers(_rendered_docs()):
        for item in container.get("env", []):
            if not CREDENTIAL_ENV_NAME.search(item["name"]):
                continue
            if item.get("value") == "":
                continue
            ref = item.get("valueFrom", {}).get("secretKeyRef")
            if ref is None or ref.get("name") != SECRET_NAME:
                offenders.append(f"{workload}/{container['name']}: {item['name']}")
    assert offenders == [], f"credential env var not read from {SECRET_NAME}: {offenders}"


def test_spicedb_server_reads_its_preshared_key_from_env_not_argv():
    """SpiceDB takes the preshared key from SPICEDB_GRPC_PRESHARED_KEY, read from the Secret."""
    spicedb = next(
        container
        for workload, container in _containers(_rendered_docs())
        if workload == "spicedb" and container["name"] == "spicedb"
    )
    env = {item["name"]: item for item in spicedb["env"]}

    assert env["SPICEDB_GRPC_PRESHARED_KEY"]["valueFrom"]["secretKeyRef"] == {
        "name": SECRET_NAME,
        "key": "spicedb-preshared-key",
    }
    assert "--grpc-preshared-key" not in spicedb.get("args", [])


def test_non_local_render_without_existing_secret_fails():
    """A non-local render fails when credentials.existingSecret is empty."""
    proc = _helm_template("--set", "global.environment=production")

    assert proc.returncode != 0
    assert "credentials.existingSecret must name a Secret" in proc.stderr


def test_existing_secret_replaces_the_rendered_secret():
    """With credentials.existingSecret, the chart renders no Secret and references that name."""
    docs = _rendered_docs(
        "--set",
        "global.environment=production",
        "--set",
        "credentials.existingSecret=team-credentials",
    )

    assert not [
        doc
        for doc in docs
        if doc.get("kind") == "Secret" and doc["metadata"]["name"] == SECRET_NAME
    ]
    refs = {
        item["valueFrom"]["secretKeyRef"]["name"]
        for _, container in _containers(docs)
        for item in container.get("env", [])
        if "secretKeyRef" in item.get("valueFrom", {})
    }
    assert "team-credentials" in refs
    assert SECRET_NAME not in refs
