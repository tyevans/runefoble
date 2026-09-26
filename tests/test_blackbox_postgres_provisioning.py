"""Blackbox TDD frontdoor test suite for PostgreSQL multi-database provisioning and connection handling.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind (postgres.yaml)
- ADR-0007: Development Tooling and Local Kind Cluster Workflows
- ADR-0011: Core Event Sourcing with eventsource-py
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Verifies:
1. Multi-database initialization script provisions zitadel, spicedb, and openpanel.
2. DSN reconciliation and asyncpg dialect normalization.
3. Database reachability probes and fallback detection.
4. Graceful in-memory fallback when database host is offline.
"""

from __future__ import annotations

import subprocess
from uuid import uuid4

import pytest
from game_session.aggregate import GameSessionAggregate
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    InMemoryEventStore,
    create_aggregate_repository,
    get_event_store,
    is_database_reachable,
    normalize_async_postgres_url,
    set_event_store,
)

from tests.helpers.postgres import get_free_port


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
    assert is_database_reachable("127.0.0.1", get_free_port(), timeout=0.1) is False

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
    offline_port = get_free_port()
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
