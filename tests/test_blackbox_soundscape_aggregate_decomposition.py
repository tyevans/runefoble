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

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.main import app

from tests.helpers.ws_identity import bearer


@pytest.fixture
def tomb_session_id(trusted_ws_issuer, game_session_upstream) -> str:
    """Create a campaign and a session through the gateway frontdoor. The default test subject owns both."""
    with TestClient(gateway_app) as gateway:
        campaign = gateway.post(
            "/api/v1/campaigns",
            json={"title": "Tomb of Echoes", "setting": "Underdark"},
            headers=bearer("soundscape-tester"),
        )
        assert campaign.status_code == 201, campaign.text
        session = gateway.post(
            f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
            json={"title": "Echoing Depths"},
            headers=bearer("soundscape-tester"),
        )
        assert session.status_code == 201, session.text
        return session.json()["id"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=bearer("soundscape-tester"))


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

    # Read the stored tension back through the public GET route
    stored_resp = client.get("/api/v1/soundscape/tension", params={"session_id": session_id})
    assert stored_resp.status_code == 200
    assert stored_resp.json()["tension_score"] == tension_data["tension_score"]

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
