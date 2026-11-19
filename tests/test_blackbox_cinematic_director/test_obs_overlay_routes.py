"""OBS transparent overlay route and sanitization blackbox tests (TASK-0190, TASK-0809).

Every session in these tests is created and filled through public routes. The party comes
from the board owner. Monsters and the owner-side DM data must not reach the overlay.
"""

from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer

OBSERVER = "spectator_sol"


def _observed_table(board_table) -> str:
    _, session_id = board_table("dm_dora", {OBSERVER: "spectator"}, start=True)
    return session_id


def test_obs_transparent_overlay_html_rendering_and_alpha_channel(
    client: TestClient, board_table
) -> None:
    """Verify GET /overlay/party-vitals/{session_id} serves HTML with alpha-transparent canvas."""
    session_id = _observed_table(board_table)
    res = client.get(f"/overlay/party-vitals/{session_id}", headers=bearer(OBSERVER))

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text

    # 1. Transparent OBS Rendering: alpha-transparent canvas and zero background color obstruction
    assert "rgba(0, 0, 0, 0)" in body
    assert "background: transparent" in body
    assert "obs-canvas" in body

    # 2. Party vitals delivered from the owner
    assert "Valeros" in body

    # 3. Sanitization: monsters and DM data stay out of the overlay
    assert "Goblin Stalker" not in body
    assert "Secret GM encounter notes" not in body
    assert "dm_notes" not in body


def test_obs_overlay_position_and_easing_customization(client: TestClient, board_table) -> None:
    """Verify overlay layout positioning and cubic-bezier easing parameters."""
    session_id = _observed_table(board_table)
    headers = bearer(OBSERVER)

    res_sidebar = client.get(
        f"/overlay/party-vitals/{session_id}?position=sidebar", headers=headers
    )
    assert res_sidebar.status_code == 200
    assert "flex-direction: column" in res_sidebar.text

    res_top = client.get(f"/overlay/party-vitals/{session_id}?position=top", headers=headers)
    assert res_top.status_code == 200
    assert "align-items: flex-start" in res_top.text

    custom_easing = "cubic-bezier(0.42, 0.0, 0.58, 1.0)"
    res_easing = client.get(
        f"/overlay/party-vitals/{session_id}?easing={custom_easing}&duration=400", headers=headers
    )
    assert res_easing.status_code == 200
    assert "400ms" in res_easing.text
    assert custom_easing in res_easing.text


def test_obs_party_vitals_json_excludes_monsters_and_dm_fields(
    client: TestClient, board_table
) -> None:
    """Verify format=json returns the owner party and no monster or DM field."""
    session_id = _observed_table(board_table)
    res = client.get(f"/overlay/party-vitals/{session_id}?format=json", headers=bearer(OBSERVER))
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == session_id
    assert [member["name"] for member in data["party"]] == ["Valeros"]
    assert data["party"][0]["hp"] == 45
    assert "dm_notes" not in data
    assert "monster_stat_blocks" not in data
    for member in data["party"]:
        assert "dm_notes" not in member
        assert member["name"] != "Goblin Stalker"


def test_obs_overlay_refuses_a_viewer_without_observe(client: TestClient, board_table) -> None:
    session_id = _observed_table(board_table)
    res = client.get(f"/overlay/party-vitals/{session_id}", headers=bearer("stranger_eve"))
    assert res.status_code == 403
