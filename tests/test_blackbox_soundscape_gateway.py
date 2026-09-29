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

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app
from soundscape.dependencies import get_or_create_leitmotif_engine, reset_dependencies
from soundscape.leitmotif import CharacterLeitmotifProfile

REPO_ROOT = Path(__file__).resolve().parent.parent
GATEWAY_ROUTER_PATH = (
    REPO_ROOT / "gateway" / "api" / "src" / "gateway_api" / "routers" / "soundscape.py"
)


@pytest.fixture(autouse=True)
def clean_state():
    reset_dependencies()
    campaign_store.reset()
    yield
    reset_dependencies()
    campaign_store.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


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
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res_camp.status_code == 201
    cid = res_camp.json()["id"]

    # 2. Assign player role to Valeros through public frontdoor
    res_role = client.post(
        f"/api/v1/campaigns/{cid}/roles",
        json={"user_id": "player_valeros", "role": "player"},
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res_role.status_code == 200

    # 3. Create session through public frontdoor
    res_sess = client.post(
        f"/api/v1/campaigns/{cid}/sessions",
        json={"title": "Echoing Depths"},
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res_sess.status_code == 201
    sid = res_sess.json()["id"]

    return {"cid": cid, "sid": sid}


# ---------------------------------------------------------------------------
# 1. File Length & Schema DoD Invariants
# ---------------------------------------------------------------------------


def test_file_length_invariants() -> None:
    """Verify soundscape router is strictly < 130 lines (DoD 1)."""
    assert GATEWAY_ROUTER_PATH.is_file(), f"{GATEWAY_ROUTER_PATH} must exist"
    lines = len(GATEWAY_ROUTER_PATH.read_text(encoding="utf-8").splitlines())
    assert lines < 130, f"soundscape.py has {lines} lines; must be strictly < 130 lines (DoD 1)"


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
    headers = {"X-User-Id": "player_valeros"}

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
    headers = {"X-User-Id": "stranger_bob"}

    res = client.post(
        "/api/v1/soundscape/cue",
        headers=headers,
        json={
            "session_id": sid,
            "cue_name": "thunder",
        },
    )
    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["error"] == "permission_denied"
    assert detail["required_permission"] == "play"


# ---------------------------------------------------------------------------
# 3. Encounter Tension Query & Calculation
# ---------------------------------------------------------------------------


def test_tension_status_query(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify GET /api/v1/soundscape/tension retrieves tension score and stem weights."""
    sid = setup_zanzibar_soundscape["sid"]
    res = client.get(f"/api/v1/soundscape/tension?session_id={sid}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sid
    assert "tension_score" in data
    assert "stem_profile" in data
    assert "active_stems" in data
    assert "stem_volumes" in data


def test_tension_calculation(client: TestClient, setup_zanzibar_soundscape: dict[str, str]) -> None:
    """Verify POST /api/v1/soundscape/tension/calculate adapts music stems."""
    sid = setup_zanzibar_soundscape["sid"]
    res = client.post(
        "/api/v1/soundscape/tension/calculate",
        json={
            "session_id": sid,
            "combat_active": True,
            "combat_round": 3,
            "enemy_cr_balance": 3.0,
            "lowest_party_health_ratio": 0.25,
        },
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
    headers = {"X-User-Id": "dm_evelyn"}

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
    headers = {"X-User-Id": "player_valeros"}

    res = client.post(
        "/api/v1/soundscape/stems/override",
        headers=headers,
        json={
            "session_id": sid,
            "mood": "boss",
        },
    )
    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["error"] == "permission_denied"
    assert detail["required_permission"] == "run_session"


def test_mood_override_unauthorized_stranger(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify unauthenticated/stranger user is 403 Forbidden when overriding mood."""
    sid = setup_zanzibar_soundscape["sid"]
    headers = {"X-User-Id": "stranger_bob"}

    res = client.post(
        "/api/v1/soundscape/stems/override",
        headers=headers,
        json={
            "session_id": sid,
            "mood": "tension",
        },
    )
    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["error"] == "permission_denied"
    assert detail["required_permission"] == "run_session"


# ---------------------------------------------------------------------------
# 5. Character Leitmotif Timbre Configuration & Query
# ---------------------------------------------------------------------------


def test_leitmotif_profile_query(
    client: TestClient, setup_zanzibar_soundscape: dict[str, str]
) -> None:
    """Verify querying character leitmotif timbre configuration."""
    sid = setup_zanzibar_soundscape["sid"]
    engine = get_or_create_leitmotif_engine(sid)
    engine.register_profile(
        CharacterLeitmotifProfile(
            session_id=sid,
            character_id="valeros",
            character_name="Valeros",
            instrument_timbre="brass",
            tempo_multiplier=1.2,
        )
    )

    res = client.get(f"/api/v1/soundscape/leitmotif/valeros?session_id={sid}")
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
    """Verify router proxies to downstream soundscape service when reachable."""
    sid = setup_zanzibar_soundscape["sid"]
    mock_resp_data = {
        "cue_id": "cue-proxied-99",
        "session_id": sid,
        "status": "triggered",
        "cue_name": "fireball",
        "sound_url": "http://silo:9000/runefoble-assets/audio/foley/fireball.ogg",
        "cue_type": "spell",
        "volume_gain": 1.0,
        "duck_music": True,
    }

    class MockResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return mock_resp_data

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def request(self, method: str, url: str, **kwargs):
            return MockResponse()

    with patch("httpx.AsyncClient", MockAsyncClient):
        res = client.post(
            "/api/v1/soundscape/cue",
            headers={"X-User-Id": "dm_evelyn"},
            json={"session_id": sid, "cue_name": "fireball"},
        )
        assert res.status_code == 200
        assert res.json()["cue_id"] == "cue-proxied-99"
