"""Real Silo (Chainguard MinIO) container for tests of the Silo client. Skips without Docker.

The images are the digest-pinned images of the Helm chart (`silo.image` and
`silo.bucketJob.image` in `deployments/helm/runefoble/values.yaml`). The bucket is made
with the MinIO client and the same arguments as the chart's `silo-buckets` Job.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import yaml

from tests.helpers.container_owner import owner_label_args, remove_test_container
from tests.helpers.docker import DOCKER_TIMEOUT_SECONDS, docker_bin, run_docker
from tests.helpers.polling import wait_until

VALUES_PATH = Path(__file__).resolve().parents[2] / "deployments/helm/runefoble/values.yaml"
ROOT_USER = "silo-test-admin"
ROOT_PASSWORD = "silo-test-secret-0926"


@dataclass(frozen=True)
class MinioServer:
    """Connection data of one running Silo container."""

    endpoint: str
    access_key: str
    secret_key: str
    bucket: str


def chart_images() -> tuple[str, str]:
    """Return the Silo server image and the MinIO client image that the chart pins."""
    silo = yaml.safe_load(VALUES_PATH.read_text(encoding="utf-8"))["silo"]
    return silo["image"], silo["bucketJob"]["image"]


def _require_docker() -> str:
    docker = docker_bin()
    if not docker:
        pytest.skip("Docker is not available: the docker CLI is not on PATH")
    probe = run_docker(docker, ["info"], timeout=DOCKER_TIMEOUT_SECONDS)
    if probe.returncode != 0:
        pytest.skip(
            f"Docker is not available: the daemon is not reachable ({probe.stderr.strip()})"
        )
    return docker


@contextmanager
def minio_container(port: int, bucket: str) -> Generator[MinioServer]:
    """Run Silo on the host port, create the bucket, and yield the connection data."""
    docker = _require_docker()
    server_image, client_image = chart_images()
    name = f"runefoble-silo-test-{port}"
    started = run_docker(
        docker,
        [
            "run",
            "--rm",
            "--name",
            name,
            *owner_label_args(),
            "-d",
            "-p",
            f"127.0.0.1:{port}:9000",
            "-e",
            f"MINIO_ROOT_USER={ROOT_USER}",
            "-e",
            f"MINIO_ROOT_PASSWORD={ROOT_PASSWORD}",
            server_image,
            "server",
            "/data",
        ],
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    if started.returncode != 0:
        raise RuntimeError(f"docker run failed for {name}: {started.stderr.strip()}")
    endpoint = f"http://127.0.0.1:{port}"
    try:
        _wait_for_minio(endpoint)
        _create_bucket(docker, client_image, name, bucket)
        yield MinioServer(endpoint, ROOT_USER, ROOT_PASSWORD, bucket)
    finally:
        remove_test_container(docker, name)


def _wait_for_minio(endpoint: str, timeout: float = 60.0) -> None:
    def is_live() -> bool:
        try:
            return httpx.get(f"{endpoint}/minio/health/live", timeout=1).status_code == 200
        except httpx.HTTPError:
            return False

    if not wait_until(is_live, timeout_s=timeout, interval_s=0.5):
        raise RuntimeError(f"Silo at {endpoint} did not become live in {timeout} seconds")


def _create_bucket(docker: str, client_image: str, server_name: str, bucket: str) -> None:
    """Make the bucket as the chart Job does: `mc mb --ignore-existing silo/<bucket>`."""
    result = run_docker(
        docker,
        [
            "run",
            "--rm",
            *owner_label_args(),
            "--network",
            f"container:{server_name}",
            "-e",
            f"MC_HOST_silo=http://{ROOT_USER}:{ROOT_PASSWORD}@127.0.0.1:9000",
            client_image,
            "mb",
            "--ignore-existing",
            f"silo/{bucket}",
        ],
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(f"mc mb failed for bucket {bucket}: {result.stderr.strip()}")
