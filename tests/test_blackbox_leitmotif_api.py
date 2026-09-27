"""Blackbox TDD REST API & Zanzibar auth suite for Character Leitmotifs.

Governed by:
- ADR-0003, ADR-0009, ADR-0013
- Hard Invariant 1 (SpiceDB Zanzibar), Hard Invariant 6 (File length < 500 lines)
- PRD-0016 & US-0046 (Character Leitmotifs and Dynamic Theme Scoring)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from soundscape.dependencies import set_spicedb_client

from tests.helpers.leitmotif_fixtures import clean_environment, client, setup_leitmotif_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
__all__ = ["clean_environment", "client"]


def test_list_timbre_presets_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/soundscape/leitmotif/timbres returns available presets."""
    resp = client.get("/api/v1/soundscape/leitmotif/timbres")
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data and "supported_timbres" in data
    for timbre in ("lute", "brass", "woodwind", "strings", "synth"):
        assert timbre in data["supported_timbres"]

    lute_preset = data["presets"]["lute"]
    assert "triumphant_stem_url" in lute_preset and "somber_stem_url" in lute_preset
    assert lute_preset["label"] == "Lute & Celtic Flute"


def test_character_leitmotif_profile_crud_frontdoor(client: TestClient) -> None:
    """Verify POST and GET /api/v1/soundscape/leitmotif/profile endpoints."""
    payload = {
        "session_id": "session-tomb-14",
        "character_id": "char-nadia",
        "character_name": "Nadia",
        "instrument_timbre": "lute",
        "tempo_multiplier": 1.05,
        "volume_gain": 1.0,
        "attack_ms": 120,
        "release_ms": 300,
        "duration_ms": 4000,
    }
    resp = client.post("/api/v1/soundscape/leitmotif/profile", json=payload)
    assert resp.status_code == 200
    created = resp.json()
    assert created["character_id"] == "char-nadia" and created["instrument_timbre"] == "lute"
    assert created["tempo_multiplier"] == 1.05
    assert "lute_triumphant.ogg" in created["triumphant_stem_url"]
    assert "lute_somber.ogg" in created["somber_stem_url"]

    get_resp = client.get(
        "/api/v1/soundscape/leitmotif/profile/char-nadia?session_id=session-tomb-14"
    )
    assert get_resp.status_code == 200
    retrieved = get_resp.json()
    assert retrieved["character_name"] == "Nadia" and retrieved["attack_ms"] == 120


def test_trigger_and_audition_leitmotif_frontdoor(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/leitmotif/trigger stinger audition."""
    setup_leitmotif_profile(client, "session-tomb-14", "char-valeros", "Valeros", "brass")
    trigger_resp = client.post(
        "/api/v1/soundscape/leitmotif/trigger",
        json={
            "session_id": "session-tomb-14",
            "character_id": "char-valeros",
            "motif_type": "triumphant",
            "trigger_reason": "audition",
        },
    )
    assert trigger_resp.status_code == 200
    playback = trigger_resp.json()
    assert playback["character_id"] == "char-valeros" and playback["motif_type"] == "triumphant"
    assert playback["instrument_timbre"] == "brass" and playback["is_ducked"] is False
    assert playback["scheduled_latency_ms"] <= 250

    active_resp = client.get("/api/v1/soundscape/leitmotif/active?session_id=session-tomb-14")
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert active_data["is_playing"] is True
    assert active_data["active_leitmotif"]["character_id"] == "char-valeros"


@pytest.mark.asyncio
async def test_zanzibar_authorization_enforced_on_leitmotif_profile(client: TestClient) -> None:
    """Verify unauthorized users receive 403 Forbidden under Zanzibar schema."""
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)

    payload = {
        "session_id": "session-tomb-14",
        "character_id": "char-restricted",
        "character_name": "Restricted Char",
        "instrument_timbre": "brass",
    }
    resp_forbidden = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json=payload,
        headers={"x-user-id": "user-unauthorized"},
    )
    assert resp_forbidden.status_code == 403 and "Forbidden" in resp_forbidden.json()["detail"]

    await mock_spicedb.write_relationship(
        resource_type="character",
        resource_id="char-restricted",
        relation="owner",
        subject_type="user",
        subject_id="user-owner",
    )
    resp_allowed = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json=payload,
        headers={"x-user-id": "user-owner"},
    )
    assert (
        resp_allowed.status_code == 200 and resp_allowed.json()["character_id"] == "char-restricted"
    )


def test_soundscape_manifest_includes_leitmotif_config(client: TestClient) -> None:
    """Verify GET /ui/manifest advertises runefoble-leitmotif-config."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    tag = "runefoble-leitmotif-config"
    assert tag in data["components"] and tag in data["tags"]
    assert any("runefoble-leitmotif-config.styles" in s for s in data["styles"])


def test_leitmotif_microfrontend_component_invariants() -> None:
    """Verify Lit component, styles, and Storybook stories conform to code limits."""
    ui_dir = REPO_ROOT / "services" / "soundscape" / "ui"
    comp_file = ui_dir / "src" / "runefoble-leitmotif-config.ts"
    styles_file = ui_dir / "src" / "runefoble-leitmotif-config.styles.ts"
    stories_file = ui_dir / "src" / "runefoble-leitmotif-config.stories.ts"

    assert comp_file.is_file() and styles_file.is_file() and stories_file.is_file()
    comp_content = comp_file.read_text(encoding="utf-8")
    styles_content = styles_file.read_text(encoding="utf-8")
    stories_content = stories_file.read_text(encoding="utf-8")

    assert len(comp_content.splitlines()) < 300 and len(styles_content.splitlines()) < 250
    assert len(stories_content.splitlines()) < 200

    assert "@customElement('runefoble-leitmotif-config')" in comp_content
    events = ("'leitmotif-audition'", "'leitmotif-configured'", "'leitmotif-timbre-selected'")
    assert all(e in comp_content for e in events)
    assert all(
        t in styles_content for t in ("--rf-accent-primary", "--rf-border-color", "--rf-shadow")
    )
    stories = ("DefaultNadiaLute", "HeroicBrass", "SomberCelloStrings", "VoiceDuckingActive")
    assert all(s in stories_content for s in stories)
