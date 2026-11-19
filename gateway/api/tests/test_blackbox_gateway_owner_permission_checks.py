"""Blackbox tests: a proxy route leaves its permission check to the owner (TASK-0845).

The gateway verifies the caller's token and forwards it. The owning service checks the object
permission, so a caller without the permission gets the owner's 403 through the gateway. Each
test drives the public gateway routes, and the owner runs as its real ASGI app on a loopback port.

Routes that keep a gateway check (composite reads, and the proxy routes listed in the
call-owning-services how-to guide) are covered at the end of the file.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_analytics.main import create_app_from_environment
from campaign_lore.main import app as lore_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.campaign_analytics_service import AnalyticsService
from tests.helpers.campaign_setup import create_campaign, create_owner_session
from tests.helpers.live_services import serve

STRANGER = "user_stranger_0845"
OWNER = "dm_owner_0845"
ANALYTICS_FORBIDDEN = "Forbidden: User lacks permission to view campaign analytics"
LORE_ATLAS_FORBIDDEN = (
    "Forbidden: SpiceDB Zanzibar policy denies view access to this campaign atlas."
)
LORE_PUBLISH_FORBIDDEN = "Forbidden: User cannot publish codex entries in this campaign."
LORE_PIN_FORBIDDEN = "Forbidden: User cannot place pins on this campaign atlas."
PLAYER = "player_pin_0768"
VIEWER = "viewer_pin_0768"


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


# ---------------------------------------------------------------------------
# game_session: GET session, start, turns/advance
# ---------------------------------------------------------------------------


@pytest.fixture
def session_client(game_session_upstream: str) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def owned_session(session_client, game_session_upstream, trusted_ws_issuer):
    owner = _auth(trusted_ws_issuer, OWNER)
    campaign = session_client.post("/api/v1/campaigns", json={"title": "Vault"}, headers=owner)
    assert campaign.status_code == 201, campaign.text
    session_id = create_owner_session(game_session_upstream, owner, campaign.json()["id"])
    return session_id


@pytest.mark.parametrize(
    ("method", "path_suffix", "permission"),
    [
        ("GET", "", "observe"),
        ("POST", "/start", "control"),
        ("POST", "/turns/advance", "control"),
    ],
)
def test_game_session_owner_refuses_a_stranger_through_the_gateway(
    session_client, owned_session, trusted_ws_issuer, method, path_suffix, permission
) -> None:
    """The owner answers 403 with its own detail. The gateway no longer writes that body."""
    res = session_client.request(
        method,
        f"/api/v1/sessions/{owned_session}{path_suffix}",
        headers=_auth(trusted_ws_issuer, STRANGER),
    )
    assert res.status_code == 403, res.text
    detail = res.json()["detail"]
    assert isinstance(detail, str), res.text
    assert f"lacks '{permission}'" in detail


@pytest.mark.parametrize(
    ("method", "path_suffix"),
    [
        ("GET", ""),
        ("POST", "/start"),
        ("POST", "/turns/advance"),
        ("GET", "/events"),
        ("GET", "/absentee-recap"),
    ],
)
def test_missing_token_is_refused_at_the_gateway(session_client, method, path_suffix) -> None:
    res = session_client.request(method, f"/api/v1/sessions/{uuid4()}{path_suffix}")
    assert res.status_code == 401, res.text


@pytest.mark.parametrize("path_suffix", ["/events", "/absentee-recap"])
def test_chronicle_reads_keep_the_gateway_check_and_hide_session_existence(
    session_client, owned_session, trusted_ws_issuer, path_suffix
) -> None:
    """game_session answers 404 for an unknown session before it checks `observe`.

    The gateway keeps its check on these two routes. A stranger gets the same 403 for a session
    that exists and for one that does not, so the 403 reveals no session id.
    """
    stranger = _auth(trusted_ws_issuer, STRANGER)
    known = session_client.get(f"/api/v1/sessions/{owned_session}{path_suffix}", headers=stranger)
    unknown = session_client.get(f"/api/v1/sessions/{uuid4()}{path_suffix}", headers=stranger)
    assert known.status_code == 403, known.text
    assert unknown.status_code == 403, unknown.text
    assert known.json()["detail"]["error"] == "permission_denied"
    assert unknown.json()["detail"]["error"] == "permission_denied"


# ---------------------------------------------------------------------------
# character_sheet: spells, guardrails, health, equipment, inventory, conditions
# ---------------------------------------------------------------------------


CHARACTER_ROUTES = [
    ("POST", "/spells/cast", {"spellName": "Magic Missile", "slotLevel": 1}),
    ("POST", "/spells/prepare", {"spellName": "Magic Missile", "spellLevel": 1}),
    ("PUT", "/guardrails", {"risk_threshold": "cautious"}),
    ("GET", "/guardrails", None),
    ("POST", "/health", {"delta": -1, "source": "damage"}),
    ("POST", "/equipment", {"slot": "main_hand", "itemName": "Sword"}),
    ("DELETE", "/equipment/main_hand", None),
    ("POST", "/inventory", {"name": "Rope"}),
    ("DELETE", "/inventory/rope-1", None),
    ("POST", "/conditions", {"condition": "prone"}),
    ("DELETE", "/conditions/prone", None),
]


@pytest.fixture
def character_client(character_sheet_upstream, game_session_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def owned_character(character_client, trusted_ws_issuer) -> str:
    res = character_client.post(
        "/api/v1/characters",
        json={"name": "Warden", "characterClass": "Fighter", "maxHp": 20},
        headers=_auth(trusted_ws_issuer, OWNER),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.parametrize(("method", "suffix", "body"), CHARACTER_ROUTES)
def test_character_owner_refuses_a_stranger_through_the_gateway(
    character_client, owned_character, trusted_ws_issuer, method, suffix, body
) -> None:
    res = character_client.request(
        method,
        f"/api/v1/characters/{owned_character}{suffix}",
        json=body,
        headers=_auth(trusted_ws_issuer, STRANGER),
    )
    assert res.status_code == 403, res.text


@pytest.mark.parametrize(("method", "suffix", "body"), CHARACTER_ROUTES)
def test_character_route_without_a_token_is_refused_at_the_gateway(
    character_client, method, suffix, body
) -> None:
    res = character_client.request(method, f"/api/v1/characters/{uuid4()}{suffix}", json=body)
    assert res.status_code == 401, res.text


# ---------------------------------------------------------------------------
# campaign_analytics: heatmap, mvp, timeline (owner checks `view`)
# ---------------------------------------------------------------------------


@pytest.fixture
def analytics_campaign(
    analytics_service: AnalyticsService, monkeypatch, game_session_upstream
) -> Iterator[tuple[TestClient, str]]:
    with serve(create_app_from_environment(), lifespan="on") as url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_ANALYTICS_URL", url)
        with TestClient(gateway_app) as gateway_client:
            cid = create_campaign(gateway_client, OWNER)
            analytics_service.grant_view(cid, OWNER)
            yield gateway_client, cid


@pytest.mark.parametrize("suffix", ["heatmap", "mvp", "timeline"])
def test_analytics_owner_refuses_a_stranger_through_the_gateway(
    analytics_campaign, trusted_ws_issuer, suffix
) -> None:
    client, cid = analytics_campaign
    res = client.get(
        f"/api/v1/analytics/campaigns/{cid}/{suffix}",
        headers=_auth(trusted_ws_issuer, STRANGER),
    )
    assert res.status_code == 403, res.text
    assert res.json() == {"detail": ANALYTICS_FORBIDDEN}


# ---------------------------------------------------------------------------
# campaign_lore: atlas read, codex read, codex publish (owner checks view, view, play)
# ---------------------------------------------------------------------------


@pytest.fixture
def lore_campaign(
    lore_backends, game_session_upstream, trusted_ws_issuer, monkeypatch
) -> Iterator[tuple[TestClient, str]]:
    with serve(lore_app, lifespan="on") as lore_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_LORE_URL", lore_url)
        with TestClient(gateway_app) as gateway_client:
            created = gateway_client.post(
                "/api/v1/campaigns",
                json={"title": "Ashes Campaign", "setting": "Ember Coast", "system": "5e"},
                headers=_auth(trusted_ws_issuer, OWNER),
            )
            assert created.status_code == 201, created.text
            yield gateway_client, created.json()["id"]


def test_lore_atlas_owner_refuses_a_stranger_through_the_gateway(
    lore_campaign, trusted_ws_issuer
) -> None:
    client, cid = lore_campaign
    res = client.get(f"/api/v1/campaigns/{cid}/atlas", headers=_auth(trusted_ws_issuer, STRANGER))
    assert res.status_code == 403, res.text
    assert res.json() == {"detail": LORE_ATLAS_FORBIDDEN}


def test_lore_codex_publish_owner_refuses_a_stranger_through_the_gateway(
    lore_campaign, trusted_ws_issuer
) -> None:
    client, cid = lore_campaign
    res = client.post(
        f"/api/v1/campaigns/{cid}/codex/entries",
        json={"title": "Stolen", "content": "Not yours.", "privacy": "party_shared"},
        headers=_auth(trusted_ws_issuer, STRANGER),
    )
    assert res.status_code == 403, res.text
    assert res.json() == {"detail": LORE_PUBLISH_FORBIDDEN}


def _invite_member(client, cid, trusted_ws_issuer, role: str, member: str) -> dict[str, str]:
    """The owner issues an invite for `role`, and `member` redeems it through the gateway."""
    invite = client.post(
        f"/api/v1/campaigns/{cid}/invites",
        json={"role": role},
        headers=_auth(trusted_ws_issuer, OWNER),
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=_auth(trusted_ws_issuer, member),
    )
    assert joined.status_code == 200, joined.text
    return _auth(trusted_ws_issuer, member)


def test_lore_atlas_pin_player_places_a_pin_through_the_gateway(
    lore_campaign, trusted_ws_issuer
) -> None:
    """A player holds `play` but not `run_session`. The gateway forwards, the owner allows."""
    client, cid = lore_campaign
    player = _invite_member(client, cid, trusted_ws_issuer, "player", PLAYER)
    res = client.post(
        f"/api/v1/campaigns/{cid}/atlas/pins",
        json={"title": "Player Gate", "coordinates": {"x": 1.0, "y": 2.0}},
        headers=player,
    )
    assert res.status_code == 201, res.text
    assert res.json()["title"] == "Player Gate"
    atlas = client.get(f"/api/v1/campaigns/{cid}/atlas", headers=player)
    assert atlas.status_code == 200, atlas.text
    assert "Player Gate" in [pin["title"] for pin in atlas.json()["pins"]]


def test_lore_atlas_pin_viewer_is_refused_by_the_owner_through_the_gateway(
    lore_campaign, trusted_ws_issuer
) -> None:
    """A spectator holds `view` only. The gateway passes the owner's 403 through unchanged."""
    client, cid = lore_campaign
    viewer = _invite_member(client, cid, trusted_ws_issuer, "spectator", VIEWER)
    res = client.post(
        f"/api/v1/campaigns/{cid}/atlas/pins",
        json={"title": "Viewer Gate", "coordinates": {"x": 1.0, "y": 2.0}},
        headers=viewer,
    )
    assert res.status_code == 403, res.text
    assert res.json() == {"detail": LORE_PIN_FORBIDDEN}
    atlas = client.get(f"/api/v1/campaigns/{cid}/atlas", headers=viewer)
    assert "Viewer Gate" not in [pin["title"] for pin in atlas.json()["pins"]]
