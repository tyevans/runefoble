"""Frontdoor tests for the delivery of the Zitadel admin PAT to the bootstrap Job.

Zitadel writes the machine user's personal access token to the file named by
`ZITADEL_FIRSTINSTANCE_PATPATH`. A publisher container in the Zitadel pod reads that file and
server-side applies the Secret `zitadel-admin` (key `pat`). The Kubernetes API is an external
process, so each test runs it as a local HTTP server. The rendered chart is read as public
manifests.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest
from helpers.local_http_server import LocalHttpServer, RecordedRequest
from runefoble_auth.kubernetes_secret import KubernetesApiError
from runefoble_auth.zitadel_pat_publisher import (
    PatFileTimeoutError,
    PublisherConfig,
    PublisherConfigError,
    run,
)

from tests.helpers.helm import render_chart

PAT_PATH = "/zitadel/bootstrap/admin.pat"
PAT_VALUE = "pat-issued-by-zitadel"
ADMIN_SECRET = "zitadel-admin"
KUBE_TOKEN = "kube-token-test"


class FakeKubernetes:
    """Records server-side apply requests for Secrets and answers with the configured status."""

    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.applied: list[RecordedRequest] = []

    def __call__(self, request: RecordedRequest) -> tuple[int, Any]:
        if request.method == "PATCH" and "/secrets/" in request.path:
            self.applied.append(request)
            return (
                (self.status, request.json())
                if self.status == 200
                else (
                    self.status,
                    {"message": "forbidden"},
                )
            )
        return 404, {"message": "not found"}

    def last_data(self) -> dict[str, str]:
        assert self.applied, "no Secret was applied"
        return self.applied[-1].json()["stringData"]


@pytest.fixture
def service_account(tmp_path: Path) -> Path:
    (tmp_path / "token").write_text(f"{KUBE_TOKEN}\n", encoding="utf-8")
    return tmp_path


def publisher_env(kube_url: str, pat_path: Path) -> dict[str, str]:
    return {
        "ZITADEL_PAT_PATH": str(pat_path),
        "ZITADEL_ADMIN_SECRET_NAME": ADMIN_SECRET,
        "POD_NAMESPACE": "runefoble",
        "KUBERNETES_API_URL": kube_url,
    }


def publisher_config(kube_url: str, pat_path: Path, service_account: Path) -> PublisherConfig:
    return PublisherConfig.from_env(
        publisher_env(kube_url, pat_path), service_account_dir=service_account
    )


def test_publisher_applies_the_pat_when_zitadel_writes_the_file(tmp_path, service_account):
    pat_file = tmp_path / "admin.pat"
    fake = FakeKubernetes()
    with LocalHttpServer(fake) as server:

        def zitadel_writes_pat_later() -> None:
            time.sleep(0.3)
            pat_file.write_text(PAT_VALUE, encoding="utf-8")

        threading.Thread(target=zitadel_writes_pat_later, daemon=True).start()
        config = publisher_config(server.url, pat_file, service_account)
        run(config, timeout_seconds=10, poll_seconds=0.05)

    assert fake.last_data() == {"pat": PAT_VALUE}
    request = fake.applied[-1]
    assert request.path.startswith(f"/api/v1/namespaces/runefoble/secrets/{ADMIN_SECRET}?")
    assert request.headers["Authorization"] == f"Bearer {KUBE_TOKEN}"
    assert request.headers["Content-Type"] == "application/apply-patch+yaml"
    assert request.json()["metadata"]["name"] == ADMIN_SECRET


def test_publisher_drops_the_trailing_newline_from_the_pat(tmp_path, service_account):
    pat_file = tmp_path / "admin.pat"
    pat_file.write_text(f"{PAT_VALUE}\n", encoding="utf-8")
    fake = FakeKubernetes()
    with LocalHttpServer(fake) as server:
        run(publisher_config(server.url, pat_file, service_account), timeout_seconds=5)

    assert fake.last_data() == {"pat": PAT_VALUE}


def test_missing_pat_file_is_reported_with_its_path(tmp_path, service_account):
    pat_file = tmp_path / "never-written.pat"
    fake = FakeKubernetes()
    with LocalHttpServer(fake) as server:
        config = publisher_config(server.url, pat_file, service_account)
        with pytest.raises(PatFileTimeoutError, match="never-written.pat"):
            run(config, timeout_seconds=0.3, poll_seconds=0.05)

    assert fake.applied == []


def test_kubernetes_refusal_is_reported_with_the_status(tmp_path, service_account):
    pat_file = tmp_path / "admin.pat"
    pat_file.write_text(PAT_VALUE, encoding="utf-8")
    fake = FakeKubernetes(status=403)
    with LocalHttpServer(fake) as server:
        config = publisher_config(server.url, pat_file, service_account)
        with pytest.raises(KubernetesApiError, match="HTTP 403"):
            run(config, timeout_seconds=5)


def test_missing_setting_is_named_in_the_error(tmp_path, service_account):
    env = publisher_env("http://127.0.0.1:1", tmp_path / "admin.pat")
    del env["POD_NAMESPACE"]
    with pytest.raises(PublisherConfigError, match="POD_NAMESPACE"):
        PublisherConfig.from_env(env, service_account_dir=service_account)


# Chart wiring: the Zitadel pod writes the PAT to a shared volume and publishes it.


def _render() -> list[dict]:
    return render_chart()


def _find(docs: list[dict], kind: str, name: str) -> dict:
    found = next(
        (d for d in docs if d.get("kind") == kind and d.get("metadata", {}).get("name") == name),
        None,
    )
    assert found is not None, f"{kind} {name} not found in rendered chart"
    return found


def _zitadel_pod_spec() -> dict:
    return _find(_render(), "Deployment", "zitadel")["spec"]["template"]["spec"]


def _container(pod: dict, name: str) -> dict:
    return next(c for c in pod["containers"] if c["name"] == name)


def test_zitadel_pod_ignores_the_service_link_variables():
    """A Service named zitadel would inject ZITADEL_PORT, which Zitadel reads as its port."""
    assert _zitadel_pod_spec()["enableServiceLinks"] is False


def test_zitadel_starts_with_the_masterkey_from_the_environment():
    args = _container(_zitadel_pod_spec(), "zitadel")["args"]
    assert "--masterkeyFromEnv" in args
    assert args[0] == "start-from-init"


def test_zitadel_writes_the_admin_pat_to_a_volume_the_publisher_reads():
    pod = _zitadel_pod_spec()
    zitadel = _container(pod, "zitadel")
    publisher = _container(pod, "pat-publisher")

    pat_path = next(
        e["value"] for e in zitadel["env"] if e["name"] == "ZITADEL_FIRSTINSTANCE_PATPATH"
    )
    assert pat_path == PAT_PATH
    assert next(e["value"] for e in publisher["env"] if e["name"] == "ZITADEL_PAT_PATH") == PAT_PATH

    mount_dir = str(Path(PAT_PATH).parent)
    zitadel_mount = next(m for m in zitadel["volumeMounts"] if m["mountPath"] == mount_dir)
    publisher_mount = next(m for m in publisher["volumeMounts"] if m["mountPath"] == mount_dir)
    assert zitadel_mount["name"] == publisher_mount["name"]
    assert any(v["name"] == zitadel_mount["name"] and "emptyDir" in v for v in pod["volumes"])


def test_publisher_runs_the_gateway_image_with_the_zitadel_service_account():
    pod = _zitadel_pod_spec()
    publisher = _container(pod, "pat-publisher")
    gateway_image = _find(_render(), "Job", "zitadel-bootstrap")["spec"]["template"]["spec"][
        "containers"
    ][0]["image"]
    assert publisher["image"] == gateway_image
    assert publisher["command"] == ["python", "-m", "runefoble_auth.zitadel_pat_publisher"]
    assert pod["serviceAccountName"] == "zitadel"


def test_zitadel_service_account_may_write_only_the_admin_secret_by_name():
    docs = _render()
    role = _find(docs, "Role", "zitadel")
    named = [r for r in role["rules"] if r.get("resourceNames")]
    assert named, "Role names no Secret"
    assert all(r["resourceNames"] == [ADMIN_SECRET] for r in named)
    assert {verb for r in named for verb in r["verbs"]} == {"get", "patch"}

    binding = _find(docs, "RoleBinding", "zitadel")
    assert binding["roleRef"]["name"] == "zitadel"
    assert binding["subjects"][0]["name"] == "zitadel"
    assert _find(docs, "ServiceAccount", "zitadel")
