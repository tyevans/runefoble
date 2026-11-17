"""Blackbox TDD suite for event store fail-fast start-up, health reporting, and Helm wiring.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: Core Event Sourcing with eventsource-py
- Hard Invariant 2: All domain state persisted through AggregateRepository
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Verifies:
1. A service process with the PostgreSQL event store enabled and an unreachable
   database exits non-zero at start-up. It does not fall back to memory.
2. /healthz reports the store kind in use ("memory" when the flag is unset).
3. Helm renders the PostgreSQL event store flag and database URL for every
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
from fastapi.testclient import TestClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    EventStoreInitializationError,
    event_store_kind,
    get_event_store,
    set_event_store,
)

from tests.helpers.postgres import get_free_port

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


def test_service_process_exits_when_postgres_event_store_is_unreachable():
    """Importing a service with the PostgreSQL flag and an offline database must fail."""
    offline_port = get_free_port()
    env = _clean_env()
    env["RUNEFOBLE_USE_POSTGRES_EVENT_STORE"] = "true"
    env.setdefault("RUNEFOBLE_SPICEDB_PRESHARED_KEY", "test-preshared-key")
    env["RUNEFOBLE_DATABASE_URL"] = (
        f"postgresql+asyncpg://runefoble_user:secret@127.0.0.1:{offline_port}/runefoble"
    )

    result = subprocess.run(
        [sys.executable, "-c", "import board_state.main"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
        check=False,
    )

    assert result.returncode != 0
    assert "EventStoreInitializationError" in result.stderr


def test_healthz_reports_memory_store_when_flag_is_unset():
    """/healthz reports the store kind in use, not the Python class name."""
    client = TestClient(board_state_app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["event_store"] == "memory"


def test_event_store_kind_reports_memory_for_in_memory_store():
    """event_store_kind returns 'memory' for the default in-memory store."""
    store = get_event_store(settings=PlatformSettings(use_postgres_event_store=False))

    assert event_store_kind(store) == "memory"


def test_offline_postgres_raises_instead_of_falling_back():
    """With the flag enabled, an unreachable database raises and returns no in-memory store."""
    offline_port = get_free_port()
    settings = PlatformSettings(
        database_url=f"postgresql://runefoble_user:secret@127.0.0.1:{offline_port}/runefoble",
        use_postgres_event_store=True,
    )

    with pytest.raises(EventStoreInitializationError):
        get_event_store(settings=settings, force_new=True)


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
    assert env.get("RUNEFOBLE_USE_POSTGRES_EVENT_STORE") == "true"
    assert env.get("RUNEFOBLE_DATABASE_URL", "").startswith("postgresql+asyncpg://")
