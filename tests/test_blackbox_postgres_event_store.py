"""Blackbox TDD frontdoor test suite for PostgreSQL event store and multi-database provisioning.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind (postgres.yaml)
- ADR-0011: Core Event Sourcing with eventsource-py (PostgreSQLEventStore)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Verifies:
1. Multi-database initialization script provisions zitadel, spicedb, and openpanel.
2. DSN reconciliation and asyncpg dialect normalization.
3. Graceful in-memory fallback when database host is offline.
4. Auto-creation of events schema upon first access.
5. End-to-end aggregate roundtrips (GameSessionAggregate, CharacterAggregate, BoardAggregate)
   persisted durably to PostgreSQL and replayed accurately.
6. Optimistic concurrency control across concurrent writers.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from collections.abc import Generator
from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from character_sheet.aggregate import CharacterAggregate
from eventsource import OptimisticLockError, StreamId
from game_session.aggregate import GameSessionAggregate
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    InMemoryEventStore,
    PostgreSQLEventStore,
    create_aggregate_repository,
    get_event_store,
    is_database_reachable,
    normalize_async_postgres_url,
    set_event_store,
)


def _get_free_port() -> int:
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

    port = _get_free_port()
    container_name = f"runefoble-pg-test-{port}"

    import tempfile

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


@pytest.fixture(autouse=True)
def reset_event_store_singleton():
    """Reset global event store singleton between tests."""
    set_event_store(None)
    yield
    set_event_store(None)


def test_dsn_normalization_and_platform_settings():
    """Verify DSN dialect normalization and PlatformSettings fields."""
    # Standard postgres:// to postgresql+asyncpg://
    assert (
        normalize_async_postgres_url("postgres://user:pass@localhost:5432/db")
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    # Standard postgresql:// to postgresql+asyncpg://
    assert (
        normalize_async_postgres_url("postgresql://user:pass@localhost:5432/db")
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    # Already asyncpg URL
    assert (
        normalize_async_postgres_url("postgresql+asyncpg://user:pass@localhost:5432/db")
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )

    # Reachability checks
    assert is_database_reachable(None, None) is True
    assert is_database_reachable("127.0.0.1", _get_free_port(), timeout=0.1) is False

    settings = PlatformSettings(
        database_url="postgresql://db_user:db_pass@db_host:5432/test_db",
        use_postgres_event_store=True,
        postgres_pool_size=8,
        postgres_max_overflow=15,
        event_store_table_name="runefoble_events",
    )
    assert settings.database_url == "postgresql://db_user:db_pass@db_host:5432/test_db"
    assert settings.postgres_dsn == settings.database_url
    assert settings.use_postgres_event_store is True
    assert settings.postgres_pool_size == 8
    assert settings.postgres_max_overflow == 15
    assert settings.event_store_table_name == "runefoble_events"


@pytest.mark.asyncio
async def test_offline_database_graceful_in_memory_fallback():
    """When PostgreSQL is activated but database host is offline, fall back to InMemoryEventStore."""
    offline_port = _get_free_port()
    settings = PlatformSettings(
        database_url=f"postgresql://runefoble_user:secret@127.0.0.1:{offline_port}/runefoble",
        use_postgres_event_store=True,
    )

    # get_event_store must catch the connection failure and return an InMemoryEventStore
    store = get_event_store(settings=settings, force_new=True)
    assert isinstance(store, InMemoryEventStore)

    # Using this store via AggregateRepository functions normally in memory
    repo = create_aggregate_repository(GameSessionAggregate, event_store=store)
    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=uuid4(), title="Fallback Adventure", dm_id="dm_test")
    assert session.state.status == "lobby"

    await repo.save(session)
    reloaded = await repo.load(session_id)
    assert reloaded.state.title == "Fallback Adventure"


def test_multidb_init_script_provisions_all_databases(postgres_service):
    """Verify that init-multidb creates zitadel, spicedb, and openpanel databases."""
    if not postgres_service:
        pytest.skip("Docker not available for multi-database test")

    container_name = postgres_service["container_name"]
    res = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            str(container_name),
            "psql",
            "-U",
            "runefoble_user",
            "-d",
            "runefoble",
            "-tAc",
            "SELECT datname FROM pg_database WHERE datname IN ('zitadel', 'spicedb', 'openpanel');",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    created_dbs = {line.strip() for line in res.stdout.strip().split("\n") if line.strip()}
    assert "zitadel" in created_dbs
    assert "spicedb" in created_dbs
    assert "openpanel" in created_dbs


@pytest.mark.asyncio
async def test_postgres_event_store_durable_aggregate_roundtrip(postgres_service):
    """Verify end-to-end durable event sourcing and reconstitution against PostgreSQL."""
    if not postgres_service:
        pytest.skip("Docker not available for PostgreSQL event store test")

    settings = PlatformSettings(
        database_url=str(postgres_service["dsn"]),
        use_postgres_event_store=True,
    )

    store = get_event_store(settings=settings, force_new=True)
    assert isinstance(store, PostgreSQLEventStore)

    # 1. GameSessionAggregate Lifecycle
    session_repo = create_aggregate_repository(GameSessionAggregate, event_store=store)
    session_id = uuid4()
    campaign_id = uuid4()
    char_id = uuid4()

    session = GameSessionAggregate(session_id)
    session.create(campaign_id=campaign_id, title="Vault of the Duergar", dm_id="the_watcher")
    session.join_player("player-valeros", char_id, "Valeros", "Fighter")
    session.start()
    session.advance_turn(active_character_id=char_id)
    session.advance_turn(active_character_id=char_id)
    session.leave_player("player-valeros", reason="Connection dropped")

    await session_repo.save(session)

    # 2. CharacterAggregate Lifecycle
    char_repo = create_aggregate_repository(CharacterAggregate, event_store=store)
    char = CharacterAggregate(char_id)
    char.create(name="Valeros", character_class="Fighter", max_hp=40)
    char.modify_health(-15, source="Crossbow trap")
    char.apply_penalty("drunk", "Celebrated before the dungeon", imposed_by="human_dm")
    char.apply_penalty("foolishness", "Charges heedlessly", imposed_by="the_watcher")

    await char_repo.save(char)

    # 3. BoardAggregate Lifecycle
    board_repo = create_aggregate_repository(BoardAggregate, event_store=store)
    board_id = uuid4()
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=12, rows=12, session_id=str(session_id))
    board.place_token("tok-valeros", name="Valeros", token_type="pc", x=3, y=3, is_friendly=True)
    board.place_token("tok-goblin", name="Goblin Archer", token_type="monster", x=7, y=8)
    board.move_token("tok-valeros", to_x=4, to_y=4)

    await board_repo.save(board)

    # 4. Verify durable reconstitution from a fresh repository instance
    fresh_session_repo = create_aggregate_repository(GameSessionAggregate, event_store=store)
    reloaded_session = await fresh_session_repo.load(session_id)
    assert reloaded_session.version == session.version
    assert reloaded_session.state.status == "active"
    assert reloaded_session.state.current_turn == 3
    assert "player-valeros" in reloaded_session.state.participants
    assert reloaded_session.state.participants["player-valeros"].is_stand_in_active is True

    fresh_char_repo = create_aggregate_repository(CharacterAggregate, event_store=store)
    reloaded_char = await fresh_char_repo.load(char_id)
    assert reloaded_char.version == char.version
    assert reloaded_char.state.current_hp == 25
    assert "drunk" in reloaded_char.state.penalties
    assert "foolishness" in reloaded_char.state.penalties

    fresh_board_repo = create_aggregate_repository(BoardAggregate, event_store=store)
    reloaded_board = await fresh_board_repo.load(board_id)
    assert reloaded_board.version == board.version
    assert reloaded_board.state.tokens["tok-valeros"].x == 4
    assert reloaded_board.state.tokens["tok-valeros"].y == 4
    assert "tok-goblin" in reloaded_board.state.tokens

    # 5. Clean up store engine
    await store.close()


@pytest.mark.asyncio
async def test_postgres_event_store_optimistic_concurrency(postgres_service):
    """Verify optimistic concurrency conflict detection in PostgreSQL event store."""
    if not postgres_service:
        pytest.skip("Docker not available for concurrency test")

    settings = PlatformSettings(
        database_url=str(postgres_service["dsn"]),
        use_postgres_event_store=True,
    )
    store = get_event_store(settings=settings, force_new=True)
    repo = create_aggregate_repository(CharacterAggregate, event_store=store)

    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Seoni", character_class="Sorcerer", max_hp=28)
    await repo.save(char)

    # Concurrent readers load same aggregate state
    replica_a = await repo.load(char_id)
    replica_b = await repo.load(char_id)

    # Writer A mutates and saves first
    replica_a.modify_health(-5, source="Magic Missile")
    await repo.save(replica_a)

    # Writer B attempts to commit on stale version
    replica_b.modify_health(-10, source="Fireball")
    with pytest.raises(OptimisticLockError):
        await repo.save(replica_b)

    await store.close()


@pytest.mark.asyncio
async def test_postgres_raw_event_stream_verification(postgres_service):
    """Verify raw stream event envelop reading directly through PostgreSQL store."""
    if not postgres_service:
        pytest.skip("Docker not available for stream verification test")

    settings = PlatformSettings(
        database_url=str(postgres_service["dsn"]),
        use_postgres_event_store=True,
    )
    store = get_event_store(settings=settings, force_new=True)
    repo = create_aggregate_repository(GameSessionAggregate, event_store=store)

    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=uuid4(), title="Stream Inspection", dm_id="the_watcher")
    session.start()
    await repo.save(session)

    stream_id = StreamId(aggregate_id=session_id, category="GameSession")
    assert await store.get_stream_version(stream_id) == 2

    envelopes = [env async for env in store.read_stream(stream_id)]
    assert len(envelopes) == 2
    assert envelopes[0].event.__class__.__name__ == "SessionCreated"
    assert envelopes[1].event.__class__.__name__ == "SessionStarted"

    assert await store.event_exists(envelopes[0].event.event_id)

    await store.close()
