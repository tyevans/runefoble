"""Teardown of test containers reports a failed removal with the container name.

Docker is a process boundary, so each test puts a small fake `docker` executable in a temp
directory and passes its path to the helper.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.helpers.container_owner import remove_test_container


def _fake_docker(directory: Path, stderr: str, exit_code: int) -> str:
    script = directory / "docker"
    script.write_text(f"#!/bin/sh\nprintf '%s\\n' '{stderr}' >&2\nexit {exit_code}\n")
    os.chmod(script, 0o755)
    return str(script)


def test_failed_container_removal_raises_with_container_name(tmp_path: Path) -> None:
    docker = _fake_docker(tmp_path, "Error response from daemon: device busy", 1)

    with pytest.raises(RuntimeError, match="runefoble-redis-test-6399") as raised:
        remove_test_container(docker, "runefoble-redis-test-6399")

    assert "device busy" in str(raised.value)


def test_removal_of_an_already_gone_container_is_not_a_failure(tmp_path: Path) -> None:
    docker = _fake_docker(tmp_path, "Error: No such container: runefoble-pg-test-5432", 1)

    remove_test_container(docker, "runefoble-pg-test-5432")


def test_successful_removal_returns_quietly(tmp_path: Path) -> None:
    docker = _fake_docker(tmp_path, "runefoble-pg-test-5432", 0)

    remove_test_container(docker, "runefoble-pg-test-5432")
