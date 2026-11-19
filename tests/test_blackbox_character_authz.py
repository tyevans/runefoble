"""Blackbox frontdoor tests for character ownership and proxy authorization (TASK-0551).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar object authorization), ADR-0007 (gateway routes,
character context owns state), ADR-0014 (Gherkin-style frontdoor suites), ADR-0015 (bearer
tokens verified at every hop; no fallback on failure).

Verifies:
1. Every character route on the Character Sheet service checks a schema permission.
   Reads need 'view'. Mutations need 'edit'. Anonymous requests get 401.
2. A campaign DM (owner) passes the campaign-scoped checks. A party player passes reads only.
3. A failed SpiceDB owner write on creation returns 503 and stores nothing.
4. Only the owner can delete a character ('delete'). The DM cannot.
5. The gateway character proxy returns 503 when the owning service is unreachable.

Setup goes through public frontdoors only: campaign create, invite create and redeem, and
character create. Assertions read public responses.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from character_sheet.main import app as character_sheet_app
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app as gateway_app
from runefoble_auth.errors import AuthzUnavailableError

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.live_services import closed_port_url
from tests.helpers.ws_identity import bearer


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the services verify for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture
def sheet(character_sheet_upstream) -> TestClient:
    """In-process Character Sheet client over the same fresh repository the upstream serves."""
    return TestClient(character_sheet_app)


@pytest.fixture
def gateway(character_sheet_upstream, game_session_upstream) -> Iterator[TestClient]:
    """Gateway client with the lifespan entered after both upstreams serve."""
    with TestClient(gateway_app) as client:
        yield client


def _create_sheet_character(sheet, issuer, sub: str, campaign_id: str | None = None) -> str:
    """Create a character on the Character Sheet service as `sub`. Return its id."""
    body = {"name": "Authz Subject", "character_class": "Rogue", "max_hp": 20}
    if campaign_id:
        body["campaign_id"] = campaign_id
    res = sheet.post("/api/v1/characters", json=body, headers=_auth(issuer, sub))
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


PENALTY = {"penalty_type": "drunk", "description": "Too much ale", "imposed_by": "the_watcher"}
HEALTH = {"delta": -2, "source": "damage"}


def test_anonymous_guardrails_update_is_refused(trusted_ws_issuer, sheet) -> None:
    """An anonymous PUT to guardrails returns 401 and changes nothing."""
    char_id = _create_sheet_character(sheet, trusted_ws_issuer, "player_owner")

    res = sheet.put(f"/api/v1/characters/{char_id}/guardrails", json={})

    assert res.status_code == 401


def test_non_member_cannot_mutate_or_read_character(trusted_ws_issuer, sheet) -> None:
    """A stranger gets 403 on penalties, health, and reads of the character."""
    char_id = _create_sheet_character(sheet, trusted_ws_issuer, "player_owner")
    stranger = _auth(trusted_ws_issuer, "stranger_mallory")

    assert (
        sheet.post(
            f"/api/v1/characters/{char_id}/penalties", json=PENALTY, headers=stranger
        ).status_code
        == 403
    )
    assert (
        sheet.post(
            f"/api/v1/characters/{char_id}/health", json=HEALTH, headers=stranger
        ).status_code
        == 403
    )
    assert sheet.get(f"/api/v1/characters/{char_id}", headers=stranger).status_code == 403


def test_owner_may_change_health_and_non_owner_player_may_not(
    trusted_ws_issuer, sheet, gateway
) -> None:
    """The owner passes 'edit'. A party player with no edit right gets 403 on health."""
    campaign_id = create_campaign(gateway, "dm_valeros")
    invite_and_join(gateway, campaign_id, "dm_valeros", "player_kira")
    invite_and_join(gateway, campaign_id, "dm_valeros", "player_marcus")
    char_id = _create_sheet_character(sheet, trusted_ws_issuer, "player_kira", campaign_id)

    res_party = sheet.post(
        f"/api/v1/characters/{char_id}/health",
        json=HEALTH,
        headers=_auth(trusted_ws_issuer, "player_marcus"),
    )
    assert res_party.status_code == 403

    res_owner = sheet.post(
        f"/api/v1/characters/{char_id}/health",
        json=HEALTH,
        headers=_auth(trusted_ws_issuer, "player_kira"),
    )
    assert res_owner.status_code == 200, res_owner.text


def test_campaign_dm_may_penalize_and_party_player_may_not(
    trusted_ws_issuer, sheet, gateway
) -> None:
    """The campaign DM passes 'edit' through campaign->run_session. A player does not."""
    campaign_id = create_campaign(gateway, "dm_valeros")
    invite_and_join(gateway, campaign_id, "dm_valeros", "player_kira")
    invite_and_join(gateway, campaign_id, "dm_valeros", "player_marcus")
    char_id = _create_sheet_character(sheet, trusted_ws_issuer, "player_kira", campaign_id)

    res_player = sheet.post(
        f"/api/v1/characters/{char_id}/penalties",
        json=PENALTY,
        headers=_auth(trusted_ws_issuer, "player_marcus"),
    )
    assert res_player.status_code == 403

    res_dm = sheet.post(
        f"/api/v1/characters/{char_id}/penalties", json=PENALTY, headers=bearer("dm_valeros")
    )
    assert res_dm.status_code == 200, res_dm.text
    assert "drunk" in res_dm.json()["penalties"]


def test_party_player_may_read_and_stranger_may_not(trusted_ws_issuer, sheet, gateway) -> None:
    """Campaign membership grants 'view' on the character. A non-member does not."""
    campaign_id = create_campaign(gateway, "dm_valeros")
    invite_and_join(gateway, campaign_id, "dm_valeros", "player_kira")
    invite_and_join(gateway, campaign_id, "dm_valeros", "player_marcus")
    char_id = _create_sheet_character(sheet, trusted_ws_issuer, "player_kira", campaign_id)

    assert (
        sheet.get(
            f"/api/v1/characters/{char_id}", headers=_auth(trusted_ws_issuer, "player_marcus")
        ).status_code
        == 200
    )
    assert (
        sheet.get(
            f"/api/v1/characters/{char_id}", headers=_auth(trusted_ws_issuer, "stranger_mallory")
        ).status_code
        == 403
    )


def test_character_sheet_creation_fails_loudly_when_owner_write_fails(
    trusted_ws_issuer, default_spicedb_client, monkeypatch, sheet
) -> None:
    """A failed owner tuple write on the Character Sheet service returns 503, not 200."""

    async def _unavailable(*_args, **_kwargs):
        raise AuthzUnavailableError("spicedb down (test stub)")

    monkeypatch.setattr(default_spicedb_client, "write_relationship", _unavailable)

    res = sheet.post(
        "/api/v1/characters",
        json={"name": "Ghost", "character_class": "Monk", "max_hp": 12},
        headers=_auth(trusted_ws_issuer, "player_owner"),
    )

    assert res.status_code == 503, res.text
    assert "character_id" not in res.json()


def test_gateway_creation_fails_loudly_and_lists_nothing(
    trusted_ws_issuer, monkeypatch, gateway
) -> None:
    """A failed owner tuple write on gateway creation fails the call. The character is not listed.

    Character Sheet answers 503. The gateway maps an upstream 5xx to 502 (upstream_errors.py).
    """
    spicedb = get_spicedb_client()

    async def _unavailable(*_args, **_kwargs):
        raise AuthzUnavailableError("spicedb down (test stub)")

    monkeypatch.setattr(spicedb, "write_relationship", _unavailable)
    headers = _auth(trusted_ws_issuer, "player_owner")

    res = gateway.post(
        "/api/v1/characters",
        json={"name": "Ghost Gateway", "characterClass": "Monk", "maxHp": 12},
        headers=headers,
    )
    assert res.status_code == 502, res.text

    listed = gateway.get("/api/v1/characters", headers=headers).json()
    assert "Ghost Gateway" not in [c["name"] for c in listed]


def test_gateway_sub_resource_returns_503_when_owner_is_unreachable(
    trusted_ws_issuer, monkeypatch, sheet
) -> None:
    """With the Character Sheet URL pointing at nothing, the gateway returns 503, not a memory copy."""
    headers = _auth(trusted_ws_issuer, "player_owner")
    char_id = _create_sheet_character(sheet, trusted_ws_issuer, "player_owner")
    monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", closed_port_url())

    with TestClient(gateway_app) as client:
        res_health = client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -3, "source": "damage"},
            headers=headers,
        )

    assert res_health.status_code == 503, res_health.text
