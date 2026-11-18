"""Blackbox TDD suite for event store fail-fast start-up, health reporting, and Helm wiring.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: Core Event Sourcing with eventsource-py
- Hard Invariant 2: All domain state persisted through AggregateRepository
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Verifies:
1. A deployed service (production) with no store setting and an unreachable
   database exits non-zero at start-up. It does not fall back to memory.
2. A deployed service refuses the memory backend.
3. The default backend is PostgreSQL. Memory is never selected silently.
4. /healthz reports the store kind in use under the test backend (memory).
5. Helm renders the PostgreSQL event store backend and database URL for every
   service that owns AggregateRepository state.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from board_state.main import app as board_state_app
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.adapters.postgresql.store import PostgreSQLEventStore
from fastapi.testclient import TestClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    EventStoreInitializationError,
    build_event_store,
    event_store_kind,
    set_event_store,
)

from tests.helpers.postgres import get_free_port
from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = REPO_ROOT / "deployments" / "helm" / "runefoble"

AGGREGATE_OWNING_DEPLOYMENTS = [
    "asset-forge",
    "board-state",
    "campaign-lore",
    "character-sheet",
    "game-session",
    "rules-compendium",
    "soundscape",
    "the-watcher",
    "voice-agent",
]


@pytest.fixture(autouse=True)
def reset_event_store_singleton():
    """Reset global event store singleton between tests."""
    set_event_store(None)
    yield
    set_event_store(None)


def _clean_env() -> dict[str, str]:
    """Return the process environment without any RUNEFOBLE_ settings."""
    return {k: v for k, v in os.environ.items() if not k.startswith("RUNEFOBLE_")}


def _offline_dsn() -> str:
    offline_port = get_free_port()
    return f"postgresql+asyncpg://runefoble_user:secret@127.0.0.1:{offline_port}/runefoble"


def _import_board_state(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = _clean_env()
    env.setdefault("RUNEFOBLE_SPICEDB_PRESHARED_KEY", "test-preshared-key")
    # The service credential check runs first. Set it so the store check decides the outcome.
    env.setdefault("RUNEFOBLE_SERVICE_CREDENTIAL", "test-service-credential")
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", "import board_state.main"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
        check=False,
    )


def test_deployed_service_without_store_setting_refuses_to_start():
    """A production process with no store setting and an offline database must fail."""
    result = _import_board_state(
        {"RUNEFOBLE_ENVIRONMENT": "production", "RUNEFOBLE_DATABASE_URL": _offline_dsn()}
    )

    assert result.returncode != 0
    assert "EventStoreInitializationError" in result.stderr


def test_postgres_event_store_backend_refuses_to_start_when_unreachable():
    """Importing a service with the PostgreSQL backend and an offline database must fail."""
    result = _import_board_state(
        {"RUNEFOBLE_EVENT_STORE_BACKEND": "postgresql", "RUNEFOBLE_DATABASE_URL": _offline_dsn()}
    )

    assert result.returncode != 0
    assert "EventStoreInitializationError" in result.stderr


def test_healthz_reports_memory_store_under_test_settings():
    """Tests select the memory backend at the root, and /healthz reports 'memory'."""
    client = TestClient(board_state_app, headers=bearer("user-test"))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["event_store"] == "memory"


def test_event_store_kind_reports_memory_for_explicit_memory_backend():
    """An explicit memory backend yields the in-memory store in development."""
    store = build_event_store(PlatformSettings(event_store_backend="memory"))

    assert isinstance(store, InMemoryEventStore)
    assert event_store_kind(store) == "memory"


def test_deployed_environment_refuses_memory_backend():
    """A deployed environment raises when the memory backend is selected."""
    settings = PlatformSettings(environment="production", event_store_backend="memory")

    with pytest.raises(EventStoreInitializationError):
        build_event_store(settings)


def test_unset_backend_defaults_to_postgresql_and_never_falls_back_to_memory(monkeypatch):
    """With no backend set, an unreachable database raises instead of using memory."""
    monkeypatch.delenv("RUNEFOBLE_EVENT_STORE_BACKEND", raising=False)
    settings = PlatformSettings(database_url=_offline_dsn())

    assert settings.event_store_backend == "postgresql"
    with pytest.raises(EventStoreInitializationError):
        build_event_store(settings)


def test_offline_postgres_raises_instead_of_falling_back():
    """With the PostgreSQL backend, an unreachable database raises and returns no store."""
    settings = PlatformSettings(
        database_url=_offline_dsn(),
        event_store_backend="postgresql",
    )

    with pytest.raises(EventStoreInitializationError):
        build_event_store(settings)


def test_deployed_service_with_reachable_postgres_starts_on_postgresql(postgres_service):
    """A production service with a reachable database gets the PostgreSQL store."""

    settings = PlatformSettings(
        environment="production",
        database_url=str(postgres_service["dsn"]),
        event_store_backend="postgresql",
    )

    store = build_event_store(settings)

    assert isinstance(store, PostgreSQLEventStore)
    assert event_store_kind(store) == "postgresql"


def _render_chart() -> list[dict]:
    if shutil.which("helm") is None:
        pytest.skip("helm not available")
    result = subprocess.run(
        ["helm", "template", "runefoble", str(CHART_DIR)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _deployment_env(doc: dict) -> dict[str, str]:
    container = doc["spec"]["template"]["spec"]["containers"][0]
    return {e["name"]: e.get("value") for e in container.get("env", [])}


@pytest.mark.parametrize("deployment", AGGREGATE_OWNING_DEPLOYMENTS)
def test_helm_enables_postgres_event_store_for_aggregate_owners(deployment):
    """Every aggregate-owning deployment renders the flag and a database URL."""
    docs = _render_chart()
    matches = [
        d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == deployment
    ]

    assert len(matches) == 1, f"deployment {deployment} not rendered exactly once"
    env = _deployment_env(matches[0])
    assert env.get("RUNEFOBLE_EVENT_STORE_BACKEND") == "postgresql"
    assert env.get("RUNEFOBLE_DATABASE_URL", "").startswith("postgresql+asyncpg://")
