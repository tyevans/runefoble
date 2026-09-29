"""Shared SpiceDB test container fixtures and network helpers.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from collections.abc import Generator

import pytest


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
