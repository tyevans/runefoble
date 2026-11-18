"""Real Redis container for tests that read Redis Streams. Skips when Docker is absent."""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Generator
from contextlib import contextmanager

import redis

from tests.helpers.container_owner import owner_label_args, remove_test_container

REDIS_IMAGE = "redis:7-alpine"
# Upper bound for one Docker CLI call. The image pull is the slowest call.
DOCKER_TIMEOUT_SECONDS = 180.0


@contextmanager
def redis_container(port: int) -> Generator[str]:
    """Run Redis on the host port and yield its URL. Remove the container on exit."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        raise RuntimeError("Docker is required for the Redis container helper")
    name = f"runefoble-redis-test-{port}"
    subprocess.run(
        [docker_bin, "rm", "-f", name], capture_output=True, timeout=DOCKER_TIMEOUT_SECONDS
    )
    subprocess.run(
        [
            docker_bin,
            "run",
            "--rm",
            "--name",
            name,
            *owner_label_args(),
            "-d",
            "-p",
            f"127.0.0.1:{port}:6379",
            REDIS_IMAGE,
        ],
        check=True,
        capture_output=True,
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    url = f"redis://127.0.0.1:{port}/0"
    try:
        _wait_for_redis(url)
        yield url
    finally:
        remove_test_container(docker_bin, name)


def _wait_for_redis(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error = "no probe completed"
    while time.time() < deadline:
        try:
            if redis.Redis.from_url(url, socket_timeout=1).ping():
                return
            last_error = "ping returned False"
        except redis.RedisError as error:
            last_error = str(error)
        time.sleep(0.3)
    raise RuntimeError(f"Redis at {url} did not become ready: {last_error}")
