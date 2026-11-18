"""Shared PostgreSQL test container fixtures and network helpers.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: Core Event Sourcing with eventsource-py
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest

from tests.helpers.container_owner import owner_label_args, remove_test_container
from tests.helpers.docker import DOCKER_TIMEOUT_SECONDS, docker_bin, run_docker
from tests.helpers.polling import wait_until
from tests.helpers.ports import free_port


@pytest.fixture(scope="module")
def postgres_service() -> Generator[dict[str, str | int]]:
    """Provision a real PostgreSQL container. Skip only when Docker is unavailable.

    Any other failure to start the container raises, so the test fails with the error.
    """
    docker = docker_bin()
    if not docker:
        pytest.skip("Docker is not available: the docker CLI is not on PATH")
    probe = run_docker(docker, ["info"], timeout=DOCKER_TIMEOUT_SECONDS)
    if probe.returncode != 0:
        pytest.skip(
            f"Docker is not available: the daemon is not reachable ({probe.stderr.strip()})"
        )

    port = free_port()
    container_name = f"runefoble-pg-test-{port}"

    init_script = (
        "#!/bin/sh\n"
        "set -e\n"
        "set -u\n"
        "create_database() {\n"
        "    local database=$1\n"
        '    echo "Provisioning database $database for user $POSTGRES_USER..."\n'
        '    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL\n'
        "        SELECT 'CREATE DATABASE ' || quote_ident('$database') || ' OWNER ' || quote_ident('$POSTGRES_USER')\n"
        "        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\\gexec\n"
        '        GRANT ALL PRIVILEGES ON DATABASE "$database" TO "$POSTGRES_USER";\n'
        "EOSQL\n"
        '    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" <<-EOSQL\n'
        '        GRANT ALL ON SCHEMA public TO "$POSTGRES_USER";\n'
        "EOSQL\n"
        "}\n"
        'DATABASES="${POSTGRES_MULTIPLE_DATABASES:-zitadel,spicedb,openpanel}"\n'
        "for db in $(echo \"$DATABASES\" | tr ',' ' '); do\n"
        '    create_database "$db"\n'
        "done\n"
    )

    script_path = ""
    try:
        descriptor, script_path = tempfile.mkstemp(suffix=".sh")
        with os.fdopen(descriptor, "w", encoding="utf-8") as script_file:
            script_file.write(init_script)
        os.chmod(script_path, 0o755)
        yield from _run_postgres_container(docker, container_name, port, script_path)
    finally:
        if script_path:
            os.unlink(script_path)


def _run_postgres_container(
    docker_bin: str, container_name: str, port: int, script_path: str
) -> Generator[dict[str, str | int]]:
    args = [
        "run",
        "--rm",
        "--name",
        container_name,
        *owner_label_args(),
        "-d",
        "--tmpfs",
        "/var/lib/postgresql/data",
        "-p",
        f"{port}:5432",
        "-v",
        f"{script_path}:/docker-entrypoint-initdb.d/init-multidb.sh:ro",
        "-e",
        "POSTGRES_USER=runefoble_user",
        "-e",
        "POSTGRES_PASSWORD=runefoble_dev_password",
        "-e",
        "POSTGRES_DB=runefoble",
        "-e",
        "POSTGRES_MULTIPLE_DATABASES=zitadel,spicedb,openpanel",
        "pgvector/pgvector:pg16",
    ]

    started = run_docker(docker_bin, args, timeout=DOCKER_TIMEOUT_SECONDS)
    if started.returncode != 0:
        raise RuntimeError(f"docker run failed for {container_name}: {started.stderr.strip()}")

    try:
        if not _wait_until_ready(docker_bin, container_name):
            raise RuntimeError(f"PostgreSQL in {container_name} did not become ready in 30 seconds")
        yield {
            "host": "127.0.0.1",
            "port": port,
            "user": "runefoble_user",
            "password": "runefoble_dev_password",
            "database": "runefoble",
            "container_name": container_name,
            "dsn": f"postgresql://runefoble_user:runefoble_dev_password@127.0.0.1:{port}/runefoble",
            "async_dsn": f"postgresql+asyncpg://runefoble_user:runefoble_dev_password@127.0.0.1:{port}/runefoble",
        }
    finally:
        remove_test_container(docker_bin, container_name)


def _wait_until_ready(docker: str, container_name: str, timeout: float = 30.0) -> bool:
    """Return True when the init script finished and the final server answers a query."""
    return wait_until(
        lambda: _postgres_is_ready(docker, container_name),
        timeout_s=timeout,
        interval_s=0.5,
    )


def _postgres_is_ready(docker: str, container_name: str) -> bool:
    logs_res = run_docker(docker, ["logs", container_name], timeout=DOCKER_TIMEOUT_SECONDS)
    logs = logs_res.stdout + logs_res.stderr
    init_complete = (
        "PostgreSQL init process complete; ready for start up." in logs
        and logs.count("database system is ready to accept connections") >= 2
    )
    if not init_complete:
        return False
    test_res = run_docker(
        docker,
        [
            "exec",
            container_name,
            "psql",
            "-U",
            "runefoble_user",
            "-d",
            "runefoble",
            "-tAc",
            "SELECT 1;",
        ],
        timeout=DOCKER_TIMEOUT_SECONDS,
    )
    return test_res.returncode == 0 and test_res.stdout.strip() == "1"
