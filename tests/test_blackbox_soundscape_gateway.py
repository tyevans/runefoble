"""Blackbox TDD frontdoor test suite for Gateway Soundscape API Routing & Zanzibar Authorization.

Governed by:
- TASK-0436: Gateway Soundscape API Routing & Zanzibar Authorization Proxy
- ADR-0001: Google Zanzibar Fine-Grained Authorization via SpiceDB
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0010: Real-Time Audio Pipeline and Ducking Coordination
- ADR-0013: Frontend Microfrontend Architecture
- Hard Invariant 1: SpiceDB Zanzibar schema authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.leitmotif import CharacterLeitmotifProfile
from soundscape.main import app as soundscape_app

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.ws_identity import SIGNING_ISSUER

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def soundscape_service(monkeypatch) -> Iterator[str]:
    """Run the real soundscape service on a loopback port and point the gateway at it."""
    with serve(soundscape_app) as url:
        monkeypatch.setenv("RUNEFOBLE_SOUNDSCAPE_URL", url)
        yield url


def _auth(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client(trusted_ws_issuer, game_session_upstream) -> Iterator[TestClient]:
    """Run the gateway lifespan after the soundscape URL is set, so the client sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def setup_zanzibar_soundscape(client: TestClient) -> dict[str, str]:
    """Frontdoor setup creating campaign, roles, and session."""
    # 1. Create campaign through public frontdoor with DM Evelyn as owner
    res_camp = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Acoustic Dungeon",
            "setting": "Underdark Caverns",
            "system": "5e",
            "description": "Soundscape testing campaign.",
        },
        headers=_auth("dm_evelyn"),
    )
    assert res_camp.status_code == 201
    cid = res_camp.json()["id"]

    # 2. Assign player role to Valeros through public frontdoor
    res_role = client.post(
        f"/api/v1/campaigns/{cid}/roles",
        json={"user_id": "player_valeros", "role": "player"},
        headers=_auth("dm_evelyn"),
    )
    assert res_role.status_code == 200

    # 3. Create session through public frontdoor
    res_sess = client.post(
        f"/api/v1/campaigns/{cid}/sessions",
        json={"title": "Echoing Depths"},
        headers=_auth("dm_evelyn"),
    )
    assert res_sess.status_code == 201
    sid = res_sess.json()["id"]

    return {"cid": cid, "sid": sid}


# ---------------------------------------------------------------------------
# 1. File Length & Schema DoD Invariants
# ---------------------------------------------------------------------------


def test_openapi_schema_exposure(client: TestClient) -> None:
    """Verify soundscape router endpoints are mounted and exposed in /openapi.json (DoD 2)."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]

    assert "/api/v1/soundscape/cue" in paths
    assert "/api/v1/soundscape/tension" in paths
    assert "/api/v1/soundscape/tension/calculate" in paths
    assert "/api/v1/soundscape/stems/override" in paths
    assert "/api/v1/soundscape/leitmotif/{character_id}" in paths


# ---------------------------------------------------------------------------
# 2. Tactical Foley Cue Triggering & Zanzibar Authorization
# ---------------------------------------------------------------------------


def test_cue_trigger_authorized_player(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify authorized player with 'play' permission can trigger foley cues."""
    sid = setup_zanzibar_soundscape["sid"]
    headers = _auth("player_valeros")

    res = client.post(
        "/api/v1/soundscape/cue",
        headers=headers,
        json={
            "session_id": sid,
            "cue_name": "thunder",
            "cue_type": "foley",
            "volume_gain": 1.0,
            "duck_music": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sid
    assert data["status"] == "triggered"
    assert data["cue_name"] == "thunder"
    assert data["duck_music"] is True
    assert "sound_url" in data


def test_cue_trigger_unauthorized_user(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify unauthorized user lacking 'play' receives 403 Forbidden."""
    sid = setup_zanzibar_soundscape["sid"]
    headers = _auth("stranger_bob")

    res = client.post(
        "/api/v1/soundscape/cue",
        headers=headers,
        json={
            "session_id": sid,
            "cue_name": "thunder",
        },
    )
    assert res.status_code == 403
    assert "insufficient Zanzibar permissions" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Encounter Tension Query & Calculation
# ---------------------------------------------------------------------------


def test_tension_status_query(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify GET /api/v1/soundscape/tension retrieves tension score and stem weights."""
    sid = setup_zanzibar_soundscape["sid"]
    res = client.get(
        f"/api/v1/soundscape/tension?session_id={sid}", headers=_auth("player_valeros")
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sid
    assert "tension_score" in data
    assert "stem_profile" in data
    assert "active_stems" in data
    assert "stem_volumes" in data


def test_tension_calculation(client: TestClient, setup_zanzibar_soundscape: dict[str, str]) -> None:
    """Verify POST /api/v1/soundscape/tension/calculate adapts music stems for session control."""
    sid = setup_zanzibar_soundscape["sid"]
    payload = {
        "session_id": sid,
        "combat_active": True,
        "combat_round": 3,
        "enemy_cr_balance": 3.0,
        "lowest_party_health_ratio": 0.25,
    }
    player = client.post(
        "/api/v1/soundscape/tension/calculate",
        headers=_auth("player_valeros"),
        json=payload,
    )
    assert player.status_code == 403

    res = client.post(
        "/api/v1/soundscape/tension/calculate",
        headers=_auth("dm_evelyn"),
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sid
    assert data["tension_score"] > 50
    assert data["stem_profile"] in ("combat", "boss")


# ---------------------------------------------------------------------------
# 4. DM Manual Mood Override & Zanzibar Authority
# ---------------------------------------------------------------------------


def test_mood_override_dm_authority(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify DM with 'run_session' / 'manage' can manually force audio mood."""
    sid = setup_zanzibar_soundscape["sid"]
    headers = _auth("dm_evelyn")

    res = client.post(
        "/api/v1/soundscape/stems/override",
        headers=headers,
        json={
            "session_id": sid,
            "mood": "combat",
            "master_volume": 0.9,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sid
    assert data["stem_profile"] == "combat"
    assert data["manual_override"] is True


def test_mood_override_player_forbidden(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify player with 'play' but lacking 'run_session' is 403 Forbidden."""
    sid = setup_zanzibar_soundscape["sid"]
    headers = _auth("player_valeros")

    res = client.post(
        "/api/v1/soundscape/stems/override",
        headers=headers,
        json={
            "session_id": sid,
            "mood": "boss",
        },
    )
    assert res.status_code == 403
    assert "lacks Zanzibar permissions" in res.json()["detail"]


def test_mood_override_unauthorized_stranger(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify unauthenticated/stranger user is 403 Forbidden when overriding mood."""
    sid = setup_zanzibar_soundscape["sid"]
    headers = _auth("stranger_bob")

    res = client.post(
        "/api/v1/soundscape/stems/override",
        headers=headers,
        json={
            "session_id": sid,
            "mood": "tension",
        },
    )
    assert res.status_code == 403
    assert "lacks Zanzibar permissions" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 5. Character Leitmotif Timbre Configuration & Query
# ---------------------------------------------------------------------------


def test_leitmotif_profile_query(
    client: TestClient,
    setup_zanzibar_soundscape: dict[str, str],
    soundscape_service: str,
) -> None:
    """Verify querying character leitmotif timbre configuration."""
    sid = setup_zanzibar_soundscape["sid"]
    profile = CharacterLeitmotifProfile(
        session_id=sid,
        character_id="valeros",
        character_name="Valeros",
        instrument_timbre="brass",
        tempo_multiplier=1.2,
    )
    # Seed the profile through the soundscape service's public route.
    seeded = httpx.post(
        f"{soundscape_service}/api/v1/soundscape/leitmotif/profile",
        json=profile.model_dump(mode="json"),
        headers=_auth("dm_evelyn"),
    )
    assert seeded.status_code == 200, seeded.text

    res = client.get(
        f"/api/v1/soundscape/leitmotif/valeros?session_id={sid}", headers=_auth("player_valeros")
    )
    assert res.status_code == 200
    data = res.json()
    assert data["character_id"] == "valeros"
    assert data["instrument_timbre"] == "brass"
    assert data["tempo_multiplier"] == 1.2


# ---------------------------------------------------------------------------
# 6. Downstream Proxy Forwarding Logic
# ---------------------------------------------------------------------------


def test_downstream_proxy_forwarding(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify the gateway returns the body of the soundscape service it reached."""
    sid = setup_zanzibar_soundscape["sid"]
    res = client.post(
        "/api/v1/soundscape/cue",
        headers=_auth("dm_evelyn"),
        json={"session_id": sid, "cue_name": "fireball"},
    )
    assert res.status_code == 200
    assert res.json()["session_id"] == sid
    assert res.json()["cue_name"] == "fireball"


def test_proxy_returns_503_when_soundscape_is_unreachable(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str], monkeypatch
) -> None:
    """Verify an unreachable soundscape service returns 503, not a local substitute."""
    sid = setup_zanzibar_soundscape["sid"]
    monkeypatch.setenv("RUNEFOBLE_SOUNDSCAPE_URL", closed_port_url())

    with TestClient(gateway_app) as restarted_gateway:
        res = restarted_gateway.post(
            "/api/v1/soundscape/cue",
            headers=_auth("dm_evelyn"),
            json={"session_id": sid, "cue_name": "fireball"},
        )
    assert res.status_code == 503
    assert res.json()["upstream"] == "soundscape"
    assert "cue_id" not in res.text


# ---------------------------------------------------------------------------
# 7. Owner Owns Validation and Routes (TASK-0589, TASK-0775)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/api/v1/soundscape/cue", "/api/v1/soundscape/stems/override"],
)
def test_malformed_body_returns_owner_422(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str], path: str
) -> None:
    """The gateway forwards the raw body, so the owning service answers the 422."""
    res = client.post(
        path,
        headers={**_auth("dm_evelyn"), "Content-Type": "application/json"},
        content=b"{not json",
    )
    assert res.status_code == 422
    assert res.json()["detail"][0]["type"] == "json_invalid"


def test_alias_override_route_is_removed(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """The alias /api/v1/soundscape/override is no longer routed (DoR 9)."""
    sid = setup_zanzibar_soundscape["sid"]
    res = client.post(
        "/api/v1/soundscape/override",
        headers=_auth("dm_evelyn"),
        json={"session_id": sid, "mood": "combat"},
    )
    assert res.status_code == 404


def test_alias_leitmotif_profile_route_is_removed(
    client: TestClient,
    setup_zanzibar_soundscape: dict[str, str],
    soundscape_service: str,
) -> None:
    """The alias /api/v1/soundscape/leitmotif/profile/{id} is no longer routed (DoR 9).

    The profile is seeded first, so a 404 can only come from the missing route.
    """
    sid = setup_zanzibar_soundscape["sid"]
    profile = CharacterLeitmotifProfile(
        session_id=sid,
        character_id="valeros",
        character_name="Valeros",
        instrument_timbre="brass",
        tempo_multiplier=1.2,
    )
    seeded = httpx.post(
        f"{soundscape_service}/api/v1/soundscape/leitmotif/profile",
        json=profile.model_dump(mode="json"),
        headers=_auth("dm_evelyn"),
    )
    assert seeded.status_code == 200, seeded.text

    res = client.get(
        f"/api/v1/soundscape/leitmotif/profile/valeros?session_id={sid}",
        headers=_auth("player_valeros"),
    )
    assert res.status_code == 404
