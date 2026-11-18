"""Shared SpiceDB test container fixtures and network helpers.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import subprocess
import time
from collections.abc import Coroutine, Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import grpc
import pytest
from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.spicedb import SpiceDBClient

SPICEDB_TEST_PRESHARED_KEY = "test"
SPICEDB_SCHEMA_DEADLINE_S = 30.0


def find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_spicedb_endpoint() -> Generator[str | None]:
    """Spins up a lightweight isolated in-memory SpiceDB test container if Docker is available."""
    if not shutil.which("docker"):
        yield None
        return

    port = find_free_port()
    try:
        container_id = (
            subprocess.check_output(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "-p",
                    f"{port}:50051",
                    "authzed/spicedb:v1.34.0",
                    "serve-testing",
                ],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        yield None
        return

    endpoint = f"127.0.0.1:{port}"
    deadline = time.time() + 15
    ready = False
    while time.time() < deadline:
        try:
            import grpc
            from authzed.api.v1 import InsecureClient, ReadSchemaRequest

            test_client = InsecureClient(endpoint, "test")
            try:
                test_client.ReadSchema(ReadSchemaRequest())
                ready = True
                break
            except grpc.RpcError as rpc_err:
                if rpc_err.code() in (grpc.StatusCode.OK, grpc.StatusCode.NOT_FOUND):
                    ready = True
                    break
        except Exception:
            pass
        time.sleep(0.2)

    if not ready:
        subprocess.run(["docker", "kill", container_id], capture_output=True)
        yield None
        return

    yield endpoint

    subprocess.run(["docker", "kill", container_id], capture_output=True)


def _run_blocking(coro: Coroutine[Any, Any, Any]) -> Any:
    """Runs a coroutine to completion from sync test code, even inside a running event loop."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class LiveSpiceDB:
    """A SpiceDB container with the Runefoble schema applied.

    Tests seed campaign roles through the SpiceDB gRPC write API, as an operator would.
    The Audience Studio process reads the same container through its endpoint setting.
    """

    def __init__(self, endpoint: str, preshared_key: str) -> None:
        self.endpoint = endpoint
        self.preshared_key = preshared_key

    @property
    def env(self) -> dict[str, str]:
        """Environment variables that point a service process at this container."""
        return {
            "RUNEFOBLE_SPICEDB_ENDPOINT": self.endpoint,
            "RUNEFOBLE_SPICEDB_PRESHARED_KEY": self.preshared_key,
        }

    def grant(self, campaign_id: str, relation: str, user_id: str) -> None:
        """Write one `campaign` relation for a user (for example `dungeon_master`)."""
        client = SpiceDBClient(
            endpoint=self.endpoint, token=self.preshared_key, insecure=True, use_mock=False
        )
        _run_blocking(client.write_relationship("campaign", campaign_id, relation, "user", user_id))


async def _apply_schema_when_ready(endpoint: str, preshared_key: str) -> None:
    """Applies the checked-in schema once the container accepts gRPC. Fails after the deadline."""
    deadline = time.time() + SPICEDB_SCHEMA_DEADLINE_S
    while True:
        client = SpiceDBClient(
            endpoint=endpoint, token=preshared_key, insecure=True, use_mock=False
        )
        try:
            await bootstrap_schema(
                endpoint=endpoint, token=preshared_key, client=client, insecure=True
            )
            return
        except grpc.RpcError as rpc_err:
            if time.time() > deadline:
                raise RuntimeError(
                    f"SpiceDB at {endpoint} did not accept the schema: {rpc_err}"
                ) from rpc_err
            time.sleep(0.3)


@pytest.fixture(scope="module")
def live_spicedb_with_schema() -> Generator[LiveSpiceDB]:
    """Runs a SpiceDB test container with runefoble.zed applied. Fails loudly when Docker is missing."""
    if not shutil.which("docker"):
        pytest.fail("Docker is required for the live SpiceDB tests (authzed/spicedb:v1.34.0)")

    port = find_free_port()
    container_id = (
        subprocess.check_output(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "-p",
                f"{port}:50051",
                "authzed/spicedb:v1.34.0",
                "serve-testing",
            ],
            stderr=subprocess.DEVNULL,
        )
        .decode()
        .strip()
    )
    try:
        endpoint = f"127.0.0.1:{port}"
        _run_blocking(_apply_schema_when_ready(endpoint, SPICEDB_TEST_PRESHARED_KEY))
        yield LiveSpiceDB(endpoint, SPICEDB_TEST_PRESHARED_KEY)
    finally:
        subprocess.run(["docker", "kill", container_id], capture_output=True)
