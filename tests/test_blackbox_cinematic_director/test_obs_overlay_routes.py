"""OBS transparent overlay route and sanitization blackbox tests (TASK-0190)."""

from typing import Any

from fastapi.testclient import TestClient
from gateway_api.spectator import set_raw_session_state


def test_obs_transparent_overlay_html_rendering_and_alpha_channel(client: TestClient) -> None:
    """Verify GET /overlay/party-vitals/{session_id} serves HTML with alpha-transparent canvas."""
    res = client.get("/overlay/party-vitals/sess-obs-alpha-1")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text

    # 1. Transparent OBS Rendering: alpha-transparent canvas and zero background color obstruction
    assert "rgba(0, 0, 0, 0)" in body
    assert "background: transparent" in body
    assert "obs-canvas" in body

    # 2. Party vitals delivered
    assert "Valeros" in body
    assert "45/45 HP" in body
    assert "Kyra" in body
    assert "AI STAND-IN" in body

    # 3. Sanitization Invariant: 100% exclusion of hidden traps, unrevealed monster HP, DM notes
    assert "Goblin Stalker" not in body
    assert "Mimic" not in body
    assert "Secret GM encounter notes" not in body
    assert "DC 15 Dex save" not in body
    assert "Carrying secret potion" not in body
    assert "dm_notes" not in body


def test_obs_overlay_position_and_easing_customization(client: TestClient) -> None:
    """Verify overlay layout positioning and cubic-bezier easing parameters."""
    # Test sidebar layout
    res_sidebar = client.get("/overlay/party-vitals/sess-layout-1?position=sidebar")
    assert res_sidebar.status_code == 200
    assert "flex-direction: column" in res_sidebar.text

    # Test top layout
    res_top = client.get("/overlay/party-vitals/sess-layout-1?position=top")
    assert res_top.status_code == 200
    assert "align-items: flex-start" in res_top.text

    # Test custom cubic-bezier and duration
    custom_easing = "cubic-bezier(0.42, 0.0, 0.58, 1.0)"
    res_easing = client.get(
        f"/overlay/party-vitals/sess-layout-1?easing={custom_easing}&duration=400"
    )
    assert res_easing.status_code == 200
    assert "400ms" in res_easing.text
    assert custom_easing in res_easing.text


def test_obs_party_vitals_json_format_sanitization(
    client: TestClient, mock_party_state: dict[str, Any]
) -> None:
    """Verify format=json provides strictly sanitized party vitals and excludes monster stats."""
    set_raw_session_state("sess-san-json", mock_party_state)

    res = client.get("/overlay/party-vitals/sess-san-json?format=json")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == "sess-san-json"
    assert data["round"] == 4
    assert len(data["party"]) == 1

    paladin = data["party"][0]
    assert paladin["name"] == "Sir Roderick"
    assert paladin["hp"] == 52
    assert paladin["max_hp"] == 60
    assert "shield of faith" in paladin["conditions"]
    assert "dm_notes" not in paladin

    # Verify 100% exclusion of unrevealed monster HP, traps, and DM notes
    assert "dm_notes" not in data
    assert "monster_stat_blocks" not in data
    for member in data["party"]:
        assert member["name"] != "Shadow Fiend"
