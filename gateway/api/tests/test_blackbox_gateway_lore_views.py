"""Blackbox frontdoor tests: gateway lore views proxy to the real campaign_lore (TASK-0587).

The gateway is called through its public HTTP routes. campaign_lore runs as its real ASGI app
on a loopback port with its own lifespan (PostgreSQL and the embeddings stand-in come from the
lore backends). Setup goes through public routes only: the owner creates the campaign, issues
an invite, a player joins it, and the owner places a pin and publishes codex entries.

No canned pin or entry is asserted. Upstream failure must reach the caller as 503 or 502, and
an owner refusal must pass through unchanged (ADR-0015).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from campaign_lore.main import app as lore_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.ws_identity import bearer

PIN_TITLE = "Gate of Ashes"
PIN_BODY = {
    "title": PIN_TITLE,
    "coordinates": {"x": 320.0, "y": 180.0},
    "layer": "continental",
}
SHARED_ENTRY = {
    "title": "Ashes Chronicle",
    "content": "The party recorded the gate that opened over the ash plain.",
    "privacy": "party_shared",
}
OTHER_ENTRY = {
    "title": "Harbour Rumours",
    "content": "Dockhands mutter about lanterns on the water.",
    "privacy": "party_shared",
}


@pytest.fixture
def live_lore(monkeypatch, lore_backends, game_session_upstream) -> Iterator[str]:
    """Serve the real campaign_lore app with its lifespan and point the gateway at it."""
    with serve(lore_app, lifespan="on") as lore_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_LORE_URL", lore_url)
        yield lore_url


@pytest.fixture
def client(live_lore) -> Iterator[TestClient]:
    """Run the gateway lifespan after the upstream URLs are set, so clients see them."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def campaign(client: TestClient, trusted_ws_issuer) -> dict[str, Any]:
    """Create a campaign as its owner, invite a player, and join the player to it."""
    owner = bearer("dm_lore_owner", issuer=trusted_ws_issuer)
    created = client.post(
        "/api/v1/campaigns",
        json={"title": "Ashes Campaign", "setting": "Ember Coast", "system": "5e"},
        headers=owner,
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]

    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player", "expires_in_hours": 24, "max_uses": 5},
        headers=owner,
    )
    assert invite.status_code == 201, invite.text

    member = bearer("player_lore_member", issuer=trusted_ws_issuer)
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=member,
    )
    assert joined.status_code == 200, joined.text
    return {
        "id": campaign_id,
        "owner": owner,
        "member": member,
        "outsider": bearer("stranger_lore", issuer=trusted_ws_issuer),
    }


def test_atlas_returns_the_pin_the_owner_placed(client: TestClient, campaign) -> None:
    campaign_id = campaign["id"]
    placed = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins", json=PIN_BODY, headers=campaign["owner"]
    )
    assert placed.status_code == 201, placed.text

    res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=campaign["owner"])

    assert res.status_code == 200, res.text
    assert PIN_TITLE in [pin["title"] for pin in res.json()["pins"]]


def test_party_shared_codex_entry_is_visible_to_a_member_and_hidden_from_an_outsider(
    client: TestClient, campaign
) -> None:
    campaign_id = campaign["id"]
    published = client.post(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        json=SHARED_ENTRY,
        headers=campaign["owner"],
    )
    assert published.status_code == 201, published.text

    member_view = client.get(f"/api/v1/campaigns/{campaign_id}/codex", headers=campaign["member"])
    assert member_view.status_code == 200, member_view.text
    assert SHARED_ENTRY["title"] in [entry["title"] for entry in member_view.json()]

    outsider_view = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex", headers=campaign["outsider"]
    )
    assert outsider_view.status_code == 403
    assert SHARED_ENTRY["title"] not in outsider_view.text


def test_codex_search_parameter_reaches_the_owner(client: TestClient, campaign) -> None:
    campaign_id = campaign["id"]
    for entry in (SHARED_ENTRY, OTHER_ENTRY):
        published = client.post(
            f"/api/v1/campaigns/{campaign_id}/codex/entries", json=entry, headers=campaign["owner"]
        )
        assert published.status_code == 201, published.text

    res = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex",
        params={"search": "ashes"},
        headers=campaign["member"],
    )

    assert res.status_code == 200, res.text
    assert [entry["title"] for entry in res.json()] == [SHARED_ENTRY["title"]]


def test_owner_down_returns_503_for_atlas_and_codex(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_LORE_URL", closed_port_url())
    owner = bearer("dm_lore_down", issuer=trusted_ws_issuer)
    with TestClient(gateway_app) as gateway_client:
        created = gateway_client.post(
            "/api/v1/campaigns",
            json={"title": "Unreachable Lore", "setting": "Ember Coast", "system": "5e"},
            headers=owner,
        )
        assert created.status_code == 201, created.text
        campaign_id = created.json()["id"]

        atlas = gateway_client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=owner)
        codex = gateway_client.get(f"/api/v1/campaigns/{campaign_id}/codex", headers=owner)

    assert atlas.status_code == 503
    assert codex.status_code == 503
    assert atlas.json()["upstream"] == "campaign_lore"
    assert PIN_TITLE not in atlas.text


def test_owner_403_passes_through_on_atlas_and_codex(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    owner = bearer("dm_lore_refused", issuer=trusted_ws_issuer)
    with TestClient(gateway_app) as gateway_client:
        created = gateway_client.post(
            "/api/v1/campaigns",
            json={"title": "Refused Lore", "setting": "Ember Coast", "system": "5e"},
            headers=owner,
        )
        assert created.status_code == 201, created.text
        campaign_id = created.json()["id"]

        with serve(unavailable_app(403)) as refusing_url:
            monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_LORE_URL", refusing_url)
            with TestClient(gateway_app) as refused_client:
                atlas = refused_client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=owner)
                codex = refused_client.get(f"/api/v1/campaigns/{campaign_id}/codex", headers=owner)

    assert atlas.status_code == 403
    assert codex.status_code == 403
    assert atlas.json() == {"detail": "service maintenance"}
