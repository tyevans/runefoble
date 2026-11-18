"""Shared SpiceDB test container fixtures and network helpers.

Two fixtures start an in-memory SpiceDB container pinned to the image in the Helm values:

- `live_spicedb_endpoint`: the endpoint only. It yields None when Docker is missing.
- `live_spicedb_with_schema`: the endpoint, a client, and test helpers (`env`, `grant`), with
  runefoble.zed loaded through `bootstrap_schema`. A failed schema write fails the fixture.

Set `RUNEFOBLE_REQUIRE_LIVE_SPICEDB=1` to make a missing Docker or a failed start raise.
Without it, the strict fixture skips and the endpoint fixture yields None.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Coroutine, Generator, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.spicedb import SpiceDBClient, preshared_key_from_env

REPO_ROOT = Path(__file__).resolve().parents[2]
HELM_VALUES = REPO_ROOT / "deployments" / "helm" / "runefoble" / "values.yaml"
REQUIRE_LIVE_ENV = "RUNEFOBLE_REQUIRE_LIVE_SPICEDB"
GRPC_PORT = 50051


@dataclass(frozen=True)
class LiveSpiceDB:
    """A running SpiceDB container with runefoble.zed loaded.

    Tests seed campaign roles through the gRPC write API, as an operator would.
    The Audience Studio process reads the same container through `env`.
    """

    endpoint: str
    client: SpiceDBClient

    @property
    def env(self) -> dict[str, str]:
        """Environment variables that point a service process at this container."""
        return {
            "RUNEFOBLE_SPICEDB_ENDPOINT": self.endpoint,
            "RUNEFOBLE_SPICEDB_PRESHARED_KEY": self.client.token,
        }

    def grant(self, campaign_id: str, relation: str, user_id: str) -> None:
        """Write one `campaign` relation for a user (for example `game_master`)."""
        _run_blocking(
            _write_campaign_relation(
                self.endpoint, self.client.token, campaign_id, relation, user_id
            )
        )


async def _write_campaign_relation(
    endpoint: str, token: str, campaign_id: str, relation: str, user_id: str
) -> None:
    """Open a client on the running loop and write one campaign relation."""
    client = SpiceDBClient(endpoint=endpoint, token=token, insecure=True)
    await client.write_relationship("campaign", campaign_id, relation, "user", user_id)


def _run_blocking(coro: Coroutine[Any, Any, Any]) -> Any:
    """Runs a coroutine to completion from sync test code, even inside a running event loop."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def spicedb_image() -> str:
    """Return the SpiceDB image tag from the Helm values. The test container uses the same tag."""
    values = yaml.safe_load(HELM_VALUES.read_text(encoding="utf-8"))
    return str(values["spicedb"]["image"])


def find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def require_live_spicedb() -> bool:
    return os.getenv(REQUIRE_LIVE_ENV) == "1"


def _wait_until_ready(endpoint: str, token: str, timeout_seconds: float = 30.0) -> None:
    """Poll ReadSchema until the server answers. NOT_FOUND means the server is up with no schema."""
    import grpc
    from authzed.api.v1 import InsecureClient, ReadSchemaRequest

    deadline = time.monotonic() + timeout_seconds
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            InsecureClient(endpoint, token).ReadSchema(ReadSchemaRequest())
            return
        except grpc.RpcError as rpc_err:
            if rpc_err.code() == grpc.StatusCode.NOT_FOUND:
                return
            last_error = f"{rpc_err.code()}: {rpc_err.details()}"
        time.sleep(0.2)
    raise RuntimeError(f"SpiceDB at {endpoint} did not become ready: {last_error}")


@contextlib.contextmanager
def run_spicedb_container(image: str, token: str) -> Iterator[str]:
    """Start an in-memory SpiceDB container and yield its endpoint.

    `serve-testing` isolates one datastore per client token. The container is killed on exit.

    Raises:
        RuntimeError: Docker is missing, `docker run` fails, or the server never answers.
    """
    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed or not on PATH")
    port = find_free_port()
    try:
        container_id = (
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "-p",
                    f"127.0.0.1:{port}:{GRPC_PORT}",
                    image,
                    "serve-testing",
                ],
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"docker run failed for {image}: {stderr}") from exc

    endpoint = f"127.0.0.1:{port}"
    try:
        _wait_until_ready(endpoint, token)
        yield endpoint
    finally:
        subprocess.run(["docker", "kill", container_id], capture_output=True, check=False)


@pytest.fixture(scope="module")
def live_spicedb_endpoint() -> Generator[str | None]:
    """Spin up an isolated in-memory SpiceDB container. Yield None when Docker is unavailable."""
    with ExitStack() as stack:
        try:
            endpoint = stack.enter_context(
                run_spicedb_container(spicedb_image(), preshared_key_from_env())
            )
        except RuntimeError:
            if require_live_spicedb():
                raise
            yield None
            return
        yield endpoint


@pytest.fixture(scope="module")
def live_spicedb_with_schema() -> Generator[LiveSpiceDB]:
    """Start SpiceDB, load runefoble.zed through bootstrap_schema, and yield the endpoint and client.

    A failed schema write means the schema is invalid, so the fixture errors.
    """
    token = preshared_key_from_env()
    with ExitStack() as stack:
        try:
            endpoint = stack.enter_context(run_spicedb_container(spicedb_image(), token))
        except RuntimeError as exc:
            if require_live_spicedb():
                raise
            pytest.skip(f"Live SpiceDB unavailable ({exc}). Set {REQUIRE_LIVE_ENV}=1 to fail.")
        client = SpiceDBClient(endpoint=endpoint, token=token, insecure=True)
        asyncio.run(bootstrap_schema(client=client))
        yield LiveSpiceDB(endpoint=endpoint, client=client)
