"""Blackbox TDD test suite for Soundscape Aggregate Handlers Modular Decomposition (TASK-0230).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: PostgreSQL Event Store via eventsource-py
- ADR-0013: Modular Decomposition
- Hard Invariant 6: File length limit (< 80 lines for aggregate.py, < 150 lines for handlers)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.application.aggregates.repository import AggregateRepository
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.aggregate import (
    SoundscapeAggregate,
)
from soundscape.main import app

from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def tomb_session_id(trusted_ws_issuer, game_session_upstream) -> str:
    """Create a campaign and a session through the gateway frontdoor. The default test subject owns both."""
    with TestClient(gateway_app) as gateway:
        campaign = gateway.post(
            "/api/v1/campaigns",
            json={"title": "Tomb of Echoes", "setting": "Underdark"},
            headers=auth_headers("soundscape-tester"),
        )
        assert campaign.status_code == 201, campaign.text
        session = gateway.post(
            f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
            json={"title": "Echoing Depths"},
            headers=auth_headers("soundscape-tester"),
        )
        assert session.status_code == 201, session.text
        return session.json()["id"]


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=auth_headers("soundscape-tester"))


@pytest.mark.asyncio
async def test_full_aggregate_domain_lifecycle_and_reconstitution():
    """Verify full domain event sourcing across mixins and event replay via AggregateRepository."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=SoundscapeAggregate)

    agg_id = uuid4()
    session_id = f"session-modular-{agg_id.hex[:8]}"

    # 1. Instantiate and apply domain commands across all mixins
    agg = SoundscapeAggregate(agg_id)

    # Stems mixin
    agg.record_track_change(
        session_id=session_id,
        track_id="track-dungeon-01",
        stem_profile="exploration",
        tension_score=20,
        crossfade_duration_ms=2000,
        active_stems=["ambient"],
    )
    assert agg.state.current_track_id == "track-dungeon-01"
    assert agg.state.stem_profile == "exploration"

    # Tension mixin
    agg.record_tension_update(
        session_id=session_id,
        tension_score=65,
        stem_profile="combat",
        combat_round=2,
        enemy_cr_balance=2.5,
        lowest_health_ratio=0.5,
    )
    assert agg.state.tension_score == 65
    assert agg.state.stem_profile == "combat"

    # Tension mixin mood override
    agg.record_stem_profile_overridden(session_id=session_id, mood="boss")
    assert agg.state.manual_override is True
    assert agg.state.stem_profile == "boss"

    # Foley mixin
    agg.record_cue(
        session_id=session_id,
        cue_id="cue-sword-clash",
        sound_url="https://s3.local/foley/sword.wav",
        volume_gain=0.9,
        duck_music=True,
    )
    assert len(agg.state.cues_history) == 1
    assert agg.state.cues_history[0]["cue_id"] == "cue-sword-clash"

    agg.record_ducking_engaged(session_id=session_id, reason="speech", duration_ms=0)
    assert agg.state.is_ducked is True
    assert agg.state.ducking_attenuation_db == -12.0
    agg.record_ducking_released(session_id=session_id)
    assert agg.state.is_ducked is False
    agg.record_ducking_engaged(session_id=session_id, reason="speech", duration_ms=0)
    agg.record_channel_volumes(session_id=session_id, channel_volumes={"melody": 0.3})
    agg.record_master_volume(session_id=session_id, master_volume=0.5)
    assert agg.state.channel_volumes["melody"] == 0.3
    assert agg.state.master_volume == 0.5

    # Leitmotif mixin
    agg.record_leitmotif_profile(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        instrument_timbre="brass",
        tempo_multiplier=1.1,
    )
    assert "char-valeros" in agg.state.character_profiles

    agg.record_leitmotif_trigger(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        motif_type="triumphant",
        instrument_timbre="brass",
    )
    assert agg.state.active_leitmotif is not None
    assert agg.state.active_leitmotif["character_id"] == "char-valeros"
    assert len(agg.state.leitmotif_history) == 1

    # Save uncommitted events into event store
    await repo.save(agg)

    # 2. Reconstitute aggregate from event store
    reconstituted = await repo.load(agg_id)
    assert reconstituted is not None
    assert reconstituted.state.current_track_id == "track-dungeon-01"
    assert reconstituted.state.tension_score == 65
    assert reconstituted.state.manual_override is True
    assert reconstituted.state.stem_profile == "boss"
    assert reconstituted.state.is_ducked is True
    assert len(reconstituted.state.cues_history) == 1
    assert "char-valeros" in reconstituted.state.character_profiles
    assert reconstituted.state.active_leitmotif["character_id"] == "char-valeros"


def test_frontdoor_http_endpoints_with_decomposed_aggregate(
    client: TestClient, tomb_session_id: str
):
    """Verify public HTTP frontdoors interact seamlessly with the decomposed aggregate."""
    session_id = tomb_session_id

    # 1. POST /api/v1/soundscape/stems/override
    override_resp = client.post(
        "/api/v1/soundscape/stems/override",
        json={
            "session_id": session_id,
            "mood": "combat",
        },
    )
    assert override_resp.status_code == 200
    data = override_resp.json()
    assert data["session_id"] == session_id
    assert data["stem_profile"] == "combat"
    assert data["manual_override"] is True

    # 2. POST /api/v1/soundscape/tension/calculate
    tension_resp = client.post(
        "/api/v1/soundscape/tension/calculate",
        json={
            "session_id": session_id,
            "combat_active": True,
            "combat_round": 1,
            "enemy_cr_balance": 1.0,
            "lowest_party_health_ratio": 0.8,
        },
    )
    assert tension_resp.status_code == 200
    tension_data = tension_resp.json()
    assert tension_data["session_id"] == session_id
    assert "tension_score" in tension_data

    # 3. POST /api/v1/soundscape/cue
    cue_resp = client.post(
        "/api/v1/soundscape/cue",
        json={
            "session_id": session_id,
            "cue_id": "cue-door-creak",
            "cue_type": "foley",
            "sound_url": "https://s3.local/foley/door.wav",
            "volume_gain": 0.8,
            "duck_music": False,
        },
    )
    assert cue_resp.status_code == 200
    cue_data = cue_resp.json()
    assert "cue_id" in cue_data
    assert cue_data["status"] == "triggered"

    # 4. POST /api/v1/soundscape/duck
    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={
            "session_id": session_id,
            "is_ducked": True,
            "reason": "speech",
        },
    )
    assert duck_resp.status_code == 200
    assert duck_resp.json()["is_ducked"] is True

    # 5. POST /api/v1/soundscape/leitmotif/profile
    motif_profile_resp = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": session_id,
            "character_id": "player-1",
            "character_name": "Lyra",
            "instrument_timbre": "lute",
            "tempo_multiplier": 1.0,
            "volume_gain": 1.0,
        },
    )
    assert motif_profile_resp.status_code == 200
    motif_data = motif_profile_resp.json()
    assert motif_data["character_id"] == "player-1"


def test_legacy_override_alias_is_not_routed(client: TestClient, tomb_session_id: str):
    """The alias POST /api/v1/soundscape/override is removed. Only /stems/override remains (DoR 9)."""
    alias_resp = client.post(
        "/api/v1/soundscape/override",
        json={"session_id": tomb_session_id, "mood": "combat"},
    )
    assert alias_resp.status_code == 404

    canonical_resp = client.post(
        "/api/v1/soundscape/stems/override",
        json={"session_id": tomb_session_id, "mood": "combat"},
    )
    assert canonical_resp.status_code == 200
    assert canonical_resp.json()["stem_profile"] == "combat"
