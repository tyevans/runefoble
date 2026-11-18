"""Blackbox tests: Soundscape mixer, ducking, and aggregate identity live in the event store.

Governed by:
- ADR-0011: Core Event Sourcing with eventsource-py (the event store is the source of truth)
- ADR-0015 (f): the PostgreSQL event store is the deployed store
- Hard Invariant 2: state changes flow through aggregates and events
- Hard Invariant 7: Blackbox TDD with frontdoor setup

Writes go through public HTTP routes. A restart is a separate Python process that reads the
same PostgreSQL event store through the public tension route. A process-local dictionary
cannot survive that restart, so these tests fail when mixer state lives in process memory.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import build_event_store, set_event_store
from runefoble_platform.redis_bus import deserialize_event
from soundscape.main import app

from tests.helpers.process import run_command
from tests.helpers.ws_identity import SIGNING_ISSUER as ISSUER

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILD_SCRIPT = REPO_ROOT / "tests" / "helpers" / "soundscape_restart_child.py"
DM = "soundscape-restart-dm"


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {ISSUER.mint(sub)}"}


def _use_postgres_event_store(dsn: str):
    settings = PlatformSettings(database_url=dsn, event_store_backend="postgresql")
    store = build_event_store(settings)
    set_event_store(store)
    return store


async def _seed_dm(session_id: str, campaign_id: str) -> None:
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", DM)
    await spicedb.write_relationship("session", session_id, "campaign", "campaign", campaign_id)


def _restart_read(dsn: str, session_id: str, *, with_aggregate_id: bool = False) -> dict:
    """Start the service in a new process on the same event store and read the tension route."""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    args = [sys.executable, str(CHILD_SCRIPT), dsn, session_id]
    if with_aggregate_id:
        args.append("aggregate")
    completed = run_command(args, cwd=REPO_ROOT, env=env, timeout=120, check=False)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.fixture(autouse=True)
def reset_event_store_singleton():
    set_event_store(None)
    yield
    set_event_store(None)


@pytest.mark.asyncio
async def test_master_volume_survives_process_restart(postgres_service):
    """A master volume set through the override route is served after a restart."""
    dsn = str(postgres_service["dsn"])
    session_id = f"session-{uuid4().hex[:8]}"
    campaign_id = str(uuid4())
    await _seed_dm(session_id, campaign_id)

    store = _use_postgres_event_store(dsn)
    with TestClient(app, headers=_bearer(DM)) as client:
        response = client.post(
            "/api/v1/soundscape/stems/override",
            json={
                "session_id": session_id,
                "mood": "combat",
                "master_volume": 0.55,
                "campaign_id": campaign_id,
            },
        )
        assert response.status_code == 200, response.text
    await store.close()

    restarted = _restart_read(dsn, session_id)
    assert restarted["status"] == 200, restarted
    assert restarted["body"]["master_volume"] == pytest.approx(0.55)
    assert restarted["body"]["stem_profile"] == "combat"


@pytest.mark.asyncio
async def test_speech_ducking_releases_after_its_stored_duration(postgres_service):
    """A ducking engagement ends when its stored duration elapses. The tension route agrees."""
    dsn = str(postgres_service["dsn"])
    session_id = f"session-{uuid4().hex[:8]}"
    campaign_id = str(uuid4())
    await _seed_dm(session_id, campaign_id)

    store = _use_postgres_event_store(dsn)
    with TestClient(app, headers=_bearer(DM)) as client:
        engaged = client.post(
            "/api/v1/soundscape/duck",
            json={
                "session_id": session_id,
                "is_ducked": True,
                "reason": "speech",
                "duration_ms": 200,
            },
        )
        assert engaged.status_code == 200, engaged.text
        during = client.get("/api/v1/soundscape/tension", params={"session_id": session_id})
        assert during.json()["is_ducked"] is True

        time.sleep(0.4)
        after = client.get("/api/v1/soundscape/tension", params={"session_id": session_id})
        assert after.status_code == 200, after.text
        assert after.json()["is_ducked"] is False
        assert after.json()["effective_gain"] == pytest.approx(1.0)
    await store.close()


@pytest.mark.asyncio
async def test_explicit_duck_release_clears_ducking_before_its_duration(postgres_service):
    """An explicit release ends an engagement that has no duration (hold until released)."""
    dsn = str(postgres_service["dsn"])
    session_id = f"session-{uuid4().hex[:8]}"
    campaign_id = str(uuid4())
    await _seed_dm(session_id, campaign_id)

    store = _use_postgres_event_store(dsn)
    with TestClient(app, headers=_bearer(DM)) as client:
        client.post(
            "/api/v1/soundscape/duck",
            json={"session_id": session_id, "is_ducked": True, "reason": "cue"},
        )
        released = client.post(
            "/api/v1/soundscape/duck",
            json={"session_id": session_id, "is_ducked": False, "reason": "cue"},
        )
        assert released.status_code == 200, released.text
        body = client.get("/api/v1/soundscape/tension", params={"session_id": session_id}).json()
        assert body["is_ducked"] is False
    await store.close()


@pytest.mark.asyncio
async def test_aggregate_id_is_stable_across_process_starts(postgres_service, mock_bus):
    """The soundscape aggregate id for a session is the same in two processes."""
    dsn = str(postgres_service["dsn"])
    session_id = f"session-{uuid4().hex[:8]}"
    campaign_id = str(uuid4())
    await _seed_dm(session_id, campaign_id)

    store = _use_postgres_event_store(dsn)
    with TestClient(app, headers=_bearer(DM)) as client:
        cue = client.post(
            "/api/v1/soundscape/cue",
            json={
                "session_id": session_id,
                "cue_name": "door_slam",
                "campaign_id": campaign_id,
            },
        )
        assert cue.status_code == 200, cue.text
    await store.close()

    emitted = [
        str(ev.aggregate_id)
        for _, fields in mock_bus.streams.get("runefoble.events.soundscape", [])
        if getattr(ev := deserialize_event(fields), "session_id", None) == session_id
    ]
    assert emitted, "the cue route must emit a soundscape event on the bus"
    first_process_id = emitted[0]
    second = _restart_read(dsn, session_id, with_aggregate_id=True)
    assert second["aggregate_id"] == first_process_id
