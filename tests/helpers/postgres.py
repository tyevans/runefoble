"""Shared PostgreSQL test container fixtures and network helpers.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: Core Event Sourcing with eventsource-py
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Generator

import pytest


def get_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def postgres_service() -> Generator[dict[str, str | int] | None]:
    """Provision a real PostgreSQL container if Docker is available on the host."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        yield None
        return

    port = get_free_port()
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

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as tmp:
        tmp.write(init_script)
        script_path = tmp.name

    subprocess.run(["chmod", "755", script_path], check=True)

    cmd = [
        docker_bin,
        "run",
        "--name",
        container_name,
        "-d",
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
        "postgres:16-alpine",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except Exception:
        yield None
        return

    # Wait for postgres entrypoint initialization to complete and final server to accept connections
    deadline = time.time() + 30
    ready = False
    while time.time() < deadline:
        time.sleep(0.5)
        # Check container logs to verify initialization script finished and permanent server started
        logs_res = subprocess.run(
            [docker_bin, "logs", container_name],
            capture_output=True,
            text=True,
        )
        logs = logs_res.stdout + logs_res.stderr
        init_complete = (
            "PostgreSQL init process complete; ready for start up." in logs
            and logs.count("database system is ready to accept connections") >= 2
        )
        if init_complete:
            # Verify psql query execution succeeds on the final server
            test_res = subprocess.run(
                [
                    docker_bin,
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
                capture_output=True,
                text=True,
            )
            if test_res.returncode == 0 and test_res.stdout.strip() == "1":
                ready = True
                break

    if not ready:
        subprocess.run([docker_bin, "rm", "-f", container_name], capture_output=True)
        yield None
        return

    info = {
        "host": "127.0.0.1",
        "port": port,
        "user": "runefoble_user",
        "password": "runefoble_dev_password",
        "database": "runefoble",
        "container_name": container_name,
        "dsn": f"postgresql://runefoble_user:runefoble_dev_password@127.0.0.1:{port}/runefoble",
        "async_dsn": f"postgresql+asyncpg://runefoble_user:runefoble_dev_password@127.0.0.1:{port}/runefoble",
    }
    try:
        yield info
    finally:
        subprocess.run([docker_bin, "rm", "-f", container_name], capture_output=True)
