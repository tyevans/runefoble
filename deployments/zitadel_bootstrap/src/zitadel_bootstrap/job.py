"""Entry point for the Zitadel bootstrap Job (`python -m zitadel_bootstrap.job`).

The Job reads its settings from the environment, provisions the OIDC project and web
application, binds the Action that puts `preferred_username` in access tokens
(`token_claims`), and server-side applies the Kubernetes Secret that the workloads read:

- `project-id`: the Zitadel project ID. Services use it as the expected token audience.
- `client-id`: the public client ID of the web application. The App Shell uses it.

Server-side apply makes a repeated run a no-op for the Secret when the data is unchanged.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from runefoble_auth.kubernetes_secret import (
    SERVICE_ACCOUNT_DIR,
    apply_secret,
    read_service_account_token,
    service_account_ca_file,
)

from zitadel_bootstrap.provisioning import (
    ApplicationSpec,
    Provisioned,
    ZitadelManagement,
    provision,
)
from zitadel_bootstrap.token_claims import ensure_username_claim_action

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
            kubernetes_token=read_service_account_token(service_account_dir),
            kubernetes_ca_file=service_account_ca_file(service_account_dir),
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
    apply_secret(
        api_url=config.kubernetes_api,
        token=config.kubernetes_token,
        ca_file=config.kubernetes_ca_file,
        namespace=config.namespace,
        name=config.secret_name,
        string_data={"project-id": provisioned.project_id, "client-id": provisioned.client_id},
        field_manager=FIELD_MANAGER,
    )


def run(config: BootstrapConfig) -> Provisioned:
    client = ZitadelManagement(config.issuer, config.internal_url, config.admin_token)
    client.wait_until_ready(READY_TIMEOUT_SECONDS)
    provisioned = provision(client, config.spec)
    ensure_username_claim_action(client)
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
