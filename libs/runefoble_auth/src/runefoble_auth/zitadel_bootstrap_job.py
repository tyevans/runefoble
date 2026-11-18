"""Entry point for the Zitadel bootstrap Job (`python -m runefoble_auth.zitadel_bootstrap_job`).

The Job reads its settings from the environment, provisions the OIDC project and web
application, and server-side applies the Kubernetes Secret that the workloads read:

- `project-id`: the Zitadel project ID. Services use it as the expected token audience.
- `client-id`: the public client ID of the web application. The App Shell uses it.

Server-side apply makes a repeated run a no-op for the Secret when the data is unchanged.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from runefoble_auth.zitadel_bootstrap import (
    ApplicationSpec,
    Provisioned,
    ZitadelManagement,
    provision,
)

SERVICE_ACCOUNT_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")
KUBERNETES_API_TIMEOUT_SECONDS = 10
READY_TIMEOUT_SECONDS = 300
FIELD_MANAGER = "runefoble-zitadel-bootstrap"


class BootstrapConfigError(ValueError):
    """A required setting is missing or empty. The message names the variable."""


@dataclass(frozen=True)
class BootstrapConfig:
    issuer: str
    internal_url: str
    admin_token: str
    namespace: str
    secret_name: str
    spec: ApplicationSpec
    kubernetes_api: str
    kubernetes_token: str
    kubernetes_ca_file: str | None

    @classmethod
    def from_env(
        cls, env: Mapping[str, str], service_account_dir: Path = SERVICE_ACCOUNT_DIR
    ) -> BootstrapConfig:
        token_path = service_account_dir / "token"
        ca_path = service_account_dir / "ca.crt"
        return cls(
            issuer=_required(env, "RUNEFOBLE_ZITADEL_ISSUER"),
            internal_url=_required(env, "RUNEFOBLE_ZITADEL_INTERNAL_URL"),
            admin_token=_required(env, "ZITADEL_ADMIN_PAT"),
            namespace=_required(env, "POD_NAMESPACE"),
            secret_name=_required(env, "RUNEFOBLE_ZITADEL_CLIENT_SECRET_NAME"),
            spec=ApplicationSpec(
                project_name=_required(env, "RUNEFOBLE_ZITADEL_PROJECT_NAME"),
                app_name=_required(env, "RUNEFOBLE_ZITADEL_APP_NAME"),
                redirect_uris=_csv(env, "RUNEFOBLE_ZITADEL_REDIRECT_URIS"),
                post_logout_redirect_uris=_csv(env, "RUNEFOBLE_ZITADEL_POST_LOGOUT_URIS"),
                dev_mode=_required(env, "RUNEFOBLE_ZITADEL_DEV_MODE").lower() == "true",
            ),
            kubernetes_api=_required(env, "KUBERNETES_API_URL"),
            kubernetes_token=token_path.read_text(encoding="utf-8").strip(),
            kubernetes_ca_file=str(ca_path) if ca_path.exists() else None,
        )


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise BootstrapConfigError(f"{name} is not set. The bootstrap Job cannot run without it.")
    return value


def _csv(env: Mapping[str, str], name: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in _required(env, name).split(",") if item.strip())
    if not values:
        raise BootstrapConfigError(f"{name} lists no URIs.")
    return values


def apply_client_secret(config: BootstrapConfig, provisioned: Provisioned) -> None:
    """Server-side apply the Secret that holds the generated project and client IDs."""
    url = (
        f"{config.kubernetes_api.rstrip('/')}/api/v1/namespaces/{config.namespace}"
        f"/secrets/{config.secret_name}"
        f"?fieldManager={FIELD_MANAGER}&force=true"
    )
    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": config.secret_name,
            "namespace": config.namespace,
            "labels": {"app.kubernetes.io/part-of": "runefoble"},
        },
        "type": "Opaque",
        "stringData": {"project-id": provisioned.project_id, "client-id": provisioned.client_id},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {config.kubernetes_token}",
            "Content-Type": "application/apply-patch+yaml",
            "Accept": "application/json",
        },
    )
    context = (
        ssl.create_default_context(cafile=config.kubernetes_ca_file) if _is_https(url) else None
    )
    try:
        with urllib.request.urlopen(
            request, timeout=KUBERNETES_API_TIMEOUT_SECONDS, context=context
        ) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(
            f"Applying Secret {config.secret_name} returned HTTP {exc.code}: {detail}"
        ) from exc


def _is_https(url: str) -> bool:
    return urllib.parse.urlsplit(url).scheme == "https"


def run(config: BootstrapConfig) -> Provisioned:
    client = ZitadelManagement(config.issuer, config.internal_url, config.admin_token)
    client.wait_until_ready(READY_TIMEOUT_SECONDS)
    provisioned = provision(client, config.spec)
    apply_client_secret(config, provisioned)
    return provisioned


def main(
    env: Mapping[str, str] | None = None,
    service_account_dir: Path = SERVICE_ACCOUNT_DIR,
) -> int:
    config = BootstrapConfig.from_env(os.environ if env is None else env, service_account_dir)
    provisioned = run(config)
    print(
        f"zitadel bootstrap: project {provisioned.project_id}, application {provisioned.app_id}, "
        f"secret {config.secret_name} applied",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
