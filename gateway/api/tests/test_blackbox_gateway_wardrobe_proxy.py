"""Blackbox tests: gateway wardrobe and active-portrait routes proxy to character_sheet (TASK-0444).

Each test drives the public gateway routes. character_sheet runs as a live loopback upstream.
The gateway holds no wardrobe state. The owner checks `view` and `edit` (ADR-0001), so a
stranger gets the owner's 403. An owner that is down returns 503, and an owner 5xx returns 502
(ADR-0015 b).
"""

from fastapi.testclient import TestClient
from gateway_api.main import app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app

GALA_URL = "https://silo.example.test/wardrobe/gala.png"


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_character(client: TestClient, headers: dict[str, str]) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": "Nadia", "characterClass": "Bard", "maxHp": 20},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _add_gala_variant(client: TestClient, char_id: str, headers: dict[str, str]):
    return client.post(
        f"/api/v1/characters/{char_id}/wardrobe",
        json={
            "variant_id": "var-gala",
            "variant_name": "Masquerade gown",
            "attire_type": "formal",
            "image_url": GALA_URL,
            "prompt": "Ballroom masquerade, silver mask",
            "set_active": False,
        },
        headers=headers,
    )


def test_added_wardrobe_variant_is_listed_by_the_next_read(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A variant posted through the gateway appears in the wardrobe that a later GET returns."""
    headers = _auth(trusted_ws_issuer, "user_wardrobe_list")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        added = _add_gala_variant(client, char_id, headers)
        listed = client.get(f"/api/v1/characters/{char_id}/wardrobe", headers=headers)

    assert added.status_code == 200, added.text
    assert listed.status_code == 200, listed.text
    variant = listed.json()["var-gala"]
    assert variant["variant_name"] == "Masquerade gown"
    assert variant["image_url"] == GALA_URL


def test_active_portrait_switches_to_the_chosen_variant(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """Switching the active portrait to a stored variant makes that variant's image active."""
    headers = _auth(trusted_ws_issuer, "user_portrait_switch")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        _add_gala_variant(client, char_id, headers)
        switched = client.post(
            f"/api/v1/characters/{char_id}/portrait/active",
            json={"variant_id": "var-gala"},
            headers=headers,
        )

    assert switched.status_code == 200, switched.text
    assert switched.json()["active_portrait_url"] == GALA_URL
    assert switched.json()["active_variant_id"] == "var-gala"


def test_stranger_is_refused_with_403_on_every_route(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A caller with no relation to the character gets the owner's 403 on read and on write."""
    owner = _auth(trusted_ws_issuer, "user_wardrobe_owner")
    stranger = _auth(trusted_ws_issuer, "user_wardrobe_stranger")
    with TestClient(app) as client:
        char_id = _create_character(client, owner)
        read = client.get(f"/api/v1/characters/{char_id}/wardrobe", headers=stranger)
        add = _add_gala_variant(client, char_id, stranger)
        switch = client.post(
            f"/api/v1/characters/{char_id}/portrait/active",
            json={"variant_id": "var-gala"},
            headers=stranger,
        )

    assert read.status_code == 403
    assert add.status_code == 403
    assert switch.status_code == 403


def test_missing_token_is_refused_by_the_owner_with_401(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """The gateway forwards a call with no bearer token, and the owner answers 401."""
    owner = _auth(trusted_ws_issuer, "user_wardrobe_anonymous_owner")
    with TestClient(app) as client:
        char_id = _create_character(client, owner)
        res = client.get(f"/api/v1/characters/{char_id}/wardrobe")

    assert res.status_code == 401


def test_owner_down_returns_503_on_wardrobe_read(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream, monkeypatch
):
    """With character_sheet unreachable, the wardrobe read fails with 503 and no fallback body."""
    headers = _auth(trusted_ws_issuer, "user_wardrobe_down")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)

    monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", closed_port_url())
    with TestClient(app) as client:
        res = client.get(f"/api/v1/characters/{char_id}/wardrobe", headers=headers)

    assert res.status_code == 503
    assert res.json()["upstream"] == "character_sheet"
    assert "wardrobe_variants" not in res.text


def test_owner_server_error_returns_502_on_portrait_switch(trusted_ws_issuer, monkeypatch):
    """An owner 5xx on the portrait switch becomes 502 at the gateway, never a 200 substitute."""
    headers = _auth(trusted_ws_issuer, "user_wardrobe_owner_500")
    with serve(unavailable_app(500)) as broken_url:
        monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", broken_url)
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/characters/00000000-0000-4000-8000-0000000000aa/portrait/active",
                json={"variant_id": "var-gala"},
                headers=headers,
            )

    assert res.status_code == 502
    assert res.json()["upstream"] == "character_sheet"
