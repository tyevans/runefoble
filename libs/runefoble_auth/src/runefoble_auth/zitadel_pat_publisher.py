"""Entry point for the Zitadel PAT publisher (`python -m runefoble_auth.zitadel_pat_publisher`).

Zitadel writes the admin machine user's personal access token to a file on first start. This
sidecar, in the Zitadel pod, waits for that file and server-side applies the Secret that the
bootstrap Job reads. The Secret key is `pat`. The Job reads the Secret when it starts, so a
stale token from an earlier install is replaced before the Job needs it.

The sidecar stays running after it publishes. A container that exits restarts, and the
restart would publish the same token again.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from runefoble_auth.kubernetes_secret import (
    SERVICE_ACCOUNT_DIR,
    apply_secret,
    read_service_account_token,
    service_account_ca_file,
)

DEFAULT_TIMEOUT_SECONDS = 1800.0
POLL_SECONDS = 1.0
FIELD_MANAGER = "runefoble-zitadel-pat-publisher"
SECRET_KEY = "pat"


class PublisherConfigError(ValueError):
    """A required setting is missing or empty. The message names the variable."""


class PatFileTimeoutError(RuntimeError):
    """Zitadel did not write the PAT file in time. The message names the file."""


@dataclass(frozen=True)
class PublisherConfig:
    pat_path: Path
    namespace: str
    secret_name: str
    kubernetes_api: str
    kubernetes_token: str
    kubernetes_ca_file: str | None

    @classmethod
    def from_env(
        cls, env: Mapping[str, str], service_account_dir: Path = SERVICE_ACCOUNT_DIR
    ) -> PublisherConfig:
        return cls(
            pat_path=Path(_required(env, "ZITADEL_PAT_PATH")),
            namespace=_required(env, "POD_NAMESPACE"),
            secret_name=_required(env, "ZITADEL_ADMIN_SECRET_NAME"),
            kubernetes_api=_required(env, "KUBERNETES_API_URL"),
            kubernetes_token=read_service_account_token(service_account_dir),
            kubernetes_ca_file=service_account_ca_file(service_account_dir),
        )


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise PublisherConfigError(f"{name} is not set. The PAT publisher cannot run without it.")
    return value


def read_pat(pat_path: Path, timeout_seconds: float, poll_seconds: float) -> str:
    """Wait until the PAT file has content, then return the token without surrounding space."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if pat_path.is_file():
            token = pat_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        if time.monotonic() >= deadline:
            raise PatFileTimeoutError(
                f"Zitadel did not write the PAT to {pat_path} within {timeout_seconds:g} seconds."
            )
        time.sleep(poll_seconds)


def run(
    config: PublisherConfig,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    poll_seconds: float = POLL_SECONDS,
) -> None:
    """Read the PAT and publish it to the admin Secret. Returns after the apply succeeds."""
    token = read_pat(config.pat_path, timeout_seconds, poll_seconds)
    apply_secret(
        api_url=config.kubernetes_api,
        token=config.kubernetes_token,
        ca_file=config.kubernetes_ca_file,
        namespace=config.namespace,
        name=config.secret_name,
        string_data={SECRET_KEY: token},
        field_manager=FIELD_MANAGER,
    )


def main(
    env: Mapping[str, str] | None = None,
    service_account_dir: Path = SERVICE_ACCOUNT_DIR,
) -> int:
    config = PublisherConfig.from_env(os.environ if env is None else env, service_account_dir)
    run(config)
    print(
        f"zitadel pat publisher: secret {config.secret_name} key {SECRET_KEY} applied",
        flush=True,
    )
    threading.Event().wait()  # Keep the sidecar running. See the module docstring.
    return 0


if __name__ == "__main__":
    sys.exit(main())
