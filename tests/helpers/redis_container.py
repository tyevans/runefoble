"""Real Redis container for tests that read Redis Streams. Skips when Docker is absent."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import redis

from tests.helpers.container_owner import owner_label_args, remove_test_container
from tests.helpers.docker import DOCKER_TIMEOUT_SECONDS, require_docker_bin, run_docker
from tests.helpers.polling import wait_until

REDIS_IMAGE = "redis:7-alpine"


@contextmanager
def redis_container(port: int) -> Generator[str]:
    """Run Redis on the host port and yield its URL. Remove the container on exit."""
    docker_bin = require_docker_bin()
    name = f"runefoble-redis-test-{port}"
    run_docker(docker_bin, ["rm", "-f", name], timeout=DOCKER_TIMEOUT_SECONDS)
    started = run_docker(
        docker_bin,
        [
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
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    if started.returncode != 0:
        raise RuntimeError(f"docker run failed for {name}: {started.stderr.strip()}")
    url = f"redis://127.0.0.1:{port}/0"
    try:
        _wait_for_redis(url)
        yield url
    finally:
        remove_test_container(docker_bin, name)


def _wait_for_redis(url: str, timeout: float = 30.0) -> None:
    last_error = ["no probe completed"]

    def answers_ping() -> bool:
        try:
            if redis.Redis.from_url(url, socket_timeout=1).ping():
                return True
            last_error[0] = "ping returned False"
        except redis.RedisError as error:
            last_error[0] = str(error)
        return False

    if not wait_until(answers_ping, timeout_s=timeout, interval_s=0.3):
        raise RuntimeError(f"Redis at {url} did not become ready: {last_error[0]}")
