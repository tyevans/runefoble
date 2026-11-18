"""Owner labels for Docker containers that test fixtures start.

Each test container carries the pid and host name of the pytest process that started it.
Before a fixture starts a container, it removes the labelled containers whose owner process is
no longer alive on this host. A killed run (SIGKILL, timeout, interrupt) skips fixture teardown,
so this rule removes its containers on the next run.

Containers of a live owner, and containers without these labels, are never touched.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import warnings

OWNER_PID_LABEL = "runefoble.test.owner-pid"
OWNER_HOST_LABEL = "runefoble.test.owner-host"
DOCKER_TIMEOUT_SECONDS = 60.0


def owner_label_args() -> list[str]:
    """Return `docker run` flags that record this process as the owner of the container."""
    return [
        "--label",
        f"{OWNER_PID_LABEL}={os.getpid()}",
        "--label",
        f"{OWNER_HOST_LABEL}={socket.gethostname()}",
    ]


def _pid_is_alive(pid: int) -> bool:
    """Return True when a process with this pid exists. A zombie counts as alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but belongs to another user, so it is alive.
        return True
    return True


def remove_orphaned_test_containers(docker_bin: str | None = None) -> None:
    """Remove labelled test containers whose owner process is dead on this host.

    Containers without the owner labels are not listed, so they are never removed. A container
    whose owner is alive is kept. If `docker ps` fails, a warning names the failure and nothing
    is removed.
    """
    docker = docker_bin or shutil.which("docker")
    if not docker:
        return
    host = socket.gethostname()
    listing = subprocess.run(
        [
            docker,
            "ps",
            "-a",
            "--filter",
            f"label={OWNER_PID_LABEL}",
            "--format",
            '{{.ID}}|{{.Label "' + OWNER_PID_LABEL + '"}}|{{.Label "' + OWNER_HOST_LABEL + '"}}',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    if listing.returncode != 0:
        warnings.warn(
            f"docker ps failed, orphaned test containers were not reaped: {listing.stderr.strip()}",
            stacklevel=2,
        )
        return
    for line in listing.stdout.splitlines():
        container_id, pid_text, owner_host = line.split("|")
        if owner_host != host:
            continue
        try:
            owner_pid = int(pid_text)
        except ValueError:
            # The label is written only as an integer by owner_label_args. Any other value is
            # not ours to remove.
            continue
        if _pid_is_alive(owner_pid):
            continue
        subprocess.run(
            [docker, "rm", "-f", container_id],
            capture_output=True,
            check=False,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )


def remove_test_container(docker_bin: str, container_name: str) -> None:
    """Force-remove a container that a fixture started. Raise when Docker refuses.

    A container that is already gone is not a failure: `docker run --rm` removes a container
    that exits on its own. Any other removal failure raises with the container name, so the
    teardown error shows in the test output.
    """
    result = subprocess.run(
        [docker_bin, "rm", "-f", container_name],
        capture_output=True,
        text=True,
        check=False,
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    if result.returncode == 0 or "No such container" in result.stderr:
        return
    raise RuntimeError(f"Failed to remove test container {container_name}: {result.stderr.strip()}")
