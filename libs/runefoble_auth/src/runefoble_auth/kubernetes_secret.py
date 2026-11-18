"""Server-side apply of a Kubernetes Secret through the in-cluster API.

Workloads in the Runefoble release use this helper to publish Secrets that Zitadel or the
bootstrap Job generates at run time. The request uses the pod's service account token.
A repeated apply with the same data changes nothing.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KUBERNETES_API_TIMEOUT_SECONDS = 10
SERVICE_ACCOUNT_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")


class KubernetesApiError(RuntimeError):
    """The Kubernetes API refused a request. The message names the Secret and the status."""


def read_service_account_token(service_account_dir: Path = SERVICE_ACCOUNT_DIR) -> str:
    return (service_account_dir / "token").read_text(encoding="utf-8").strip()


def service_account_ca_file(service_account_dir: Path = SERVICE_ACCOUNT_DIR) -> str | None:
    ca_path = service_account_dir / "ca.crt"
    return str(ca_path) if ca_path.exists() else None


def apply_secret(
    *,
    api_url: str,
    token: str,
    ca_file: str | None,
    namespace: str,
    name: str,
    string_data: dict[str, str],
    field_manager: str,
) -> None:
    """Server-side apply a generic Secret. It creates the Secret or updates the named keys."""
    url = (
        f"{api_url.rstrip('/')}/api/v1/namespaces/{namespace}/secrets/{name}"
        f"?fieldManager={field_manager}&force=true"
    )
    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app.kubernetes.io/part-of": "runefoble"},
        },
        "type": "Opaque",
        "stringData": string_data,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/apply-patch+yaml",
            "Accept": "application/json",
        },
    )
    context = (
        ssl.create_default_context(cafile=ca_file)
        if urllib.parse.urlsplit(url).scheme == "https"
        else None
    )
    try:
        with urllib.request.urlopen(
            request, timeout=KUBERNETES_API_TIMEOUT_SECONDS, context=context
        ) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise KubernetesApiError(
            f"Applying Secret {name} returned HTTP {exc.code}: {detail}"
        ) from exc
