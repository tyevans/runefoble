"""Blackbox TDD frontdoor test suite for Soundscape Mixing Panel UI (TASK-0109).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0006: Redis Streams Event Bus
- ADR-0007: API Gateway Architecture and Service Endpoints
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client as set_gw_spicedb_client
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus as set_gw_event_bus
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient
from soundscape.dependencies import (
    reset_dependencies,
    set_spicedb_client,
)
from soundscape.main import app as soundscape_app

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean soundscape and gateway state for each test."""
    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)
    set_gw_spicedb_client(mock_db)
    set_gw_event_bus(None)
    reset_dependencies()
    set_spicedb_client(mock_db)
    yield
    reset_dependencies()
    set_spicedb_client(SpiceDBClient())
    set_gw_spicedb_client(SpiceDBClient())
    set_gw_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(soundscape_app)


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & File Structure Integrity
# ---------------------------------------------------------------------------


def test_soundscape_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "soundscape"
    assert data["package"] == "@runefoble/soundscape-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-soundscape-controls" in data["components"]
    assert "runefoble-soundscape-controls" in data["tags"]
    assert any("runefoble-soundscape-controls.styles" in s for s in data["styles"])
    assert any("index.ts" in s for s in data["scripts"])


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/soundscape/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/soundscape/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()

    assert manifest_data["service"] == endpoint_data["service"]
    assert manifest_data["package"] == endpoint_data["package"]
    assert manifest_data["components"] == endpoint_data["components"]
    assert manifest_data["tags"] == endpoint_data["tags"]


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/soundscape/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/soundscape-ui"
    assert "./runefoble-soundscape-controls" in pkg_json["exports"]
    assert "./runefoble-soundscape-controls.styles" in pkg_json["exports"]

    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()

    comp_file = ui_dir / "src/runefoble-soundscape-controls.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-soundscape-controls')" in comp_src
    assert "class RunefobleSoundscapeControls" in comp_src
    assert "playEarcon" in comp_src
    assert "triggerDucking" in comp_src
    assert "stemVolumes" in comp_src
    assert "thunder" in comp_src
    assert "door_slam" in comp_src
    assert "steel_clash" in comp_src
    assert "roar" in comp_src
    assert "soundscape-volume" in comp_src
    assert "soundscape-mood" in comp_src
    assert "soundscape-cue" in comp_src
    assert "soundscape-duck" in comp_src
    assert "soundscape-stem-volume" in comp_src

    styles_file = ui_dir / "src/runefoble-soundscape-controls.styles.ts"
    assert styles_file.is_file()
    styles_src = styles_file.read_text(encoding="utf-8")
    assert "--rf-accent-primary" in styles_src
    assert "--rf-border-color" in styles_src
    assert "--rf-shadow" in styles_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include QuietAmbient, HighTensionCombat, and ActiveFoleyPlayback."""
    stories_file = REPO_ROOT / "services/soundscape/ui/src/runefoble-soundscape-controls.stories.ts"
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    assert "ExplorationDefault" in content
    assert "QuietAmbient" in content
    assert "CombatActive" in content
    assert "HighTensionCombat" in content
    assert "BossClimax" in content
    assert "ActiveFoleyPlayback" in content
    assert "VoiceDuckingActive" in content
    assert "runefoble-soundscape-controls" in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports the microfrontend per ADR-0013."""
    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-soundscape-controls.ts"
    assert forwarding_file.is_file()
    content = forwarding_file.read_text(encoding="utf-8")
    assert "@runefoble/soundscape-ui" in content

    shell_index = REPO_ROOT / "frontend/src/index.ts"
    shell_src = shell_index.read_text(encoding="utf-8")
    assert "runefoble-soundscape-controls" in shell_src

    frontend_pkg = json.loads((REPO_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert "@runefoble/soundscape-ui" in frontend_pkg["dependencies"]


# ---------------------------------------------------------------------------
# 2. REST Frontdoor Data Binding Integration
# ---------------------------------------------------------------------------


def test_rest_data_binding_catalog_and_foley_presets(client: TestClient) -> None:
    """Verify GET /api/v1/soundscape/stems lists layers, presets, and stem channels."""
    resp = client.get("/api/v1/soundscape/stems?session_id=sess-ui-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    assert "ambient" in data["stem_layers"]
    assert "combat" in data["stem_layers"]
    assert "thunder" in data["foley_presets"]
    assert "door_slam" in data["foley_presets"]
    assert "steel_clash" in data["foley_presets"]
    assert "roar" in data["foley_presets"]
    assert "stem_channels" in data
    assert "melody" in data["stem_channels"]
    assert "percussion" in data["stem_channels"]


def test_rest_data_binding_multi_channel_stem_volume_sliders(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/stems/volume updates individual stem channel sliders."""
    payload = {
        "session_id": "sess-ui-01",
        "stem_volumes": {
            "melody": 0.95,
            "percussion": 0.60,
            "drone": 0.40,
            "ambient": 0.85,
        },
    }
    resp = client.post("/api/v1/soundscape/stems/volume", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    assert data["stem_channels"]["melody"] == 0.95
    assert data["stem_channels"]["percussion"] == 0.60
    assert data["stem_channels"]["drone"] == 0.40
    assert data["stem_channels"]["ambient"] == 0.85


def test_rest_data_binding_foley_cue_trigger(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/cue triggers acoustic foley effects with ducking."""
    cue_payload = {
        "session_id": "sess-ui-01",
        "cue_name": "thunder",
        "cue_type": "foley",
        "volume_gain": 1.1,
        "duck_music": True,
    }
    resp = client.post("/api/v1/soundscape/cue", json=cue_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    assert data["cue_name"] == "thunder"
    assert data["status"] == "triggered"
    assert data["duck_music"] is True


def test_rest_data_binding_webaudio_ducking(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/duck toggles -12dB attenuation coordinator."""
    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": "sess-ui-01", "is_ducked": True, "reason": "speech"},
    )
    assert duck_resp.status_code == 200
    data = duck_resp.json()
    assert data["is_ducked"] is True
    assert data["attenuation_db"] == -12.0
    assert math.isclose(data["effective_gain"], 0.2512, rel_tol=1e-3)

    unduck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": "sess-ui-01", "is_ducked": False, "reason": "speech_ended"},
    )
    assert unduck_resp.status_code == 200
    unduck_data = unduck_resp.json()
    assert unduck_data["is_ducked"] is False
    assert unduck_data["attenuation_db"] == 0.0
    assert unduck_data["effective_gain"] == 1.0


def test_rest_data_binding_tension_calculation(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/tension/calculate computes tension metrics."""
    calc_payload = {
        "session_id": "sess-ui-01",
        "combat_active": True,
        "combat_round": 2,
        "enemy_cr_balance": 2.5,
        "lowest_party_health_ratio": 0.4,
    }
    resp = client.post("/api/v1/soundscape/tension/calculate", json=calc_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    assert data["tension_score"] >= 50
    assert data["stem_profile"] in ("tension", "combat", "boss")


# ---------------------------------------------------------------------------
# 3. SpiceDB Zanzibar Object-Level Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spicedb_zanzibar_authorization_on_soundscape_controls(
    client: TestClient,
) -> None:
    """Verify Zanzibar permissions guard DM mood overrides and controls."""
    session_id = "sess-zanzibar-01"
    campaign_id = str(uuid4())
    dm_user = "dm-evelyn"
    player_user = "player-marcus"

    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)

    # 1. Player without DM authority attempts mood override -> 403 Forbidden
    resp_unauth = client.post(
        "/api/v1/soundscape/override",
        headers={"X-User-ID": player_user},
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "mood": "boss",
            "master_volume": 0.9,
        },
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    # 2. Grant DM run_session permission in Zanzibar
    await mock_db.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="run_session",
        subject_type="user",
        subject_id=dm_user,
    )

    # 3. DM with permission performs mood override -> 200 OK
    resp_auth = client.post(
        "/api/v1/soundscape/override",
        headers={"X-User-ID": dm_user},
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "mood": "boss",
            "master_volume": 0.9,
        },
    )
    assert resp_auth.status_code == 200
    data = resp_auth.json()
    assert data["stem_profile"] == "boss"
    assert data["manual_override"] is True
    assert data["master_volume"] == 0.9


# ---------------------------------------------------------------------------
# 4. Gateway WebSocket Broadcast Data Binding
# ---------------------------------------------------------------------------


def test_gateway_websocket_soundscape_broadcast(gateway_client: TestClient) -> None:
    """Verify soundscape acoustic cues fan out through the campaign WebSocket."""
    campaign_id = "camp-soundscape-ws-01"
    dm_user = "dm-evelyn"

    mock_db = MockSpiceDBClient()
    set_gw_spicedb_client(mock_db)

    asyncio.run(
        mock_db.write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="dungeon_master",
            subject_type="user",
            subject_id=dm_user,
        )
    )

    with gateway_client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={dm_user}") as ws:
        connected_frame = ws.receive_json()
        assert connected_frame["type"] == "connected"

        # Broadcast soundboard foley trigger action
        ws.send_json(
            {
                "action": "soundscape_cue",
                "cue_name": "thunder",
                "duck_music": True,
                "volume_gain": 1.1,
                "session_id": "sess-ws-1",
            }
        )

        broadcast = ws.receive_json()
        assert broadcast["type"] == "soundscape_cue"
        assert broadcast["action"] == "soundscape_cue"
        assert broadcast["cue_name"] == "thunder"
        assert broadcast["duck_music"] is True
        assert broadcast["status"] == "applied"
        assert broadcast["user_id"] == dm_user
