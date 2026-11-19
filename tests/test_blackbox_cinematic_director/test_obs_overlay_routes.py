"""OBS party vitals route blackbox tests (TASK-0190, TASK-0809, TASK-0823).

Every session in these tests is created and filled through public routes. The party and the
camera come from the board owner. Monsters and the owner-side DM data must not reach the overlay.
The gateway serves JSON only. An HTML request gets 406 until an App Shell route hosts the
`<runefoble-spectator-overlay>` component.
"""

from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer

OBSERVER = "spectator_sol"


def _observed_table(board_table) -> str:
    _, session_id = board_table("dm_dora", {OBSERVER: "spectator"}, start=True)
    return session_id


def test_obs_overlay_refuses_an_html_request_with_406(client: TestClient, board_table) -> None:
    session_id = _observed_table(board_table)
    res = client.get(
        f"/overlay/party-vitals/{session_id}",
        headers={**bearer(OBSERVER), "Accept": "text/html,application/xhtml+xml"},
    )
    assert res.status_code == 406
    assert res.json()["detail"]["error"] == "html_not_served"


def test_obs_overlay_json_carries_the_requested_position(client: TestClient, board_table) -> None:
    session_id = _observed_table(board_table)
    headers = bearer(OBSERVER)

    res_sidebar = client.get(
        f"/overlay/party-vitals/{session_id}?format=json&position=sidebar", headers=headers
    )
    assert res_sidebar.status_code == 200
    assert res_sidebar.json()["position"] == "sidebar"

    res_top = client.get(
        f"/overlay/party-vitals/{session_id}?format=json&position=top", headers=headers
    )
    assert res_top.status_code == 200
    assert res_top.json()["position"] == "top"


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
    assert "Goblin Stalker" not in res.text
    assert "dm_notes" not in res.text
    assert "monster_stat_blocks" not in data
    for member in data["party"]:
        assert "dm_notes" not in member
        assert member["name"] != "Goblin Stalker"


def test_obs_overlay_refuses_a_viewer_without_observe(client: TestClient, board_table) -> None:
    session_id = _observed_table(board_table)
    res = client.get(f"/overlay/party-vitals/{session_id}", headers=bearer("stranger_eve"))
    assert res.status_code == 403
